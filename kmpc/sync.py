import os
import io
from threading import Thread
from Queue import Queue, Empty
from functools import partial
from subprocess import call, PIPE, Popen
from kmpc.mpd import MPDProtocol
from kmpc.mpdfactory import MPDClientFactory,MpdConnection
from kmpc.extra import KmpcHelpers

import kivy
kivy.require('1.10.0')

from twisted.internet.defer import Deferred,DeferredList

from kivy.logger import Logger

Helpers=KmpcHelpers()

class Sync(object):

    def __init__(self,config,runparts=[]):
        from twisted.internet import reactor
        self.config=config
        self.mpdhost=config.get('mpd','mpdhost')
        self.mpdport=config.get('mpd','mpdport')
        self.synchost=config.get('sync','synchost')
        self.syncmpdport=config.get('sync','syncmpdport')
        self.synclist=config.get('sync','syncplaylist')
        self.basepath=config.get('paths','musicpath')
        self.fanartpath=config.get('paths','fanartpath')
        self.syncbasepath=config.get('sync','syncmusicpath')
        self.syncfanartpath=config.get('sync','syncfanartpath')
        self.tmppath=config.get('paths','tmppath')
        self.runparts=runparts
        self.localconnected=False
        self.syncconnected=False
        self.kivy=True
        self.thread=None
        self.filelist={}
        self.updating=False
        self.updatedone=False
        self.modulesdone=False
        self.ratingsdone=False
        self.fanartdone=False
        self.finished=False
        self.callbacks=[]
        Logger.info("Sync: running sync with synchost "+self.synchost+" with modules "+format(runparts))
        if self.mpdhost==self.synchost:
            Logger.warn('Sync: will not sync identical hosts!')
            return
        self.localmpd=MpdConnection(self.config,self.mpdhost,self.mpdport,self.mpd_idle_handler,[self.init_local_mpd],True)
        self.syncmpd=MpdConnection(self.config,self.synchost,self.syncmpdport,None,[self.init_sync_mpd],True)
        self.d = Deferred()
        self.d2 = Deferred()
        self.d3 = Deferred()
        if 'music' in runparts:
            self.callbacks.append(self.d.addCallbacks(self.sync_music,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.build_filelist,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.output_to,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.cleanup_music_sync,self.errback))
            self.callbacks.append(self.d2)
        if 'fanart' in runparts:
            self.callbacks.append(self.d.addCallbacks(self.sync_fanart,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.output_to,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.finish_fanart_sync,self.errback))
        if 'ratings' in runparts:
            self.callbacks.append(self.d.addCallbacks(self.sync_ratings,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.handle_export_ratings,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.import_ratings,self.errback))
            self.callbacks.append(self.d.addCallbacks(self.handle_import_ratings,self.errback))
            self.callbacks.append(self.d3)
        if not reactor.running:
            self.kivy=False
            reactor.run()

#### override these when subclassing
    def runatend(self):
        from twisted.internet import reactor
        #print "RUNATEND"
        if not self.finished:
            #print "NOTFINISHED"
            self.finished=True
            if not self.kivy:
                #print "REACTOR STOP"
                reactor.stop() # if this runs twice we get an unhandled exception
        #else:
            #print "ALREADYFINISHED"

    def output_to(self,q):
        Logger.debug("infolog: started")
        while self.is_thread_alive():
            try: line=q.get_nowait()
            except Empty: pass
            else: Logger.info("Stdout Log: "+line.rstrip())
        return True

#### overall operation functions
    def init_local_mpd(self,conn):
        Logger.debug("init_local_mpd: connected")
        self.localconnected=True
        self.do_sync()

    def init_sync_mpd(self,conn):
        Logger.debug("init_sync_mpd: connected")
        self.syncconnected=True
        self.do_sync()

    def do_sync(self):
        if self.localconnected and self.syncconnected:
            Logger.info("Sync: beginning sync process")
            dlist=DeferredList(self.callbacks,consumeErrors=True)
            dlist.addCallback(self.finishup)
            self.d.callback('BEGIN')
#            callbacks=[]
#            d=Deferred()
#            for part in self.runparts:
#                callbacks.append(d.addCallback(getattr(self,'sync_'+part)))
#            callbacks = DeferredList(callbacks)
#            callbacks.addCallback(self.finalize)
#            callbacks.addErrback(self.errback)
#            d.callback(None)

    def finishup(self,result):
        print format(result)

