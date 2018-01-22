# import dependencies
from mpd import MPDProtocol
import os
import traceback
import mutagen
import io
import random
import ConfigParser
from pkg_resources import resource_filename

# make sure we are on an updated version of kivy
import kivy
kivy.require('1.10.0')

#install twisted reactor to interface with mpd
from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor, protocol
from twisted.internet.defer import inlineCallbacks

# import all the other kivy stuff
from kivy.config import Config
from kivy.app import App
from kivy.logger import Logger
from kivy.graphics import Color,Rectangle
from kivy.core.image import Image as CoreImage
from kivy.metrics import Metrics, sp
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image,AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.slider import Slider
from kivy.factory import Factory
from kivy.lang import Builder

# import our local modules
from mpdfactory import MPDClientFactory
from extra import KmpcHelpers,ExtraSlider,ClearButton
from playlistpanel import PlaylistTabbedPanelItem

# sets the location of the config folder
configdir = os.path.join(os.path.expanduser('~'),".kmpc")

# load the interface.kv file
Builder.load_file(resource_filename(__name__,os.path.join('resources','interface.kv')))

Helpers=KmpcHelpers()

class KmpcInterface(TabbedPanel):
    """The main class that ties it all together."""

    def __init__(self):
        """Pull the config from the config file, hook up to mpd, zero out variables."""
        super(self.__class__,self).__init__()
        # pull config into the class
        self.config = Helpers.loadconfigfile()
        # set up mpd connection
        self.factory = MPDClientFactory()
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        reactor.connectTCP(self.config.get('mpd','mpdhost'), self.config.getint('mpd','mpdport'), self.factory)
        # bind callbacks for tab changes
        self.bind(current_tab=self.main_tab_changed)
        self.mpd_status={'state':'stop','repeat':0,'single':0,'random':0,'consume':0,'curpos':0}
        self.currsong=None
        self.nextsong=None
        self.currfile=None
        self.track_slider_task=None
        self.accessoryPopup=Factory.AccessoryPopup()

    def mpd_connectionMade(self,protocol):
        """Callback when mpd is connected."""
        # copy the protocol to all the classes
        self.protocol = protocol
        self.ids.playlist_tab.protocol=protocol
        self.ids.library_tab.protocol=protocol
        self.ids.config_tab.protocol=protocol
        Logger.info('Application: Connected to mpd server host='+self.config.get('mpd','mpdhost')+' port='+self.config.get('mpd','mpdport'))
        # get the initial mpd status
        self.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)
        # create the once-per-second update of the track slider
        self.track_slider_task=Clock.schedule_interval(self.update_track_slider,1)
        self.track_slider_task.cancel()
        # subscribe to 'kmpc' to check for messages from mpd
        self.protocol.subscribe('kmpc')

    def main_tab_changed(self,obj,value):
        """Callback when top tab is changed."""
        self.active_tab = value.text
        Logger.info("Application: Changed active tab to "+self.active_tab)
        if self.active_tab == 'Now Playing':
            pass
        elif self.active_tab == 'Playlist':
            pass
            # switching to the playlist tab repopulates it if it is empty
            # this is skipped right now by the 'pass' above, I can't remember why, I think it's handled a different way now
            if len(self.ids.playlist_tab.rv.data) == 0:
                self.protocol.playlistinfo().addCallback(self.ids.playlist_tab.populate_playlist).addErrback(self.ids.playlist_tab.handle_mpd_error)
        elif self.active_tab == 'Config':
            # switching to the config tab repopulates options
            self.protocol.status().addCallback(self.ids.config_tab.update_mpd_status).addErrback(self.ids.config_tab.handle_mpd_error)

    def mpd_connectionLost(self,protocol, reason):
        """Callback when mpd connection is lost."""
        Logger.warn('Application: Connection lost: %s' % reason)
        # kills the app for now since I don't know how to handle this yet
        App.get_running_app().stop()

    def handle_mpd_error(self,result):
        """Prints handled errors to the error log."""
        Logger.error('Application: MPDIdleHandler Callback error: {}'.format(result))

    def handle_mpd_message(self,result):
        """Callback for mpd 'kmpc' messages."""
        # result is an iterator although it only generally has one member
        for m in result:
            message = m['message']
            Logger.info("Application: MPD Message: "+message)
            if message == 'AccessoryOff':
                # generated by mausberry circuit, accessory power is off
                self.accessoryPopup.open()
            elif message == 'AccessoryOn':
                # generated by mausberry circuit, accessory power is on
                self.accessoryPopup.dismiss()

    def current_track_slider_release(self):
        """Callback when track slider is released."""
        # get the value of the track slider
        curpos = int(self.ids.current_track_slider.value)
        Logger.debug("Application: touch up on track slider at "+str(curpos))
        # seek to that position in the track
        self.protocol.seekcur(str(curpos)).addErrback(self.handle_mpd_error)

    def current_track_slider_down(self):
        """Callback when track slider is pressed."""
        Logger.debug("Application: touch down on track slider")
        # cancel the once-per-second update while finger is down so it doesn't move out from under it
        self.track_slider_task.cancel()

    def update_track_slider(self,dt):
        """Increment the slider by 1 second every second."""
        Logger.debug("Application: update_track_slider")
        curpos=int(self.ids.current_track_slider.value)+1
        self.ids.current_track_slider.value=curpos

    def stop_zero_stuff(self):
        """Clear the screen and variables if playback is fully stopped."""
        self.ids.current_track_slider.value=0
        self.ids.current_track_slider.max=0
        self.ids.current_playlist_track_number_label.text=''
        self.ids.next_song_artist_label.text = ''
        self.currfile = None
        self.currsong = None
        self.nextsong = None
        self.ids.song_star_layout.clear_widgets()
        self.ids.album_cover_layout.clear_widgets()
        self.ids.trackinfo.clear_widgets()
        lbl = Label(text="Playback Stopped")
        self.ids.trackinfo.add_widget(lbl)
        self.ids.player.canvas.before.add(Rectangle(source=resource_filename(__name__,os.path.join("resources","backdrop.png")),size=self.ids.player.size,pos=self.ids.player.pos))

    def update_mpd_status(self,result):
        """Callback when mpd status changes."""
        Logger.debug('NowPlaying: update_mpd_status()')
        # probably state is the only one necessary, but hey
        self.mpd_status['state']=result['state']
        self.mpd_status['repeat']=result['repeat']
        self.mpd_status['single']=result['single']
        self.mpd_status['random']=result['random']
        self.mpd_status['consume']=result['consume']
        if self.mpd_status['state'] == 'stop':
            # if stopped, there are no current or next songs
            self.currsong=None
            self.nextsong=None
        else:
            # save current song, this is a 0-based index into the playlist
            self.currsong=result['song']
            # ask mpd for current song data
            self.protocol.currentsong().addCallback(self.update_mpd_currentsong).addErrback(self.handle_mpd_error)
            # save next song, this is a 0-based index into the playlist
            if 'nextsong' in result:
                self.nextsong=result['nextsong']
                # ask mpd for next song data
                self.protocol.playlistinfo(self.nextsong).addCallback(self.update_mpd_nextsong).addErrback(self.handle_mpd_error)
            else:
                self.nextsong=None
        stflags=['normal','down']
        # check various flag states
        self.ids.repeat_button.state=stflags[int(self.mpd_status['repeat'])]
        self.ids.single_button.state=stflags[int(self.mpd_status['single'])]
        self.ids.random_button.state=stflags[int(self.mpd_status['random'])]
        self.ids.consume_button.state=stflags[int(self.mpd_status['consume'])]
        if self.mpd_status['state']=='pause' or self.mpd_status['state']=='stop':
            # play/pause button should be a play button that is unpressed
            self.ids.play_button.state='normal'
            self.ids.play_button.text=u"\uf04b"
            self.track_slider_task.cancel()
        else:
            # play/pause button should be a pause button that is pressed
            self.ids.play_button.state='down'
            self.ids.play_button.text=u"\uf04c"
        if self.mpd_status['state'] == 'stop':
            # zero everything out if we are stopped
            self.stop_zero_stuff()
        else:
            # mpd returns {elapsed seconds}:{total seconds}, the following splits each to minute:second
            c,t=result['time'].split(":")
            # set the max slider value to the total seconds
            self.ids.current_track_slider.max = int(t)
            # set the current slider value to the current seconds
            self.mpd_status['curpos']=int(c)
            self.ids.current_track_slider.value = int(c)
            if self.mpd_status['state']!='pause':
                self.track_slider_task()
            # throws an exception if i don't do this
            a=int(result['song'])+1
            b=int(result['playlistlength'])
            self.ids.current_playlist_track_number_label.text = "%d of %d" % (a,b)
        # update the playlist tab with status results
        self.ids.playlist_tab.update_mpd_status(result)
        # update the config tab with status results
        self.ids.config_tab.update_mpd_status(result)

    def update_mpd_currentsong(self,result):
        """Callback for mpd currentsong data."""
        Logger.debug('NowPlaying: update_mpd_currentsong()')
        # this is so expensive screen updates only happen if the song has changed since the last time this callback was called
        songchange=False
        # ti is the track info widget
        ti=self.ids.trackinfo
        # if result is undefined, there's not actually a song playing
        if result:
            # if class's current file doesn't match what mpd returns, the song has changed
            if self.currfile != result['file']:
                songchange=True
            # update class's current file
            self.currfile = result['file']
            if songchange:
                # clear the track info widget
                ti.clear_widgets()
                # clear the album cover
                self.ids.album_cover_layout.clear_widgets()
                # get the stored star rating
                self.protocol.sticker_get('song',self.currfile,'rating').addCallback(self.update_mpd_sticker_rating).addErrback(self.handle_mpd_no_sticker)
                # figure out the full path of the file
                bp=self.config.get('paths','musicpath')
                # p is the absolute path
                p=os.path.join(bp,result['file'])
                haslogo=False
                # set the release year if mpd has it
                year=None
                if 'date' in result:
                    year=result['date'][:4]
                # pull the fanart folder from ini file
                fa_path=self.config.get('paths','fanartpath')
                # try to get the artistid, set it to 0000 if it doesn't exist
                try:
                    aids=str(result['musicbrainz_artistid'])
                except KeyError:
                    aids='0000'
                # if a track has multiple artists, split it up
                artistids=aids.split('/')
                # create a widget to hold the cover art
                cbl = BoxLayout(size_hint=(1,1),orientation='horizontal')
                # loop through artistids
                for mb_aid in artistids:
                    # try to find a logo for this artist in the fanart folder
                    try:
                        # look in the 'logo' subfolder of the artistid path
                        al_path=os.path.join(fa_path,mb_aid,'logo')
                        # pick one at random
                        img_path=os.path.join(al_path,random.choice(os.listdir(al_path)))
                        if os.path.isfile(img_path):
                            # create an image button out of the logo so you can press it
                            img = ImageButton(source=os.path.join(al_path,img_path),allow_stretch=True,color=(1,1,1,0.65))
                            cbl.add_widget(img)
                            haslogo=True
                    except:
                        pass
                if haslogo:
                    # we found a logo, show it
                    current_artist_label = cbl
                else:
                    # no logo found, just print the artist name instead
                    current_artist_label = InfoLargeLabel(text = result['artist'],font_size=Helpers.getfontsize(result['artist']))
                # clear the background of the player canvas so we can show the artist background
                self.ids.player.canvas.before.clear()
                # pick an artistid at random for the background
                mb_aid=random.choice(artistids)
                try:
                    # look in the 'artistbackground' subfolder of the artistid path
                    ab_path=os.path.join(fa_path,mb_aid,'artistbackground')
                    # pick one at random
                    img_path=random.choice(os.listdir(ab_path))
                    # update the player background with the image
                    self.ids.player.canvas.before.add(Rectangle(source=os.path.join(ab_path,img_path),size=self.ids.player.size,pos=self.ids.player.pos))
                except:
                    # update the player background with the default backdrop
                    self.ids.player.canvas.before.add(Rectangle(source=resource_filename(__name__,os.path.join("resources","backdrop.png")),size=self.ids.player.size,pos=self.ids.player.pos))
                if os.path.isfile(p):
                    Logger.debug('NowPlaying: found good file at path '+p)
                    # load up the file to read the tags
                    f = mutagen.File(p)
                    cimg = None
                    data = None
                    # if the original year mp3 tag exists use it instead of mpd's year
                    # I prefer this year to be displayed, rather than the year an album was remastered
                    if 'TXXX:originalyear' in f.keys():
                        year=format(f['TXXX:originalyear'])
                    # try to get mp3 cover, if this throws an exception it's not an mp3 or it doesn't have a cover
                    try:
                        pframes = f.tags.getall("APIC")
                        # id3v2 can store any number of image frames, we just want the first one
                        for frame in pframes:
                            ext = 'img'
                            # figure out the file type
                            if frame.mime.endswith('jpeg') or frame.mime.endswith('jpg'):
                                ext = 'jpg'
                            elif frame.mime.endswith('png'):
                                ext = 'png'
                            elif frame.mime.endswith('bmp'):
                                ext = 'bmp'
                            elif frame.mime.endswith('gif'):
                                ext = 'gif'
                            # pull the raw image data into a variable
                            data=io.BytesIO(bytearray(frame.data))
                            break
                    except AttributeError:
                        pass
                    # try to get mp4 cover
                    if 'covr' in f.keys():
                        # figure out the file type
                        if f['covr'][0].imageformat == mutagen.mp4.MP4Cover.FORMAT_PNG:
                            ext = 'png'
                        else:
                            ext = 'jpg'
                        # pull the raw image data into a variable
                        data=io.BytesIO(bytearray(f['covr'][0]))
                    if data:
                        # if we got image data, load it as a kivy.core.image
                        cimg = CoreImage(data,ext=ext)
                    if cimg:
                        # if the image loading worked, create an image widget and fix up the layout
                        # TODO: sometimes this just returns a black rectangle, i think i need to catch more specific exceptions
                        # and figure out what exactly is happening
                        img=ImageButton(texture=cimg.texture,allow_stretch=True)
                        self.ids.album_cover_layout.add_widget(img)
                        # popup the cover large if you press it
                        img.bind(on_press=self.cover_popup)
                else:
                    # this should _probably_ never happen
                    Logger.debug('NowPlaying: no file found at path '+p)
                # add the correct artist name widget
                ti.add_widget(current_artist_label)
                # if we got a year tag from somewhere, include it in the album label
                if year:
                    yeartext = result['album']+' ['+year+']'
                else:
                    yeartext = result['album']
                if haslogo:
                    # we found an artist logo, put the song and album labels in a separate boxlayout to separate them a bit
                    lyt = BoxLayout(orientation='vertical',padding_y='10sp')
                    current_song_label = InfoLargeLabel(text = result['title'],font_size=Helpers.getfontsize(result['title']))
                    lyt.add_widget(current_song_label)
                    current_album_label = InfoLargeLabel(text = yeartext,font_size=Helpers.getfontsize(yeartext))
                    lyt.add_widget(current_album_label)
                    ti.add_widget(lyt)
                else:
                    # no artist logo, just add the song and album labels directly to the track info widget
                    current_song_label = InfoLargeLabel(text = result['title'],font_size=Helpers.getfontsize(result['title']))
                    ti.add_widget(current_song_label)
                    current_album_label = InfoLargeLabel(text = yeartext,font_size=Helpers.getfontsize(yeartext))
                    ti.add_widget(current_album_label)
        else:
            # there's not a current song, so zero everything out
            self.stop_zero_stuff()

    def update_mpd_sticker_rating(self,result):
        """Callback for song that has a rating in mpd."""
        Logger.debug('NowPlaying: update_mpd_sticker_rating')
        # make a clear button for the star rating
        btn = ClearButton(padding_x='10sp',font_name=resource_filename(__name__,os.path.join('resources','FontAwesome.ttf')),halign='center',valign='middle',markup=True)
        # look up the correct string for the rating
        btn.text = Helpers.songratings(self.config)[result]['stars']
        # bind the popup for setting rating
        btn.bind(on_press=self.rating_popup)
        # clear the layout widget and add the new one
        self.ids.song_star_layout.clear_widgets()
        self.ids.song_star_layout.add_widget(btn)

    def handle_mpd_no_sticker(self,result):
        """Callback for song that has no rating in mpd."""
        Logger.debug('NowPlaying: handle_mpd_no_sticker')
        # make a clear button for the star rating
        btn = ClearButton(padding_x='10sp',font_name=resource_filename(__name__,os.path.join('resources','FontAwesome.ttf')),halign='center',valign='middle',markup=True)
        # set the string to the circled question mark icon
        btn.text = u"\uf29c"
        # bind the popup for setting rating
        btn.bind(on_press=self.rating_popup)
        # clear the layout widget and add the new one
        self.ids.song_star_layout.clear_widgets()
        self.ids.song_star_layout.add_widget(btn)

    def update_mpd_nextsong(self,result):
        """Callback for next song data from mpd."""
        Logger.debug('NowPlaying: update_mpd_nextsong()')
        # result is a list with one member
        for obj in result:
            # set the next song label
            self.ids.next_song_artist_label.text = 'Up Next: '+obj['artist']+' - '+obj['title']

    def prev_pressed(self):
        """Callback for prev button pressed."""
        Logger.debug('Application: prev_pressed()')
        self.protocol.previous()

    def play_pressed(self):
        """Callback for play/pause button pressed."""
        Logger.debug('Application: play_pressed()')
        if self.mpd_status['state'] == 'play':
            # pause if playing
            self.protocol.pause()
        else:
            # play if paused or stopped
            self.protocol.play()

    def next_pressed(self):
        """Callback for next button pressed."""
        Logger.debug('Application: next_pressed()')
        self.protocol.next()

    def repeat_pressed(self):
        """Callback for repeat button pressed."""
        Logger.debug('Application: repeat_pressed()')
        # toggle on/off
        self.protocol.repeat(str(1-int(self.mpd_status['repeat'])))

    def single_pressed(self):
        """Callback for single button pressed."""
        Logger.debug('Application: single_pressed()')
        # toggle on/off
        self.protocol.single(str(1-int(self.mpd_status['single'])))

    def random_pressed(self):
        """Callback for random button pressed."""
        Logger.debug('Application: random_pressed()')
        # toggle on/off
        self.protocol.random(str(1-int(self.mpd_status['random'])))

    def consume_pressed(self):
        """Callback for consume button pressed."""
        Logger.debug('Application: consume_pressed()')
        # toggle on/off
        self.protocol.consume(str(1-int(self.mpd_status['consume'])))

    def rating_popup(self,instance):
        """Popup for setting song rating."""
        Logger.debug('Application: rating_popup()')
        # create a layout and add it to the popup
        layout = GridLayout(cols=2,spacing=10)
        popup = Popup(title='Rating',content=layout,size_hint=(0.8,1))
        # loop from 0-10
        for r in list(range(0,11)):
            # make a button
            btn=Button(font_name=resource_filename(__name__,os.path.join('resources','FontAwesome.ttf')))
            # look up the correct string for the rating
            btn.text=Helpers.songratings(self.config)[str(r)]['stars']
            # set some widget variables
            btn.rating=str(r)
            btn.popup=popup
            # add the button to the layout
            layout.add_widget(btn)
            # bind the button press to set the rating
            btn.bind(on_press=self.rating_set)
            # add a label to explain the ratings, this is pretty subjective
            lbl=Label(text=Helpers.songratings(self.config)[str(r)]['meaning'],halign='left')
            # add the label to the layout
            layout.add_widget(lbl)
        # pop it on up, if you press outside the popup it just goes away without setting the rating
        popup.open()

    def rating_set(self,instance):
        """Method that sets a song's rating."""
        Logger.debug('Application: rating_set('+instance.rating+')')
        # close the rating popup
        instance.popup.dismiss()
        # tell mpd to set the rating sticker
        self.protocol.sticker_set('song',self.currfile,'rating',instance.rating)

    def cover_popup(self,instance):
        """Popup for showing a larger version of the album cover."""
        Logger.debug('Application: cover_popup()')
        layout = BoxLayout()
        popup = Popup(title='Cover',content=layout,size_hint=(0.6,1))
        # pull the already loaded image texture
        img = Image(texture=instance.texture,allow_stretch=True)
        # add it to the layout
        layout.add_widget(img)
        # pop pop pop
        popup.open()

    def change_backlight(self,value):
        """Method that sets the backlight to a certain value."""
        Logger.info('Application: change_backlight('+str(value)+') rpienable = '+self.config.get('flags','rpienable'))
        # only if the ini file says it's ok
        if self.config.getboolean('flags','rpienable'):
            import rpi_backlight as bl
            # set the brightness
            bl.set_brightness(int(value), smooth=True, duration=1)

