import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.support import install_twisted_reactor
from kivy.config import Config
import ConfigParser
from mpd import MPDFactory

#kivy display settings
Config.set('graphics','width','800')
Config.set('graphics','height','480')

#read config values
config = ConfigParser.ConfigParser()
config.read('kmpc.ini')
MPD_HOST = config.get('mpd','host')
MPD_PORT = int(config.get('mpd','port'))

#install twisted reactor to interface with mpd
import sys
if 'twisted.internet.reactor' in sys.modules:
    del sys.modules['twisted.internet.reactor']
install_twisted_reactor()
from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.defer import inlineCallbacks

class KmpcInterface(TabbedPanel):
    def __init__(self):
        super(self.__class__,self).__init__()
        self.factory = MPDFactory()
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        reactor.connectTCP(MPD_HOST, MPD_PORT, self.factory)
    def mpd_connectionMade(self,protocol):
        self.mpd_protocol = protocol
        print 'Connected to mpd server host='+MPD_HOST+' port='+str(MPD_PORT)
        self.status_task=task.LoopingCall(self.update_current_status)
        self.status_task.start(1.0)
    def mpd_connectionLost(self,protocol, reason):
        print 'Connection lost: %s' % reason
    @inlineCallbacks
    def update_current_status(self):
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.status()
        self.mpd_protocol.currentsong()
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0]
        c,t=result['time'].split(":")
        cm,cs=divmod(int(c),60)
        tm,ts=divmod(int(t),60)
        self.ids.current_track_time_label.text = "%02d:%02d" % (cm,cs)
        self.ids.current_track_totaltime_label.text = "%02d:%02d" % (tm,ts)
        self.ids.current_track_progressbar.max = int(t)
        self.ids.current_track_progressbar.value = int(c)
        self.ids.current_playlist_track_number_label.text = "%d of %d" % (int(result['song']),int(result['playlistlength']))
        if int(result['repeat']):
            self.ids.repeat_button.state='down'
        else:
            self.ids.repeat_button.state='normal'
        if int(result['single']):
            self.ids.single_button.state='down'
        else:
            self.ids.single_button.state='normal'
        if int(result['random']):
            self.ids.shuffle_button.state='down'
        else:
            self.ids.shuffle_button.state='normal'
        if int(result['consume']):
            self.ids.consume_button.state='down'
        else:
            self.ids.consume_button.state='normal'
        if result['state']=='pause':
            self.ids.play_button.state='normal'
            self.ids.play_button.text='Play'
        else:
            self.ids.play_button.state='down'
            self.ids.play_button.text='Pause'
        ns=result['nextsong']
        result=reslist[1]
        self.ids.current_song_label.text = result['title']
        self.ids.current_artist_label.text = result['artist']
        self.ids.current_album_label.text = result['album']
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.playlistinfo(ns)
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0][0]
        self.ids.next_song_artist_label.text = result['artist']+' - '+result['title']
    def prev_pressed(self):
        self.mpd_protocol.previous()
        self.update_current_status()
    def play_pressed(self):
        if self.ids.play_button.state == 'normal':
            self.mpd_protocol.pause()
        else: #playing
            self.mpd_protocol.play()
        self.update_current_status()
    def next_pressed(self):
        self.mpd_protocol.next()
        self.update_current_status()
    def repeat_pressed(self):
        if self.ids.repeat_button.state == 'normal':
            self.mpd_protocol.repeat(0)
        else:
            self.mpd_protocol.repeat(1)
        self.update_current_status()
    def single_pressed(self):
        if self.ids.single_button.state == 'normal':
            self.mpd_protocol.single(0)
        else:
            self.mpd_protocol.single(1)
        self.update_current_status()
    def shuffle_pressed(self):
        if self.ids.shuffle_button.state == 'normal':
            self.mpd_protocol.random(0)
        else:
            self.mpd_protocol.random(1)
        self.update_current_status()
    def consume_pressed(self):
        if self.ids.consume_button.state == 'normal':
            self.mpd_protocol.consume(0)
        else:
            self.mpd_protocol.consume(1)
        self.update_current_status()
    @inlineCallbacks
    def refresh_artists(self):
        self.mpd_protocol.command_list_ok_begin()
        self.mpd_protocol.list('albumartist')
        reslist=yield self.mpd_protocol.command_list_end()
        result=reslist[0]
        print "%s" % result

class KmpcApp(App):
    def build(self):
        return KmpcInterface()

if __name__ == '__main__':
    KmpcApp().run()

