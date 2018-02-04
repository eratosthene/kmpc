import os
import io

import kivy
kivy.require('1.10.0')

from twisted.internet.defer import Deferred,DeferredList

from kivy.logger import Logger

class KmpcHelpers(object):

    def formatsong(self,rec):
        """Method used by library browser to properly format a song row."""
        song = ''
        # check if there is more than one disc and display if so
        dd=rec['disc'].split('/')
        if len(dd)>1:
            if int(dd[1]) > 1:
                song+='(Disc '+'%02d' % int(dd[0])+') '
        # sometimes track numbers are like '01/05' (one of five), so drop that second number
        tt=rec['track'].split('/')
        song+='%02d' % int(tt[0])+' '
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

    def removeEmptyFolders(self,path,removeRoot=True):
        'Function to remove empty folders'
        if not os.path.isdir(path):
            return
        # remove empty subfolders
        files = os.listdir(path)
        if len(files):
            for f in files:
                fullpath = os.path.join(path, f)
                if os.path.isdir(fullpath):
                     self.removeEmptyFolders(fullpath)
        # if folder empty, delete it
        files = os.listdir(path)
        if len(files) == 0 and removeRoot:
            Logger.debug("removeEmptyDir:"+path)
            os.rmdir(path)

