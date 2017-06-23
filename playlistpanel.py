import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.logger import Logger
from kivy.metrics import Metrics

from extra import ScrollButton,ScrollBoxLayout

class PlaylistTabbedPanelItem(TabbedPanelItem):

    def playlist_clear_pressed(self):
        Logger.info("Playlist: clear")
        self.protocol.clear()
        self.protocol.playlistinfo().addCallback(self.populate_playlist).addErrback(self.handle_mpd_error)

    def playlist_delete_pressed(self):
        Logger.info("Playlist: delete")
        for pos in self.playlist_marked:
            Logger.debug("Playlist: deleting pos "+pos)
            self.protocol.delete(pos)
        self.protocol.playlistinfo().addCallback(self.populate_playlist).addErrback(self.handle_mpd_error)

    def playlist_move_pressed(self):
        Logger.info("Playlist: move")
        self.protocol.playlistinfo().addCallback(self.populate_playlist).addErrback(self.handle_mpd_error)

    def playlist_shuffle_pressed(self):
        Logger.info("Playlist: shuffle")
        self.protocol.shuffle()
        self.protocol.playlistinfo().addCallback(self.populate_playlist).addErrback(self.handle_mpd_error)

    def playlist_swap_pressed(self):
        Logger.info("Playlist: swap")
        self.protocol.playlistinfo().addCallback(self.populate_playlist).addErrback(self.handle_mpd_error)

    def populate_playlist(self,result):
        Logger.info("Application: populate_playlist()")
        self.playlist_marked={}
        self.ids.playlist_sv.clear_widgets()
        layout = GridLayout(cols=1,spacing=10,size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        for row in result:
            Logger.debug("Playlist: row "+row['pos']+" found = "+row['title'])
            bl = ScrollBoxLayout(orientation='horizontal')
            chk = CheckBox(size_hint_x=None)
            chk.plpos=row['pos']
            chk.bind(active=self.playlist_checkbox_pressed)
            lbl = Label(text=str(int(row['pos'])+1),size_hint_x=None,height='50sp')
            btn = ScrollButton(text=row['artist']+' - '+row['title'])
            btn.plpos=row['pos']
            btn.bind(on_press=self.playlist_button_pressed)
            btn.texture_update()
            bl.add_widget(chk)
            bl.add_widget(lbl)
            bl.add_widget(btn)
            layout.add_widget(bl)
            Logger.debug("Playlist: "+str(row['pos'])+' btn.height '+format(btn.height))
            nh=kivy.metrics.sp((int(btn.height/Metrics.dpi/(Metrics.density*Metrics.density))*20))+kivy.metrics.sp(btn.padding_y)
            Logger.debug("Playlist: nh = "+str(nh))
            if nh < kivy.metrics.sp(50):
                nh = kivy.metrics.sp(50)
            bl.height=nh
            Logger.debug('Playlist: bl.height '+format(bl.height))
        self.ids.playlist_sv.add_widget(layout)

    def playlist_button_pressed(self,btn):
        Logger.debug("Playlist: playlist_button_pressed("+str(btn.plpos)+")")
        self.protocol.play(btn.plpos)

    def playlist_checkbox_pressed(self,checkbox,value):
        Logger.debug("Playlist: playlist_checkbox_pressed("+format(checkbox.plpos)+")")
        if value:
            self.playlist_marked[checkbox.plpos]=True
        else:
            if checkbox.plpos in self.playlist_marked:
                del self.playlist_marked[checkbox.plpos]

    def update_mpd_status(self,result):
        Logger.debug('Playlist: update_mpd_status()')
        if result['state'] == 'stop':
            self.currsong=None
        else:
            self.currsong=result['song']
        sv=self.ids.playlist_sv
        if len(list(sv.children)) > 0:
            gl=sv.children[0]
            for sl in gl.children:
                btn=sl.children[0]
                if btn.plpos==self.currsong:
                    btn.background_color=(2,2,2,1)
                else:
                    btn.background_color=(1,1,1,1)

    def handle_mpd_error(self,result):
        Logger.error('Playlist: MPDIdleHandler Callback error: {}'.format(result))
