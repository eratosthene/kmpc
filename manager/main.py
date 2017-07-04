#!/usr/bin/env python

import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.support import install_twisted_reactor
from kivy.config import Config
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
from mpd import MPDProtocol
import os
import traceback
import mutagen
import io
import random
import musicbrainzngs
import pickle
from functools import partial
import json
import subprocess
import tempfile
import shutil

#install twisted reactor to interface with mpd
import sys
if 'twisted.internet.reactor' in sys.modules:
    del sys.modules['twisted.internet.reactor']
install_twisted_reactor()
from twisted.internet import reactor, protocol, task, defer, threads
from twisted.internet.defer import inlineCallbacks

from mpdfactory import MPDClientFactory
from extra import songratings,getfontsize

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
        self.config = config
        # set up mpd connection
        self.factory = MPDClientFactory()
        self.factory.connectionMade = self.mpd_connectionMade
        self.factory.connectionLost = self.mpd_connectionLost
        reactor.connectTCP(self.config.get('mpd','host'), self.config.getint('mpd','port'), self.factory)
        self.artist_id_hash={}
        self.artist_name_hash={}
        self.media_hash={}
        self.file_hash={}
        musicbrainzngs.set_rate_limit()
        musicbrainzngs.set_useragent("kmpcmanager","1.0")
        self.totaldone=0
        self.selected_row=None
        self.rsync_data={}
        self.rsync_file=None

    def mpd_connectionMade(self,protocol):
        self.protocol = protocol
        Logger.info('Manager: Connected to mpd server host='+self.config.get('mpd','host')+' port='+self.config.get('mpd','port'))
        self.ids.library_tab.protocol = self.protocol

    def mpd_connectionLost(self,protocol, reason):
        Logger.warn('Manager: Connection lost: %s' % reason)

    def handle_mpd_error(self,result):
        Logger.error('Manager: MPDIdleHandler Callback error: {}'.format(result))

    def refresh_artists(self):
        self.protocol.listallinfo('/').addCallback(self.populate_artists).addErrback(self.handle_mpd_error)

    def populate_artists(self,result):
        Logger.info("Manager: populate_artists")
        self.totaldone=0
        for row in result:
            if 'file' in row:
                self.ids.status.text='looking for id'
                if 'musicbrainz_artistid' in row:
                    aids = row['musicbrainz_artistid']
                    for aid in aids.split('/'):
                        if aid not in self.artist_id_hash:
                            #d = threads.deferToThread(partial(self.query_mb,aid))
                            d = self.query_mb(aid)
                            d.addCallback(partial(self.handle_mb_query,aid))
                            d.addErrback(self.handle_mb_error)
