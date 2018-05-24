import os
import io

from twisted.internet.defer import Deferred, DeferredList
import kivy
from kivy.logger import Logger

# make sure we are on updated version of kivy
kivy.require('1.10.0')


class KmpcHelpers(object):

    def formatsong(self, rec):
        """Method used by library browser to properly format a song row."""
        song = ''
        # check if there is more than one disc and display if so
        dd = rec['disc'].split('/')
        if len(dd) > 1:
            if int(dd[1]) > 1:
                song += '(Disc ' + '%02d' % int(dd[0]) + ') '
        # sometimes track numbers are like '01/05' (one of five), so drop that
        # second number
        tt = rec['track'].split('/')
        song += '%02d' % int(tt[0]) + ' '
        # if albumartist is different than track artist, display the track
        # artist
        if rec['artist'] != rec['albumartist']:
            song += rec['artist'] + ' - '
        # display the track title
        song += rec['title']
        return song

    def getfontsize(self, s, scale=1):
        """Method that determines font size based on text length."""
        # helper array for scaling font sizes based on text length
        sizearray = ['39', '38', '37', '36', '35', '34', '33', '32',
                     '31', '30', '29', '28', '27', '26', '25']
        lr = len(s)
        if lr < 33:
            rsize = '40'
        elif lr >= 55:
            rsize = '24'
        else:
            rsize = sizearray[int(round((lr-33)/21*14))]
        return format(int(round(int(rsize)/scale))) + 'sp'

    def decodeFileName(self, name):
        """Method that tries to intelligently decode a filename to handle
        unicode weirdness."""
        if type(name) == str:
            try:
                name = name.decode('utf8')
            except Exception:
                name = name.decode('windows-1252')
        return name

    def removeEmptyFolders(self, path, removeRoot=True):
        """Function to remove empty folders"""
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
            Logger.debug("removeEmptyDir:" + path)
            os.rmdir(path)
