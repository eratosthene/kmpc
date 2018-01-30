import os
import io
from functools import partial
from subprocess import call, PIPE, Popen
from kmpc.mpd import MPDProtocol
from kmpc.mpdfactory import MPDClientFactory

import kivy
kivy.require('1.10.0')

from twisted.internet.defer import Deferred

from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem

class Sync(object):

    def __init__(self,config,runparts=[]):
        from twisted.internet import reactor
        self.config=config
        self.mpdhost=config.get('mpd','mpdhost')
        self.mpdport=config.get('mpd','mpdport')
        self.synchost=config.get('sync','synchost')
        self.syncmpdport=config.get('sync','syncmpdport')
        self.synclist=config.get('sync','syncplaylist')
        self.basepath=config.get('paths','musicpath')
        self.syncbasepath=config.get('sync','syncmusicpath')
        self.tmppath=config.get('paths','tmppath')
        self.runparts=runparts
        self.localconnected=False
        self.syncconnected=False
        self.kivy=True
        Logger.info("Sync: running sync with synchost "+self.synchost)
        if self.mpdhost==self.synchost:
            Logger.warn('Sync: will not sync identical hosts!')
            return
        self.localmpd=MpdConnection(self.config,self.mpdhost,self.mpdport,None,[self.init_local_mpd],True)
        self.syncmpd=MpdConnection(self.config,self.synchost,self.syncmpdport,None,[self.init_sync_mpd],True)
        if not reactor.running:
            self.kivy=False
            reactor.run()

    def init_local_mpd(self,conn):
        Logger.debug("init_local_mpd: connected")
        self.localconnected=True
        self.do_sync()

    def init_sync_mpd(self,conn):
        Logger.debug("init_sync_mpd: connected")
        self.syncconnected=True
        self.do_sync()

    def do_sync(self):
        if self.localconnected and self.syncconnected:
            Logger.info("Sync: beginning sync process")
            d=Deferred()
            for part in self.runparts:
                d.addCallback(getattr(self,'sync_'+part))
            d.addCallback(self.finish_sync)
            d.addErrback(self.errback)
            d.callback(None)

    def errback(self,result):
        Logger.error('Sync: Callback error: {}'.format(result))

    def finish_sync(self,result):
        from twisted.internet import reactor
        Logger.debug("finish_sync: "+result)
        if not self.kivy:
            reactor.stop()

    def sync_test(self,result):
        Logger.debug("Sync: test "+result)
        return "test done"

    def sync_synclist(self,result):
        Logger.info("Sync: syncing using playlist ["+self.synclist+"]")
        return self.syncmpd.protocol.listplaylist(self.synclist).addCallback(self.build_filelist).addErrback(self.syncmpd.handle_mpd_error)

    def build_filelist(self,result):
        filelist={}
        Helpers=KmpcHelpers()
        # write synclist to a temp file and a hash
        f=io.open(os.path.join(self.tmppath,'rsync.inc'),mode='w',encoding="utf-8")
        for row in result:
            f.write(Helpers.decodeFileName(row)+"\n")
            filelist[Helpers.decodeFileName(row.rstrip())]=True
        f.close()
        # this whole block walks the filesystem and deletes any file that is not in the synclist
        for dirpath, dirnames, filenames in os.walk(Helpers.decodeFileName(self.basepath)):
            if len(filenames)>0:
                rpath = dirpath[len(self.basepath+os.sep):]
                for filename in filenames:
                    fpath=os.path.join(Helpers.decodeFileName(rpath),Helpers.decodeFileName(filename))
                    apath = os.path.join(Helpers.decodeFileName(dirpath),Helpers.decodeFileName(filename))
                    if fpath not in filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(Helpers.decodeFileName(apath))
        # remove empty folders
        Helpers.removeEmptyFolders(self.basepath)
        # rsync the files
        call([
            'rsync',
            '-vruxhm',
            '--files-from='+os.path.join(self.tmppath,'rsync.inc'),
            self.synchost+':'+self.syncbasepath+'/',
            self.basepath
            ])

        # clean up
#        os.remove(os.path.join(self.tmppath,'rsync.inc'))
        return 'synclist done'

# this class just returns a debug message for all calls to it to handle bad mpd connections
class Dummy(object):
    def __getattr__(self,attr):
        Logger.debug("MpdConnection: no connection when calling "+attr+" method")
        return self
    def __call__(self,*args):
        return self

class MpdConnection(object):

    def __init__(self,config,mpdhost,mpdport,idlehandler=None,initconnections=[],quiet=False):
        self.config = config
        self.mpdhost = mpdhost
        self.mpdport = mpdport
        self.quiet = quiet
        Logger.debug("MpdConnection: connecting to "+mpdhost+":"+mpdport)
        # set up mpd connection
        self.initconnections=initconnections
        self.factory = MPDClientFactory(idlehandler)
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        from twisted.internet import reactor
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
        if not self.quiet: Logger.info('MpdConnection: Connected to mpd server host='+self.mpdhost+' port='+self.mpdport)
        for ic in self.initconnections:
            if callable(ic):
                 ic(self)

    def mpd_connectionLost(self,protocol, reason):
        """Callback when mpd connection is lost."""
        if not self.quiet: Logger.warn('MpdConnection: Connection lost: %s' % reason)

    def handle_mpd_error(self,result):
        """Prints handled errors to the error log."""
        if not self.quiet: Logger.error('MpdConnection: Callback error: {}'.format(result))

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
