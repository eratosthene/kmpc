import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
import git
import os
import stat
import codecs
import socket
from subprocess import call, PIPE, Popen
from threading import Thread
from Queue import Queue, Empty
from functools import partial

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
        self.ids.ip_label.text="IP Address: "+format(self.get_ip())

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

    def do_reboot(self):
        Logger.info('Config: reboot')
        call('reboot')

    def do_poweroff(self):
        Logger.info('Config: poweroff')
        call('poweroff')

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def enqueue_output(self,out,queue,event,popup,tpath,synchost,layout,sv):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()
        event.cancel()
        popup.dismiss()
        Logger.info('Filesync: Cleaning up')
        l=Label(text='Cleaning up temporary files',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        try:
            call(['sudo','cp',tpath,'/var/lib/mpd/playlists/root.m3u'])
            os.remove(tpath)
            os.remove('/tmp/sticker.sql')
            os.remove('/tmp/scmd')
            os.remove('sync.sh')
            call(['ssh',synchost,'rm','-f','/tmp/sticker.sql'])
            call(['ssh',synchost,'rm','-f','/tmp/scmd'])
        except:
            pass

    def write_queue_line(self,q,layout,sv,dt):
        try: line=q.get_nowait()
        except Empty:
            pass
        else:
            l=Label(text=line,size_hint=(None,None),font_size='12sp',halign='left')
            l.bind(texture_size=l.setter('size'))
            layout.add_widget(l)
            sv.scroll_to(l)

    def filesync(self):
        Logger.info('Config: filesync')
        layout = GridLayout(cols=1, spacing=1, padding=1, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        popup = Popup(title='Sync',size_hint=(0.8,1))
        sv=ScrollView(size_hint=(1,1))
        sv.add_widget(layout)
        popup = Popup(title='Sync',content=sv,size_hint=(0.8,1))
        popup.open()
        tpath="/tmp/rsync.inc"
        synchost = App.get_running_app().root.config.get('mpd','synchost')
        syncbasepath = App.get_running_app().root.config.get('mpd','syncbasepath')
        syncfanartpath= App.get_running_app().root.config.get('mpd','syncfanartpath')
        basepath = App.get_running_app().root.config.get('mpd','basepath')
        fanartpath= App.get_running_app().root.config.get('mpd','fanartpath')
        Logger.info('Filesync: Copying rsync file to carpi')
        l=Label(text='Copying rsync file to carpi',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        call(["scp",synchost+":rsync.inc",tpath])
        filelist={}
        with codecs.open(tpath,'r','utf-8') as f:
            for line in f:
                filelist[line.rstrip().encode(encoding='UTF-8')]=True
        Logger.info('Filesync: Removing old files from carpi')
        l=Label(text='Removing old files from carpi',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        for dirpath, dirnames, filenames in os.walk(basepath):
            if len(filenames)>0:
                rpath = dirpath[len(basepath+os.sep):].encode(encoding='UTF-8')
                for filename in filenames:
                    fpath=os.path.join(rpath,filename.encode(encoding='UTF-8'))
                    apath = os.path.join(dirpath.encode(encoding='UTF-8'),filename.encode(encoding='UTF-8'))
                    if fpath not in filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(apath)
        with open('sync.sh','w') as sfile:
            sfile.write("#!/bin/bash\n")
            sfile.write('find "'+basepath+'" -type d -empty -delete 2>/dev/null\n')
            sfile.write('rsync -vruxhm --files-from="'+tpath+'" '+synchost+':"'+syncbasepath+'"/ "'+basepath+'"\n')
            sfile.write('scp /var/lib/mpd/sticker.sql '+synchost+':/tmp\n')
            with open('/tmp/scmd','w') as f:
                f.write("attach database \"/tmp/sticker.sql\" as carpi;\n")
                f.write("replace into sticker select * from carpi.sticker;\n")
                f.write("replace into carpi.sticker select * from sticker where name='rating';\n")
                f.write(".quit\n")
            sfile.write('scp /tmp/scmd '+synchost+':/tmp\n')
            sfile.write('ssh -t '+synchost+' sudo sqlite3 /var/lib/mpd/sticker.sql < /tmp/scmd\n')
            sfile.write('scp '+synchost+':/tmp/sticker.sql /tmp\n')
            with open('/tmp/scmd','w') as f:
                f.write("attach database \"/tmp/sticker.sql\" as carpi;\n")
                f.write("replace into sticker select * from carpi.sticker;\n")
                f.write(".quit\n")
            sfile.write('cat /tmp/scmd | sudo sqlite3 /var/lib/mpd/sticker.sql\n')
            sfile.write('rsync -vruxhm '+synchost+':"'+syncfanartpath+'"/ "'+fanartpath+'"\n')
            sfile.write("mpc update\n")
        os.chmod('sync.sh',os.stat('sync.sh').st_mode|0111)
        q = Queue()
        p = Popen(['./sync.sh'],stdout=PIPE,bufsize=1,close_fds=True)
        event=Clock.schedule_interval(partial(self.write_queue_line,q,layout,sv),0.1)
        t = Thread(target=self.enqueue_output,args=(p.stdout,q,event,popup,tpath,synchost,layout,sv))
        t.daemon = True
        t.start()
