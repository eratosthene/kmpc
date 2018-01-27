import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty,StringProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.vkeyboard import VKeyboard
from kivy.clock import Clock
from functools import partial

from kmpc.extra import OutlineTabbedPanelItem
import kmpc.kmpcapp

class PlaylistTabbedPanelItem(OutlineTabbedPanelItem):
    """The Playlist tab, shows the current playlist and allows interacting with it."""
    playlist_selection={}

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.app=App.get_running_app().root

    def playlist_clear_pressed(self):
        """Callback for playlist clear button."""
        Logger.info("Playlist: clear")
        kmpc.kmpcapp.mainmpdconnection.protocol.clear()

    def playlist_delete_pressed(self):
        """Callback for playlist delete button."""
        Logger.info("Playlist: delete")
        # loop through all selected tracks and remove each one from the playlist
        for pos in self.playlist_selection:
            songid=str(self.rv.data[pos]['songid'])
            Logger.debug("Playlist: deleting songid "+songid)
            kmpc.kmpcapp.mainmpdconnection.protocol.deleteid(songid)
        self.rbl.clear_selection()

    def playlist_move_pressed(self):
        """Callback for playlist move button."""
        # TODO: implement this
        Logger.info("Playlist: move")
        Logger.warn("Playlist: move not implemented")
        self.rbl.clear_selection()

    def playlist_shuffle_pressed(self):
        """Callback for playlist shuffle button."""
        Logger.info("Playlist: shuffle")
        # shuffle the playlist. note that this is different from toggling random playback, as it
        # actually reorders the playlist randomly rather than just playing in random order
        kmpc.kmpcapp.mainmpdconnection.protocol.shuffle()
        self.rbl.clear_selection()

    def playlist_swap_pressed(self):
        """Callback for playlist swap button."""
        Logger.info("Playlist: swap")
        # if exactly 2 tracks are selected, swap them
        if len(self.playlist_selection) != 2:
            Logger.warn("Playlist: swap only works with two rows selected")
        else:
            s1 = self.playlist_selection.keys()[0]
            s2 = self.playlist_selection.keys()[1]
            kmpc.kmpcapp.mainmpdconnection.protocol.swap(str(s1),str(s2)).addErrback(self.handle_mpd_error)
        self.rbl.clear_selection()

    def playlist_save_pressed(self):
        """Callback for playlist save button."""
        Logger.info("Playlist: save")
        self.rbl.clear_selection()
        # build a popup for naming the playlist
        layout = BoxLayout(orientation='vertical')
        popup = Popup(title='Playlist Name',content=layout)
        l1 = BoxLayout(size_hint_y='0.1')
        ti = TextInput()
        l1.add_widget(ti)
        layout.add_widget(l1)
        l2 = BoxLayout(size_hint_y='0.1',orientation='horizontal')
        btnok = Button(text="OK")
        btncl = Button(text="Cancel")
        btncl.bind(on_press=popup.dismiss)
        btnok.bind(on_press=partial(self.save_playlist,ti,popup))
        l2.add_widget(btnok)
        l2.add_widget(btncl)
        layout.add_widget(l2)
        l3 = BoxLayout()
        layout.add_widget(l3)
        popup.open()
        ti.show_keyboard()

    def save_playlist(self,ti,popup,instance):
        """Tell mpd to save the current playlist with the name that was input."""
        Logger.info("Playlist: save_playlist("+ti.text+")")
        kmpc.kmpcapp.mainmpdconnection.protocol.save(ti.text).addErrback(self.handle_mpd_error)
        popup.dismiss()

    def populate_playlist(self,result):
        """Callback for mpd playlist info."""
        Logger.info("Playlist: populate_playlist()")
        self.rv.data = []
        # loop through mpd playlist info and add to the recycleview
        for row in result:
            Logger.debug("Playlist: row "+row['pos']+" found = "+row['title'])
            r = {'plpos':row['pos'],'rownum':str(int(row['pos'])+1),'artist':format(row['artist']),'title':format(row['title']),'songid':format(row['id'])}
            self.rv.data.append(r)
        # when playlist is populated, also ask mpd for current status to highlight current track
        kmpc.kmpcapp.mainmpdconnection.protocol.status().addCallback(self.update_mpd_status).addErrback(self.handle_mpd_error)

    def update_mpd_status(self,result):
        """Callback for mpd status about current track."""
        Logger.debug('Playlist: update_mpd_status()')
        # TODO: pretty sure this is what crashes the player on super-long playlists
        if result['state'] == 'stop':
            # if stopped, there's no current track
            self.currsong=None
            # loop through recycleview, unhighlight all tracks
            for r in self.rv.data:
                r['iscurrent'] = False
        else:
            self.currsong=result['song']
            # loop through recycleview, highlight current track and unhighlight all others
            for r in self.rv.data:
                if r['plpos'] == result['song']:
                    r['iscurrent'] = True
                else:
                    r['iscurrent'] = False
        # tell the recycleview to refresh itself from the changed data
        self.rv.refresh_from_layout()

    def handle_mpd_error(self,result):
        """Callback for handling mpd exceptions."""
        Logger.error('Playlist: MPDIdleHandler Callback error: {}'.format(result))

class PlaylistRecycleBoxLayout(LayoutSelectionBehavior,RecycleBoxLayout):
    """Adds selection and focus behaviour to the recyclebox."""

class PlaylistRow(RecycleDataViewBehavior,BoxLayout):
    """Adds selection and long-press support to the recycleview."""
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.app=App.get_running_app().root

    def playfrom(self, touch, index, *args):
        """Handle long-press on a playlist row."""
        Logger.debug("Playlist: long-touch playfrom "+str(index))
        kmpc.kmpcapp.mainmpdconnection.protocol.play(str(index))
        self.app.ids.playlist_tab.rbl.clear_selection()

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes."""
        self.index = index
        return super(self.__class__, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        """Adds selection and long-press on touch down."""
        if super(self.__class__, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            # these lines start a 1 second clock to detect long-presses
            callback = partial(self.playfrom, touch, self.index)
            Clock.schedule_once(callback, 1)
            touch.ud['event'] = callback
            return self.parent.select_with_touch(self.index, touch)

    def on_touch_up(self, touch):
        """Clean up long-press on touch up."""
        if super(PlaylistRow, self).on_touch_up(touch):
            return True
        # if i don't check for this, the app crashes when things scroll off screen
        if 'event' in touch.ud:
            Clock.unschedule(touch.ud['event'])

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected
        pt=self.app.ids.playlist_tab
        if is_selected:
            pt.playlist_selection[index] = True
        else:
            if index in pt.playlist_selection:
                del pt.playlist_selection[index]

