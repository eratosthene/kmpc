import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.metrics import Metrics
from twisted.internet.defer import inlineCallbacks
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
import os

from extra import ScrollButton,ScrollBoxLayout,formatsong

class LibraryTabbedPanelItem(TabbedPanelItem):
    file_browser_base = '/'
    active_tab = None
    album_browser_base = {"level":"root","base":"root","upto":None}
    track_browser_base = {"level":"root","base":"root"}
    library_selection = {}

    def library_tab_changed(self,obj,value):
        tabname = value.text
        self.ids.library_panel.active_tab = tabname
        Logger.info("Library: Changed tab: "+tabname)
        if tabname == 'Files':
            self.protocol.lsinfo(self.file_browser_base).addCallback(self.populate_file_browser).addErrback(self.handle_mpd_error)
        elif tabname == 'Albums':
            self.populate_album_browser()
        elif tabname == 'Tracks':
            self.populate_track_browser()
        elif tabname == 'Playlists':
            self.protocol.listplaylists().addCallback(self.populate_playlist_browser).addErrback(self.handle_mpd_error)

    def handle_mpd_error(self,result):
        Logger.error('Library: MPDIdleHandler Callback error: {}'.format(result))

    def populate_file_browser(self,result):
#        self.browser_marked={}
        base=self.file_browser_base
        (hbase,tbase)=os.path.split(base)
        Logger.info("Library: populate_file_browser, base=["+base+"], tbase=["+tbase+"]")
#        self.ids.library_files_sv.clear_widgets()
#        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
#        layout.bind(minimum_height=layout.setter('height'))
        self.library_files_rv.data=[]
        if base != '/':
            (b1,b2)=os.path.split(hbase)
            if b2 == '':
                b2 = 'root'
            btn = Button(text=".. ("+b2+")",size_hint_y=None,height='50sp')
            btn.base=os.path.normpath(base+'/..')
#            btn.repopulate = True
            if btn.base == '.':
                btn.base = '/'
 #           btn.bind(on_press=self.file_browser_button)
            layout.add_widget(btn)
            lbl = Label(text=tbase,size_hint_y=None,height='50sp')
            layout.add_widget(lbl)
#        pos=0
        for row in result:
            if 'directory' in row:
                Logger.debug("FileBrowser: directory found: ["+row['directory']+"]")
                (b1,b2)=os.path.split(row['directory'])
                r={'value':b2,'base':row['directory'],'info':{'type':'uri'}}
                self.library_files_rv.data.append(r)
#                btn = ScrollButton(text=b2)
#                btn.base = row['directory']
#                btn.repopulate = True
#                btn.bind(on_press=self.file_browser_button)
#                bl = ScrollBoxLayout(orientation='horizontal')
#                chk = CheckBox(size_hint_x=None)
#                chk.base = row['directory']
#                chk.info = {'type':'uri'}
#                chk.bind(active=self.browser_checkbox_pressed)
#                bl.add_widget(chk)
#                bl.add_widget(btn)
#                layout.add_widget(bl)
            elif 'file' in row:
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                r={'value':formatsong(row),'base':os.path.normpath(base),'info':{'type':'uri'}}
                self.library_files_rv.data.append(r)
