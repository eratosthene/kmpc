import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
from kivy.lang.builder import Builder
import os
import stat
import codecs
from subprocess import call, PIPE, Popen
from threading import Thread
from Queue import Queue, Empty
from functools import partial

from kmpc.extra import KmpcHelpers, OutlineLabel, OutlineTabbedPanelItem

Helpers=KmpcHelpers()

class SystemTabbedPanelItem(OutlineTabbedPanelItem):
    """The System tab, for internal functions."""

    def printit(self,result):
        """An internal debugging function. Probably shouldn't ever be used."""
        print format(result)

    def update(self):
        """Runs the 'updatecommand' from the config file."""
        Logger.info('System: update')
        call(self.config.get('system','updatecommand').split(' '))

    def do_reboot(self):
        """Method that reboots the host."""
        Logger.info('System: reboot')
        call(['sudo','reboot'])

    def do_poweroff(self):
        """Method that shuts down the host."""
        Logger.info('System: poweroff')
        call(['sudo','poweroff'])

    def enqueue_output(self,out,queue,event,popup,tpath,synchost,layout,sv):
        """Method that is called in its own thread to write commandline script output to a popup, then clean up afterwards."""
        # loop through the stdout output and shove it into the queue
        for line in iter(out.readline, b''):
            queue.put(line)
        # close the output stream, cancel the .1 second update event, dismiss the popup
        out.close()
        event.cancel()
        popup.dismiss() # seems like this is too early, since we're writing more data in the next few lines
        Logger.info('Filesync: Cleaning up')
        l=OutlineLabel(text='Cleaning up temporary files',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        # try removing all temporary files, should probably catch more specific exceptions in case something truly breaks
        try:
            call(['sudo','cp',tpath,'/var/lib/mpd/playlists/root.m3u'])
            os.remove(tpath)
            os.remove(os.path.join(self.config.get('paths','tmppath'),'sticker.sql'))
            os.remove(os.path.join(self.config.get('paths','tmppath'),'scmd'))
            os.remove(os.path.join(self.config.get('paths','tmppath'),'sync.sh'))
            call(['ssh',synchost,'rm','-f',self.config.get('sync','synctmppath')+'/sticker.sql'])
            call(['ssh',synchost,'rm','-f',self.config.get('sync','synctmppath')+'/scmd'])
        except Exception as e:
            Logger.exception("enqueue_output: "+format(e))

    def write_queue_line(self,q,layout,sv,dt):
        """Method that checks the queue for output and adds a new label line if any output exists."""
        try: line=q.get_nowait()
        except Empty:
            pass
        else:
            # TODO: figure out why lines all seem to have a blank line between them, probably something to do with \n at the end or something
            l=OutlineLabel(text=line,size_hint=(None,None),font_size='12sp',halign='left')
            l.bind(texture_size=l.setter('size'))
            layout.add_widget(l)
            sv.scroll_to(l)

    def filesync(self):
        """Callback when the user presses the Sync button. This relies on keyless ssh working, and does most of the work in shell scripts."""
        Logger.info('System: filesync')
        # look in the ini file for all the relevant paths
        synchost = self.config.get('sync','synchost')
        syncbasepath = self.config.get('sync','syncmusicpath')
        syncfanartpath= self.config.get('sync','syncfanartpath')
        basepath = self.config.get('paths','musicpath')
        fanartpath= self.config.get('paths','fanartpath')
        mpdhost = self.config.get('mpd','mpdhost')
        # Check to make sure synchost and mpdhost are not the same
        if mpdhost==synchost:
            Logger.warn('System: will not sync identical hosts!')
            popup=Builder.load_string('''
Popup:
    title: "Warning"
    size_hint_x: 0.6
    size_hint_y: 0.3
    size_hint_min_y: l.height
    OutlineLabel:
        id: l
        text: "Your mpdhost and synchost config fields are identical, sync is disabled to prevent data corruption."
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
        valign: 'middle'
            ''')
            popup.open()
            Clock.schedule_once(popup.dismiss,2)
            return
        # set up a popup containing a scrollview to contain stdout output
        layout = GridLayout(cols=1, spacing=1, padding=1, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        popup = Popup(title='Sync',size_hint=(0.8,1))
        sv=ScrollView(size_hint=(1,1))
        sv.add_widget(layout)
        popup = Popup(title='Sync',content=sv,size_hint=(0.8,1))
        popup.open()
        # temp file for the rsync, probably a better way to do this
        # this file describes exactly what songs should exist on the host, no more, no less
        tpath=os.path.join(self.config.get('paths','tmppath'),"rsync.inc")
        # look in the ini file for all the relevant paths
        synchost = self.config.get('sync','synchost')
        syncbasepath = self.config.get('sync','syncmusicpath')
        syncfanartpath= self.config.get('sync','syncfanartpath')
        basepath = self.config.get('paths','musicpath')
        fanartpath= self.config.get('paths','fanartpath')
        Logger.info('Filesync: Copying rsync file to carpi')
        # TODO: figure out why this doesn't show up on the screen until after the os.walk has completed
        l=OutlineLabel(text='Copying rsync file to carpi',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        # copy the rsync file from the synchost
        # TODO: implement this using python instead of call
        call(["scp",synchost+":rsync.inc",tpath])
        filelist={}
        # use codecs.open to ensure the file is read as utf8, otherwise special chars can be mangled
        with codecs.open(tpath,'r','utf-8') as f:
            for line in f:
                # add each filename to a dict for easy searching later
                filelist[Helpers.decodeFileName(line.rstrip())]=True
        Logger.info('Filesync: Removing old files from carpi')
        # TODO: figure out why this doesn't show up on the screen until after the os.walk has completed
        l=OutlineLabel(text='Removing old files from carpi',size_hint=(None,None),font_size='12sp',halign='left')
        l.bind(texture_size=l.setter('size'))
        layout.add_widget(l)
        sv.scroll_to(l)
        # this whole block walks the filesystem and deletes any file that is not in the rsync file
        # the sync operation is split up into a delete and a copy because that was the only way I could get
        # rsync to work correctly, it was always copying/deleting the wrong things otherwise
        for dirpath, dirnames, filenames in os.walk(Helpers.decodeFileName(basepath)):
            if len(filenames)>0:
                rpath = dirpath[len(basepath+os.sep):]
                for filename in filenames:
                    fpath=os.path.join(Helpers.decodeFileName(rpath),Helpers.decodeFileName(filename))
                    apath = os.path.join(Helpers.decodeFileName(dirpath),Helpers.decodeFileName(filename))
                    if fpath not in filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(Helpers.decodeFileName(apath))
        # TODO: somehow do this all in python instead of shell script, it's ugly
        # also, if the host somehow has tmppath mounted with the no-execute bit set, this will fail
        with open(os.path.join(self.config.get('paths','tmppath'),'sync.sh'),'w') as sfile:
            sfile.write("#!/bin/bash\n")
            # delete all empty directories
            sfile.write('find "'+basepath+'" -type d -empty -delete 2>/dev/null\n')
            # copy/update only the files that exist in the rsync file
            sfile.write('rsync -vruxhm --files-from="'+tpath+'" '+synchost+':"'+syncbasepath+'"/ "'+basepath+'"\n')
            # copy the car sticker database to the synchost
            sfile.write('scp /var/lib/mpd/sticker.sql '+synchost+':'+self.config.get('sync','synctmppath')+'\n')
            # build a secondary shell script to perform the sticker update on the synchost
            with open(os.path.join(self.config.get('paths','tmppath'),'scmd'),'w') as f:
                # attach the copied database and merge sticker data from it to update ratings user has added in the car
                # not using os.path.join here since who knows what os the synchost uses...use linux
                f.write("attach database \""+self.config.get('sync','synctmppath')+"/sticker.sql\" as carpi;\n")
                f.write("replace into sticker select * from carpi.sticker;\n")
                f.write("replace into carpi.sticker select * from sticker where name='rating';\n")
                f.write(".quit\n")
            # copy secondary script to synchost and run it
            sfile.write('scp '+os.path.join(self.config.get('paths','tmppath'),'scmd')+' '+synchost+':'+self.config.get('sync','synctmppath')+'\n')
            # not using os.path.join here since who knows what os the synchost uses...use linux
            sfile.write('ssh -t '+synchost+' sudo sqlite3 /var/lib/mpd/sticker.sql < '+self.config.get('sync','synctmppath')+'/scmd\n')
            # copy the now updated sticker database back from the synchost
            # not using os.path.join here since who knows what os the synchost uses...use linux
            sfile.write('scp '+synchost+':'+self.config.get('sync','synctmppath')+'/sticker.sql '+self.config.get('paths','tmppath')+'\n')
            # build a secondary shell script to perform the sticker update on the host
            with open(os.path.join(self.config.get('paths','tmppath'),'scmd'),'w') as f:
                # attach the copied database and merge sticker data from it to update ratings user has added at home
                f.write("attach database \""+os.path.join(self.config.get('paths','tmppath'),"sticker.sql")+"\" as carpi;\n")
                f.write("replace into sticker select * from carpi.sticker;\n")
                f.write(".quit\n")
            # run the secondary script
            sfile.write('cat '+os.path.join(self.config.get('paths','tmppath'),'scmd')+' | sudo sqlite3 /var/lib/mpd/sticker.sql\n')
            # rsync over all the fanart
            sfile.write('rsync -vruxhm '+synchost+':"'+syncfanartpath+'"/ "'+fanartpath+'"\n')
            # tell mpd about any changes
            sfile.write("mpc update\n")
        # make the shell script executable
        os.chmod(os.path.join(self.config.get('paths','tmppath'),'sync.sh'),os.stat(os.path.join(self.config.get('paths','tmppath'),'sync.sh')).st_mode|0111)
        # queue for holding stdout
        q = Queue()
        # create a subprocess for the shell script and capture stdout
        p = Popen([os.path.join(self.config.get('paths','tmppath'),'sync.sh')],stdout=PIPE,bufsize=1,close_fds=True)
        # check the stdout queue every .1 seconds and write lines to the scrollview if there is output
        event=Clock.schedule_interval(partial(self.write_queue_line,q,layout,sv),0.1)
        # run all this crap in a separate thread to be non-blocking
        t = Thread(target=self.enqueue_output,args=(p.stdout,q,event,popup,tpath,synchost,layout,sv))
        t.daemon = True
        t.start()
