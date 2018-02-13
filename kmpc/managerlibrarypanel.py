from copy import deepcopy
from functools import partial
import os

from twisted.internet.defer import inlineCallbacks
import kivy
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.factory import Factory
from kivy.clock import Clock

from kmpc.extra import KmpcHelpers
from kmpc.widgets import fontawesomefont
from kmpc.librarypanel import LibraryTabbedPanelItem, LibraryRow

# make sure we are on updated version of kivy
kivy.require('1.10.0')

Helpers = KmpcHelpers()


class ManagerLibraryTabbedPanelItem(LibraryTabbedPanelItem):

    def render_row(self, r, has_sticker, result):
        rr = deepcopy(r)
        if has_sticker:
            rr['copy_flag'] = str(result)
        else:
            rr['copy_flag'] = ''
        (App.get_running_app().root.syncmpdconnection.protocol.
            sticker_get('song', rr['base'], 'rating').
            addCallback(partial(self.render_row2, rr, True)).
            addErrback(partial(self.render_row2, rr, False)))

    def render_row2(self, r, has_sticker, result):
        rr = deepcopy(r)
        if has_sticker:
            rr['rating'] = str(result)
        else:
            rr['rating'] = ''
        self.rv.data.append(rr)

    def reload_view(self, result):
        Logger.info("Library: reload_view() current type: "
                    + self.current_view['info']['type'])
        self.rv.data = []
        if self.current_view['info']['type'] == 'uri':
            if self.current_view['base'] != '/':
                hbase, tbase = os.path.split(self.current_view['base'])
                b1, b2 = os.path.split(hbase)
                if b2 == '':
                    b2 = 'root'
                upbase = os.path.normpath(
                        os.path.join(self.current_view['base'], '..'))
                if upbase == '.':
                    upbase = '/'
                r = {'value': "up to "+b2,
                     'base': upbase,
                     'info': {'type': 'uri'},
                     'copy_flag': '',
                     'rating': ''}
                self.rv.data.append(r)
                self.current_header.text = tbase
            else:
                self.current_header.text = 'All Files'
        elif self.current_view['info']['type'] == 'albumartistsort':
            r = {'value': 'up to All Album Artists',
                 'base': 'All Album Artists',
                 'info': {'type': 'rootalbums'},
                 'copy_flag': '',
                 'rating': ''}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'album':
            v = self.current_view['info']['albumartistsort']
            r = {'value': 'up to '+v,
                 'base': self.current_view['info']['albumartistsort'],
                 'info': {'type': 'albumartistsort'},
                 'copy_flag': '',
                 'rating': ''}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'artistsort':
            r = {'value': 'up to All Track Artists',
                 'base': 'All Track Artists',
                 'info': {'type': 'roottracks'},
                 'copy_flag': '',
                 'rating': ''}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        else:
            self.current_header.text = self.current_view['base']
        for row in result:
            if 'playlist' in row:
                if self.current_view['info']['type'] != 'uri':
                    Logger.debug("Library: playlist found = "+row['playlist'])
                    r = {'value': row['playlist'],
                         'base': row['playlist'],
                         'info': {'type': 'playlist'},
                         'copy_flag': '',
                         'rating': ''}
                    self.rv.data.append(r)
            elif 'directory' in row:
                Logger.debug("Library: directory found: ["
                             + row['directory']+"]")
                b1, b2 = os.path.split(row['directory'])
                r = {'value': b2,
                     'base': row['directory'],
                     'info': {'type': 'uri'},
                     'copy_flag': '',
                     'rating': ''}
                self.rv.data.append(r)
            elif 'file' in row:
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                r = {'value': Helpers.formatsong(row),
                     'base': row['file'],
                     'info': {'type': 'file'}}
                (App.get_running_app().root.syncmpdconnection.protocol.
                    sticker_get('song', row['file'], 'copy_flag').
                    addCallback(partial(self.render_row, r, True)).
                    addErrback(partial(self.render_row, r, False)))
            else:
                if self.current_view['info']['type'] == 'rootalbums':
                    Logger.debug("Library: album artist found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'albumartistsort'},
                         'copy_flag': '',
                         'rating': ''}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'albumartistsort':
                    Logger.debug("Library: album found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {
                                'type': 'album',
                                'albumartistsort': self.current_view['base']},
                         'copy_flag': '',
                         'rating': ''}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'roottracks':
                    Logger.debug("Library: track artist found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'artistsort'},
                         'copy_flag': '',
                         'rating': ''}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'artistsort':
                    Logger.debug("Library: track found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'track',
                                  'artistsort': self.current_view['base']},
                         'copy_flag': '',
                         'rating': ''}
                    self.rv.data.append(r)
                else:
                    Logger.warn("Library: not sure what to do with ["
                                + format(row)+"]")

    def handle_double_click(self, row, index):
        Logger.debug("Library: handle_double_click("+format(row)+")")
        self.current_view = deepcopy(row)
        if row['info']['type'] == 'uri':
            (App.get_running_app().root.syncmpdconnection.protocol.
                lsinfo(row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'rootalbums':
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('albumartistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'albumartistsort':
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('album', 'albumartistsort', row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'album':
            (App.get_running_app().root.syncmpdconnection.protocol.
                find('album',
                     row['base'],
                     'albumartistsort',
                     row['info']['albumartistsort']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'roottracks':
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('artistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'artistsort':
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('title', 'artistsort', row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'playlist':
            pass
        elif row['info']['type'] == 'file':
            pass
        else:
            Logger.warn("Library: double click for ["
                        + format(row)+"] not implemented")

    def reload_row_after_sticker(self, copy_flag, index, result):
        self.rv.data[index]['copy_flag'] = copy_flag
        self.rv.refresh_from_data()

    def set_copy_flag_find(self, copy_flag, index, result):
        for rrow in result:
            if copy_flag:
                Logger.debug("set_copy_flag_find: setting copy_flag to "
                             + copy_flag+" for file "+rrow['file'])
                (App.get_running_app().root.syncmpdconnection.protocol.
                    sticker_set('song', rrow['file'], 'copy_flag', copy_flag).
                    addCallback(partial(self.reload_row_after_sticker,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            else:
                Logger.debug("set_copy_flag_find: clearing copy_flag for file "
                             + rrow['file'])
                (App.get_running_app().root.syncmpdconnection.protocol.
                    sticker_delete('song', rrow['file'], 'copy_flag').
                    addCallback(partial(self.reload_row_after_sticker,
                                        '',
                                        index)).
                    addErrback(self.handle_mpd_error))

    def set_copy_flag_find_one(self, copy_flag, index, result):
        for rrow in result:
            if copy_flag:
                Logger.debug("set_copy_flag_find_one: setting copy_flag to "
                             + copy_flag+" for file "+rrow['file'])
                (App.get_running_app().root.syncmpdconnection.protocol.
                    sticker_set('song', rrow['file'], 'copy_flag', copy_flag).
                    addCallback(partial(self.reload_row_after_sticker,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            else:
                Logger.debug("set_copy_flag_find_one: clearing copy_flag "
                             + "for file "+rrow['file'])
                (App.get_running_app().root.syncmpdconnection.protocol.
                    sticker_delete('song', rrow['file'], 'copy_flag').
                    addCallback(partial(self.reload_row_after_sticker,
                                        '',
                                        index)).
                    addErrback(self.handle_mpd_error))
            break

    def set_copy_flag(self, copy_flag):
        Logger.info('Library: set_copy_flag('+str(copy_flag)+')')
        for index in self.rbl.selected_nodes:
            row = self.rv.data[index]
            mtype = row['info']['type']
            Logger.info("Library: Setting copy_flag for "+mtype+" '"
                        + row['base']+"' to "+copy_flag)
            if mtype == 'file':
                Logger.debug("set_copy_flag: adding uri or file")
                if copy_flag:
                    Logger.debug("set_copy_flag: setting copy_flag to "
                                 + copy_flag+" for file "+row['base'])
                    (App.get_running_app().root.syncmpdconnection.protocol.
                        sticker_set('song',
                                    row['base'],
                                    'copy_flag',
                                    copy_flag).
                        addCallback(partial(self.reload_row_after_sticker,
                                            copy_flag,
                                            index)).
                        addErrback(self.handle_mpd_error))
                else:
                    Logger.debug("set_copy_flag: clearing copy_flag for file "
                                 + row['base'])
                    (App.get_running_app().root.syncmpdconnection.protocol.
                        sticker_delete('song', row['base'], 'copy_flag').
                        addCallback(partial(self.reload_row_after_sticker,
                                            '',
                                            index)).
                        addErrback(self.handle_mpd_error))
            elif mtype == 'albumartistsort':
                (App.get_running_app().root.syncmpdconnection.protocol.
                    find(mtype, row['base']).
                    addCallback(partial(self.set_copy_flag_find,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'album':
                (App.get_running_app().root.syncmpdconnection.protocol.
                    find(mtype,
                         row['base'],
                         'albumartistsort',
                         row['info']['albumartistsort']).
                    addCallback(partial(self.set_copy_flag_find,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'artistsort':
                (App.get_running_app().root.syncmpdconnection.protocol.
                    find(mtype, row['base']).
                    addCallback(partial(self.set_copy_flag_find,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'track':
                (App.get_running_app().root.syncmpdconnection.protocol.
                    find('artistsort',
                         row['info']['artistsort'],
                         'title',
                         row['base']).
                    addCallback(partial(self.set_copy_flag_find_one,
                                        copy_flag,
                                        index)).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'playlist' or mtype == 'uri':
                Logger.info("Library: "+mtype+" copy_flag not implemented")
            else:
                Logger.warning("Library: "+mtype+' copy_flag not implemented')
        self.rbl.clear_selection()

    def rating_set(self, index, rating, popup):
        Logger.debug('Application: rating_set('+rating+')')
        popup.dismiss()
        if rating:
            (App.get_running_app().root.syncmpdconnection.protocol.
                sticker_set('song',
                            self.rv.data[index]['base'],
                            'rating',
                            rating).
                addCallback(partial(self.handle_rating_set,
                                    index,
                                    rating,
                                    True)).
                addErrback(partial(self.handle_rating_set,
                                   index,
                                   rating,
                                   False)))
        else:
            (App.get_running_app().root.syncmpdconnection.protocol.
                sticker_delete('song',
                               self.rv.data[index]['base'],
                               'rating').
                addCallback(partial(self.handle_rating_set,
                                    index,
                                    rating,
                                    True)).
                addErrback(partial(self.handle_rating_set,
                                   index,
                                   rating,
                                   False)))

    def handle_rating_set(self, index, rating, succ, result):
        if succ:
            Logger.info("Library: successfully set song rating for "
                        + self.rv.data[index]['base'])
            self.rv.data[index]['rating'] = rating
            self.rv.refresh_from_data()
        else:
            Logger.info("Library: could not set song rating for "
                        + self.rv.data[index]['base'])

    def generate_list(self, ltype, stars, op='>=', pname='playlist'):
        Logger.info('generate_list: generating with minimum stars '+str(stars))
        self.tlist = {}
        (App.get_running_app().root.syncmpdconnection.protocol.
            sticker_find('song', '', 'rating').
            addCallback(partial(self.generate_play_list,
                                ltype,
                                stars,
                                op,
                                pname)).
            addErrback(self.handle_mpd_error))

    def generate_play_list(self, ltype, stars, op, pname, result):
        Logger.debug("generate_play_list: "+ltype)
        for row in result:
            rating = row['sticker'].split('=')[1]
            uri = row['file']
            if ((op == '<' and int(rating) < int(stars)) or
                    (op == '<=' and int(rating) <= int(stars)) or
                    (op == '=' and int(rating) == int(stars)) or
                    (op == '>=' and int(rating) >= int(stars)) or
                    (op == '>' and int(rating) > int(stars))):
                Logger.debug("generate_play_list: rating ["
                             + rating+"] file ["+uri+"]")
                self.tlist[uri] = 1
        if ltype == 'playlist':
            Logger.info("generate_play_list: writing to playlist ["+pname+"]")
            (App.get_running_app().root.syncmpdconnection.protocol.
                playlistclear(pname).
                addErrback(self.handle_mpd_error))
            for k in sorted(self.tlist.keys()):
                (App.get_running_app().root.syncmpdconnection.protocol.
                    playlistadd(pname, k).
                    addErrback(self.handle_mpd_error))
        elif ltype == 'synclist':
            (App.get_running_app().root.syncmpdconnection.protocol.
                sticker_find('song', '', 'copy_flag').
                addCallback(self.generate_sync_list).
                addErrback(self.handle_mpd_error))

    def generate_sync_list(self, result):
        for row in result:
            uri = row['file']
            if row['sticker'] == 'copy_flag=Y':
                Logger.debug("generate_sync_list: copy flag adding "+uri)
                self.tlist[uri] = 1
            else:
                Logger.debug("generate_sync_list: copy flag removing "+uri)
                try:
                    del self.tlist[uri]
                except KeyError:
                    pass
        Logger.info("generate_sync_list: writing to playlist ["
                    + App.get_running_app().root.config.get(
                        'sync',
                        'syncplaylist')+"]")
        (App.get_running_app().root.syncmpdconnection.protocol.
            playlistclear(App.get_running_app().root.config.get(
                    'sync',
                    'syncplaylist')).
            addErrback(self.handle_mpd_error))
        for k in sorted(self.tlist.keys()):
            (App.get_running_app().root.syncmpdconnection.protocol.
                playlistadd(
                        App.get_running_app().root.config.get('sync',
                                                              'syncplaylist'),
                        k).
                addErrback(self.handle_mpd_error))

    def change_view_type(self, value):
        Logger.info("Library: View changed to "+value)
        self.rbl.clear_selection()
        if value == 'Files':
            self.current_view = {'value': 'root',
                                 'base': '/',
                                 'info': {'type': 'uri'}}
            (App.get_running_app().root.syncmpdconnection.protocol.
                lsinfo(self.current_view['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif value == 'Albums':
            self.current_view = {'value': 'All Album Artists',
                                 'base': 'All Album Artists',
                                 'info': {'type': 'rootalbums'}}
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('albumartistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif value == 'Tracks':
            self.current_view = {'value': 'All Track Artists',
                                 'base': 'All Track Artists',
                                 'info': {'type': 'roottracks'}}
            (App.get_running_app().root.syncmpdconnection.protocol.
                list('artistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))

    def popup_generate(self):
        """Callback when user presses the Generate button."""
        generatePopup = Factory.ManagerGeneratePopup(library_tab=self)
        generatePopup.open()


class ManagerGeneratePopup(Popup):

    library_tab = ObjectProperty(None)


class ManagerLibraryRow(LibraryRow):
    ''' Add selection support to the Label '''

    def rating_popup(self, instance):
        aroot = App.get_running_app().root
        Logger.debug('Library: rating_popup()')
        popup = Factory.RatingPopup(
                index=self.index,
                rating_set=aroot.ids.library_tab.rating_set)
        popup.open()

    def long_touch(self, touch, index, *args):
        """Callback when user long-presses on a row."""
        aroot = App.get_running_app().root
        Logger.debug("Library: long-touch on "+str(index))
        aroot.ids.library_tab.rbl.clear_selection()
        aroot.ids.library_tab.handle_double_click(
                aroot.ids.library_tab.rv.data[index],
                index)

    def on_touch_down(self, touch):
        """Adds selection, long-press handling on touch down."""
        aroot = App.get_running_app().root
        if BoxLayout.on_touch_down(self, touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            # these lines start a 1 second clock to detect long-presses
            callback = partial(self.long_touch, touch, self.index)
            Clock.schedule_once(callback, 1)
            touch.ud['event'] = callback
            if touch.is_double_tap:
                Logger.debug("Library: double-click on "+str(self.index))
                aroot.ids.library_tab.rbl.clear_selection()
                aroot.ids.library_tab.handle_double_click(
                        aroot.ids.library_tab.rv.data[self.index],
                        self.index)
            else:
                return self.parent.select_with_touch(self.index, touch)