#                btn = ScrollButton(text=formatsong(row))
#                btn.base=os.path.normpath(base)
#                btn.repopulate = False
#                btn.plpos=pos
#                btn.bind(on_press=self.file_browser_button)
#                bl = ScrollBoxLayout(orientation='horizontal')
#                chk = CheckBox(size_hint_x=None)
#                chk.base = row['file']
#                chk.info = {'type':'uri'}
#                chk.bind(active=self.browser_checkbox_pressed)
#                bl.add_widget(chk)
#                bl.add_widget(btn)
#                layout.add_widget(bl)
#            pos+=1
#        self.ids.library_files_sv.add_widget(layout)

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

    def populate_track_browser(self):
        self.browser_marked={}
        base=self.track_browser_base['base']
        level=self.track_browser_base['level']
        Logger.info("Library: populate_track_browser, base=["+base+"] level=["+level+"]")
        if self.track_browser_base['level'] == 'root':
            self.protocol.list('artistsort').addCallback(self.populate_root_track_browser).addErrback(self.handle_mpd_error)
        elif self.track_browser_base['level'] == 'artist':
            self.protocol.list('title','artistsort',base).addCallback(self.populate_artist_track_browser).addErrback(self.handle_mpd_error)

    def populate_root_track_browser(self,result):
        base=self.track_browser_base['base']
        level=self.track_browser_base['level']
        self.ids.library_tracks_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
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
        self.ids.library_tracks_sv.add_widget(layout)

    def populate_artist_track_browser(self,result):
        base=self.track_browser_base['base']
        level=self.track_browser_base['level']
        self.ids.library_tracks_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        btn = Button(text=".. (root)",size_hint_y=None,height='50sp')
        btn.base = 'root'
        btn.bind(on_press=self.track_browser_button)
        layout.add_widget(btn)
        lbl = Label(text=base,size_hint_y=None,height='50sp')
        layout.add_widget(lbl)
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
        Logger.debug("Library: track_browser_button("+instance.text+","+instance.base+")")
        blevel=self.track_browser_base['level']
        bbase=self.track_browser_base['base']
        if blevel == 'root':
            self.track_browser_base={'level':'artist','base':instance.base}
        else:
            self.track_browser_base={'level':'root','base':'root'}
        self.populate_track_browser()

    def populate_playlist_browser(self,result):
        Logger.info("Library: populate_playlist_browser()")
        self.library_playlists_rv.data=[]
        for row in result:
            Logger.debug("PlaylistBrowser: playlist found = "+row['playlist'])
            r = {'value':row['playlist']}
            self.library_playlists_rv.data.append(r)

    def browser_checkbox_pressed(self,checkbox,value):
        Logger.debug("Library: browser_checkbox_pressed("+checkbox.base+","+format(checkbox.info)+")")
        if value:
            self.browser_marked[checkbox.base]=checkbox.info
        else:
            if checkbox.base in self.browser_marked:
                del self.browser_marked[checkbox.base]

    def browser_add_find(self,result):
        for rrow in result:
            self.protocol.add(rrow['file'])

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
                self.protocol.find(mtype,row).addCallback(self.browser_add_find).addErrback(self.handle_mpd_error)
            elif mtype == 'album':
                self.protocol.find(mtype,row,'albumartistsort',self.browser_marked[row]['albumartistsort']).addCallback(self.browser_add_find).addErrback(self.handle_mpd_error)
            elif mtype == 'artistsort':
                self.protocol.find(mtype,row).addCallback(self.browser_add_find).addErrback(self.handle_mpd_error)
            elif mtype == 'title':
                self.protocol.find('artistsort',self.browser_marked[row]['artistsort'],mtype,row).addCallback(self.browser_add_find).addErrback(self.handle_mpd_error)
            else:
                Logger.warning("Browser: "+mtype+' not implemented')

class LibraryRecycleBoxLayout(FocusBehavior,LayoutSelectionBehavior,RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class LibraryRow(RecycleDataViewBehavior,BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(LibraryRow, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(LibraryRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            # if we have a double-click, play from that location instead of selecting
            if touch.is_double_tap:
                Logger.debug("Library: double-click playfrom "+str(self.index))
#                App.get_running_app().root.protocol.play(str(self.index))
#                App.get_running_app().root.ids.playlist_tab.prbl.clear_selection()
            else:
                return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
#        lt=App.get_running_app().root.ids.library_tab
        if is_selected:
            rv.rv_selection[index] = True
#            lt.library_selection[index] = True
        else:
            if index in rv.rv_selection:
                del rv.rv_selection[index]
#            if index in lt.library_selection:
#                del lt.library_selection[index]
