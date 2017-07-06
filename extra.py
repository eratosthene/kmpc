import kivy
kivy.require('1.10.0')
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider

def formatsong(rec):
    song = ''
    (d1,d2)=rec['disc'].split('/')
    if int(d2) > 1:
        song+='(Disc '+'%02d' % int(d1)+') '
    (t1,t2)=rec['track'].split('/')
    song+='%02d' % int(t1)+' '
    if rec['artist'] != rec['albumartist']:
        song+=rec['artist']+' - '
    song+=rec['title']
    return song

songratings = {
        '0': {'stars': u"\uf006\uf006\uf006\uf006\uf006",'meaning':'Noise/silence/useless'},
        '1': {'stars': u"\uf123\uf006\uf006\uf006\uf006",'meaning':'Songs that should never be heard'},
        '2': {'stars': u"\uf005\uf006\uf006\uf006\uf006",'meaning':'Songs no one likes'},
        '3': {'stars': u"\uf005\uf123\uf006\uf006\uf006",'meaning':'Songs for certain occasions'},
        '4': {'stars': u"\uf005\uf005\uf006\uf006\uf006",'meaning':'Songs someone else likes'},
        '5': {'stars': u"\uf005\uf005\uf123\uf006\uf006",'meaning':'Only included for discography'},
        '6': {'stars': u"\uf005\uf005\uf005\uf006\uf006",'meaning':'Okay on a random playlist'},
        '7': {'stars': u"\uf005\uf005\uf005\uf123\uf006",'meaning':'Good songs by all artists'},
        '8': {'stars': u"\uf005\uf005\uf005\uf005\uf006",'meaning':'Great songs by all artists'},
        '9': {'stars': u"\uf005\uf005\uf005\uf005\uf123",'meaning':'Best songs by all artists'},
        '10': {'stars': u"\uf005\uf005\uf005\uf005\uf005",'meaning':'Best songs by favorite artists'},
        '' : {'stars': u"\uf29c", 'meaning':'No sticker set'}
}

sizearray = ['39sp','38sp','37sp','36sp','35sp','34sp','33sp','32sp','31sp','30sp','29sp','28sp','27sp','26sp','25sp']

def getfontsize(str):
    lr = len(str)
    if lr < 33:
	rsize = '40sp'
    elif lr >= 55:
	rsize = '24sp'
    else:
	rsize = sizearray[int(round((lr-33)/21*14))]
    return rsize

class ExtraSlider(Slider):

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.register_event_type('on_release')

    def on_release(self):
        pass

    def on_touch_up(self, touch):
        released = super(self.__class__,self).on_touch_up(touch)
        if released:
            self.dispatch('on_release')
        return released

class ClearButton(Button):
    pass
