import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.logger import Logger
from kivy.app import App
import git
import os
from subprocess import call
import codecs

class ConfigTabbedPanelItem(TabbedPanelItem):

    def handle_mpd_error(self,result):
        Logger.error('Config: MPDIdleHandler Callback error: {}'.format(result))

    def update_mpd_status(self,result):
        Logger.debug('Config: update_mpd_status')
        if 'xfade' in result:
            v = int(result['xfade'])
        else:
            v = 0
        self.ids.crossfade_slider.value=v
        if 'mixrampdb' in result:
            v = round(float(result['mixrampdb']),6)
        else:
            v = 0.0
        self.ids.mixrampdb_slider.value=float(str(v)[1:])
        if 'mixrampdelay' in result:
            v = round(float(result['mixrampdelay']),6)
        else:
            v = 0.0
        self.ids.mixrampdelay_slider.value=v

    def printit(self,result):
        print format(result)

    def change_crossfade(self):
        Logger.info('Config: change_crossfade')
        v=int(round(self.ids.crossfade_slider.value))
        self.protocol.crossfade(str(v)).addErrback(self.handle_mpd_error)

    def change_mixrampdb(self):
        Logger.info('Config: change_mixrampdb')
        v=0.0-round(self.ids.mixrampdb_slider.value,6)
        self.protocol.mixrampdb(str(v)).addErrback(self.handle_mpd_error)

    def change_mixrampdelay(self):
        Logger.info('Config: change_mixrampdelay')
        v=round(self.ids.mixrampdelay_slider.value,6)
        self.protocol.mixrampdelay(str(v)).addErrback(self.handle_mpd_error)

    def git_pull(self):
        Logger.info('Config: git_pull')
        g = git.cmd.Git(os.getcwd())
        Logger.info(g.pull())

    def filesync(self):
        Logger.info('Config: filesync')
        tpath="/tmp/rsync.inc"
        synchost = App.get_running_app().root.config.get('mpd','synchost')
        basepath = App.get_running_app().root.config.get('mpd','basepath')
        Logger.info('Filesync: copying rsync file to carpi')
        call(["scp",synchost+":rsync.inc",tpath])
        filelist={}
        with codecs.open(tpath,'r','utf-8') as f:
            for line in f:
                filelist[u""+line.rstrip()]=True
        os.remove(tpath)
        Logger.info('Filesync: removing old files from carpi')
        for dirpath, dirnames, filenames in os.walk(basepath):
            if len(filenames)>0:
                rpath = os.sep.join(dirpath.split(os.sep)[3:])
                for filename in filenames:
                    fpath=u""+os.path.join(rpath,filename)
                    if fpath not in filelist:
                        Logger.debug("Filesync: deleting "+fpath)
                        #os.remove(u""+os.path.join(dirpath,filename))
        Logger.info('Filesync: removing empty directories from carpi')
        call(['find',basepath,'-type','d','-empty','-delete'])
        Logger.info('Filesync: Rsyncing new files to carpi')
        call(['rsync','-vruxhm','--progress','--files-from='+tpath,synchost+':/mnt/music/',basepath])
