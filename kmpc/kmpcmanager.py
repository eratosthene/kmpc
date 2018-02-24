import os
import sys
import io
from pkg_resources import resource_filename

import kivy
from kivy.config import Config
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import get_color_from_hex

from kmpc.mpdfactory import MpdConnection
from kmpc.managerinterface import ManagerInterface

# make sure we are on updated version of kivy
kivy.require('1.10.0')

# sets the location of the config folder
configdir = os.path.join(os.path.expanduser('~'), ".kmpc")

# load the interface kv files
Builder.load_file(
        resource_filename(
                __name__,
                os.path.join('resources/kv', 'widgets.kv')))
Builder.load_file(
        resource_filename(
                __name__,
                os.path.join('resources/kv', 'library.kv')))
Builder.load_file(
        resource_filename(
                __name__,
                os.path.join('resources/kv', 'manager.kv')))


class ManagerApp(App):

    def __init__(self, args):
        self.args = args
        super(self.__class__, self).__init__()

    def build_config(self, config):
        config.setdefaults('sync', {
            'synchost': '127.0.0.1',
            'syncmpdport': '6600',
            'synclocalmusicpath': '/mnt/music',
            'synclocalfanartpath': '/mnt/fanart',
            'syncplaylist': 'synclist'
        })
        config.setdefaults('logs', {
            'artlog': False
        })
        config.setdefaults('fanart', {
            'client_key': ''
        })
        config.setdefaults('songratings', {
            'star0': 'Silence',
            'star1': 'Songs that should never be heard',
            'star2': 'Songs no one likes',
            'star3': 'Songs for certain occasions',
            'star4': 'Songs someone else likes',
            'star5': 'Filler tracks with no music',
            'star6': 'Meh track or short musical filler',
            'star7': 'Occasional listening songs',
            'star8': 'Great songs for all occasions',
            'star9': 'Best songs by an artist',
            'star10': 'Favorite songs of all time'
        })
        config.setdefaults('artblacklist', {})
        config.setdefaults('colors', {
            'button': '#00B361',
            'backdrop': '#4096FF',
            'listitem': '#4080FF',
            'listitemselected': '#FFFF00',
            'listitemcurrent': '#521C4F'
        })

    def get_color(self, c):
        cc = self.config.get('colors', c)
        try:
            # if backdrop or button, alpha channel=1, else 0.5
            if c in ['backdrop', 'button']:
                cc += 'FF'
            else:
                cc += '80'
            t = get_color_from_hex(cc)
        except Exception:
            Logger.error("Application: color "
                         + cc+" for "+c+" is invalid")
            t = (1, 1, 1, 1)
        return t

    def get_application_config(self):
        inifile = os.path.join(configdir, 'config.ini')
        return super(self.__class__, self).get_application_config(inifile)

    def build_settings(self, settings):
        settings.add_json_panel(
                'sync settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json',
                                     'config_manager_sync.json')))
        settings.add_json_panel(
                'log settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json',
                                     'config_manager_logs.json')))
        settings.add_json_panel(
                'fanart settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json',
                                     'config_fanart.json')))
        settings.add_json_panel(
                'song ratings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json',
                                     'config_star.json')))
        settings.add_json_panel(
                'colors',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json',
                                     'config_colors.json')))

    def build(self):
        if not os.path.isdir(configdir):
            os.mkdir(configdir)
        # try to read existing config file
        self.config = self.load_config()
        # write out config file in case it doesn't exist yet
        self.config.write()
        if self.args.newconfig:
            sys.exit(0)
        else:
            return ManagerInterface(self.config)


if __name__ == '__main__':
    ManagerApp().run()
