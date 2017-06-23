import kivy
kivy.require('1.10.0')
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

class ScrollButton(Button):
    pass

class ScrollBoxLayout(BoxLayout):
    pass

def formatsong(rec):
    song = ''
    (d1,d2)=rec['disc'].split('/')
    if int(d2) > 1:
        song+='(Disc '+'%02d' % int(d1)+') '
    (t1,t2)=rec['track'].split('/')
    song+='%02d' % int(t1)+' '+rec['title']
    return song
