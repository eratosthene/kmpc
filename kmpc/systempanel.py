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

class SystemTabbedPanelItem(OutlineTabbedPanelItem):
    """The System tab, for internal functions."""

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.syncPopup=Factory.SyncPopup()

    def sync_popup(self):
        self.syncPopup.open()

    def printit(self,result):
        """An internal debugging function. Probably shouldn't ever be used."""
        print format(result)

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

