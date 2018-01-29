# import dependencies
import os
import sys
import traceback
import mutagen
import io
import random
import socket
import re
from pkg_resources import resource_filename
from functools import partial
from PIL import Image as PImage

# make sure we are on an updated version of kivy
import kivy
kivy.require('1.10.0')

# import all the other kivy stuff
from kivy.config import Config,ConfigParser
from kivy.app import App
from kivy.logger import Logger
from kivy.graphics import Color,Rectangle
from kivy.core.image import Image as CoreImage
from kivy.metrics import Metrics, sp
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image,AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty,StringProperty,BooleanProperty

# import our local modules
from kmpc.extra import KmpcHelpers,ExtraSlider,ClearButton,OutlineLabel,OutlineButton,MpdConnection
from kmpc.playlistpanel import PlaylistTabbedPanelItem
from kmpc.version import VERSION_STR

# sets the location of the config folder
configdir = os.path.join(os.path.expanduser('~'),".kmpc")

# load the interface.kv file
Builder.load_file(resource_filename(__name__,os.path.join('resources','interface.kv')))

# set the maximum size for cover images, to prevent texture overloading
max_cover_size=1000

Helpers=KmpcHelpers()

class KmpcInterface(TabbedPanel):
    """The main class that ties it all together."""

    def __init__(self,config,**kwargs):
        """Zero out variables, pull in config file, connect to mpd."""
        super(self.__class__,self).__init__(**kwargs)
        # bind callbacks for tab changes
        self.bind(current_tab=self.main_tab_changed)
        self.mpd_status={'state':'stop','repeat':0,'single':0,'random':0,'consume':0,'curpos':0}
        self.currsong=None
        self.nextsong=None
        self.currfile=None
        self.track_slider_task=None
        self.accessoryPopup=Factory.AccessoryPopup()
        self.tcolor=1
        self.ocolor=0
        self.settingsPopup=Factory.SettingsPopup()
        self.config=config
        global mainmpdconnection
        mainmpdconnection=MpdConnection(self.config,self.config.get('mpd','mpdhost'),self.config.get('mpd','mpdport'),self.mpd_idle_handler,[self.init_mpd])

    def settings_popup(self):
        self.settingsPopup.open()
        # get the host's IP address and display it
        self.settingsPopup.ids.ip_label.text="IP Address: "+format(self.get_ip())
        mainmpdconnection.protocol.status().addCallback(partial(self.update_mixers,self.settingsPopup)).addErrback(self.handle_mpd_error)

    def update_mixers(self,p,result):
        # set up the crossfade slider
        if 'xfade' in result:
            v = int(result['xfade'])
        else:
            v = 0
        p.ids.crossfade_slider.value=v
        # set up the mixrampdb slider
        if 'mixrampdb' in result:
            v = round(float(result['mixrampdb']),6)
        else:
            v = 0.0
        p.ids.mixrampdb_slider.value=float(str(v)[1:])
        # set up the mixrampdelay slider
        if 'mixrampdelay' in result:
            v = round(float(result['mixrampdelay']),6)
        else:
            v = 0.0
        p.ids.mixrampdelay_slider.value=v

    def change_text_color(self,color):
        Logger.debug("NowPlaying: change_text_color to "+format(color))
        self.tcolor=color
        def _tc(widget):
            for child in widget.children:
                _tc(child)
            if issubclass(widget.__class__,OutlineLabel):
                widget.color=[color,color,color,1]
        for child in self.children:
            _tc(child)

    def change_outline_color(self,color):
        Logger.debug("NowPlaying: change_outline_color to "+format(color))
        self.ocolor=color
        def _tc(widget):
            for child in widget.children:
                _tc(child)
            if issubclass(widget.__class__,OutlineLabel):
                widget.outline_color=[color,color,color,1]
        for child in self.children:
            _tc(child)

    def change_crossfade(self,v):
        """Callback when user changes crossfade slider."""
        Logger.info('Settings: change_crossfade')
        mainmpdconnection.protocol.crossfade(str(v)).addErrback(self.handle_mpd_error)

    def change_mixrampdb(self,v):
        """Callback when user changes mixrampdb slider."""
        Logger.info('Settings: change_mixrampdb')
        mainmpdconnection.protocol.mixrampdb(str(0.0-v)).addErrback(self.handle_mpd_error)

    def change_mixrampdelay(self,v):
        """Callback when user changes mixrampdelay slider."""
        Logger.info('Settings: change_mixrampdelay')
        mainmpdconnection.protocol.mixrampdelay(str(v)).addErrback(self.handle_mpd_error)

    def get_ip(self):
        """Method that tries to get the local IP address, and returns localhost if there isn't one."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def main_tab_changed(self,obj,value):
        """Callback when top tab is changed."""
        self.active_tab = value.text
        Logger.info("Application: Changed active tab to "+self.active_tab)
        if self.active_tab != 'Now Playing':
            # pause the track slider task
            self.track_slider_task.cancel()
        else:
            # update current track status
            mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(mainmpdconnection.handle_mpd_error)
        if self.active_tab == 'Playlist':
            # switching to the playlist tab repopulates it if it is empty
            if len(self.ids.playlist_tab.rv.data) == 0:
                mainmpdconnection.protocol.playlistinfo().addCallback(self.ids.playlist_tab.populate_playlist).addErrback(self.ids.playlist_tab.handle_mpd_error)

    def handle_mpd_error(self,result):
        mainmpdconnection.handle_mpd_error(result)

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
        mainmpdconnection.protocol.seekcur(str(curpos)).addErrback(self.handle_mpd_error)

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
        lbl = OutlineLabel(text="Playback Stopped")
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
            mainmpdconnection.protocol.currentsong().addCallback(partial(self.update_mpd_currentsong,False)).addErrback(self.handle_mpd_error)
            # save next song, this is a 0-based index into the playlist
            if 'nextsong' in result:
                self.nextsong=result['nextsong']
                # ask mpd for next song data
                mainmpdconnection.protocol.playlistinfo(self.nextsong).addCallback(self.update_mpd_nextsong).addErrback(self.handle_mpd_error)
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
        # update the playlist tab with status results so that current track will be highlighted
        self.ids.playlist_tab.update_mpd_status(result)

    def change_artist_image(self,img,al_path,instance):
        """Called when you click on an artist logo, changes it to another at random."""
        Logger.debug("change_artist_image: (current path is "+img.source+")")
        img_path=img.source
        if len(os.listdir(al_path))>1:
            while img_path==img.source:
                img_path=os.path.join(al_path,random.choice(os.listdir(al_path)))
            if os.path.isfile(img_path):
                img.source=img_path
            Logger.debug("change_artist_image: (new path is "+img.source+")")
        else:
            Logger.debug("change_artist_image: no other choices for logo")

    def update_mpd_currentsong(self,force,result):
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
            if songchange or force:
                # clear the track info widget
                ti.clear_widgets()
                # clear the album cover
                self.ids.album_cover_layout.clear_widgets()
                # get the stored star rating
                mainmpdconnection.protocol.sticker_get('song',self.currfile,'rating').addCallback(self.update_mpd_sticker_rating).addErrback(self.handle_mpd_no_sticker)
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
                            img.bind(on_press=partial(self.change_artist_image,img,al_path))
                            cbl.add_widget(img)
                            haslogo=True
                    except OSError:
                        Logger.debug("update_mpd_currentsong: No logos for artist "+mb_aid)
                    except Exception as e:
                        Logger.exception("update_mpd_currentsong: "+format(e))
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
                    Logger.debug('update_mpd_currentsong: found good file at path '+p)
                    # load up the file to read the tags
                    f = mutagen.File(p)
                    cimg = None
                    data = None
                    originalyear = None
                    # if config file says use originalyear, use it instead of mpd's year
                    if self.config.getboolean('system','originalyear'):
                        if 'TXXX:originalyear' in f.keys():
                            originalyear=format(f['TXXX:originalyear'])
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
                        # filter through PIL first to resize it if it is too large for a texture
                        pimg = PImage.open(data)
                        (w,h) = pimg.size
                        if w > max_cover_size or h > max_cover_size:
                            Logger.debug('update_mpd_currentsong: resizing cover image to maximum of '+format(max_cover_size)+'x'+format(max_cover_size))
                            pimg.thumbnail((max_cover_size,max_cover_size))
                            data2=io.BytesIO()
                            pimg.save(data2,'PNG')
                            data2.seek(0)
                            cimg = CoreImage(data2,ext='png')
                        else:
                            Logger.debug('update_mpd_currentsong: pulling cover directly from tag')
                            data.seek(0)
                            cimg = CoreImage(data,ext=ext)
                    if self.config.getboolean('system','originalyear') and originalyear and year and int(originalyear)!=int(year):
                        self.ids.yearlabel.text="["+originalyear+"]"
                        self.ids.remasterlabel.text="{"+year+"}"
                    elif year:
                        self.ids.yearlabel.text="["+year+"]"
                        self.ids.remasterlabel.text=""
                    else:
                        self.ids.yearlabel.text=""
                        self.ids.remasterlabel.text=""
                    if cimg:
                        img=CoverButton(img=cimg,layout=self.ids.album_cover_layout,halign='center')
                    else:
                        img=CoverButton(img=CoreImage(resource_filename(__name__,os.path.join('resources','clear.png'))),layout=self.ids.album_cover_layout,halign='center')
                    self.ids.album_cover_layout.add_widget(img)
                    # popup the cover large if you press it
                    img.bind(on_press=partial(self.cover_popup,originalyear,year,result['album']))
                else:
                    # this should _probably_ never happen
                    Logger.debug('NowPlaying: no file found at path '+p)
                # add the correct artist name widget
                ti.add_widget(current_artist_label)
                lyt = BoxLayout(orientation='vertical',padding_y='2sp')
                if self.config.getboolean('system','advancedtitles'):
                    # check to see if song title has any data deliminated by () or []
                    stitle=re.split('[\(\[\]\)]',result['title'])
                    Logger.debug('TITLE: '+format(stitle))
                    if len(stitle) > 1:
                        lyt2=BoxLayout(orientation='vertical',padding_y='2sp')
                        # split the title up and put the parentheses in smaller text below
                        lyt2.add_widget(InfoLargeLabel(text = stitle[0], font_size=Helpers.getfontsize(stitle[0])))
                        l2=""
                        for i, v in enumerate(stitle):
                            if i > 0 and v.strip():
                                if l2: l2=l2+' '
                                l2=l2+'('+v.strip()+')'
                        lyt2.add_widget(InfoLargeLabel(text = l2, font_size=Helpers.getfontsize(l2,2)))
                        lyt.add_widget(lyt2)
                    else:
                        lyt.add_widget(InfoLargeLabel(text = result['title'],font_size=Helpers.getfontsize(result['title'])))
                    # check to see if album is a single or EP
                    amatch=re.match(r'(.*) (\(single\)|EP)( .*)',result['album'])
                    # check if ' EP' is at the very end of the album title
                    if not amatch: amatch=re.match(r'(.*) (EP)($)',result['album'])
                    if amatch:
                        special=str(amatch.group(2)).strip("()")
                        Logger.debug("ALBUM: special release: "+special)
                        self.ids.releasetypelabel.text=special
                        galbum=str(amatch.group(1))+str(amatch.group(3))
                    else:
                        galbum=result['album']
                        self.ids.releasetypelabel.text='album'
                    # check to see if album is an import
                    amatch=re.match(r'(.*) (\(.. Import\))(.*)',galbum)
                    if amatch:
                        aimport=str(amatch.group(2))
                        Logger.debug("ALBUM: import: "+aimport)
                        galbum=str(amatch.group(1))+str(amatch.group(3))
                    else:
                        aimport=None
                    # check to see if album title is a split (has a ' / ' in the middle)
                    talbum=galbum.split(' / ')
                    Logger.debug('ALBUM1: '+format(talbum))
                    lyt2=BoxLayout(orientation='horizontal',padding_x='2sp')
                    if len(talbum)>1:
                        Logger.debug('ALBUM1: album is a split')
                        split=True
                    else:
                        split=False
                    for j, a in enumerate(talbum):
                        if j>0: lyt2.add_widget(InfoLargeLabel(font_size='50sp',text=u'\u2571',size_hint_x=None,font_name=App.get_running_app().normalfont))
                        # check to see if album title has any data deliminated by () or []
                        salbum=re.split('[\(\[\]\)]',a)
                        Logger.debug('ALBUM2: '+format(salbum))
                        if len(salbum) > 1:
                            lyt3=BoxLayout(orientation='vertical',padding_y='2sp')
                            # split the album up and put the parentheses in smaller text below
                            if split:
                                lyt3.add_widget(InfoLargeLabel(text = salbum[0], font_size=Helpers.getfontsize(salbum[0],1.5)))
                            else:
                                lyt3.add_widget(InfoLargeLabel(text = salbum[0], font_size=Helpers.getfontsize(salbum[0])))
                            l2=""
                            for i, v in enumerate(salbum):
                                if i > 0 and v.strip():
                                    if l2: l2=l2+' '
                                    l2=l2+'('+v.strip()+')'
                            lyt3.add_widget(InfoLargeLabel(text = l2, font_size=Helpers.getfontsize(l2,2)))
                            lyt2.add_widget(lyt3)
                        else:
                            if split:
                                lyt2.add_widget(InfoLargeLabel(text = a, font_size=Helpers.getfontsize(a,1.5)))
                            else:
                                lyt2.add_widget(InfoLargeLabel(text = a, font_size=Helpers.getfontsize(a)))
                    lyt.add_widget(lyt2)
                    if aimport: lyt.add_widget(InfoLargeLabel(text=aimport,font_size=Helpers.getfontsize(aimport,2)))
                else:
                    self.ids.releasetypelabel.text=''
                    lyt.add_widget(InfoLargeLabel(text = result['title'],font_size=Helpers.getfontsize(result['title'])))
                    lyt.add_widget(InfoLargeLabel(text = result['album'],font_size=Helpers.getfontsize(result['album'])))
                ti.add_widget(lyt)
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
        mainmpdconnection.protocol.previous()

    def play_pressed(self):
        """Callback for play/pause button pressed."""
        Logger.debug('Application: play_pressed()')
        if self.mpd_status['state'] == 'play':
            # pause if playing
            mainmpdconnection.protocol.pause()
        else:
            # play if paused or stopped
            mainmpdconnection.protocol.play()

    def next_pressed(self):
        """Callback for next button pressed."""
        Logger.debug('Application: next_pressed()')
        mainmpdconnection.protocol.next()

    def repeat_pressed(self):
        """Callback for repeat button pressed."""
        Logger.debug('Application: repeat_pressed()')
        # toggle on/off
        mainmpdconnection.protocol.repeat(str(1-int(self.mpd_status['repeat'])))

    def single_pressed(self):
        """Callback for single button pressed."""
        Logger.debug('Application: single_pressed()')
        # toggle on/off
        mainmpdconnection.protocol.single(str(1-int(self.mpd_status['single'])))

    def random_pressed(self):
        """Callback for random button pressed."""
        Logger.debug('Application: random_pressed()')
        # toggle on/off
        mainmpdconnection.protocol.random(str(1-int(self.mpd_status['random'])))

    def consume_pressed(self):
        """Callback for consume button pressed."""
        Logger.debug('Application: consume_pressed()')
        # toggle on/off
        mainmpdconnection.protocol.consume(str(1-int(self.mpd_status['consume'])))

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
            lbl=OutlineLabel(text=Helpers.songratings(self.config)[str(r)]['meaning'],halign='left')
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
        mainmpdconnection.protocol.sticker_set('song',self.currfile,'rating',instance.rating)

    def cover_popup(self,originalyear,year,album,instance):
        """Popup for showing a larger version of the album cover."""
        Logger.debug('Application: cover_popup()')
        title='"'+album+'"'
        if year and originalyear and year!=originalyear:
            title=title+' released '+originalyear+' (remastered '+year+')'
        elif year:
            title=title+' released '+year
        layout = BoxLayout()
        popup = Popup(title=title,content=layout,size_hint=(0.6,1))
        # pull the already loaded image texture
        img = Image(texture=instance.img.texture,allow_stretch=True)
        # add it to the layout
        layout.add_widget(img)
        # pop pop pop
        popup.open()

    def change_backlight(self,value):
        """Method that sets the backlight to a certain value."""
        Logger.info('Application: change_backlight('+str(value)+') rpienable = '+self.config.get('system','rpienable'))
        # only if the ini file says it's ok
        if self.config.getboolean('system','rpienable'):
            import rpi_backlight as bl
            # set the brightness
            bl.set_brightness(int(value), smooth=True, duration=1)

    def settings_update(self):
        mainmpdconnection.protocol.currentsong().addCallback(partial(self.update_mpd_currentsong,True)).addErrback(mainmpdconnection.handle_mpd_error)

    def init_mpd(self,instance):
        # get the initial mpd status
        mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(mainmpdconnection.handle_mpd_error)
        # create the once-per-second update of the track slider
        self.track_slider_task=Clock.schedule_interval(self.update_track_slider,1)
        self.track_slider_task.cancel()
        # subscribe to 'kmpc' to check for messages from mpd
        mainmpdconnection.protocol.subscribe('kmpc')

    def mpd_idle_handler(self,result):
        # notify various subsystems based on what changed
        for s in result:
            Logger.info('MPDIdleHandler: Changed '+format(s))
            if format(s) == 'playlist':
                # playlist was changed, ask mpd for playlist info
                mainmpdconnection.protocol.playlistinfo().addCallback(self.ids.playlist_tab.populate_playlist).addErrback(self.ids.playlist_tab.handle_mpd_error)
                # force a reload of nextsong if playlist changes
                self.nextsong = None
                mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)
            elif format(s) == 'player':
                # player was changed, ask mpd for player status
                mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)
            elif format(s) == 'sticker':
                # song rating sticker was changed, ask mpd for current song rating
                mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)
                mainmpdconnection.protocol.sticker_get('song',self.currfile,'rating').addCallback(self.update_mpd_sticker_rating).addErrback(self.handle_mpd_no_sticker)
            elif format(s) == 'options':
                # some playback option was changed, ask mpd for player status
                mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)
            elif format(s) == 'message':
                # an mpd message was received, ask mpd what it was
                mainmpdconnection.protocol.readmessages().addCallback(self.handle_mpd_message).addErrback(self.handle_mpd_error)
            else:
                # default if none of the above, ask mpd for player status
                mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)

class KmpcApp(App):
    """The overall app class, builds the main interface widget."""

    def __init__(self,args):
        """Override kivy config values with necessary ones"""
        Config.set('kivy','keyboard_mode','systemanddock')
        Config.set('graphics','width',800)
        Config.set('graphics','height',480)
        self.args=args
        super(self.__class__,self).__init__()

    def build_config(self,config):
        config.setdefaults('mpd', {
            'mpdhost': '127.0.0.1',
            'mpdport': '6600'
        })
        config.setdefaults('paths', {
            'musicpath': '/mnt/music',
            'fanartpath': '/mnt/fanart',
            'tmppath': '/tmp'
        })
        config.setdefaults('sync', {
            'synchost': '127.0.0.1',
            'syncmusicpath': '/mnt/music',
            'syncfanartpath': '/mnt/fanart',
            'synctmppath': '/tmp'
        })
        config.setdefaults('system', {
            'rpienable': '0',
            'originalyear': '1',
            'advancedtitles': '0',
            'updatecommand': 'sudo pip install -U kmpc',
        })
        config.setdefaults('songratings', {
            'star0': 'Silence',
            'star1': 'Songs that should never be heard',
            'star2': 'Songs no one likes',
            'star3': 'Songs for certain occasions',
            'star4': 'Songs someone else likes',
            'star5': 'Filler tracks with no music',
            'star6': 'Meh track or short musical filler',
            'star7': 'Occasional listening songs',
            'star8': 'Great songs for all occasions',
            'star9': 'Best songs by an artist',
            'star10': 'Favorite songs of all time'
        })

    def get_application_config(self):
        return super(self.__class__,self).get_application_config(configdir+'/config.ini')

    def build_settings(self,settings):
        settings.add_json_panel('mpd settings',self.config,resource_filename(__name__,os.path.join('resources','config_mpd.json')))
        settings.add_json_panel('path settings',self.config,resource_filename(__name__,os.path.join('resources','config_paths.json')))
        settings.add_json_panel('sync settings',self.config,resource_filename(__name__,os.path.join('resources','config_sync.json')))
        settings.add_json_panel('system settings',self.config,resource_filename(__name__,os.path.join('resources','config_system.json')))
        settings.add_json_panel('song ratings',self.config,resource_filename(__name__,os.path.join('resources','config_star.json')))

    def on_config_change(self, config, section, key, value):
        if config is self.config:
            Logger.info("Application: config entry has changed: ["+section+"] "+key+"="+value)
            if callable (self.root.settings_update): self.root.settings_update()

    def build(self,*args):
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
        self.version_str=VERSION_STR
        if not os.path.isdir(configdir):
            os.mkdir(configdir)
        # try to read existing config file
        self.config=self.load_config()
        # write out config file in case it doesn't exist yet
        self.config.write()
        if self.args.newconfig:
            sys.exit(0)
        else:
            return KmpcInterface(self.config)

class InfoLargeLabel(OutlineLabel):
    """A label with large text."""
    pass

class InfoSmallLabel(OutlineLabel):
    """A label with small text."""
    pass

class ImageButton(ButtonBehavior, AsyncImage):
    """An image that you can press."""
    pass

class CoverButton(OutlineButton):
    img = ObjectProperty(None)
    layout = ObjectProperty(None)

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.background_normal = resource_filename(__name__,os.path.join('resources','clear.png'))
        self.background_down = resource_filename(__name__,os.path.join('resources','clear.png'))
        self.font_name = resource_filename(__name__,os.path.join('resources','DejaVuSans-Bold.ttf'))
        with self.canvas.before:
            Rectangle(texture=self.img.texture,pos=self.layout.pos,size=self.layout.size)

if __name__ == '__main__':
    # run the app!
    KmpcApp().run()