#### fanart sync functions
    def sync_fanart(self,result):
        Logger.info("Sync: syncing fanart")
        q = Queue()
        # rsync the files
        p=Popen([
            'rsync',
            '-vruxhm',
            self.synchost+':'+self.syncfanartpath+'/',
            self.fanartpath
            ],stdout=PIPE,bufsize=1,close_fds=True)
        self.thread = Thread(target=self.buffer_stdout,args=(p,q))
        self.thread.daemon = True
        self.thread.start()
        #self.dfanart=Deferred()
        #d.addCallback(self.output_to)
        #d.addCallback(self.finish_fanart_sync)
        #d.addErrback(self.errback)
        #d.callback(q)
        return q

    def finish_fanart_sync(self,result):
        Logger.info("Sync: fanart synced from synchost")
        return True
#        self.fanartdone=True
#        if self.check_stop(): self.runatend()

#### ratings sync functions
    def sync_ratings(self,result):
        Logger.info("Sync: syncing ratings")
        return self.localmpd.protocol.sticker_find('song','','rating')
        #return self.localmpd.protocol.sticker_find('song','','rating').addCallback(self.handle_export_ratings).addErrback(self.errback)

    def handle_export_ratings(self,result):
        Logger.debug("Sync: handle_export_ratings")
        cb=[]
        for row in result:
            uri=Helpers.decodeFileName(row['file'])
            rating=str(row['sticker'].split('=')[1])
            cb.append(self.syncmpd.protocol.sticker_set('song',uri,'rating',rating).addCallback(partial(self.handle_rating_set,'export',uri,rating,True)).addErrback(partial(self.handle_rating_set,'export',uri,rating,False)))
        udl=DeferredList(cb,consumeErrors=True)
        return udl.addCallback(self.finish_export_ratings)

    def finish_export_ratings(self,result):
        Logger.debug("Sync: finish_export_ratings")
        #self.d3.callback(True)
        return True

    def import_ratings(self,result):
        Logger.debug("Sync: import_ratings")
        return self.syncmpd.protocol.sticker_find('song','','rating')
        #return self.syncmpd.protocol.sticker_find('song','','rating').addCallback(self.handle_import_ratings).addErrback(self.errback)

    def handle_import_ratings(self,result):
        Logger.debug("Sync: handle_import_ratings")
#        callbacks=[]
        cb=[]
        for row in result:
            uri=Helpers.decodeFileName(row['file'])
            rating=str(row['sticker'].split('=')[1])
#            callbacks.append(self.localmpd.protocol.sticker_set('song',uri,'rating',rating).addCallback(partial(self.handle_rating_set,'import',uri,rating,True)).addErrback(partial(self.handle_rating_set,'import',uri,rating,False)))
            cb.append(self.localmpd.protocol.sticker_set('song',uri,'rating',rating).addCallback(partial(self.handle_rating_set,'import',uri,rating,True)).addErrback(partial(self.handle_rating_set,'import',uri,rating,False)))
        #callbacks=DeferredList(callbacks)
        #callbacks.addCallback(self.set_ratingsdone)
        udl=DeferredList(cb,consumeErrors=True)
        return udl.addCallback(self.finish_import_ratings)
        #return callbacks
        #return True

    def finish_import_ratings(self,result):
        Logger.debug("Sync: finish_import_ratings")
        self.d3.callback(True)
        return True

    def handle_rating_set(self,sdir,uri,rating,succ,result):
        if succ:
            Logger.debug("handle_rating_set: successfully "+sdir+"ed rating for "+uri)

    def set_ratingsdone(self,result):
        Logger.info('Sync: ratings synced with synchost')
        self.ratingsdone=True
        self.localmpd.protocol.update()
        if self.check_stop(): self.runatend()

