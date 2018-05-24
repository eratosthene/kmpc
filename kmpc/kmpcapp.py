import os
import sys
from pkg_resources import resource_filename

import kivy
from kivy.config import Config, ConfigParser
from kivy.app import App
from kivy.logger import Logger
from kivy.lang import Builder
from kivy.utils import get_color_from_hex

from kmpc.version import VERSION_STR
from kmpc.sync import Sync
from kmpc.kmpcinterface import KmpcInterface

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
                os.path.join('resources/kv', 'playlist.kv')))
Builder.load_file(
        resource_filename(
                __name__,
                os.path.join('resources/kv', 'system.kv')))
Builder.load_file(
        resource_filename(
                __name__,
                os.path.join('resources/kv', 'interface.kv')))


class KmpcApp(App):
    """The overall app class, builds the main interface widget."""

    def __init__(self, args):
        """Override kivy config values with necessary ones"""
        self.args = args
        super(self.__class__, self).__init__()

    def build_config(self, config):
        config.setdefaults('mpd', {
            'mpdhost': '127.0.0.1',
            'mpdport': '6600'
        })
        config.setdefaults('paths', {
            'musicpath': '/mnt/music',
            'fanartpath': '/mnt/fanart',
            'tmppath': '/tmp'
        })
        config.setdefaults('sync', {
            'synchost': '127.0.0.1',
            'syncmpdport': '6600',
            'syncmusicpath': '/mnt/music',
            'syncfanartpath': '/mnt/fanart',
            'synctmppath': '/tmp',
            'syncplaylist': 'synclist'
        })
        config.setdefaults('system', {
            'rpienable': '0',
            'originalyear': '1',
            'advancedtitles': '0',
            'updatecommand': 'sudo pip install -U kmpc --no-deps',
            'rebootcommand': 'sudo reboot',
            'poweroffcommand': 'sudo poweroff',
            'exportfirst': '1',
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
            Logger.error("Application: color " + cc
                         + " for " + c + " is invalid")
            t = (1, 1, 1, 1)
        return t

    def get_application_config(self):
        ini = os.path.join(configdir, 'config.ini')
        return super(self.__class__, self).get_application_config(ini)

    def build_settings(self, settings):
        settings.add_json_panel(
                'mpd settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_mpd.json')))
        settings.add_json_panel(
                'path settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_paths.json')))
        settings.add_json_panel(
                'sync settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_sync.json')))
        settings.add_json_panel(
                'system settings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_system.json')))
        settings.add_json_panel(
                'song ratings',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_star.json')))
        settings.add_json_panel(
                'colors',
                self.config,
                resource_filename(
                        __name__,
                        os.path.join('resources/json', 'config_colors.json')))

    def on_config_change(self, config, section, key, value):
        if config is self.config:
            Logger.info("Application: config entry has changed: ["
                        + section + "] " + key + "=" + value)
            if callable(self.root.settings_update):
                self.root.settings_update()

    def build(self, *args):
        """Instantiates KmpcInterface."""
        self.version_str = VERSION_STR
        if not os.path.isdir(configdir):
            os.mkdir(configdir)
        # try to read existing config file
        self.config = self.load_config()
        # write out config file in case it doesn't exist yet
        self.config.write()
        if self.args.newconfig:
            sys.exit(0)
        elif self.args.sync:
            if self.args.sync == 'all':
                if self.config.getboolean('system', 'exportfirst'):
                    s = Sync(self.config, [
                            'music', 'fanart',
                            'exportratings', 'importratings'])
                else:
                    s = Sync(self.config, [
                            'music', 'fanart',
                            'importratings', 'exportratings'])
            else:
                s = Sync(self.config, [self.args.sync])
            sys.exit(0)
        else:
            return KmpcInterface(self.config)


if __name__ == '__main__':
    # run the app!
    KmpcApp().run()