#                            Logger.debug("querying musicbrainz for aid "+aid)
#                            try:
#                                mbres=musicbrainzngs.get_artist_by_id(aid)
#                            except musicbrainzngs.WebServiceError as e:
#                                Logger.error("MusicBrainz: web service error "+format(e))
#                            else:
#                                aname=mbres['artist']['name']
#                                self.artist_id_hash[aid]=aname
#                                self.artist_name_hash[aname]=aid
#                                data = {'artist_id':aid,'artist_name':aname}
#                                self.ids.artist_tab.rv.data.append(data)
                    self.totaldone=self.totaldone+1
                    self.ids.status.text=aids+' ('+str(self.totaldone)+')'
                else:
                    ef=open('manager.err.txt','a')
                    ef.write(row['file'].encode('UTF-8')+"\n")
                    ef.close()
                self.file_hash[row['file']] = True
        self.ids.status.text=self.ids.status.text+' ('+str(len(self.artist_id_hash))+' total lines)'

    def query_mb(self,aid):
        d = defer.Deferred()
        d.callback(musicbrainzngs.get_artist_by_id(aid))
        return d

    def handle_mb_query(self,aid,mbres):
        aname=mbres['artist']['name']
        Logger.debug("result from musicbrainz for aid "+aid+": "+aname)
        self.artist_id_hash[aid]=aname
        self.artist_name_hash[aname]=aid
        data = {'artist_id':aid,'artist_name':aname}
        self.ids.artist_tab.rv.data.append(data)
        self.ids.artist_tab.rv.refresh_from_data()

    def handle_mb_error(self,result):
        Logger.error("MusicBrainz: web service error "+format(result))

    def write_artists_to_cache(self):
        cachefile=open('artist_cache.pkl','w')
        pickle.dump((self.artist_id_hash,self.artist_name_hash,self.media_hash,self.file_hash),cachefile,-1)
        cachefile.close()

    def refresh_artists_from_cache(self):
        cachefile=open('artist_cache.pkl','r')
        (self.artist_id_hash,self.artist_name_hash,self.media_hash,self.file_hash)=pickle.load(cachefile)
        cachefile.close()
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
        self.totaldone=len(self.file_hash)
        self.ids.status.text=str(self.totaldone)+' files checked, pulled '+str(len(self.artist_id_hash))+' lines from cache'
        self.ids.artist_tab.rv.data=sorted(newdata,key=lambda k: k['artist_name'])

    def scan_for_media(self,index):
        Logger.info('Manager: scanning '+self.ids.artist_tab.rv.data[index]['artist_id']+'for media')
        fa_path=self.config.get('mpd','fanartpath')
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
        print "fixing "+filename
        print "using tfile "+tf1
        subprocess.call(['convert',filename,'-bordercolor','none','-border','10x10',tf1])
        subprocess.call(['convert',tf1,'-trim','+repage',filename])
        shutil.rmtree(tdir)

    def pull_art(self,index):
        Logger.info('Manager: pulling art for '+self.ids.artist_tab.rv.data[index]['artist_id'])
	aid=self.ids.artist_tab.rv.data[index]['artist_id']
	aname=self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path=self.config.get('mpd','fanartpath')
	fanart=self.config.get('mpd','fanarturl')
        api_key=self.config.get('mpd','api_key')
        print fanart+aid+"?api_key="+api_key
        request = UrlRequest(url=fanart+aid+"?api_key="+api_key,on_success=partial(self.pull_art2,index))

    def pull_art2(self,index,request,result):
	aid=self.ids.artist_tab.rv.data[index]['artist_id']
	aname=self.ids.artist_tab.rv.data[index]['artist_name']
        fa_path=self.config.get('mpd','fanartpath')
	fanart=self.config.get('mpd','fanarturl')
        api_key=self.config.get('mpd','api_key')
        d=result
	if 'hdmusiclogo' in d or 'artistbackground' in d or 'musiclogo' in d:
	    fapath=os.path.join(fa_path,aid)
	    lpath=os.path.join(fapath,"logo")
	    abpath=os.path.join(fapath,"artistbackground")
	    try:
		print "downloading to "+fapath
		os.mkdir(fapath)
		with open(os.path.join(fapath,"__"+aname.replace('/','_')+"__"),'w'):
		    pass
	    except OSError:
		pass
	    if 'hdmusiclogo' in d:
		try:
		    os.mkdir(lpath)
		except OSError:
		    pass
		for idx,img in enumerate(d['hdmusiclogo']):
		    if not os.path.isfile(os.path.join(lpath,img['id']+'.png')):
			print "downloading hdmusiclogo "+img['id']
                        fp=os.path.join(lpath,img['id']+'.png')
                        req = UrlRequest(img['url'],on_success=partial(self.trim_image,fp),file_path=fp)
                        adfile=open('artlog.txt','a')
                        adfile.write(os.path.join(lpath,img['id']+'.png')+"\n")
                        adfile.close()
	    if 'musiclogo' in d:
		try:
		    os.mkdir(lpath)
		except OSError:
		    pass
		for idx,img in enumerate(d['musiclogo']):
		    if not os.path.isfile(os.path.join(lpath,img['id']+'.png')):
			print "downloading musiclogo "+img['id']
                        fp=os.path.join(lpath,img['id']+'.png')
                        req = UrlRequest(img['url'],on_success=partial(self.trim_image,fp),file_path=fp)
                        adfile=open('artlog.txt','a')
                        adfile.write(os.path.join(lpath,img['id']+'.png')+"\n")
                        adfile.close()
	    if 'artistbackground' in d:
		try:
		    os.mkdir(abpath)
		except OSError:
		    pass
		for idx,img in enumerate(d['artistbackground']):
		    if not os.path.isfile(os.path.join(abpath,img['id']+'.png')):
			print "downloading artistbackground "+img['id']
                        fp=os.path.join(abpath,img['id']+'.png')
                        req = UrlRequest(img['url'],file_path=fp)
                        adfile=open('artlog.txt','a')
                        adfile.write(os.path.join(abpath,img['id']+'.png')+"\n")
                        adfile.close()

    def pull_art_for_row(self):
        if self.selected_row is not None:
            self.pull_art(self.selected_row)
            self.scan_for_media(self.selected_row)
        self.write_artists_to_cache()

    def pull_art_for_all(self):
        for idx in range(0,len(self.ids.artist_tab.rv.data)):
            datum=self.ids.artist_tab.rv.data[idx]
            try:
                if not datum['has_logo'] and not datum['has_badge'] and not datum['has_artistbackground']:
                    self.pull_art(idx)
                    self.scan_for_media(idx)
            except KeyError:
                pass
        self.write_artists_to_cache()

    def generate_rsync(self):
        Logger.info('Rsync: generating with minimum stars '+self.ids.minimum_stars.text)
        self.rsync_data={}
        self.rsync_file=open('rsync.inc','w')
