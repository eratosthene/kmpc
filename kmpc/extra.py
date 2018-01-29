import os
from kmpc.mpd import MPDProtocol
from kmpc.mpdfactory import MPDClientFactory

import kivy
kivy.require('1.10.0')

#install twisted reactor to interface with mpd
from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor, protocol
from twisted.internet.defer import inlineCallbacks

from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem

# this class just returns a debug message for all calls to it to handle bad mpd connections
class Dummy(object):
    def __getattr__(self,attr):
        Logger.debug("MpdConnection: no connection when calling "+attr+" method")
        return self
    def __call__(self,*args):
        return self

class MpdConnection(object):

    def __init__(self,config,mpdhost,mpdport,idlehandler=None,initconnections=[]):
        self.config = config
        self.mpdhost = mpdhost
        self.mpdport = mpdport
        # set up mpd connection
        self.initconnections=initconnections
        self.factory = MPDClientFactory(idlehandler)
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        reactor.connectTCP(mpdhost, int(mpdport), self.factory)
        self.noprotocol=Dummy()

    # this part handles calls to protocol when it hasn't been set up yet or is incorrectly specified in config
    @property
    def protocol(self):
        try:
            if self.realprotocol:
                return self.realprotocol
        except AttributeError:
            Logger.debug("MpdConnection: no mpd connected")
            return self.noprotocol

    def mpd_connectionMade(self,protocol):
        """Callback when mpd is connected."""
        # copy the protocol to all the classes
        self.realprotocol = protocol
        Logger.info('mpd_connectionMade: Connected to mpd server host='+self.mpdhost+' port='+self.mpdport)
        for ic in self.initconnections:
            if callable(ic):
                 ic(self)

    def mpd_connectionLost(self,protocol, reason):
        """Callback when mpd connection is lost."""
        Logger.warn('mpd_connectionLost: Connection lost: %s' % reason)

    def handle_mpd_error(self,result):
        """Prints handled errors to the error log."""
        Logger.error('Application: MPDIdleHandler Callback error: {}'.format(result))

class KmpcHelpers(object):

    def formatsong(self,rec):
        """Method used by library browser to properly format a song row."""
        song = ''
        # check if there is more than one disc and display if so
        (d1,d2)=rec['disc'].split('/')
        if int(d2) > 1:
            song+='(Disc '+'%02d' % int(d1)+') '
        # sometimes track numbers are like '01/05' (one of five), so drop that second number
        (t1,t2)=rec['track'].split('/')
        song+='%02d' % int(t1)+' '
        # if albumartist is different than track artist, display the track artist
        if rec['artist'] != rec['albumartist']:
            song+=rec['artist']+' - '
        # display the track title
        song+=rec['title']
        return song

    # fontawesome strings and subjective interpretations of song ratings.
    def songratings(self,config):
        sr= {
            '0': {'stars': u"\uf006\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','star0')},
            '1': {'stars': u"\uf123\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','star1')},
            '2': {'stars': u"\uf005\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','star2')},
            '3': {'stars': u"\uf005\uf123\uf006\uf006\uf006",'meaning':config.get('songratings','star3')},
            '4': {'stars': u"\uf005\uf005\uf006\uf006\uf006",'meaning':config.get('songratings','star4')},
            '5': {'stars': u"\uf005\uf005\uf123\uf006\uf006",'meaning':config.get('songratings','star5')},
            '6': {'stars': u"\uf005\uf005\uf005\uf006\uf006",'meaning':config.get('songratings','star6')},
            '7': {'stars': u"\uf005\uf005\uf005\uf123\uf006",'meaning':config.get('songratings','star7')},
            '8': {'stars': u"\uf005\uf005\uf005\uf005\uf006",'meaning':config.get('songratings','star8')},
            '9': {'stars': u"\uf005\uf005\uf005\uf005\uf123",'meaning':config.get('songratings','star9')},
            '10': {'stars': u"\uf005\uf005\uf005\uf005\uf005",'meaning':config.get('songratings','star10')},
            '' : {'stars': u"\uf29c", 'meaning':'No sticker set'}
        }
        return sr

    def getfontsize(self,str,scale=1):
        """Method that determines font size based on text length."""
        # helper array for scaling font sizes based on text length
        #sizearray = ['39sp','38sp','37sp','36sp','35sp','34sp','33sp','32sp','31sp','30sp','29sp','28sp','27sp','26sp','25sp']
        sizearray = ['39','38','37','36','35','34','33','32','31','30','29','28','27','26','25']
        lr = len(str)
        if lr < 33:
            rsize = '40'
        elif lr >= 55:
            rsize = '24'
        else:
            rsize = sizearray[int(round((lr-33)/21*14))]
        return format(int(round(int(rsize)/scale)))+'sp'

    def decodeFileName(self,name):
        """Method that tries to intelligently decode a filename to handle unicode weirdness."""
        if type(name) == str:
            try:
                name = name.decode('utf8')
            except:
                name = name.decode('windows-1252')
        return name

class ExtraSlider(Slider):
    """Class that implements some extra stuff on top of a standard slider."""

    def __init__(self,**kwargs):
        """Do normal init routine, but also register on_release event."""
        super(self.__class__,self).__init__(**kwargs)
        self.register_event_type('on_release')

    def on_release(self):
        """Override this with something you want this slider to do."""
        pass

    def on_touch_up(self, touch):
        """Check if slider is released, dispatch the on_release event if so."""
        released = super(self.__class__,self).on_touch_up(touch)
        if released:
            self.dispatch('on_release')
        return released

class OutlineLabel(Label):
    """A label that has an outline around it."""
    pass

class OutlineButton(Button,OutlineLabel):
    """A button with a label that has an outline around it."""
    pass

class ClearButton(Button,OutlineLabel):
    """A button that is clear instead of opaque."""
    pass

class OutlineTabbedPanelItem(TabbedPanelItem,OutlineLabel):
    """A label that has an outline around it."""
    pass
