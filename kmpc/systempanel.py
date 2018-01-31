import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.logger import Logger
from kivy.app import App
from kivy.factory import Factory

from kmpc.extra import OutlineTabbedPanelItem,OutlineLabel
from kmpc.sync import Sync

class GuiSync(Sync):

    def __init__(self,popup,config,runparts=[]):
        try:
            self.popup=popup
            self.pb={}
            App.get_running_app().root.do_idle_handler=False
            super(self.__class__,self).__init__(config,runparts)
        except Exception as e:
            Logger.error("__init__: "+format(e))

    def run_at_end(self,result):
        try:
            self.popup.dismiss()
            App.get_running_app().root.ids.system_tab.syncPopup.dismiss()
            App.get_running_app().root.do_idle_handler=True
        except Exception as e:
            Logger.error("run_at_end: "+format(e))

    def print_line(self,line):
        try:
            l=OutlineLabel(text=line.rstrip(),size_hint=(None,None),font_size='12sp',halign='left')
            l.bind(texture_size=l.setter('size'))
            self.popup.ids.layout.add_widget(l)
            self.popup.ids.sv.scroll_to(l)
            super(self.__class__,self).print_line(line)
        except Exception as e:
            Logger.error("print_line: "+format(e))

    def show_ratings_progress(self,done,total,sdir):
        try:
            self.pb[sdir].max=total
            self.pb[sdir].value=done
        except Exception as e:
            Logger.error("show_ratings_progress: "+format(e))

    def ratings_incoming(self,sdir):
        try:
            self.pb[sdir] = ProgressBar()
            l=OutlineLabel(text=sdir,size_hint=(None,None),font_size='12sp',halign='left')
            l.bind(texture_size=l.setter('size'))
            self.popup.ids.layout.add_widget(l)
            self.popup.ids.layout.add_widget(self.pb[sdir])
            self.popup.ids.sv.scroll_to(self.pb[sdir])
        except Exception as e:
            Logger.error("ratings_incoming: "+format(e))

class SystemTabbedPanelItem(OutlineTabbedPanelItem):
    """The System tab, for internal functions."""

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.syncPopup=Factory.SyncPopup()

    def sync_popup(self):
        self.syncPopup.open()

    def sync_fanart(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['fanart'])

    def sync_music(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['music'])

    def sync_ratings(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['ratings'])

    def sync_all(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['music','fanart','ratings'])

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

