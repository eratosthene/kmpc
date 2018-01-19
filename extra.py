import kivy
kivy.require('1.10.0')
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider

def formatsong(rec):
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
# 'meaning' should probably be broken out into the ini file for runtime configuration
songratings = {
        '0': {'stars': u"\uf006\uf006\uf006\uf006\uf006",'meaning':'Silence'},
        '1': {'stars': u"\uf123\uf006\uf006\uf006\uf006",'meaning':'Songs that should never be heard'},
        '2': {'stars': u"\uf005\uf006\uf006\uf006\uf006",'meaning':'Songs no one likes'},
        '3': {'stars': u"\uf005\uf123\uf006\uf006\uf006",'meaning':'Songs for certain occasions'},
        '4': {'stars': u"\uf005\uf005\uf006\uf006\uf006",'meaning':'Songs someone else likes'},
        '5': {'stars': u"\uf005\uf005\uf123\uf006\uf006",'meaning':'Filler tracks with no music'},
        '6': {'stars': u"\uf005\uf005\uf005\uf006\uf006",'meaning':'Meh track or short musical filler'},
        '7': {'stars': u"\uf005\uf005\uf005\uf123\uf006",'meaning':'Occasional listening songs'},
        '8': {'stars': u"\uf005\uf005\uf005\uf005\uf006",'meaning':'Great songs for all occasions'},
        '9': {'stars': u"\uf005\uf005\uf005\uf005\uf123",'meaning':'Best songs by an artist'},
        '10': {'stars': u"\uf005\uf005\uf005\uf005\uf005",'meaning':'Favorite songs of all time'},
        '' : {'stars': u"\uf29c", 'meaning':'No sticker set'}
}

# helper array for scaling font sizes based on text length
sizearray = ['39sp','38sp','37sp','36sp','35sp','34sp','33sp','32sp','31sp','30sp','29sp','28sp','27sp','26sp','25sp']

def getfontsize(str):
    """Method that determines font size based on text length."""
    lr = len(str)
    if lr < 33:
	rsize = '40sp'
    elif lr >= 55:
	rsize = '24sp'
    else:
	rsize = sizearray[int(round((lr-33)/21*14))]
    return rsize

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