#        self.rsync_file.write("/**/\n")
        self.protocol.listallinfo('/').addCallback(self.generate2).addErrback(self.handle_mpd_error)

    def generate2(self,result):
        for row in result:
            if 'file' in row:
                uri=row['file']
                self.protocol.sticker_list('song',uri).addCallback(partial(self.rsync_add_uri,uri)).addErrback(partial(self.rsync_add_uri,uri))

    def rsync_add_uri(self,uri,result):
        docopy = False
        try:
            if 'rating' in result:
                if int(result['rating']) >= int(self.ids.minimum_stars.text):
                    docopy=True
            if 'copy_flag' in result:
                if result['copy_flag'] == 'Y':
                    docopy=True
                elif result['copy_flag'] == 'N':
                    docopy=False
        except:
            docopy = False
#        paths=os.path.normpath(uri).split(os.sep)
#        for idx,p in enumerate(paths):
#            if idx<(len(paths)-1):
#                mpath=''
#                for i in range(0,idx+1):
#                    if mpath=='':
#                        mpath=mpath+paths[i]
#                    else:
#                        mpath=mpath+os.sep+paths[i]
#                if mpath not in self.rsync_data:
#                    self.rsync_data[mpath]=True
#                    wline="+ "+mpath.encode("UTF-8")
#                    self.rsync_file.write(wline+"\n")
#                    Logger.debug("rsync: "+wline)
#        self.rsync_data[uri]=True
#        if docopy:
#            wline="+ "
#        else:
#            wline="- "
#        wline=wline+uri.encode("UTF-8")
#        self.rsync_file.write(wline+"\n")
#        Logger.debug("rsync: "+wline)
        if docopy:
            wline=uri.encode("UTF-8")
            self.rsync_file.write(wline+"\n")
            Logger.debug("rsync: "+wline)

    def write_rsync(self):
        Logger.info('Rsync: writing to disk')
#        self.rsync_file.write("- *\n")
        self.rsync_file.close()

class ManagerApp(App):
    def build_config(self,config):
        config.setdefaults('mpd',{
            'host': '127.0.0.1',
            'port': 6600,
            'basepath': '/mnt/music'
        })
        config.setdefaults('kivy',{
            'log_level': 'info',
            'log_enable': 1,
            'keyboard_mode': 'systemandmulti'
        })
        config.setdefaults('graphics',{
            'width': 1280,
            'height': 720
        })
        Config.read(self.get_application_config())
        self.config=config
    def build(self):
        return ManagerInterface(self.config)

if __name__ == '__main__':
    ManagerApp().run()

