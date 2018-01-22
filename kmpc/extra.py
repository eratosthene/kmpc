import os
import ConfigParser

import kivy
kivy.require('1.10.0')
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider

# sets the location of the config folder
configdir = os.path.expanduser('~')+"/.kmpc"

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

    def loadconfigfile(self):
        # set up config with default values
        config=ConfigParser.SafeConfigParser()
        config.add_section('mpd')
        config.set('mpd','mpdhost','127.0.0.1')
        config.set('mpd','mpdport','6600')
        config.add_section('paths')
        config.set('paths','musicpath','/mnt/music')
        config.set('paths','fanartpath','/mnt/fanart')
        config.set('paths','tmppath','/tmp')
        config.add_section('sync')
        config.set('sync','synchost','127.0.0.1')
        config.set('sync','syncmusicpath','/mnt/music')
        config.set('sync','syncfanartpath','/mnt/fanart')
        config.set('sync','synctmppath','/tmp')
        config.add_section('flags')
        config.set('flags','rpienable','False')
        config.add_section('api')
        config.set('api','fanarturl','http://webservice.fanart.tv/v3/music/')
        config.set('api','api_key','CHANGEME')
        config.set('api','artlog','False')
        config.add_section('songratings')
        config.set('songratings','zero','Silence')
        config.set('songratings','one','Songs that should never be heard')
        config.set('songratings','two','Songs no one likes')
        config.set('songratings','three','Songs for certain occasions')
        config.set('songratings','four','Songs someone else likes')
        config.set('songratings','five','Filler tracks with no music')
        config.set('songratings','six','Meh track or short musical filler')
        config.set('songratings','seven','Occasional listening songs')
        config.set('songratings','eight','Great songs for all occasions')
        config.set('songratings','nine','Best songs by an artist')
        config.set('songratings','ten','Favorite songs of all time')
        # check if config folder exists
        if os.path.isdir(configdir):
            # try to read existing config file
            config.read([configdir+'/config.ini'])
            # write out config file in case it doesn't exist yet
            with open(configdir+'/config.ini','wb') as cf:
                config.write(cf)
        else:
            os.mkdir(configdir)
            # write out config file
            with open(configdir+'/config.ini','wb') as cf:
                config.write(cf)
        # return the generated config
        return config

    # fontawesome strings and subjective interpretations of song ratings.
    def songratings(self,config):
        sr= {
            '0': {'stars': u"\uf006\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','zero')},
            '1': {'stars': u"\uf123\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','one')},
            '2': {'stars': u"\uf005\uf006\uf006\uf006\uf006",'meaning':config.get('songratings','two')},
            '3': {'stars': u"\uf005\uf123\uf006\uf006\uf006",'meaning':config.get('songratings','three')},
            '4': {'stars': u"\uf005\uf005\uf006\uf006\uf006",'meaning':config.get('songratings','four')},
            '5': {'stars': u"\uf005\uf005\uf123\uf006\uf006",'meaning':config.get('songratings','five')},
            '6': {'stars': u"\uf005\uf005\uf005\uf006\uf006",'meaning':config.get('songratings','six')},
            '7': {'stars': u"\uf005\uf005\uf005\uf123\uf006",'meaning':config.get('songratings','seven')},
            '8': {'stars': u"\uf005\uf005\uf005\uf005\uf006",'meaning':config.get('songratings','eight')},
            '9': {'stars': u"\uf005\uf005\uf005\uf005\uf123",'meaning':config.get('songratings','nine')},
            '10': {'stars': u"\uf005\uf005\uf005\uf005\uf005",'meaning':config.get('songratings','ten')},
            '' : {'stars': u"\uf29c", 'meaning':'No sticker set'}
        }
        return sr

    def getfontsize(self,str):
        """Method that determines font size based on text length."""
        lr = len(str)
        if lr < 33:
            rsize = '40sp'
        elif lr >= 55:
            rsize = '24sp'
        else:
            rsize = sizearray[int(round((lr-33)/21*14))]
        return rsize

# helper array for scaling font sizes based on text length
sizearray = ['39sp','38sp','37sp','36sp','35sp','34sp','33sp','32sp','31sp','30sp','29sp','28sp','27sp','26sp','25sp']

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

class ClearButton(Button):
    """A button that is clear instead of opaque."""
    pass
