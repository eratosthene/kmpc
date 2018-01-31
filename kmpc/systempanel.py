import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.logger import Logger
from kivy.app import App
from kivy.factory import Factory

from kmpc.extra import OutlineTabbedPanelItem
from kmpc.sync import Sync

class GuiSync(Sync):

    def run_at_end(self,result):
        #super(self.__class__,self).run_at_end(result)
        App.get_running_app().root.ids.system_tab.syncPopup.dismiss()

    def output_to(self,q):
        super(self.__class__,self).output_to(q)

    def print_line(self,line):
        super(self.__class__,self).print_line(line)

    def show_ratings_progress(self,done,total):
        super(self.__class__,self).show_ratings_progress(done,total)

class SystemTabbedPanelItem(OutlineTabbedPanelItem):
    """The System tab, for internal functions."""

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.syncPopup=Factory.SyncPopup()

    def sync_popup(self):
        self.syncPopup.open()

    def sync_fanart(self):
        GuiSync(self.config,'fanart')

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

