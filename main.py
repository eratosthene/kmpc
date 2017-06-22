#!/usr/bin/env python

import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.support import install_twisted_reactor
from kivy.config import Config
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.logger import Logger
from kivy.metrics import Metrics
from mpd import MPDProtocol
import os
import traceback

#install twisted reactor to interface with mpd
import sys
if 'twisted.internet.reactor' in sys.modules:
    del sys.modules['twisted.internet.reactor']
install_twisted_reactor()
from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import task
from twisted.internet.defer import inlineCallbacks

def formatsong(rec):
    song = ''
    (d1,d2)=rec['disc'].split('/')
    if int(d2) > 1:
        song+='(Disc '+'%02d' % int(d1)+') '
    (t1,t2)=rec['track'].split('/')
    song+='%02d' % int(t1)+' '+rec['title']
    return song

class MPDFactoryProtocol(MPDProtocol):
    def connectionMade(self):
        if callable(self.factory.connectionMade):
            self.factory.connectionMade(self)
    def connectionLost(self, reason):
        if callable(self.factory.connectionLost):
            self.factory.connectionLost(self, reason)

class MPDClientFactory(protocol.ReconnectingClientFactory):
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None

    def buildProtocol(self, addr):
        Logger.debug('MPDClientFactory: buildProtocol()')
        protocol = self.protocol()
        protocol.factory = self
        return protocol

class KmpcInterface(TabbedPanel):

    def __init__(self,config):
        super(self.__class__,self).__init__()
        self.config = config
        # set up mpd connection
        self.factory = MPDClientFactory()
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        reactor.connectTCP(self.config.get('mpd','host'), self.config.getint('mpd','port'), self.factory)
        # bind callbacks for tab changes
        self.bind(current_tab=self.main_tab_changed)
        self.ids.library_panel.bind(current_tab=self.library_tab_changed)
        self.mpd_status={'state':'stop','repeat':0,'single':0,'random':0,'consume':0}

    def mpd_connectionMade(self,protocol):
        self.mpd_protocol = protocol
        Logger.info('Application: Connected to mpd server host='+self.config.get('mpd','host')+' port='+self.config.get('mpd','port'))
        # start the interface update task after mpd connection
        self.status_task=task.LoopingCall(self.update_current_status)
        self.status_task.start(1.0)

    def main_tab_changed(self,obj,value):
        self.active_tab = value.text
        Logger.info("Application: Changed active tab to "+self.active_tab)
        if self.active_tab == 'Now Playing':
            pass
        elif self.active_tab == 'Playlist':
            self.populate_playlist()
        elif self.active_tab == 'Library':
            if self.ids.library_panel.active_tab is None:
                self.ids.library_panel.active_tab = 'Files'
                self.populate_file_browser()

    def library_tab_changed(self,obj,value):
        tabname = value.text
        self.ids.library_panel.active_tab = tabname
        Logger.info("Application: Changed library tab: "+tabname)
        if tabname == 'Files':
            self.populate_file_browser()
        elif tabname == 'Albums':
            self.populate_album_browser()
        elif tabname == 'Tracks':
            self.populate_track_browser()
        elif tabname == 'Playlists':
            self.populate_playlist_browser()
        elif tabname == 'Genres':
            pass

    def mpd_connectionLost(self,protocol, reason):
        Logger.info('Application: Connection lost: %s' % reason)

