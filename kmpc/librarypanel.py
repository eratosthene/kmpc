from copy import deepcopy
from functools import partial
import os

from twisted.internet.defer import Deferred, DeferredList
import kivy
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
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
from kivy.clock import Clock
from kivy.factory import Factory

from kmpc.extra import KmpcHelpers
from kmpc.widgets import OutlineTabbedPanelItem

# make sure we are on updated version of kivy
kivy.require('1.10.0')

Helpers = KmpcHelpers()


class LibraryTabbedPanelItem(OutlineTabbedPanelItem):
    """The Library tab, for browsing through mpd's library."""

    # set some initial variables
    current_view = {
            'value': 'root',
            'base': '/',
            'info': {'type': 'uri'}}
    library_selection = {}

    def change_view_type(self, value):
        """Callback when user presses one of the Library view buttons."""
        Logger.info("Library: View changed to "+value)
        # make sure nothing is selected in the recyclebox
        self.rbl.clear_selection()
        # the button state things sort of implement a tabbed view without it
        # being a tabbedview so there doesn't have to be a separate recyclebox
        # for each view type
        # probably a more elegant way of doing this
        if value == 'Files':
            self.current_view = {
                    'value': 'root',
                    'base': '/',
                    'info': {'type': 'uri'}}
            (App.get_running_app().root.mpdconnection.protocol.
                lsinfo(self.current_view['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
            self.ids.delete_button.disabled = True
        elif value == 'Albums':
            self.current_view = {
                    'value': 'All Album Artists',
                    'base': 'All Album Artists',
                    'info': {'type': 'rootalbums'}}
            (App.get_running_app().root.mpdconnection.protocol.
                list('albumartistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
            self.ids.delete_button.disabled = True
        elif value == 'Tracks':
            self.current_view = {
                    'value': 'All Track Artists',
                    'base': 'All Track Artists',
                    'info': {'type': 'roottracks'}}
            (App.get_running_app().root.mpdconnection.protocol.
                list('artistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
            self.ids.delete_button.disabled = True
        elif value == 'Playlists':
            self.current_view = {
                    'value': 'All Playlists',
                    'base': 'All Playlists',
                    'info': {'type': 'playlist'}}
            (App.get_running_app().root.mpdconnection.protocol.
                listplaylists().
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
            self.ids.delete_button.disabled = False

    def reload_view(self, result):
        """Callback that loads library data from mpd into the recyclebox."""
        Logger.info("Library: reload_view() current type: "
                    + self.current_view['info']['type'])
        # clear all current recycleview data
        self.rv.data = []
        if self.current_view['info']['type'] == 'uri':
            # file-based browsing uses uri types
            if self.current_view['base'] != '/':
                # if we aren't at the base of the filesystem, allow browsing to
                # parent folder
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
                     'info': {'type': 'uri'}}
                self.rv.data.append(r)
                self.current_header.text = tbase
            else:
                # at filesystem base
                self.current_header.text = 'All Files'
        elif self.current_view['info']['type'] == 'albumartistsort':
            # inside a particular album artist, allow browsing to root
            r = {'value': 'up to All Album Artists',
                 'base': 'All Album Artists',
                 'info': {'type': 'rootalbums'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'album':
            # inside a particular album, allow browsing to album artist
            v = 'up to '+self.current_view['info']['albumartistsort']
            r = {'value': v,
                 'base': self.current_view['info']['albumartistsort'],
                 'info': {'type': 'albumartistsort'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        elif self.current_view['info']['type'] == 'artistsort':
            # inside a particular artist, allow browsing to root
            r = {'value': 'up to All Track Artists',
                 'base': 'All Track Artists',
                 'info': {'type': 'roottracks'}}
            self.rv.data.append(r)
            self.current_header.text = self.current_view['base']
        else:
            # something else?
            self.current_header.text = self.current_view['base']
        # loop through the rows mpd returned and add them to the recycleview
        for row in result:
            if 'playlist' in row:
                # we found a playlist, display it
                if self.current_view['info']['type'] != 'uri':
                    Logger.debug("Library: playlist found = "+row['playlist'])
                    r = {'value': row['playlist'],
                         'base': row['playlist'],
                         'info': {'type': 'playlist'}}
                    self.rv.data.append(r)
            elif 'directory' in row:
                # we found a directory, format and display it
                Logger.debug(
                        "Library: directory found: ["+row['directory']+"]")
                b1, b2 = os.path.split(row['directory'])
                r = {'value': b2,
                     'base': row['directory'],
                     'info': {'type': 'uri'}}
                self.rv.data.append(r)
            elif 'file' in row:
                # we found a song, format and display it
                Logger.debug("FileBrowser: file found: ["+row['file']+"]")
                r = {'value': Helpers.formatsong(row),
                     'base': row['file'],
                     'info': {'type': 'file'}}
                self.rv.data.append(r)
            else:
                # we found something else, figure out what it is based on our
                # current view type
                if self.current_view['info']['type'] == 'rootalbums':
                    # we found an album artist, display it
                    Logger.debug("Library: album artist found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'albumartistsort'}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'albumartistsort':
                    # we found an album, display it
                    Logger.debug("Library: album found: ["+row+"]")
                    v = self.current_view['base']
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'album',
                                  'albumartistsort': v}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'roottracks':
                    # we found an artist, display it
                    Logger.debug("Library: track artist found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'artistsort'}}
                    self.rv.data.append(r)
                elif self.current_view['info']['type'] == 'artistsort':
                    # we found a track, display it
                    # note that tracks are not parsed by Helpers.formatsong
                    # like filenames are; mpd formats a track itself
                    Logger.debug("Library: track found: ["+row+"]")
                    r = {'value': row,
                         'base': row,
                         'info': {'type': 'track',
                                  'artistsort': self.current_view['base']}}
                    self.rv.data.append(r)
                else:
                    # shouldn't ever see this, but y'know, whatever
                    Logger.warn("Library: "
                                + "not sure what to do with ["+format(row)+"]")

    def handle_long_touch(self, row, index):
        """Callback for handling long touches in the recycleview."""
        Logger.debug("Library: handle_long_touch("+format(row)+")")
        # load up the selected row as the current view, then display it
        self.current_view = deepcopy(row)
        if row['info']['type'] == 'uri':
            # selected a directory
            (App.get_running_app().root.mpdconnection.protocol.
                lsinfo(row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'rootalbums':
            # selected an album artist
            (App.get_running_app().root.mpdconnection.protocol.
                list('albumartistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'albumartistsort':
            # selected an album
            (App.get_running_app().root.mpdconnection.protocol.
                list('album', 'albumartistsort', row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'album':
            # selected an album track
            (App.get_running_app().root.mpdconnection.protocol.
                find('album',
                     row['base'],
                     'albumartistsort',
                     row['info']['albumartistsort']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'roottracks':
            # selected an artist
            (App.get_running_app().root.mpdconnection.protocol.
                list('artistsort').
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'artistsort':
            # selected a track
            (App.get_running_app().root.mpdconnection.protocol.
                list('title', 'artistsort', row['base']).
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        elif row['info']['type'] == 'playlist':
            # selected a playlist, go ahead and load it up and play it
            App.get_running_app().root.mpdconnection.protocol.clear()
            App.get_running_app().root.mpdconnection.protocol.load(row['base'])
            App.get_running_app().root.mpdconnection.protocol.play('0')
        elif row['info']['type'] == 'file':
            # selected a file, append it to the playlist and play from there
            App.get_running_app().root.mpdconnection.protocol.clear()
            a, b = os.path.split(row['base'])
            App.get_running_app().root.mpdconnection.protocol.add(a)
            (App.get_running_app().root.mpdconnection.protocol.
                play(str(int(index)-1)))
        else:
            # should never see this
            Logger.warn("Library: long-touch for ["
                        + format(row)+"] not implemented")

    def handle_mpd_error(self, result):
        """Callback for handling mpd exceptions."""
        Logger.error('Library: Callback error: '+format(result))

    def browser_add_find(self, result):
        """Callback for appending a bunch of tracks to the playlist."""
        for rrow in result:
            App.get_running_app().root.mpdconnection.protocol.add(rrow['file'])

    def browser_add_find_one(self, result):
        """Callback for appending one track to the playlist."""
        # since mpd always returns a list, just do the first one then break
        for rrow in result:
            App.get_running_app().root.mpdconnection.protocol.add(rrow['file'])
            break

    def browser_add(self, clearfirst, insert):
        """Callback when user presses the '+' (add), '!' (clear then add), or
        '>' (insert) buttons."""
        Logger.info('Library: browser_add('+str(clearfirst)+')')
        # if !, clear the playlist
        if clearfirst:
            Logger.info('Library: Clearing playlist')
            App.get_running_app().root.mpdconnection.protocol.clear()
        # loop through the recyclebox and add each selected node
        for index in self.rbl.selected_nodes:
            row = self.rv.data[index]
            mtype = row['info']['type']
            Logger.info("Library: Adding "+mtype+" '"
                        + row['base']+"' to current playlist")
            if mtype == 'uri' or mtype == 'file':
                if insert and App.get_running_app().root.currsong:
                    # if >, insert the song/directory after the currently
                    # playing song
                    App.get_running_app().root.mpdconnection.protocol.addid(
                            row['base'],
                            str(int(App.get_running_app().root.currsong)+1))
                else:
                    # append the song/directory to the playlist
                    (App.get_running_app().root.mpdconnection.protocol.
                        add(row['base']))
            elif mtype == 'albumartistsort':
                # append all tracks by a particular album artist
                (App.get_running_app().root.mpdconnection.protocol.
                    find(mtype, row['base']).
                    addCallback(self.browser_add_find).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'album':
                # append all tracks on a particular album
                (App.get_running_app().root.mpdconnection.protocol.
                    find(mtype,
                         row['base'],
                         'albumartistsort',
                         row['info']['albumartistsort']).
                    addCallback(self.browser_add_find).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'artistsort':
                # append all tracks by a particular artist
                (App.get_running_app().root.mpdconnection.protocol.
                    find(mtype, row['base']).
                    addCallback(self.browser_add_find).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'track':
                # append a particular artist's specific track
                # currently just adds the first match that mpd finds
                (App.get_running_app().root.mpdconnection.protocol.
                    find('artistsort',
                         row['info']['artistsort'],
                         'title',
                         row['base']).
                    addCallback(self.browser_add_find_one).
                    addErrback(self.handle_mpd_error))
            elif mtype == 'playlist':
                # append a playlist
                (App.get_running_app().root.mpdconnection.protocol.
                    load(row['base']))
            else:
                # should never see this
                Logger.warning("Library: "+mtype+' not implemented')
        # clear the currently selected rows after doing the above work
        self.rbl.clear_selection()

    def browser_delete(self):
        """Callback when user presses the delete playlist button."""
        for index in self.rbl.selected_nodes:
            plname = self.rv.data[index]['base']
            Logger.info("Library: deleting playlist "+plname)
            (App.get_running_app().root.mpdconnection.protocol.
                rm(plname).
                addErrback(self.handle_mpd_error))
            self.current_view = {
                    'value': 'All Playlists',
                    'base': 'All Playlists',
                    'info': {'type': 'playlist'}}
            (App.get_running_app().root.mpdconnection.protocol.
                listplaylists().
                addCallback(self.reload_view).
                addErrback(self.handle_mpd_error))
        self.rbl.clear_selection()

    def popup_generate(self):
        """Callback when user presses the Generate button."""
        generatePopup = Factory.GeneratePopup()
        generatePopup.open()

    def update_generate_text(self, p):
        """Callback when user changes the generate spinners."""
        stars = p.ids.ratings_spinner.text
        op = p.ids.operation_spinner.text
        if stars == 'None':
            p.ids.playlist_name.text = 'No Stars'
        elif op == '<':
            p.ids.playlist_name.text = 'Less Than '+stars+'-Star'
        elif op == '<=':
            p.ids.playlist_name.text = stars+'-Star or Less'
        elif op == '=':
            p.ids.playlist_name.text = stars+'-Star'
        elif op == '>=':
            p.ids.playlist_name.text = stars+'-Star or More'
        elif op == '>':
            p.ids.playlist_name.text = 'More Than '+stars+'-Star'

    def generate_playlist(self, p):
        """Callback when user presses the final Generate button after choosing
        ratings and operation."""
        Logger.info("Library: generating playlist "+p.ids.playlist_name.text)
        # gets all songs with ratings
        if p.ids.ratings_spinner.text != 'None':
            (App.get_running_app().root.mpdconnection.protocol.
                sticker_find('song', '', 'rating').
                addCallback(partial(self.generate_playlist2, p)))

    def generate_playlist2(self, p, result):
        """Callback to filter the list of all songs with ratings."""
        Logger.debug("generate_playlist2: filtering result")
        tlist = {}
        stars = p.ids.ratings_spinner.text
        op = p.ids.operation_spinner.text
        pname = p.ids.playlist_name.text
        cb = []
        aroot = App.get_running_app().root
        cb.append(aroot.mpdconnection.protocol.playlistclear(pname))
        for row in result:
            rating = row['sticker'].split('=')[1]
            uri = row['file']
            if ((op == '<' and int(rating) < int(stars)) or
                    (op == '<=' and int(rating) <= int(stars)) or
                    (op == '=' and int(rating) == int(stars)) or
                    (op == '>=' and int(rating) >= int(stars)) or
                    (op == '>' and int(rating) > int(stars))):
                tlist[uri] = 1
        for k in sorted(tlist.keys()):
            Logger.debug("gpl2: "+k)
            cb.append(aroot.mpdconnection.protocol.playlistadd(pname, k))
        dl = DeferredList(cb, consumeErrors=True)
        dl.addCallback(partial(self.dismiss_generate_popup, p))

    def dismiss_generate_popup(self, p, result):
        p.dismiss()


class LibraryRecycleBoxLayout(LayoutSelectionBehavior, RecycleBoxLayout):
    """Adds selection and focus behaviour to a recyclebox."""


class LibraryRow(RecycleDataViewBehavior, BoxLayout):
    """Adds selection support to a row in a recycleview."""
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def long_touch(self, touch, index, *args):
        """Callback when user long-presses on a row."""
        Logger.debug("Library: long-touch on "+str(index))
        App.get_running_app().root.ids.library_tab.rbl.clear_selection()
        App.get_running_app().root.ids.library_tab.handle_long_touch(
                App.get_running_app().root.ids.library_tab.rv.data[index],
                index)

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes."""
        self.index = index
        return (RecycleDataViewBehavior.
                refresh_view_attrs(self, rv, index, data))

    def on_touch_down(self, touch):
        """Adds selection, long-press handling on touch down."""
        if BoxLayout.on_touch_down(self, touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            # these lines start a 1 second clock to detect long-presses
            callback = partial(self.long_touch, touch, self.index)
            Clock.schedule_once(callback, 1)
            touch.ud['event'] = callback
            return self.parent.select_with_touch(self.index, touch)

    def on_touch_up(self, touch):
        """Clean up long-press handling on touch up."""
        if BoxLayout.on_touch_up(self, touch):
            return True
        # if i don't check for this, the app crashes when things scroll off
        # screen
        if 'event' in touch.ud:
            Clock.unschedule(touch.ud['event'])

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected
        lt = App.get_running_app().root.ids.library_tab
        if is_selected:
            lt.library_selection[index] = True
        else:
            if index in lt.library_selection:
                del lt.library_selection[index]