class KmpcApp(App):
    """The overall app class, builds the main interface widget."""

    def __init__(self,args):
        """Override kivy config values with necessary ones."""
        Config.set('kivy','keyboard_mode','systemanddock')
        Config.set('graphics','width',800)
        Config.set('graphics','height',480)
        super(self.__class__,self).__init__()

    def build(self):
        """Instantiates KmpcInterface."""
        # setup some variables that interface.kv will use
        # this is necessary to support packaging the app
        self.normalfont = resource_filename(__name__,os.path.join('resources','DejaVuSans.ttf'))
        self.boldfont = resource_filename(__name__,os.path.join('resources','DejaVuSans-Bold.ttf'))
        self.fontawesomefont = resource_filename(__name__,os.path.join('resources','FontAwesome.ttf'))
        self.buttonnormal = resource_filename(__name__,os.path.join('resources','button-normal.png'))
        self.buttondown = resource_filename(__name__,os.path.join('resources','button-down.png'))
        self.clear = resource_filename(__name__,os.path.join('resources','clear.png'))
        self.backdrop = resource_filename(__name__,os.path.join('resources','backdrop.png'))
        self.listbackdrop = resource_filename(__name__,os.path.join('resources','list-backdrop.png'))
        self.listbackdropselected = resource_filename(__name__,os.path.join('resources','list-backdrop-selected.png'))
        self.trackslidercursor = resource_filename(__name__,os.path.join('resources','track-slider-cursor.png'))
        return KmpcInterface()

class InfoLargeLabel(Label):
    """A label with large text."""
    pass

class InfoSmallLabel(Label):
    """A label with small text."""
    pass

class ImageButton(ButtonBehavior, AsyncImage):
    """An image that you can press."""
    pass

if __name__ == '__main__':
    # run the app!
    KmpcApp().run()

