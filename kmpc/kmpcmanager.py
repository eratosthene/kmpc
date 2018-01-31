# import dependencies
import os
import sys
import traceback
import mutagen
import io
import random
import pickle
from functools import partial
import json
import subprocess
import tempfile
import shutil
from pkg_resources import resource_filename
import musicbrainzngs
import ConfigParser

# make sure we are on an updated version of kivy
import kivy
kivy.require('1.10.0')

# import all the other kivy stuff
from kivy.config import Config
from kivy.app import App
from kivy.support import install_twisted_reactor
from kivy.logger import Logger
from kivy.graphics import Color,Rectangle
from kivy.core.image import Image as CoreImage
from kivy.metrics import Metrics, sp
from kivy.properties import BooleanProperty
from kivy.network.urlrequest import UrlRequest
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image,AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior, FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.lang import Builder

# import our local modules
from kmpc.extra import KmpcHelpers
from kmpc.version import VERSION, VERSION_STR
from kmpc.mpdfactory import MpdConnection

# sets the location of the config folder
configdir = os.path.join(os.path.expanduser('~'),".kmpc")

# load the manager.kv file
Builder.load_file(resource_filename(__name__,os.path.join('resources','manager.kv')))

Helpers=KmpcHelpers()

class ArtistRecycleBoxLayout(FocusBehavior,LayoutSelectionBehavior,RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class ArtistRow(RecycleDataViewBehavior,BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(ArtistRow, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(ArtistRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            App.get_running_app().root.selected_row=index

class UneditTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        pass

class ManagerInterface(TabbedPanel):

    def __init__(self,config):
        super(self.__class__,self).__init__()
        self.config=config
        self.songratings=Helpers.songratings(config)
        self.artist_id_hash={}
        self.artist_name_hash={}
        self.media_hash={}
        self.wr_hash={}
        self.totaldone=0
        self.selected_row=None
        musicbrainzngs.set_useragent("kmpcmanager",VERSION_STR,'https://github.com/eratosthene/kmpc')
        self.fanarturl="http://webservice.fanart.tv/v3/music/"
        self.api_key="406b2a5af85c14b819c1c6332354b313"
        #install twisted reactor to interface with mpd
        install_twisted_reactor()
        global mainmpdconnection
        mainmpdconnection=MpdConnection(self.config,self.config.get('sync','synchost'),self.config.get('sync','syncmpdport'),None,[self.init_mpd])

    def init_mpd(self,instance):
        self.refresh_artists_from_cache()

    def refresh_artists(self):
        mainmpdconnection.protocol.list('musicbrainz_artistid').addCallback(self.populate_artists).addErrback(mainmpdconnection.handle_mpd_error)

    def populate_artists(self,result):
        Logger.info("Manager: populate_artists")
        self.totaldone=0
        waittime=1
        self.wr_hash={}
        for row in result:
            aids = str(row)
            for aid in aids.split('/'):
                if aid not in self.artist_id_hash and aid not in self.wr_hash and len(aid)>0:
                    Logger.debug("MusicBrainz: scheduling query in "+str(waittime)+" seconds")
                    Clock.schedule_once(partial(self.query_mb,aid),waittime)
                    waittime=waittime+1
                    self.wr_hash[aid]=True

    def query_mb(self,aid,*largs):
        Logger.info("MusicBrainz: get_artist_by_id("+aid+")")
        try:
            mbres=musicbrainzngs.get_artist_by_id(aid)
        except WebServiceError as exc:
            Logger.error("MusicBrainz: web service error "+format(exc))
        else:
            aname=mbres['artist']['name']
            Logger.debug("query_mb: result from musicbrainz for aid "+aid+": "+aname)
            self.artist_id_hash[aid]=aname
            self.artist_name_hash[aname]=aid
            data = {'artist_id':aid,'artist_name':aname}
            self.ids.artist_tab.rv.data.append(data)
            self.ids.artist_tab.rv.refresh_from_data()
            self.totaldone=self.totaldone+1
            self.ids.status.text=aid+' ('+str(self.totaldone)+')'

    def write_artists_to_cache(self):
        cachefile=open(os.path.join(configdir,'artist_cache.pkl'),'w')
        pickle.dump((self.artist_id_hash,self.artist_name_hash,self.media_hash),cachefile,-1)
        cachefile.close()

    def refresh_artists_from_cache(self):
        try:
            cachefile=open(os.path.join(configdir,'artist_cache.pkl'),'r')
            (self.artist_id_hash,self.artist_name_hash,self.media_hash)=pickle.load(cachefile)
            cachefile.close()
        except IOError:
            pass
        self.ids.artist_tab.rv.data=[]
        newdata=[]
        for aid,aname in self.artist_id_hash.iteritems():
            try:
                has_artistbackground=self.media_hash[aid]['has_artistbackground']
            except:
                has_artistbackground=False
            try:
                has_logo=self.media_hash[aid]['has_logo']
            except:
                has_logo=False
            try:
                has_badge=self.media_hash[aid]['has_badge']
            except:
                has_badge=False
            datum = {'artist_id':aid,'artist_name':aname,'has_artistbackground':has_artistbackground,'has_logo':has_logo,'has_badge':has_badge}
            newdata.append(datum)
        self.ids.status.text='pulled '+str(len(self.artist_id_hash))+' lines from cache'
        self.ids.artist_tab.rv.data=sorted(newdata,key=lambda k: k['artist_name'])

    def scan_for_media(self,index):
        Logger.info('Manager: scanning '+self.ids.artist_tab.rv.data[index]['artist_id']+'for media')
        fa_path=self.config.get('paths','fanartpath')
        artistbackground_path=os.path.join(fa_path,self.ids.artist_tab.rv.data[index]['artist_id'],'artistbackground')
        logo_path=os.path.join(fa_path,self.ids.artist_tab.rv.data[index]['artist_id'],'logo')
        badge_path=os.path.join(fa_path,self.ids.artist_tab.rv.data[index]['artist_id'],'badge')
        self.ids.artist_tab.rv.data[index]['has_artistbackground']=os.path.isdir(artistbackground_path)
        self.ids.artist_tab.rv.data[index]['has_logo']=os.path.isdir(logo_path)
        self.ids.artist_tab.rv.data[index]['has_badge']=os.path.isdir(badge_path)
        self.media_hash[self.ids.artist_tab.rv.data[index]['artist_id']]={}
        self.media_hash[self.ids.artist_tab.rv.data[index]['artist_id']]['has_artistbackground']=os.path.isdir(artistbackground_path)
        self.media_hash[self.ids.artist_tab.rv.data[index]['artist_id']]['has_logo']=os.path.isdir(logo_path)
        self.media_hash[self.ids.artist_tab.rv.data[index]['artist_id']]['has_badge']=os.path.isdir(badge_path)
        self.ids.artist_tab.rv.refresh_from_data()

    def scan_row_for_media(self):
        if self.selected_row is not None:
            self.scan_for_media(self.selected_row)
        self.write_artists_to_cache()

    def scan_all_for_media(self):
        for idx in range(0,len(self.ids.artist_tab.rv.data)):
            self.scan_for_media(idx)
        self.write_artists_to_cache()

    def trim_image(self,filename,request,result):
        tdir=tempfile.mkdtemp()
        tf1=os.path.join(tdir,'tf1.png')
        Logger.debug("trim_image: fixing "+filename)
        Logger.debug("trim_image: using tfile "+tf1)
        subprocess.call(['convert',filename,'-bordercolor','none','-border','10x10',tf1])
        subprocess.call(['convert',tf1,'-trim','+repage',filename])
        shutil.rmtree(tdir)

    def pull_art(self,index,*largs):
        Logger.info('Manager: pulling art for '+self.ids.artist_tab.rv.data[index]['artist_id'])
        aid=self.ids.artist_tab.rv.data[index]['artist_id']
        aname=self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path=self.config.get('paths','fanartpath')
        fanart=self.fanarturl
        api_key=self.api_key
        furl=fanart+aid+"?api_key="+api_key
        client_key=self.config.get('fanart','client_key')
        if client_key:
            furl=furl+"&client_key="+client_key
        Logger.debug("pull_art: querying "+furl)
        request = UrlRequest(url=furl,on_success=partial(self.pull_art2,index))

    def pull_art2(self,index,request,result):
        aid=self.ids.artist_tab.rv.data[index]['artist_id']
        aname=self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path=self.config.get('paths','fanartpath')
        d=result
        # see if there are blacklist entries for this artist
        bl=[]
        try:
            bl=self.config.get('artblacklist',aid).split(',')
        except ConfigParser.NoSectionError:
            Logger.debug('pull_art2: no artblacklist section found')
        except ConfigParser.NoOptionError:
            Logger.debug('pull_art2: no blacklist entries found for '+aid)
        except Exception as e:
            Logger.exception('pull_art2: '+format(e))
        else:
            Logger.debug('pull_art2: found blacklist entries for '+aid+': '+format(bl))
        if 'hdmusiclogo' in d or 'artistbackground' in d or 'musiclogo' in d:
            fapath=os.path.join(fa_path,aid)
            lpath=os.path.join(fapath,"logo")
            abpath=os.path.join(fapath,"artistbackground")
            bpath=os.path.join(fapath,"badge")
            try:
                Logger.debug("pull_art2: downloading to "+fapath)
                os.mkdir(fapath)
                with open(os.path.join(fapath,"__"+aname.replace(os.sep,'_')+"__"),'w'):
                    pass
            except OSError:
                pass
            if 'hdmusiclogo' in d:
                try:
                    os.mkdir(lpath)
                except OSError:
                    pass
                for idx,img in enumerate(d['hdmusiclogo']):
                    if not os.path.isfile(os.path.join(lpath,img['id']+'.png')) and not os.path.isfile(os.path.join(bpath,img['id']+'.png')) and not img['id'] in bl:
                        Logger.debug("pull_art2: downloading hdmusiclogo "+img['id'])
                        fp=os.path.join(lpath,img['id']+'.png')
                        req = UrlRequest(img['url'],on_success=partial(self.trim_image,fp),file_path=fp)
                        if self.config.getboolean('logs','artlog'):
                            adfile=open(os.path.join(configdir,'artlog.txt'),'a')
                            adfile.write(os.path.join(lpath,img['id']+'.png')+"\n")
                            adfile.close()
            if 'musiclogo' in d:
                try:
                    os.mkdir(lpath)
                except OSError:
                    pass
                for idx,img in enumerate(d['musiclogo']):
                    if not os.path.isfile(os.path.join(lpath,img['id']+'.png')) and not os.path.isfile(os.path.join(bpath,img['id']+'.png')) and not img['id'] in bl:
                        Logger.debug("pull_art2: downloading musiclogo "+img['id'])
                        fp=os.path.join(lpath,img['id']+'.png')
                        req = UrlRequest(img['url'],on_success=partial(self.trim_image,fp),file_path=fp)
                        if self.config.getboolean('logs','artlog'):
                            adfile=open(os.path.join(configdir,'artlog.txt'),'a')
                            adfile.write(os.path.join(lpath,img['id']+'.png')+"\n")
                            adfile.close()
            if 'artistbackground' in d:
                try:
                    os.mkdir(abpath)
                except OSError:
                    pass
                for idx,img in enumerate(d['artistbackground']):
                    if not os.path.isfile(os.path.join(abpath,img['id']+'.png')) and not img['id'] in bl:
                        Logger.debug("pull_art2: downloading artistbackground "+img['id'])
                        fp=os.path.join(abpath,img['id']+'.png')
                        req = UrlRequest(img['url'],file_path=fp)
                        if self.config.getboolean('logs','artlog'):
                            adfile=open(os.path.join(configdir,'artlog.txt'),'a')
                            adfile.write(os.path.join(abpath,img['id']+'.png')+"\n")
                            adfile.close()

    def pull_art_for_row(self):
        if self.selected_row is not None:
            self.pull_art(self.selected_row)
            self.scan_for_media(self.selected_row)
        self.write_artists_to_cache()

    def pull_art_for_all(self):
        waittime=1
        for idx in range(0,len(self.ids.artist_tab.rv.data)):
            Logger.debug("FanArt.tv: scheduling query in "+str(waittime)+" seconds")
            Clock.schedule_once(partial(self.pull_art,idx),waittime)
            waittime=waittime+1
        Clock.schedule_once(self.scan_all_for_media,waittime+5)
        self.write_artists_to_cache()


class ManagerApp(App):

    def __init__(self,args):
        Config.set('graphics','width',1280)
        Config.set('graphics','height',720)
        Config.set('kivy','keyboard_mode','system')
        self.args=args
        super(self.__class__,self).__init__()

    def build_config(self,config):
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

    def get_application_config(self):
        return super(self.__class__,self).get_application_config(configdir+'/config.ini')

    def build_settings(self,settings):
        settings.add_json_panel('sync settings',self.config,resource_filename(__name__,os.path.join('resources','config_manager_sync.json')))
        settings.add_json_panel('log settings',self.config,resource_filename(__name__,os.path.join('resources','config_manager_logs.json')))
        settings.add_json_panel('fanart settings',self.config,resource_filename(__name__,os.path.join('resources','config_fanart.json')))
        settings.add_json_panel('song ratings',self.config,resource_filename(__name__,os.path.join('resources','config_star.json')))

    def build(self):
        if not os.path.isdir(configdir):
            os.mkdir(configdir)
        # try to read existing config file
        self.config=self.load_config()
        # write out config file in case it doesn't exist yet
        self.config.write()
        # setup some variables that interface.kv will use
        # this is necessary to support packaging the app
        self.normalfont = resource_filename(__name__,os.path.join('resources','DejaVuSans.ttf'))
        self.fontawesomefont = resource_filename(__name__,os.path.join('resources','FontAwesome.ttf'))
        if self.args.newconfig:
            sys.exit(0)
        else:
            return ManagerInterface(self.config)

if __name__ == '__main__':
    ManagerApp().run()

