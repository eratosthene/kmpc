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
        syncbasepath = App.get_running_app().root.config.get('mpd','syncbasepath')
        syncfanartpath= App.get_running_app().root.config.get('mpd','syncfanartpath')
        basepath = App.get_running_app().root.config.get('mpd','basepath')
        fanartpath= App.get_running_app().root.config.get('mpd','fanartpath')
        Logger.info('Filesync: Copying rsync file to carpi')
        call(["scp",synchost+":rsync.inc",tpath])
        filelist={}
        with codecs.open(tpath,'r','utf-8') as f:
            for line in f:
                filelist[line.rstrip().encode(encoding='UTF-8')]=True
        Logger.info('Filesync: Removing old files from carpi')
        for dirpath, dirnames, filenames in os.walk(basepath):
            if len(filenames)>0:
                rpath = dirpath[len(basepath+os.sep):].encode(encoding='UTF-8')
                for filename in filenames:
                    fpath=os.path.join(rpath,filename.encode(encoding='UTF-8'))
                    apath = os.path.join(dirpath.encode(encoding='UTF-8'),filename.encode(encoding='UTF-8'))
                    if fpath not in filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(apath)
        Logger.info('Filesync: Removing empty directories from carpi')
        call(['find',basepath,'-type','d','-empty','-delete'])
        Logger.info('Filesync: Rsyncing new files to carpi')
        call(['rsync','-vruxhm','--progress','--files-from='+tpath,synchost+':'+syncbasepath+'/',basepath])
        Logger.info('Filesync: Updating sticker databases')
        Logger.debug('Filesync: Copying stickers from carpi')
        call(['scp','/var/lib/mpd/sticker.sql',synchost+':/tmp'])
        Logger.debug('Filesync: Merging sticker databases')
        with open('/tmp/scmd','w') as f:
            f.write("attach database \"/tmp/sticker.sql\" as carpi;\n")
            f.write("replace into sticker select * from carpi.sticker;\n")
            f.write("replace into carpi.sticker select * from sticker where name='rating';\n")
            f.write(".quit\n")
        call(['scp','/tmp/scmd',synchost+':/tmp'])
        call(['ssh','-t',synchost,'sudo','sqlite3','/var/lib/mpd/sticker.sql','<','/tmp/scmd'])
        Logger.debug('Filesync: Copying stickers to carpi')
        call(['scp',synchost+':/tmp/sticker.sql','/tmp'])
        with open('/tmp/scmd','w') as f:
            f.write("attach database \"/tmp/sticker.sql\" as carpi;\n")
            f.write("replace into sticker select * from carpi.sticker;\n")
            f.write(".quit\n")
        with open('/tmp/scmd','r') as f:
            call(['sudo','sqlite3','/var/lib/mpd/sticker.sql'],stdin=f)
        Logger.info('Filesync: Cleaning up')
        os.remove(tpath)
        os.remove('/tmp/sticker.sql')
        os.remove('/tmp/scmd')
        call(['ssh',synchost,'rm','-f','/tmp/sticker.sql'])
        call(['ssh',synchost,'rm','-f','/tmp/scmd'])
        Logger.info("Filesync: Syncing fanart")
        call(['rsync','-vruxhm','--progress',synchost+':'+syncfanartpath+'/',fanartpath])