#    @inlineCallbacks
    def current_track_slider_click(self):
        curpos=int(self.ids.current_track_slider.value)
        Logger.info('Application: current_track_slider_click('+str(curpos)+')')
        self.mpd_protocol.seekcur(str(curpos))

    @inlineCallbacks
    def update_current_status(self):
        Logger.debug('Application: update_current_status()')
        if self.active_tab == 'Now Playing':
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.status()
            self.mpd_protocol.currentsong()
            reslist=yield self.mpd_protocol.command_list_end()
            # first result is status command
            result=reslist[0]
            Logger.debug('StatusTask: status = '+format(result))
            self.mpd_status['state']=result['state']
            self.mpd_status['repeat']=int(result['repeat'])
            self.mpd_status['single']=int(result['single'])
            self.mpd_status['random']=int(result['random'])
            self.mpd_status['consume']=int(result['consume'])
            if int(result['repeat']):
                self.ids.repeat_button.state='down'
            else:
                self.ids.repeat_button.state='normal'
            if int(result['single']):
                self.ids.single_button.state='down'
            else:
                self.ids.single_button.state='normal'
            if int(result['random']):
                self.ids.random_button.state='down'
            else:
                self.ids.random_button.state='normal'
            if int(result['consume']):
                self.ids.consume_button.state='down'
            else:
                self.ids.consume_button.state='normal'
            if result['state']=='pause' or result['state']=='stop':
                self.ids.play_button.state='normal'
                self.ids.play_button.text=u"\uf04b"
            else:
                self.ids.play_button.state='down'
                self.ids.play_button.text=u"\uf04c"
            if result['state'] == 'stop':
                self.ids.current_track_time_label.text=''
                self.ids.current_track_totaltime_label.text=''
                self.ids.current_track_slider.value=0
                self.ids.current_playlist_track_number_label.text=''
                self.ids.current_song_label.text = 'Playback Stopped'
                self.ids.current_artist_label.text = ''
                self.ids.current_album_label.text = ''
                self.ids.next_track_label.text = ''
                self.ids.next_song_artist_label.text = ''
            else:
                c,t=result['time'].split(":")
                cm,cs=divmod(int(c),60)
                tm,ts=divmod(int(t),60)
                self.ids.current_track_time_label.text = "%02d:%02d" % (cm,cs)
                self.ids.current_track_totaltime_label.text = "%02d:%02d" % (tm,ts)
                self.ids.current_track_slider.max = int(t)
                self.ids.current_track_slider.value = int(c)
                # throws an exception if i don't do this
                a=int(result['song'])+1
                b=int(result['playlistlength'])
                self.ids.current_playlist_track_number_label.text = "%d of %d" % (a,b)
                # save the next song for later use
                if result['nextsong']:
                    ns=result['nextsong']
                else:
                    ns=None
                # second result is currentsong command
                result=reslist[1]
                Logger.debug('StatusTask: currentsong = '+format(result))
                self.ids.current_song_label.text = result['title']
                self.ids.current_artist_label.text = result['artist']
                self.ids.current_album_label.text = result['album']
                if ns:
                    #not sure if command list is needed, but it works
                    self.mpd_protocol.command_list_ok_begin()
                    # get info about next song
                    self.mpd_protocol.playlistinfo(ns)
                    reslist=yield self.mpd_protocol.command_list_end()
                    result=reslist[0][0]
                    Logger.debug('StatusTask: nextsong = '+format(result))
                    self.ids.next_track_label.text = 'Up Next:'
                    self.ids.next_song_artist_label.text = result['artist']+' - '+result['title']
                else:
                    self.ids.next_track_label.text = ''
                    self.ids.next_song_artist_label.text = ''

    def prev_pressed(self):
        Logger.debug('Application: prev_pressed()')
        self.mpd_protocol.previous()
        self.update_current_status()

    def play_pressed(self):
        Logger.debug('Application: play_pressed()')
        if self.ids.play_button.state == 'normal' and self.mpd_status['state'] != 'stop':
            self.mpd_protocol.pause()
        else:
            self.mpd_protocol.play()
        self.update_current_status()

    def next_pressed(self):
        Logger.debug('Application: next_pressed()')
        self.mpd_protocol.next()
        self.update_current_status()

    def repeat_pressed(self):
        Logger.debug('Application: repeat_pressed()')
        self.mpd_protocol.repeat(str(1-self.mpd_status['repeat']))
        self.update_current_status()

    def single_pressed(self):
        Logger.debug('Application: single_pressed()')
        self.mpd_protocol.single(str(1-self.mpd_status['single']))
        self.update_current_status()

    def random_pressed(self):
        Logger.debug('Application: random_pressed()')
        self.mpd_protocol.random(str(1-self.mpd_status['random']))
        self.update_current_status()

    def consume_pressed(self):
        Logger.debug('Application: consume_pressed()')
        self.mpd_protocol.consume(str(1-self.mpd_status['consume']))
        self.update_current_status()

    @inlineCallbacks
    def browser_add(self,clearfirst):
        Logger.debug('Application: browser_add('+str(clearfirst)+')')
        if clearfirst:
            Logger.info('Browser: Clearing playlist')
            self.mpd_protocol.clear()
        for row in self.browser_marked:
            mtype=self.browser_marked[row]['type']
            Logger.info("Browser: Adding "+mtype+" '"+row+"' to current playlist")
            if mtype == 'uri':
                self.mpd_protocol.add(row)
            elif mtype == 'albumartistsort':
                self.mpd_protocol.command_list_ok_begin()
                self.mpd_protocol.find(mtype,row)
                reslist=yield self.mpd_protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.mpd_protocol.add(rrow['file'])
            elif mtype == 'album':
                self.mpd_protocol.command_list_ok_begin()
                self.mpd_protocol.find(mtype,row,'albumartistsort',self.browser_marked[row]['albumartistsort'])
                reslist=yield self.mpd_protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+",albumartistsort,"+self.browser_marked[row]['albumartistsort']+") = "+format(result))
                for rrow in result:
                    self.mpd_protocol.add(rrow['file'])
            elif mtype == 'artistsort':
                self.mpd_protocol.command_list_ok_begin()
                self.mpd_protocol.find(mtype,row)
                reslist=yield self.mpd_protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.mpd_protocol.add(rrow['file'])
            elif mtype == 'title':
                self.mpd_protocol.command_list_ok_begin()
                self.mpd_protocol.find('artistsort',self.browser_marked[row]['artistsort'],mtype,row)
                reslist=yield self.mpd_protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find(artistsort,"+self.browser_marked[row]['artistsort']+","+mtype+","+row+") = "+format(result))
                if result:
                    self.mpd_protocol.add(result[0]['file'])
            else:
                Logger.warning("Browser: "+mtype+' not implemented')

    @inlineCallbacks
    def populate_file_browser(self):
        self.browser_marked={}
        base=self.file_browser_base
        (hbase,tbase)=os.path.split(base)
        Logger.info("Application: populate_file_browser, base=["+base+"], tbase=["+tbase+"]")
        self.ids.library_files_panel.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if base != '/':
            (b1,b2)=os.path.split(hbase)
            if b2 == '':
                b2 = 'root'
            btn = Button(text=".. ("+b2+")",size_hint_y=None,height='0.5in')
            btn.base=os.path.normpath(base+'/..')
            if btn.base == '.':
                btn.base = '/'
            btn.bind(on_press=self.file_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=tbase,size_hint_y=None,height='0.5in')
            layout.add_widget(lbl)
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.lsinfo(base)
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0]
        for row in result:
            if 'directory' in row:
                Logger.debug("FileBrowser: directory found: ["+row['directory']+"]")
                (b1,b2)=os.path.split(row['directory'])
                btn = ScrollButton(text=b2)
                btn.base = row['directory']
                btn.bind(on_press=self.file_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['directory']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
            elif 'file' in row:
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                btn = ScrollButton(text=formatsong(row))
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['file']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        sv=ScrollView(size_hint=(1,1),do_scroll_x=False)
        sv.add_widget(layout)
        self.ids.library_files_panel.add_widget(sv)

    def file_browser_button(self,instance):
        Logger.debug('Application: file_browser_button('+instance.text+')')
        self.file_browser_base=instance.base
        self.populate_file_browser()

    @inlineCallbacks
    def populate_album_browser(self):
        self.album_browser_marked={}
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        Logger.info("Application: populate_album_browser, base=["+base+"] level=["+level+"]")
        self.ids.library_albums_panel.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if level == 'root':
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.list('albumartistsort')
            reslist=yield self.mpd_protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("AlbumBrowser: artist found = "+row)
                btn = ScrollButton(text=row)
                btn.base = row
                btn.nextlevel = 'artist'
                btn.bind(on_press=self.album_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'albumartistsort'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        elif level == "artist":
            btn = Button(text=".. (root)",size_hint_y=None,height='0.5in')
            btn.base = upto
            btn.nextlevel = 'root'
            btn.bind(on_press=self.album_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='0.5in')
            layout.add_widget(lbl)
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.list('album','albumartistsort',base)
            reslist=yield self.mpd_protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug('AlbumBrowser: album found = '+row)
                btn = ScrollButton(text=row,size_hint_y=None,height='0.5in')
                btn.base = row
                btn.nextlevel = 'album'
                btn.bind(on_press=self.album_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'album','albumartistsort':base}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        elif level == "album":
            btn = Button(text=".. ("+upto+")",size_hint_y=None,height='0.5in')
            btn.base = upto
            btn.nextlevel = 'artist'
            btn.bind(on_press=self.album_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='0.5in')
            layout.add_widget(lbl)
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.find('album',base,'albumartistsort',upto)
            reslist=yield self.mpd_protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("AlbumBrowser: track found = "+row['file'])
                btn = ScrollButton(text=formatsong(row),size_hint_y=None,height='0.5in')
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['file']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        sv=ScrollView(size_hint=(1,1),do_scroll_x=False)
        sv.add_widget(layout)
        self.ids.library_albums_panel.add_widget(sv)

    def album_browser_button(self,instance):
        Logger.debug('Application: album_browser_button('+instance.text+','+instance.base+','+instance.nextlevel+')')
        blevel=self.album_browser_base['level']
        bbase=self.album_browser_base['base']
        bupto=self.album_browser_base['upto']
        self.album_browser_base={'level':instance.nextlevel,'base':instance.base,'upto':bbase}
        self.populate_album_browser()

    @inlineCallbacks
    def populate_track_browser(self):
        self.browser_marked={}
        base=self.track_browser_base['base']
        level=self.track_browser_base['level']
        Logger.info("Application: populate_track_browser, base=["+base+"] level=["+level+"]")
        self.ids.library_tracks_panel.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if level == 'root':
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.list('artistsort')
            reslist=yield self.mpd_protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("TrackBrowser: artist found = "+row)
                btn = ScrollButton(text=row)
                btn.base = row
                btn.nextlevel = 'artist'
                btn.bind(on_press=self.track_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'artistsort'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        elif level == "artist":
            btn = Button(text=".. (root)",size_hint_y=None,height='0.5in')
            btn.base = 'root'
            btn.bind(on_press=self.track_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='0.5in')
            layout.add_widget(lbl)
            self.mpd_protocol.command_list_ok_begin()
            self.mpd_protocol.list('title','artistsort',base)
            reslist=yield self.mpd_protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("TrackBrowser: track found = "+row)
                btn = ScrollButton(text=row)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'title','artistsort':base}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        sv=ScrollView(size_hint=(1,1),do_scroll_x=False)
        sv.add_widget(layout)
        self.ids.library_tracks_panel.add_widget(sv)

    def track_browser_button(self,instance):
        Logger.debug("Application: track_browser_button("+instance.text+","+instance.base+","+instance.nextlevel+")")
        blevel=self.track_browser_base['level']
        bbase=self.track_browser_base['base']
        if blevel == 'root':
            self.track_browser_base={'level':'artist','base':instance.base}
        else:
            self.track_browser_base={'level':'root','base':'root'}
        self.populate_track_browser()

    @inlineCallbacks
    def populate_playlist_browser(self):
        Logger.info("Application: populate_playlist_browser()")
        self.ids.library_playlists_panel.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.listplaylists()
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0]
        for row in result:
            Logger.debug("PlaylistBrowser: playlist found = "+row['playlist'])
            btn = Button(text=row['playlist'],size_hint_y=None,height='0.5in')
            layout.add_widget(btn)
        sv=ScrollView(size_hint=(1,1),do_scroll_x=False)
        sv.add_widget(layout)
        self.ids.library_playlists_panel.add_widget(sv)

    def browser_checkbox_pressed(self,checkbox,value):
        Logger.debug("Application: browser_checkbox_pressed("+checkbox.base+","+format(checkbox.info)+")")
        if value:
            self.browser_marked[checkbox.base]=checkbox.info
        else:
            if checkbox.base in self.browser_marked:
                del self.browser_marked[checkbox.base]

    def playlist_clear_pressed(self):
        Logger.info("Playlist: clear")
        self.mpd_protocol.clear()
        self.populate_playlist()

    def playlist_delete_pressed(self):
        Logger.info("Playlist: delete")
        for pos in self.playlist_marked:
            Logger.debug("Playlist: deleting pos "+pos)
            self.mpd_protocol.delete(pos)
        self.populate_playlist()

    def playlist_move_pressed(self):
        Logger.info("Playlist: move")
        self.populate_playlist()

    def playlist_shuffle_pressed(self):
        Logger.info("Playlist: shuffle")
        self.mpd_protocol.shuffle()
        self.populate_playlist()

    def playlist_swap_pressed(self):
        Logger.info("Playlist: swap")
        self.populate_playlist()

    @inlineCallbacks
    def populate_playlist(self):
        Logger.info("Application: populate_playlist()")
        self.playlist_marked={}
        self.ids.playlist_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.playlistinfo()
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0]
        for row in result:
            Logger.debug("Playlist: row "+row['pos']+" found = "+row['title'])
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            chk.plpos=row['pos']
            chk.bind(active=self.playlist_checkbox_pressed)
            lbl = Label(text=str(int(row['pos'])+1),size_hint_x=None)
            btn = ScrollButton(text=row['artist']+' - '+row['title'])
            btn.plpos=row['pos']
            btn.texture_update()
            bl.add_widget(chk)
            bl.add_widget(lbl)
            bl.add_widget(btn)
            layout.add_widget(bl)
            bl.height=btn.height/16
            if bl.height < kivy.metrics.inch(0.5):
                bl.height = kivy.metrics.inch(0.5)
            print 'bl.height '+format(bl.height)
            print 'btn.height'+format(btn.height)
        self.ids.playlist_sv.add_widget(layout)

    def playlist_checkbox_pressed(self,checkbox,value):
        Logger.debug("Application: playlist_checkbox_pressed("+format(checkbox.plpos)+")")
        if value:
            self.playlist_marked[checkbox.plpos]=True
        else:
            if checkbox.plpos in self.playlist_marked:
                del self.playlist_marked[checkbox.plpos]

class ScrollButton(Button):
    pass

class ScrollBoxLayout(BoxLayout):
    pass

class KmpcApp(App):
    def build_config(self,config):
        config.setdefaults('mpd',{
            'host': '127.0.0.1',
            'port': 6600,
            'basepath': '/mnt/music'
        })
        config.setdefaults('kivy',{
            'log_level': 'info',
            'log_enable': 1,
            'keyboard_mode': 'systemandmulti'
        })
        config.setdefaults('graphics',{
            'width': 800,
            'height': 480
        })
        Config.read(self.get_application_config())
        self.config=config
    def build(self):
        return KmpcInterface(self.config)

if __name__ == '__main__':
    Logger.info("Metrics: density "+format(Metrics.density))
    Logger.info("Metrics: dpi "+format(Metrics.dpi))
    Logger.info("Metrics: fontscale "+format(Metrics.fontscale))
    KmpcApp().run()

