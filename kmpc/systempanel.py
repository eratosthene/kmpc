import os
import sys
from subprocess import call
from functools import partial

import kivy
kivy.require('1.10.0')
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.button import Button
from kivy.logger import Logger
from kivy.app import App
from kivy.factory import Factory
from kivy.lang.builder import Builder

from kmpc.widgets import OutlineTabbedPanelItem,OutlineLabel
from kmpc.sync import Sync,Subproc
from kmpc.kmpcapp import configdir

from twisted.internet.defer import Deferred,DeferredList

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
        stdoutPopup.ids.layout.bind(minimum_height=stdoutPopup.ids.layout.setter('height'))
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['fanart'])

    def sync_music(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.ids.layout.bind(minimum_height=stdoutPopup.ids.layout.setter('height'))
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['music'])

    def sync_export_ratings(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.ids.layout.bind(minimum_height=stdoutPopup.ids.layout.setter('height'))
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['exportratings'])

    def sync_import_ratings(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.ids.layout.bind(minimum_height=stdoutPopup.ids.layout.setter('height'))
        stdoutPopup.open()
        GuiSync(stdoutPopup,self.config,['importratings'])

    def sync_all(self):
        stdoutPopup=Factory.StdoutPopup()
        stdoutPopup.ids.layout.bind(minimum_height=stdoutPopup.ids.layout.setter('height'))
        stdoutPopup.open()
        if self.config.getboolean('system','exportfirst'):
            GuiSync(stdoutPopup,self.config,['music','fanart','exportratings','importratings'])
        else:
            GuiSync(stdoutPopup,self.config,['music','fanart','importratings','exportratings'])


    def update_print_line(self,popup,line):
        try:
            l=OutlineLabel(text=line.rstrip(),size_hint=(None,None),font_size='12sp',halign='left')
            l.bind(texture_size=l.setter('size'))
            popup.ids.layout.add_widget(l)
            popup.ids.sv.scroll_to(l)
            Logger.debug("Update: "+line.rstrip())
        except Exception as e:
            Logger.error("update_print_line: "+format(e))

    def update(self):
        """Runs the 'updatecommand' from the config file."""
        Logger.info('System: update')
        from twisted.internet import reactor
        updatePopup=Factory.StdoutPopup(title='Update kmpc')
        updatePopup.ids.layout.bind(minimum_height=updatePopup.ids.layout.setter('height'))
        updatePopup.open()
        d=Deferred()
        cb=[]
        cmdline=self.config.get('system','updatecommand').split(' ')
        pp=Subproc(partial(self.update_print_line,updatePopup))
        pp.deferred=Deferred()
        pp.deferred.addCallback(partial(self.closeit,updatePopup))
        reactor.spawnProcess(pp,cmdline[0],cmdline,{'PATH':os.environ['PATH']})

    def closeit(self,popup,r):
        popup.dismiss()

    def do_plugins(self):
        choosePluginPopup=Factory.ChoosePluginPopup()
        plugins=[]
        scripts=[]
        for dirpath, dirnames, filenames in os.walk(os.path.join(configdir,'plugins')):
            if 'plugin.kv' in filenames and 'plugin.py' in filenames:
                plugins.append(os.path.basename(dirpath))
            if 'plugin.sh' in filenames:
                scripts.append(os.path.basename(dirpath))
        for plugin in plugins:
            pbutton=Button(text=plugin)
            choosePluginPopup.ids.layout.add_widget(pbutton)
            pbutton.bind(on_press=choosePluginPopup.dismiss)
            pbutton.bind(on_press=partial(self.load_plugin,plugin))
        for script in scripts:
            pbutton=Button(text=script)
            choosePluginPopup.ids.layout.add_widget(pbutton)
            pbutton.bind(on_press=choosePluginPopup.dismiss)
            pbutton.bind(on_press=self.run_script)
            pbutton.script=os.path.join(configdir,'plugins',script,'plugin.sh')
        choosePluginPopup.open()

    def run_script(self,instance):
        Logger.debug("run_script: "+instance.script)
        call(instance.script,shell=True)

    def load_plugin(self,plugin,instance):
        Logger.debug("load_plugin: "+plugin)
        sys.path.append(os.path.join(configdir,'plugins',plugin))
        pluginmodule=__import__('plugin')
        reload(pluginmodule)
        Builder.load_file(os.path.join(configdir,'plugins',plugin,'plugin.kv'))
        pluginPopup=Factory.PluginPopup(title='Plugin: '+plugin)
        pluginContent=eval('Factory.'+plugin+'PluginContent()')
        pluginPopup.ids.plugincontent.add_widget(pluginContent)
        pluginPopup.ids.closebutton.bind(on_press=partial(self.unload_plugin,plugin,pluginmodule))
        pluginPopup.open()

    def unload_plugin(self,plugin,pluginmodule,instance):
        Logger.debug("unload_plugin: "+plugin)
        del pluginmodule
        Builder.unload_file(os.path.join(configdir,'plugins',plugin,'plugin.kv'))

    def do_reboot(self):
        """Method that reboots the host."""
        Logger.info('System: reboot')
        call(self.config.get('system','rebootcommand').split(' '))

    def do_poweroff(self):
        """Method that shuts down the host."""
        Logger.info('System: poweroff')
        call(self.config.get('system','poweroffcommand').split(' '))

