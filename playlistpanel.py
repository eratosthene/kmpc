import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.metrics import Metrics
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from functools import partial

class PlaylistTabbedPanelItem(TabbedPanelItem):

    playlist_selection={}

    def playlist_clear_pressed(self):
        Logger.info("Playlist: clear")
        self.protocol.clear()

    def playlist_delete_pressed(self):
        Logger.info("Playlist: delete")
        for pos in self.playlist_selection:
            Logger.debug("Playlist: deleting pos "+str(pos))
            self.protocol.delete(str(pos))
        self.rbl.clear_selection()

    def playlist_move_pressed(self):
        Logger.info("Playlist: move")
        Logger.warn("Playlist: move not implemented")
        self.rbl.clear_selection()

    def playlist_shuffle_pressed(self):
        Logger.info("Playlist: shuffle")
        self.protocol.shuffle()
        self.rbl.clear_selection()

    def playlist_swap_pressed(self):
        Logger.info("Playlist: swap")
        Logger.warn("Playlist: swap not implemented")
        self.rbl.clear_selection()

    def populate_playlist(self,result):
        Logger.info("Playlist: populate_playlist()")
        self.rv.data = []
        for row in result:
            Logger.debug("Playlist: row "+row['pos']+" found = "+row['title'])
            r = {'plpos':row['pos'],'rownum':str(int(row['pos'])+1),'artist':format(row['artist']),'title':format(row['title'])}
            self.rv.data.append(r)
        self.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)

    def update_mpd_status(self,result):
        Logger.debug('Playlist: update_mpd_status()')
        if result['state'] == 'stop':
            self.currsong=None
            for r in self.rv.data:
                r['iscurrent'] = False
        else:
            self.currsong=result['song']
            for r in self.rv.data:
                if r['plpos'] == result['song']:
                    r['iscurrent'] = True
                else:
                    r['iscurrent'] = False
        self.rv.refresh_from_layout()

    def handle_mpd_error(self,result):
        Logger.error('Playlist: MPDIdleHandler Callback error: {}'.format(result))

class PlaylistRecycleBoxLayout(FocusBehavior,LayoutSelectionBehavior,RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class PlaylistRow(RecycleDataViewBehavior,BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(PlaylistRow, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(PlaylistRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            # if we have a double-click, play from that location instead of selecting
            if touch.is_double_tap:
                Logger.debug("Playlist: double-click playfrom "+str(self.index))
                App.get_running_app().root.protocol.play(str(self.index))
                App.get_running_app().root.ids.playlist_tab.rbl.clear_selection()
            else:
                return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        pt=App.get_running_app().root.ids.playlist_tab
        if is_selected:
            pt.playlist_selection[index] = True
        else:
            if index in pt.playlist_selection:
                del pt.playlist_selection[index]

