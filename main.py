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
from kivy.graphics import Color,Rectangle
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

from mpdfactory import MPDFactoryProtocol,MPDIdleHandler,MPDClientFactory
from extra import ScrollButton,ScrollBoxLayout
from playlistpanel import PlaylistTabbedPanelItem

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
        self.mpd_status={'state':'stop','repeat':0,'single':0,'random':0,'consume':0,'curpos':0}
        self.update_slider=True
        self.currsong=None
        self.nextsong=None

    def mpd_connectionMade(self,protocol):
        self.protocol = protocol
        self.ids.playlist_tab.protocol=protocol
        Logger.info('Application: Connected to mpd server host='+self.config.get('mpd','host')+' port='+self.config.get('mpd','port'))
        # start the interface update task after mpd connection
        self.status_task=task.LoopingCall(self.protocol.status)
        self.status_task.start(1.0)

    def main_tab_changed(self,obj,value):
        self.active_tab = value.text
        Logger.info("Application: Changed active tab to "+self.active_tab)
        if self.active_tab == 'Now Playing':
            if 'protocol' in locals():
                self.protocol.status()
        elif self.active_tab == 'Playlist':
            self.protocol.playlistinfo().addCallback(self.ids.playlist_tab.populate_playlist).addErrback(self.handle_mpd_error)
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

    def mpd_connectionLost(self,protocol, reason):
        Logger.info('Application: Connection lost: %s' % reason)

    def current_track_slider_up(self):
        curpos=int(self.ids.current_track_slider.value)
        Logger.info('Application: current_track_slider_up('+str(curpos)+')')
        self.update_slider=False
        self.protocol.seekcur(str(curpos))
        self.update_slider=True

    def current_track_slider_move(self):
        Logger.info('Application: current_track_slider_move()')
        self.update_slider=False

    def handle_mpd_error(self,result):
        Logger.error('Application: MPDIdleHandler Callback error: {}'.format(result))

    def update_mpd_status(self,result):
        Logger.debug('NowPlaying: update_mpd_status()')
        self.mpd_status['state']=result['state']
        self.mpd_status['repeat']=result['repeat']
        self.mpd_status['single']=result['single']
        self.mpd_status['random']=result['random']
        self.mpd_status['consume']=result['consume']
        if self.mpd_status['state'] == 'stop':
            self.currsong=None
            self.nextsong=None
        else:
            self.currsong=result['song']
            # save the next song for later use
            if result['nextsong']:
                self.nextsong=result['nextsong']
            else:
                self.nextsong=None
        if int(self.mpd_status['repeat']):
            self.ids.repeat_button.state='down'
        else:
            self.ids.repeat_button.state='normal'
        if int(self.mpd_status['single']):
            self.ids.single_button.state='down'
        else:
            self.ids.single_button.state='normal'
        if int(self.mpd_status['random']):
            self.ids.random_button.state='down'
        else:
            self.ids.random_button.state='normal'
        if int(self.mpd_status['consume']):
            self.ids.consume_button.state='down'
        else:
            self.ids.consume_button.state='normal'
        if self.mpd_status['state']=='pause' or self.mpd_status['state']=='stop':
            self.ids.play_button.state='normal'
            self.ids.play_button.text=u"\uf04b"
        else:
            self.ids.play_button.state='down'
            self.ids.play_button.text=u"\uf04c"
        if self.mpd_status['state'] == 'stop':
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
            # mpd returns {elapsed seconds}:{total seconds}, the following splits each to minute:second
            c,t=result['time'].split(":")
            cm,cs=divmod(int(c),60)
            tm,ts=divmod(int(t),60)
            self.ids.current_track_time_label.text = "%02d:%02d" % (cm,cs)
            self.ids.current_track_totaltime_label.text = "%02d:%02d" % (tm,ts)
            self.ids.current_track_slider.max = int(t)
            self.mpd_status['curpos']=int(c)
            if self.update_slider:
                self.ids.current_track_slider.value = int(c)
            # throws an exception if i don't do this
            a=int(result['song'])+1
            b=int(result['playlistlength'])
            self.ids.current_playlist_track_number_label.text = "%d of %d" % (a,b)

    def update_mpd_currentsong(self,result):
        Logger.debug('NowPlaying: update_mpd_currentsong()')
        if self.mpd_status['state'] != 'stop':
            self.ids.current_song_label.text = result['title']
            self.ids.current_artist_label.text = result['artist']
            self.ids.current_album_label.text = result['album']

    def update_mpd_nextsong(self,result):
        if self.active_tab == 'Now Playing':
            Logger.debug('NowPlaying: update_mpd_nextsong()')
            self.ids.next_track_label.text = 'Up Next:'
            for obj in result:
                self.ids.next_song_artist_label.text = obj['artist']+' - '+obj['title']

    def prev_pressed(self):
        Logger.debug('Application: prev_pressed()')
        self.protocol.previous()

    def play_pressed(self):
        Logger.debug('Application: play_pressed()')
        if self.ids.play_button.state == 'normal' and self.mpd_status['state'] != 'stop':
            self.protocol.pause()
        else:
            self.protocol.play()

    def next_pressed(self):
        Logger.debug('Application: next_pressed()')
        self.protocol.next()

    def repeat_pressed(self):
        Logger.debug('Application: repeat_pressed()')
        self.protocol.repeat(str(1-int(self.mpd_status['repeat'])))

    def single_pressed(self):
        Logger.debug('Application: single_pressed()')
        self.protocol.single(str(1-int(self.mpd_status['single'])))

    def random_pressed(self):
        Logger.debug('Application: random_pressed()')
        self.protocol.random(str(1-int(self.mpd_status['random'])))

    def consume_pressed(self):
        Logger.debug('Application: consume_pressed()')
        self.protocol.consume(str(1-int(self.mpd_status['consume'])))

    @inlineCallbacks
    def browser_add(self,clearfirst):
        Logger.debug('Application: browser_add('+str(clearfirst)+')')
        if clearfirst:
            Logger.info('Browser: Clearing playlist')
            self.protocol.clear()
        for row in self.browser_marked:
            mtype=self.browser_marked[row]['type']
            Logger.info("Browser: Adding "+mtype+" '"+row+"' to current playlist")
            if mtype == 'uri':
                self.protocol.add(row)
            elif mtype == 'albumartistsort':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'album':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row,'albumartistsort',self.browser_marked[row]['albumartistsort'])
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+",albumartistsort,"+self.browser_marked[row]['albumartistsort']+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'artistsort':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'title':
                self.protocol.command_list_ok_begin()
                self.protocol.find('artistsort',self.browser_marked[row]['artistsort'],mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find(artistsort,"+self.browser_marked[row]['artistsort']+","+mtype+","+row+") = "+format(result))
                if result:
                    self.protocol.add(result[0]['file'])
            else:
                Logger.warning("Browser: "+mtype+' not implemented')

    @inlineCallbacks
    def populate_file_browser(self):
        self.browser_marked={}
        base=self.file_browser_base
        (hbase,tbase)=os.path.split(base)
        Logger.info("Application: populate_file_browser, base=["+base+"], tbase=["+tbase+"]")
        self.ids.library_files_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if base != '/':
            (b1,b2)=os.path.split(hbase)
            if b2 == '':
                b2 = 'root'
            btn = Button(text=".. ("+b2+")",size_hint_y=None,height='50sp')
            btn.base=os.path.normpath(base+'/..')
            if btn.base == '.':
                btn.base = '/'
            btn.bind(on_press=self.file_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=tbase,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
        self.protocol.command_list_ok_begin()
        self.protocol.lsinfo(base)
        reslist=yield self.protocol.command_list_end()
        result=reslist[0]
        pos=0
        for row in result:
            if 'directory' in row:
                Logger.debug("FileBrowser: directory found: ["+row['directory']+"]")
                (b1,b2)=os.path.split(row['directory'])
                btn = ScrollButton(text=b2)
                btn.base = row['directory']
                btn.repopulate = True
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
                btn.base=os.path.normpath(base)
                btn.repopulate = False
                btn.plpos=pos
                btn.bind(on_press=self.file_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['file']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
            pos+=1
        self.ids.library_files_sv.add_widget(layout)

    def file_browser_button(self,instance):
        Logger.debug('Application: file_browser_button('+instance.text+')')
        if instance.repopulate:
            self.file_browser_base=instance.base
            self.populate_file_browser()
        else:
            self.protocol.clear()
            self.protocol.add(instance.base)
            self.protocol.play(str(instance.plpos))

    @inlineCallbacks
    def populate_album_browser(self):
        self.album_browser_marked={}
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        Logger.info("Application: populate_album_browser, base=["+base+"] level=["+level+"]")
        self.ids.library_albums_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if level == 'root':
            self.protocol.command_list_ok_begin()
            self.protocol.list('albumartistsort')
            reslist=yield self.protocol.command_list_end()
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
            btn = Button(text=".. (root)",size_hint_y=None,height='50sp')
            btn.base = upto
            btn.nextlevel = 'root'
            btn.bind(on_press=self.album_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
            self.protocol.command_list_ok_begin()
            self.protocol.list('album','albumartistsort',base)
            reslist=yield self.protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug('AlbumBrowser: album found = '+row)
                btn = ScrollButton(text=row,size_hint_y=None)
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
            btn = Button(text=".. ("+upto+")",size_hint_y=None,height='50sp')
            btn.base = upto
            btn.nextlevel = 'artist'
            btn.bind(on_press=self.album_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
            self.protocol.command_list_ok_begin()
            self.protocol.find('album',base,'albumartistsort',upto)
            reslist=yield self.protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("AlbumBrowser: track found = "+row['file'])
                btn = ScrollButton(text=formatsong(row),size_hint_y=None)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['file']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        self.ids.library_albums_sv.add_widget(layout)

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
        self.ids.library_tracks_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if level == 'root':
            self.protocol.command_list_ok_begin()
            self.protocol.list('artistsort')
            reslist=yield self.protocol.command_list_end()
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
            btn = Button(text=".. (root)",size_hint_y=None,height='50sp')
            btn.base = 'root'
            btn.bind(on_press=self.track_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
            self.protocol.command_list_ok_begin()
            self.protocol.list('title','artistsort',base)
            reslist=yield self.protocol.command_list_end()
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
        self.ids.library_tracks_sv.add_widget(layout)

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
#        self.ids.library_playlists_panel.clear_widgets()
        self.ids.library_playlists_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        self.protocol.command_list_ok_begin()
        self.protocol.listplaylists()
        reslist=yield self.protocol.command_list_end()
        result=reslist[0]
        for row in result:
            Logger.debug("PlaylistBrowser: playlist found = "+row['playlist'])
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            btn = ScrollButton(text=row['playlist'])
            btn.texture_update()
            bl.add_widget(chk)
            bl.add_widget(btn)
            layout.add_widget(bl)
            Logger.debug("PlaylistBrowser: btn.height "+format(btn.height))
            nh=kivy.metrics.sp((int(btn.height/Metrics.dpi/(Metrics.density*Metrics.density))*20))+kivy.metrics.sp(btn.padding_y)
            Logger.debug("PlaylistBrowser: nh = "+str(nh))
            if nh < kivy.metrics.sp(50):
                nh = kivy.metrics.sp(50)
            bl.height=nh
            Logger.debug('PlaylistBrowser: bl.height '+format(bl.height))
        self.ids.library_playlists_sv.add_widget(layout)

    def browser_checkbox_pressed(self,checkbox,value):
        Logger.debug("Application: browser_checkbox_pressed("+checkbox.base+","+format(checkbox.info)+")")
        if value:
            self.browser_marked[checkbox.base]=checkbox.info
        else:
            if checkbox.base in self.browser_marked:
                del self.browser_marked[checkbox.base]

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
    Logger.info("Metrics: 1 sp = "+format(kivy.metrics.sp(1)))
    KmpcApp().run()

