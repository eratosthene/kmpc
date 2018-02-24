import os
import pickle
from functools import partial

import musicbrainzngs
from PIL import Image as PImage
from ConfigParser import NoSectionError, NoOptionError
import kivy
from kivy.app import App
from kivy.support import install_twisted_reactor
from kivy.logger import Logger
from kivy.network.urlrequest import UrlRequest
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.clock import Clock

from kmpc.version import VERSION, VERSION_STR
from kmpc.mpdfactory import MpdConnection
from kmpc.widgets import ArtistRecycleBoxLayout, ArtistRow, UneditTextInput

# make sure we are on updated version of kivy
kivy.require('1.10.0')

# sets the location of the config folder
configdir = os.path.join(os.path.expanduser('~'), ".kmpc")


class ManagerInterface(TabbedPanel):

    def __init__(self, config, **kwargs):
        TabbedPanel.__init__(self, **kwargs)
        self.config = config
        self.artist_id_hash = {}
        self.artist_name_hash = {}
        self.media_hash = {}
        self.wr_hash = {}
        self.totaldone = 0
        self.selected_row = None
        musicbrainzngs.set_useragent(
                "kmpcmanager",
                VERSION_STR,
                'https://github.com/eratosthene/kmpc')
        self.fanarturl = "http://webservice.fanart.tv/v3/music/"
        self.api_key = "406b2a5af85c14b819c1c6332354b313"
        # install twisted reactor to interface with mpd
        install_twisted_reactor()
        # open mpd connection
        self.syncmpdconnection = MpdConnection(
                self.config,
                self.config.get('sync', 'synchost'),
                self.config.get('sync', 'syncmpdport'),
                None,
                [self.init_mpd])
        if not App.get_running_app().root:
            # root isn't defined yet, it must be us
            Logger.debug("ManagerInterface: running as full app")
        else:
            # root is something else
            Logger.debug("ManagerInterface: running as class")
            App.get_running_app().root.syncmpdconnection = \
                self.syncmpdconnection

    def init_mpd(self, instance):
        self.refresh_artists_from_cache()

    def refresh_artists(self):
        (self.syncmpdconnection.protocol.
            list('musicbrainz_artistid').
            addCallback(self.populate_artists).
            addErrback(self.syncmpdconnection.handle_mpd_error))

    def populate_artists(self, result):
        Logger.info("Manager: populate_artists")
        self.totaldone = 0
        waittime = 1
        self.wr_hash = {}
        for row in result:
            aids = str(row)
            for aid in aids.split('/'):
                if (aid not in self.artist_id_hash and
                        aid not in self.wr_hash and
                        len(aid) > 0):
                    Logger.debug("MusicBrainz: scheduling query in "
                                 + str(waittime)+" seconds")
                    Clock.schedule_once(partial(self.query_mb, aid), waittime)
                    waittime += 1
                    self.wr_hash[aid] = True

    def query_mb(self, aid, *args):
        Logger.info("MusicBrainz: get_artist_by_id("+aid+")")
        try:
            mbres = musicbrainzngs.get_artist_by_id(aid)
        except WebServiceError as exc:
            Logger.error("MusicBrainz: web service error "+format(exc))
        else:
            aname = mbres['artist']['name']
            Logger.debug("query_mb: result from musicbrainz for aid "
                         + aid+": "+aname)
            self.artist_id_hash[aid] = aname
            self.artist_name_hash[aname] = aid
            data = {'artist_id': aid, 'artist_name': aname}
            self.ids.artist_tab.rv.data.append(data)
            self.ids.artist_tab.rv.refresh_from_data()
            self.totaldone += 1
            self.ids.status.text = aid+' ('+str(self.totaldone)+')'

    def write_artists_to_cache(self):
        cachefile = open(os.path.join(configdir, 'artist_cache.pkl'), 'w')
        pickle.dump(
                (self.artist_id_hash, self.artist_name_hash, self.media_hash),
                cachefile,
                -1)
        cachefile.close()

    def refresh_artists_from_cache(self):
        siat = self.ids.artist_tab
        try:
            cachefile = open(os.path.join(configdir, 'artist_cache.pkl'), 'r')
            (self.artist_id_hash, self.artist_name_hash, self.media_hash) = \
                pickle.load(cachefile)
            cachefile.close()
        except IOError:
            pass
        siat.rv.data = []
        newdata = []
        for aid, aname in self.artist_id_hash.iteritems():
            try:
                has_artistbackground = \
                    self.media_hash[aid]['has_artistbackground']
            except Exception:
                has_artistbackground = False
            try:
                has_logo = self.media_hash[aid]['has_logo']
            except Exception:
                has_logo = False
            try:
                has_badge = self.media_hash[aid]['has_badge']
            except Exception:
                has_badge = False
            datum = {
                    'artist_id': aid,
                    'artist_name': aname,
                    'has_artistbackground': has_artistbackground,
                    'has_logo': has_logo,
                    'has_badge': has_badge}
            newdata.append(datum)
        self.ids.status.text = \
            'pulled '+str(len(self.artist_id_hash)) + ' lines from cache'
        siat.rv.data = sorted(newdata, key=lambda k: k['artist_name'])

    def scan_for_media(self, index):
        siat = self.ids.artist_tab
        Logger.info('Manager: scanning '
                    + siat.rv.data[index]['artist_id']
                    + 'for media')
        fa_path = self.config.get('paths', 'fanartpath')
        artistbackground_path = os.path.join(
                fa_path,
                siat.rv.data[index]['artist_id'],
                'artistbackground')
        logo_path = os.path.join(
                fa_path,
                siat.rv.data[index]['artist_id'],
                'logo')
        badge_path = os.path.join(
                fa_path,
                siat.rv.data[index]['artist_id'],
                'badge')
        siat.rv.data[index]['has_artistbackground'] = \
            os.path.isdir(artistbackground_path)
        siat.rv.data[index]['has_logo'] = os.path.isdir(logo_path)
        siat.rv.data[index]['has_badge'] = os.path.isdir(badge_path)
        self.media_hash[siat.rv.data[index]['artist_id']] = {}
        self.media_hash[
            siat.rv.data[index]['artist_id']
            ]['has_artistbackground'] = os.path.isdir(artistbackground_path)
        self.media_hash[siat.rv.data[index]['artist_id']]['has_logo'] = \
            os.path.isdir(logo_path)
        self.media_hash[siat.rv.data[index]['artist_id']]['has_badge'] = \
            os.path.isdir(badge_path)
        siat.rv.refresh_from_data()

    def scan_row_for_media(self):
        if self.selected_row is not None:
            self.scan_for_media(self.selected_row)
        self.write_artists_to_cache()

    def scan_all_for_media(self, *args):
        for idx in range(0, len(self.ids.artist_tab.rv.data)):
            self.scan_for_media(idx)
        self.write_artists_to_cache()

    def trim_image(self, filename, request, result):
        Logger.debug("trim_image: fixing "+filename)
        image = PImage.open(filename)
        # convert to RGBa before getting bounding box to account for
        # transparent pixels
        bbox = image.convert("RGBa").getbbox()
        # crop it and save
        image = image.crop(bbox)
        image.save(filename)

    def pull_art(self, index, *args):
        Logger.info('Manager: pulling art for '
                    + self.ids.artist_tab.rv.data[index]['artist_id'])
        aid = self.ids.artist_tab.rv.data[index]['artist_id']
        aname = self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path = self.config.get('paths', 'fanartpath')
        fanart = self.fanarturl
        api_key = self.api_key
        furl = fanart+aid+"?api_key="+api_key
        client_key = self.config.get('fanart', 'client_key')
        if client_key:
            furl = furl+"&client_key="+client_key
        Logger.debug("pull_art: querying "+furl)
        request = UrlRequest(
                url=furl,
                on_success=partial(self.pull_art2, index))

    def pull_art2(self, index, request, result):
        aid = self.ids.artist_tab.rv.data[index]['artist_id']
        aname = self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path = self.config.get('paths', 'fanartpath')
        d = result
        # see if there are blacklist entries for this artist
        bl = []
        try:
            bl = self.config.get('artblacklist', aid).split(',')
        except NoSectionError:
            Logger.debug('pull_art2: no artblacklist section found')
        except NoOptionError:
            Logger.debug('pull_art2: no blacklist entries found for '+aid)
        except Exception as e:
            Logger.exception('pull_art2: '+format(e))
        else:
            Logger.debug('pull_art2: found blacklist entries for '
                         + aid+': '+format(bl))
        if 'hdmusiclogo' in d or 'artistbackground' in d or 'musiclogo' in d:
            fapath = os.path.join(fa_path, aid)
            lpath = os.path.join(fapath, "logo")
            abpath = os.path.join(fapath, "artistbackground")
            bpath = os.path.join(fapath, "badge")
            try:
                Logger.debug("pull_art2: downloading to "+fapath)
                os.mkdir(fapath)
                with open(
                        os.path.join(
                                fapath,
                                "__"+aname.replace(os.sep, '_')+"__"),
                        'w'):
                    pass
            except OSError:
                pass
            if 'hdmusiclogo' in d:
                try:
                    os.mkdir(lpath)
                except OSError:
                    pass
                for idx, img in enumerate(d['hdmusiclogo']):
                    if (not os.path.isfile(
                                os.path.join(lpath, img['id']+'.png')) and
                            not os.path.isfile(
                                    os.path.join(bpath, img['id']+'.png')) and
                            not img['id'] in bl):
                        Logger.debug("pull_art2: downloading hdmusiclogo "
                                     + img['id'])
                        fp = os.path.join(lpath, img['id']+'.png')
                        req = UrlRequest(
                                img['url'],
                                on_success=partial(self.trim_image, fp),
                                file_path=fp)
                        if self.config.getboolean('logs', 'artlog'):
                            adfile = open(
                                    os.path.join(configdir, 'artlog.txt'),
                                    'a')
                            adfile.write(
                                    os.path.join(lpath, img['id']+'.png')+"\n")
                            adfile.close()
            if 'musiclogo' in d:
                try:
                    os.mkdir(lpath)
                except OSError:
                    pass
                for idx, img in enumerate(d['musiclogo']):
                    if (not os.path.isfile(
                                os.path.join(lpath, img['id']+'.png')) and
                            not os.path.isfile(
                                    os.path.join(bpath, img['id']+'.png')) and
                            not img['id'] in bl):
                        Logger.debug("pull_art2: downloading musiclogo "
                                     + img['id'])
                        fp = os.path.join(lpath, img['id']+'.png')
                        req = UrlRequest(
                                img['url'],
                                on_success=partial(self.trim_image, fp),
                                file_path=fp)
                        if self.config.getboolean('logs', 'artlog'):
                            adfile = open(
                                    os.path.join(configdir, 'artlog.txt'),
                                    'a')
                            adfile.write(
                                    os.path.join(lpath, img['id']+'.png')+"\n")
                            adfile.close()
            if 'artistbackground' in d:
                try:
                    os.mkdir(abpath)
                except OSError:
                    pass
                for idx, img in enumerate(d['artistbackground']):
                    if (not os.path.isfile(
                                os.path.join(abpath, img['id']+'.png')) and
                            not img['id'] in bl):
                        Logger.debug("pull_art2: downloading artistbackground "
                                     + img['id'])
                        fp = os.path.join(abpath, img['id']+'.png')
                        req = UrlRequest(img['url'], file_path=fp)
                        if self.config.getboolean('logs', 'artlog'):
                            adfile = open(
                                    os.path.join(configdir, 'artlog.txt'),
                                    'a')
                            adfile.write(
                                    os.path.join(
                                            abpath,
                                            img['id']+'.png')+"\n")
                            adfile.close()

    def pull_art_for_row(self):
        if self.selected_row is not None:
            self.pull_art(self.selected_row)
            self.scan_for_media(self.selected_row)
        self.write_artists_to_cache()

    def pull_art_for_all(self):
        waittime = 1
        for idx in range(0, len(self.ids.artist_tab.rv.data)):
            Logger.debug("FanArt.tv: scheduling query in "
                         + str(waittime)+" seconds")
            Clock.schedule_once(partial(self.pull_art, idx), waittime)
            waittime += 1
        Clock.schedule_once(self.scan_all_for_media, waittime+5)
        self.write_artists_to_cache()
