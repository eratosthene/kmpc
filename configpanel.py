import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.logger import Logger

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

