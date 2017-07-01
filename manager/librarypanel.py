import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from twisted.internet.defer import inlineCallbacks
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from copy import deepcopy
from functools import partial
import os

from extra import formatsong

class LibraryTabbedPanelItem(TabbedPanelItem):
    current_view = {'value': 'root', 'base':'/','info':{'type':'uri'}}
    library_selection = {}

    def change_view_type(self,value):
        Logger.info("Library: View changed to "+value)
        self.rbl.clear_selection()
        if value == 'Files':
            self.current_view = {'value': 'root','base':'/','info':{'type':'uri'}}
            self.protocol.lsinfo(self.current_view['base']).addCallback(self.reload_view).addErrback(self.handle_mpd_error)
            self.ids.files_button.state='down'
            self.ids.albums_button.state='normal'
            self.ids.tracks_button.state='normal'
            self.ids.playlists_button.state='normal'
        elif value == 'Albums':
            self.current_view = {'value': 'All Album Artists','base':'All Album Artists','info':{'type':'rootalbums'}}
            self.protocol.list('albumartistsort').addCallback(self.reload_view).addErrback(self.handle_mpd_error)
            self.ids.files_button.state='normal'
            self.ids.albums_button.state='down'
            self.ids.tracks_button.state='normal'
            self.ids.playlists_button.state='normal'
        elif value == 'Tracks':
            self.current_view = {'value': 'All Track Artists','base':'All Track Artists','info':{'type':'roottracks'}}
            self.protocol.list('artistsort').addCallback(self.reload_view).addErrback(self.handle_mpd_error)
            self.ids.files_button.state='normal'
            self.ids.albums_button.state='normal'
            self.ids.tracks_button.state='down'
            self.ids.playlists_button.state='normal'
        elif value == 'Playlists':
            self.current_view = {'value':'All Playlists','base':'All Playlists','info':{'type':'playlist'}}
            self.protocol.listplaylists().addCallback(self.reload_view).addErrback(self.handle_mpd_error)
            self.ids.files_button.state='normal'
            self.ids.albums_button.state='normal'
            self.ids.tracks_button.state='normal'
            self.ids.playlists_button.state='down'

    def render_row(self,r,has_sticker,result):
        rr=deepcopy(r)
        if has_sticker:
            rr['copy_flag']=str(result)
            self.rv.data.append(rr)
        else:
            rr['copy_flag']=''
            self.rv.data.append(rr)

    def reload_view(self,result):
        Logger.info("Library: reload_view() current type: "+self.current_view['info']['type'])
        self.rv.data=[]
        if self.current_view['info']['type'] == 'uri':
            if self.current_view['base'] != '/':
                (hbase,tbase)=os.path.split(self.current_view['base'])
                (b1,b2)=os.path.split(hbase)
                if b2 == '':
                    b2 = 'root'
                upbase=os.path.normpath(self.current_view['base']+'/..')
                if upbase == '.':
                    upbase = '/'
                r = {'value':"up to "+b2,'base':upbase,'info':{'type':'uri'}}
                self.rv.data.append(r)
                self.current_header.text = tbase
            else:
                self.current_header.text = 'All Files'
        elif self.current_view['info']['type'] == 'albumartistsort':
            r={'value': 'up to All Album Artists','base':'All Album Artists','info':{'type':'rootalbums'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'album':
            r={'value':'up to '+self.current_view['info']['albumartistsort'],'base':self.current_view['info']['albumartistsort'],'info':{'type':'albumartistsort'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'artistsort':
            r={'value': 'up to All Track Artists','base':'All Track Artists','info':{'type':'roottracks'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        else:
            self.current_header.text = self.current_view['base']
        for row in result:
            if 'playlist' in row:
                if self.current_view['info']['type'] != 'uri':
                    Logger.debug("Library: playlist found = "+row['playlist'])
                    r = {'value':row['playlist'],'base':row['playlist'],'info':{'type':'playlist'}}
                    self.rv.data.append(r)
            elif 'directory' in row:
                Logger.debug("Library: directory found: ["+row['directory']+"]")
                (b1,b2)=os.path.split(row['directory'])
                r={'value':b2,'base':row['directory'],'info':{'type':'uri'}}
                self.rv.data.append(r)
            elif 'file' in row:
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                r={'value':formatsong(row),'base':row['file'],'info':{'type':'file'}}
                self.protocol.sticker_get('song',row['file'],'copy_flag').addCallback(partial(self.render_row,r,True)).addErrback(partial(self.render_row,r,False))
            else:
                if self.current_view['info']['type'] == 'rootalbums':
                    Logger.debug("Library: album artist found: ["+row+"]")
                    r={'value':row,'base':row,'info':{'type':'albumartistsort'}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'albumartistsort':
                    Logger.debug("Library: album found: ["+row+"]")
                    r={'value':row,'base':row,'info':{'type':'album','albumartistsort':self.current_view['base']}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'roottracks':
                    Logger.debug("Library: track artist found: ["+row+"]")
                    r={'value':row,'base':row,'info':{'type':'artistsort'}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'artistsort':
                    Logger.debug("Library: track found: ["+row+"]")
                    r={'value':row,'base':row,'info':{'type':'track','artistsort':self.current_view['base']}}
                    self.rv.data.append(r)
                else:
                    Logger.warn("Library: not sure what to do with ["+format(row)+"]")

    def handle_double_click(self,row,index):
        Logger.debug("Library: handle_double_click("+format(row)+")")
        self.current_view = deepcopy(row)
        if row['info']['type'] == 'uri':
            self.protocol.lsinfo(row['base']).addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'rootalbums':
            self.protocol.list('albumartistsort').addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'albumartistsort':
            self.protocol.list('album','albumartistsort',row['base']).addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'album':
            self.protocol.find('album',row['base'],'albumartistsort',row['info']['albumartistsort']).addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'roottracks':
            self.protocol.list('artistsort').addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'artistsort':
            self.protocol.list('title','artistsort',row['base']).addCallback(self.reload_view).addErrback(self.handle_mpd_error)
        elif row['info']['type'] == 'playlist':
            pass
        elif row['info']['type'] == 'file':
            pass
        else:
            Logger.warn("Library: double click for ["+format(row)+"] not implemented")

    def handle_mpd_error(self,result):
        Logger.error('Library: MPDIdleHandler Callback error: {}'.format(result))

    def reload_row_after_sticker(self,copy_flag,index,result):
        self.rv.data[index]['copy_flag']=copy_flag
        self.rv.refresh_from_data()

    def set_copy_flag_find(self,copy_flag,index,result):
        for rrow in result:
            if copy_flag:
                print "setting copy_flag to "+copy_flag+" for file "+rrow['file']
                self.protocol.sticker_set('song',rrow['file'],'copy_flag',copy_flag).addCallback(partial(self.reload_row_after_sticker,copy_flag,index)).addErrback(self.handle_mpd_error)
            else:
                print "clearing copy_flag for file "+rrow['file']
                self.protocol.sticker_delete('song',rrow['file'],'copy_flag').addCallback(partial(self.reload_row_after_sticker,'',index)).addErrback(self.handle_mpd_error)

    def set_copy_flag_find_one(self,copy_flag,index,result):
        for rrow in result:
            if copy_flag:
                print "setting copy_flag to "+copy_flag+" for file "+rrow['file']
                self.protocol.sticker_set('song',rrow['file'],'copy_flag',copy_flag).addCallback(partial(self.reload_row_after_sticker,copy_flag,index)).addErrback(self.handle_mpd_error)
            else:
                print "clearing copy_flag for file "+rrow['file']
                self.protocol.sticker_delete('song',rrow['file'],'copy_flag').addCallback(partial(self.reload_row_after_sticker,'',index)).addErrback(self.handle_mpd_error)
            break

    def set_copy_flag(self,copy_flag):
        Logger.info('Library: set_copy_flag('+str(copy_flag)+')')
        for index in self.rbl.selected_nodes:
            row = self.rv.data[index]
            mtype=row['info']['type']
            Logger.info("Library: Adding "+mtype+" '"+row['base']+"' to current playlist")
            if mtype == 'uri' or mtype == 'file':
                print "adding uri or file"
                if copy_flag:
                    print "setting copy_flag to "+copy_flag+" for file "+row['base']
                    self.protocol.sticker_set('song',row['base'],'copy_flag',copy_flag).addCallback(partial(self.reload_row_after_sticker,copy_flag,index)).addErrback(self.handle_mpd_error)
                else:
                    print "clearing copy_flag for file "+row['base']
                    self.protocol.sticker_delete('song',row['base'],'copy_flag').addCallback(partial(self.reload_row_after_sticker,'',index)).addErrback(self.handle_mpd_error)
            elif mtype == 'albumartistsort':
                self.protocol.find(mtype,row['base']).addCallback(partial(self.set_copy_flag_find,copy_flag,index)).addErrback(self.handle_mpd_error)
            elif mtype == 'album':
                self.protocol.find(mtype,row['base'],'albumartistsort',row['info']['albumartistsort']).addCallback(partial(self.set_copy_flag_find,copy_flag,index)).addErrback(self.handle_mpd_error)
            elif mtype == 'artistsort':
                self.protocol.find(mtype,row['base']).addCallback(partial(self.set_copy_flag_find,copy_flag,index)).addErrback(self.handle_mpd_error)
            elif mtype == 'track':
                self.protocol.find('artistsort',row['info']['artistsort'],'title',row['base']).addCallback(partial(self.set_copy_flag_find_one,copy_flag,index)).addErrback(self.handle_mpd_error)
            elif mtype == 'playlist':
                pass
                #self.protocol.load(row['base'])
            else:
                Logger.warning("Library: "+mtype+' not implemented')
        self.rbl.clear_selection()

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
                Logger.debug("Library: double-click on "+str(self.index))
                App.get_running_app().root.ids.library_tab.rbl.clear_selection()
                App.get_running_app().root.ids.library_tab.handle_double_click(App.get_running_app().root.ids.library_tab.rv.data[self.index],self.index)
            else:
                return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        lt=App.get_running_app().root.ids.library_tab
        if is_selected:
            lt.library_selection[index] = True
        else:
            if index in lt.library_selection:
                del lt.library_selection[index]
