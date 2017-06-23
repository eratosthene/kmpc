import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.metrics import Metrics
from twisted.internet.defer import inlineCallbacks
import os

from extra import ScrollButton,ScrollBoxLayout,formatsong

class LibraryTabbedPanelItem(TabbedPanelItem):
    file_browser_base = '/'
    active_tab = None
    album_browser_base = {"level":"root","base":"root","upto":None}
    track_browser_base = {"level":"root","base":"root"}

    def library_tab_changed(self,obj,value):
        tabname = value.text
        self.ids.library_panel.active_tab = tabname
        Logger.info("Library: Changed tab: "+tabname)
        if tabname == 'Files':
            self.protocol.lsinfo(self.file_browser_base).addCallback(self.populate_file_browser).addErrback(self.handle_mpd_error)
        elif tabname == 'Albums':
            self.populate_album_browser()
        elif tabname == 'Tracks':
            pass
#            self.populate_track_browser()
        elif tabname == 'Playlists':
            pass
#            self.populate_playlist_browser()

    def handle_mpd_error(self,result):
        Logger.error('Library: MPDIdleHandler Callback error: {}'.format(result))

    def populate_file_browser(self,result):
        self.browser_marked={}
        base=self.file_browser_base
        (hbase,tbase)=os.path.split(base)
        Logger.info("Library: populate_file_browser, base=["+base+"], tbase=["+tbase+"]")
        self.ids.library_files_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if base != '/':
            (b1,b2)=os.path.split(hbase)
            if b2 == '':
                b2 = 'root'
            btn = Button(text=".. ("+b2+")",size_hint_y=None,height='50sp')
            btn.base=os.path.normpath(base+'/..')
            if btn.base == '.':
                btn.base = '/'
            btn.bind(on_press=self.file_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=tbase,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
        pos=0
        for row in result:
            if 'directory' in row:
                Logger.debug("FileBrowser: directory found: ["+row['directory']+"]")
                (b1,b2)=os.path.split(row['directory'])
                btn = ScrollButton(text=b2)
                btn.base = row['directory']
                btn.repopulate = True
                btn.bind(on_press=self.file_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['directory']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
            elif 'file' in row:
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                btn = ScrollButton(text=formatsong(row))
                btn.base=os.path.normpath(base)
                btn.repopulate = False
                btn.plpos=pos
                btn.bind(on_press=self.file_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row['file']
                chk.info = {'type':'uri'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
            pos+=1
        self.ids.library_files_sv.add_widget(layout)

    def file_browser_button(self,instance):
        Logger.debug('Library: file_browser_button('+instance.text+')')
        if instance.repopulate:
            self.file_browser_base=instance.base
            self.protocol.lsinfo(self.file_browser_base).addCallback(self.populate_file_browser).addErrback(self.handle_mpd_error)
        else:
            self.protocol.clear()
            self.protocol.add(instance.base)
            self.protocol.play(str(instance.plpos))

    def populate_album_browser(self):
        self.album_browser_marked={}
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        Logger.info("Library: populate_album_browser, base=["+base+"] level=["+level+"]")
        if self.album_browser_base['level'] == 'root':
            self.protocol.list('albumartistsort').addCallback(self.populate_root_album_browser).addErrback(self.handle_mpd_error)
        elif self.album_browser_base['level'] == 'artist':
            self.protocol.list('album','albumartistsort',base).addCallback(self.populate_artist_album_browser).addErrback(self.handle_mpd_error)
        elif self.album_browser_base['level'] == 'album':
            self.protocol.find('album',base,'albumartistsort',upto).addCallback(self.populate_album_album_browser).addErrback(self.handle_mpd_error)

    def populate_root_album_browser(self,result):
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        self.ids.library_albums_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        for row in result:
            Logger.debug("AlbumBrowser: artist found = "+row)
            btn = ScrollButton(text=row)
            btn.base = row
            btn.nextlevel = 'artist'
            btn.bind(on_press=self.album_browser_button)
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            chk.base = row
            chk.info = {'type':'albumartistsort'}
            chk.bind(active=self.browser_checkbox_pressed)
            bl.add_widget(chk)
            bl.add_widget(btn)
            layout.add_widget(bl)
        self.ids.library_albums_sv.add_widget(layout)

    def populate_artist_album_browser(self,result):
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        self.ids.library_albums_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        btn = Button(text=".. (root)",size_hint_y=None,height='50sp')
        btn.base = upto
        btn.nextlevel = 'root'
        btn.bind(on_press=self.album_browser_button)
        layout.add_widget(btn)
        lbl = Label(text=base,size_hint_y=None,height='50sp')
        layout.add_widget(lbl)
        for row in result:
            Logger.debug('AlbumBrowser: album found = '+row)
            btn = ScrollButton(text=row,size_hint_y=None)
            btn.base = row
            btn.nextlevel = 'album'
            btn.bind(on_press=self.album_browser_button)
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            chk.base = row
            chk.info = {'type':'album','albumartistsort':base}
            chk.bind(active=self.browser_checkbox_pressed)
            bl.add_widget(chk)
            bl.add_widget(btn)
            layout.add_widget(bl)
        self.ids.library_albums_sv.add_widget(layout)

    def populate_album_album_browser(self,result):
        base=self.album_browser_base['base']
        level=self.album_browser_base['level']
        upto=self.album_browser_base['upto']
        self.ids.library_albums_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        btn = Button(text=".. ("+upto+")",size_hint_y=None,height='50sp')
        btn.base = upto
        btn.nextlevel = 'artist'
        btn.bind(on_press=self.album_browser_button)
        layout.add_widget(btn)
        lbl = Label(text=base,size_hint_y=None,height='50sp')
        layout.add_widget(lbl)
        for row in result:
            Logger.debug("AlbumBrowser: track found = "+row['file'])
            btn = ScrollButton(text=formatsong(row),size_hint_y=None)
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            chk.base = row['file']
            chk.info = {'type':'uri'}
            chk.bind(active=self.browser_checkbox_pressed)
            bl.add_widget(chk)
            bl.add_widget(btn)
            layout.add_widget(bl)
        self.ids.library_albums_sv.add_widget(layout)

    def album_browser_button(self,instance):
        Logger.debug('Library: album_browser_button('+instance.text+','+instance.base+','+instance.nextlevel+')')
        blevel=self.album_browser_base['level']
        bbase=self.album_browser_base['base']
        bupto=self.album_browser_base['upto']
        self.album_browser_base={'level':instance.nextlevel,'base':instance.base,'upto':bbase}
        self.populate_album_browser()

    @inlineCallbacks
    def populate_track_browser(self):
        self.browser_marked={}
        base=self.track_browser_base['base']
        level=self.track_browser_base['level']
        Logger.info("Application: populate_track_browser, base=["+base+"] level=["+level+"]")
        self.ids.library_tracks_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        if level == 'root':
            self.protocol.command_list_ok_begin()
            self.protocol.list('artistsort')
            reslist=yield self.protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("TrackBrowser: artist found = "+row)
                btn = ScrollButton(text=row)
                btn.base = row
                btn.nextlevel = 'artist'
                btn.bind(on_press=self.track_browser_button)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'artistsort'}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        elif level == "artist":
            btn = Button(text=".. (root)",size_hint_y=None,height='50sp')
            btn.base = 'root'
            btn.bind(on_press=self.track_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=base,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
            self.protocol.command_list_ok_begin()
            self.protocol.list('title','artistsort',base)
            reslist=yield self.protocol.command_list_end()
            result=reslist[0]
            for row in result:
                Logger.debug("TrackBrowser: track found = "+row)
                btn = ScrollButton(text=row)
                bl = ScrollBoxLayout(orientation='horizontal')
                chk = CheckBox(size_hint_x=None)
                chk.base = row
                chk.info = {'type':'title','artistsort':base}
                chk.bind(active=self.browser_checkbox_pressed)
                bl.add_widget(chk)
                bl.add_widget(btn)
                layout.add_widget(bl)
        self.ids.library_tracks_sv.add_widget(layout)

    def track_browser_button(self,instance):
        Logger.debug("Application: track_browser_button("+instance.text+","+instance.base+","+instance.nextlevel+")")
        blevel=self.track_browser_base['level']
        bbase=self.track_browser_base['base']
        if blevel == 'root':
            self.track_browser_base={'level':'artist','base':instance.base}
        else:
            self.track_browser_base={'level':'root','base':'root'}
        self.populate_track_browser()

    @inlineCallbacks
    def populate_playlist_browser(self):
        Logger.info("Application: populate_playlist_browser()")
#        self.ids.library_playlists_panel.clear_widgets()
        self.ids.library_playlists_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        self.protocol.command_list_ok_begin()
        self.protocol.listplaylists()
        reslist=yield self.protocol.command_list_end()
        result=reslist[0]
        for row in result:
            Logger.debug("PlaylistBrowser: playlist found = "+row['playlist'])
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            btn = ScrollButton(text=row['playlist'])
            btn.texture_update()
            bl.add_widget(chk)
            bl.add_widget(btn)
            layout.add_widget(bl)
            Logger.debug("PlaylistBrowser: btn.height "+format(btn.height))
            nh=kivy.metrics.sp((int(btn.height/Metrics.dpi/(Metrics.density*Metrics.density))*20))+kivy.metrics.sp(btn.padding_y)
            Logger.debug("PlaylistBrowser: nh = "+str(nh))
            if nh < kivy.metrics.sp(50):
                nh = kivy.metrics.sp(50)
            bl.height=nh
            Logger.debug('PlaylistBrowser: bl.height '+format(bl.height))
        self.ids.library_playlists_sv.add_widget(layout)

    def browser_checkbox_pressed(self,checkbox,value):
        Logger.debug("Library: browser_checkbox_pressed("+checkbox.base+","+format(checkbox.info)+")")
        if value:
            self.browser_marked[checkbox.base]=checkbox.info
        else:
            if checkbox.base in self.browser_marked:
                del self.browser_marked[checkbox.base]

    @inlineCallbacks
    def browser_add(self,clearfirst):
        Logger.debug('Application: browser_add('+str(clearfirst)+')')
        if clearfirst:
            Logger.info('Browser: Clearing playlist')
            self.protocol.clear()
        for row in self.browser_marked:
            mtype=self.browser_marked[row]['type']
            Logger.info("Browser: Adding "+mtype+" '"+row+"' to current playlist")
            if mtype == 'uri':
                self.protocol.add(row)
            elif mtype == 'albumartistsort':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'album':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row,'albumartistsort',self.browser_marked[row]['albumartistsort'])
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+",albumartistsort,"+self.browser_marked[row]['albumartistsort']+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'artistsort':
                self.protocol.command_list_ok_begin()
                self.protocol.find(mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find("+mtype+","+row+") = "+format(result))
                for rrow in result:
                    self.protocol.add(rrow['file'])
            elif mtype == 'title':
                self.protocol.command_list_ok_begin()
                self.protocol.find('artistsort',self.browser_marked[row]['artistsort'],mtype,row)
                reslist=yield self.protocol.command_list_end()
                result=reslist[0]
                Logger.debug("Browser: find(artistsort,"+self.browser_marked[row]['artistsort']+","+mtype+","+row+") = "+format(result))
                if result:
                    self.protocol.add(result[0]['file'])
            else:
                Logger.warning("Browser: "+mtype+' not implemented')

