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
	self.mpd_protocol.status().addCallback(self.mpd_print_status)
        #update everything possible from the status() command
        self.mpd_protocol.status().addCallback(self.update_current_status)
        #update everything possible from the currentsong() command
        self.mpd_protocol.currentsong().addCallback(self.update_current_song)
    def mpd_connectionLost(self,protocol, reason):
        print 'Connection lost: %s' % reason
    def mpd_print_status(self,result):
	print 'Status: %s' % result
    def update_current_status(self,result):
        c,t=result['time'].split(":")
        cm,cs=divmod(int(c),60)
        tm,ts=divmod(int(t),60)
        self.ids.current_track_time_label.text = "%02d:%02d" % (cm,cs)
        self.ids.current_track_totaltime_label.text = "%02d:%02d" % (tm,ts)
        self.ids.current_track_progressbar.max = int(t)
        self.ids.current_track_progressbar.value = int(c)
        self.ids.current_playlist_track_number_label.text = "%d of %d" % (int(result['song']),int(result['playlistlength']))
    def update_current_song(self,result):
        self.ids.current_song_label.text = result['title']
        self.ids.current_artist_label.text = result['artist']
        self.ids.current_album_label.text = result['album']

class KmpcApp(App):
    def build(self):
        return KmpcInterface()

if __name__ == '__main__':
    KmpcApp().run()