#### music sync functions
    def sync_music(self,result):
        Logger.info("Sync: syncing using playlist ["+self.synclist+"]")
        # clear the local 'root' playlist
        self.localmpd.protocol.playlistclear('root').addErrback(self.localmpd.handle_mpd_error)
        return self.syncmpd.protocol.listplaylist(self.synclist)
        #return self.syncmpd.protocol.listplaylist(self.synclist).addCallback(self.build_filelist).addCallback(self.output_to).addCallback(self.finish_filesync).addErrback(self.syncmpd.handle_mpd_error)

    def build_filelist(self,result):
        Logger.debug("build_filelist: writing file/hash")
        # write synclist to a temp file, and a hash
        f=io.open(os.path.join(self.tmppath,'rsync.inc'),mode='w',encoding="utf-8")
        for row in result:
            f.write(Helpers.decodeFileName(row)+"\n")
            self.filelist[Helpers.decodeFileName(row.rstrip())]=True
        f.close()
        # this whole block walks the filesystem and deletes any file that is not in the synclist
        Logger.debug("build_filelist: deleting old files")
        for dirpath, dirnames, filenames in os.walk(Helpers.decodeFileName(self.basepath)):
            if len(filenames)>0:
                rpath = dirpath[len(self.basepath+os.sep):]
                for filename in filenames:
                    fpath=os.path.join(Helpers.decodeFileName(rpath),Helpers.decodeFileName(filename))
                    apath = os.path.join(Helpers.decodeFileName(dirpath),Helpers.decodeFileName(filename))
                    if fpath not in self.filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(Helpers.decodeFileName(apath))
        Logger.debug("build_filelist: removing empty folders")
        # remove empty folders
        Helpers.removeEmptyFolders(self.basepath)
        # queue to hold stdout
        q = Queue()
        # rsync the files
        p=Popen([
            'rsync',
            '-vruxhm',
            '--files-from='+os.path.join(self.tmppath,'rsync.inc'),
            self.synchost+':'+self.syncbasepath+'/',
            self.basepath
            ],stdout=PIPE,bufsize=1,close_fds=True)
        self.thread = Thread(target=self.buffer_stdout,args=(p,q))
        self.thread.daemon = True
        self.thread.start()
        return q

    def cleanup_music_sync(self,result):
        Logger.info("Sync: cleaning up")
        # clean up
        os.remove(os.path.join(self.tmppath,'rsync.inc'))
        self.localmpd.protocol.update()
        return True

    def mpd_idle_handler(self,result):
        for s in result:
            if format(s)=='update':
                Logger.debug('mpd_idle_handler: Changed '+format(s))
                self.localmpd.protocol.status().addCallback(self.handle_update)

    def handle_update(self,result):
        if 'updating_db' not in result:
            Logger.debug("handle_update: updating_db done")
            cb=[]
            for k in sorted(self.filelist.keys()):
                cb.append(self.localmpd.protocol.playlistadd('root',k))
            udl=DeferredList(cb,consumeErrors=True)
            udl.addCallback(self.finish_update)
        return True

    def finish_update(self,result):
        print "FINISHUPDATE"
        self.d2.callback(True)
        return True

    def old_handle_update(self,result):
        if 'updating_db' in result:
            self.updating=True
            #print "SET UPDATING TRUE"
        else:
            if self.updating:
                # this is where tasks that must wait til after update db go
                callbacks=[]
                for k in sorted(self.filelist.keys()):
                    callbacks.append(self.localmpd.protocol.playlistadd('root',k).addErrback(self.localmpd.handle_mpd_error))
                callbacks=DeferredList(callbacks)
                callbacks.addCallback(self.set_updatedone)
                callbacks.callback(0)

    def set_updatedone(self,result):
        Logger.info('Sync: update done and playlist updated')
        self.updating=False
        #print "SET UPDATING FALSE"
        self.updatedone=True
        #if self.check_stop(): self.runatend()

#    def finalize(self,result):
#        Logger.info("Sync: all sync modules run")
#        self.modulesdone=True
#        if self.check_stop(): self.runatend()

#### helper functions
    def is_thread_alive(self):
        if self.thread and self.thread.is_alive(): return True
        else: return False

    def check_stop(self):
        stopit=self.modulesdone
        #print "MODULESDONE: "+format(stopit)
        if 'ratings' in self.runparts:
            # only if ratings are complete
            stopit=stopit and self.ratingsdone
            #print "RATINGSDONE: "+format(stopit)
        if 'fanart' in self.runparts:
            # only if fanart sync is complete
            stopit=stopit and self.fanartdone
            #print "FANARTDONE: "+format(stopit)
        if 'music' in self.runparts:
            # only if update is complete
            stopit=stopit and self.updatedone
            #print "MUSICDONE: "+format(stopit)
        #print "RETURNING "+format(stopit)
        return stopit

    def errback(self,result):
        Logger.error('Sync: Callback error: {}'.format(result))

    def buffer_stdout(self,proc,queue):
        Logger.debug("buffer_stdout: start")
        for line in iter(proc.stdout.readline, b''):
            queue.put(line)
        Logger.debug("buffer_stdout: end")


