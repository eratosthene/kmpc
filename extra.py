import kivy
kivy.require('1.10.0')
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

def formatsong(rec):
    song = ''
    (d1,d2)=rec['disc'].split('/')
    if int(d2) > 1:
        song+='(Disc '+'%02d' % int(d1)+') '
    (t1,t2)=rec['track'].split('/')
    song+='%02d' % int(t1)+' '+rec['title']
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
        '10': {'stars': u"\uf005\uf005\uf005\uf005\uf005",'meaning':'Best songs by favorite artists'}
}
