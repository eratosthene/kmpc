from __future__ import print_function
import os
import io
from functools import partial

from twisted.internet import protocol
from twisted.internet.defer import Deferred, DeferredList
import kivy
from kivy.logger import Logger

from kmpc.mpd import MPDProtocol
from kmpc.mpdfactory import MpdConnection
from kmpc.extra import KmpcHelpers

# make sure we are on updated version of kivy
kivy.require('1.10.0')

Helpers = KmpcHelpers()


class Sync(object):

    def __init__(self, config, runparts=[]):
        from twisted.internet import reactor
        self.config = config
        self.mpdhost = config.get('mpd', 'mpdhost')
        self.mpdport = config.get('mpd', 'mpdport')
        self.synchost = config.get('sync', 'synchost')
        self.syncmpdport = config.get('sync', 'syncmpdport')
        self.synclist = config.get('sync', 'syncplaylist')
        self.basepath = config.get('paths', 'musicpath')
        self.fanartpath = config.get('paths', 'fanartpath')
        self.syncbasepath = config.get('sync', 'syncmusicpath')
        self.syncfanartpath = config.get('sync', 'syncfanartpath')
        self.tmppath = config.get('paths', 'tmppath')
        self.runparts = runparts
        self.localconnected = False
        self.syncconnected = False
        self.kivy = True
        self.filelist = {}
        self.callbacks = []
        self.print_line("Running sync with synchost "
                        + self.synchost+" with modules "+format(runparts))
        if self.mpdhost == self.synchost:
            Logger.warn('Sync: will not sync identical hosts!')
            return
        self.localmpd = MpdConnection(
                self.config,
                self.mpdhost,
                self.mpdport,
                self.mpd_idle_handler,
                [self.init_local_mpd],
                True,
                False)
        self.syncmpd = MpdConnection(
                self.config,
                self.synchost,
                self.syncmpdport,
                None,
                [self.init_sync_mpd],
                True,
                False)
        self.d = Deferred()
        self.d2 = Deferred()
        self.d3 = Deferred()
        self.d4 = Deferred()
        if 'music' in runparts:
            self.callbacks.append(self.d.addCallbacks(
                    self.sync_music,
                    self.errback))
            self.callbacks.append(self.d.addCallbacks(
                    self.build_filelist,
                    self.errback))
            self.callbacks.append(self.d.addCallbacks(
                    self.cleanup_music_sync,
                    self.errback))
            self.callbacks.append(self.d2.addErrback(self.errback))
        if 'fanart' in runparts:
            self.callbacks.append(self.d.addCallbacks(
                    self.sync_fanart,
                    self.errback))
            self.callbacks.append(self.d.addCallbacks(
                    self.finish_fanart_sync,
                    self.errback))
        if 'exportratings' in runparts:
            self.callbacks.append(self.d.addCallbacks(
                    self.sync_export_ratings,
                    self.errback))
            self.callbacks.append(self.d.addCallbacks(
                self.handle_export_ratings,
                self.errback))
            self.callbacks.append(self.d3.addErrback(self.errback))
        if 'importratings' in runparts:
            self.callbacks.append(self.d.addCallbacks(
                    self.sync_import_ratings,
                    self.errback))
            self.callbacks.append(self.d.addCallbacks(
                    self.handle_import_ratings,
                    self.errback))
            self.callbacks.append(self.d4.addErrback(self.errback))
        if not reactor.running:
            self.kivy = False
            reactor.run()

###################################
# override these when subclassing #
###################################
    def run_at_end(self, result):
        from twisted.internet import reactor
        Logger.debug("Sync: callbacks done: "+format(result))
        if not self.kivy:
            reactor.stop()

    def show_ratings_progress(self, done, total, sdir):
        print(done, 'of', total, end='\r')

    def ratings_incoming(self, sdir):
        pass

    def print_line(self, line):
        Logger.info("Sync: "+line)

    def errback(self, result):
        Logger.error('Sync: Callback error: '+format(result))

###############################
# overall operation functions #
###############################
    def init_local_mpd(self, conn):
        Logger.debug("init_local_mpd: connected")
        self.localconnected = True
        self.do_sync()

    def init_sync_mpd(self, conn):
        Logger.debug("init_sync_mpd: connected")
        self.syncconnected = True
        self.do_sync()

    def do_sync(self):
        if self.localconnected and self.syncconnected:
            self.print_line("Beginning sync process")
            dlist = DeferredList(self.callbacks, consumeErrors=True)
            dlist.addCallbacks(self.disconnect, self.errback)
            dlist.addCallbacks(self.run_at_end, self.errback)
            self.d.callback('BEGIN')

    def disconnect(self, result):
        self.print_line("Disconnecting from synchost")
        try:
            self.localmpd.reactor.disconnect()
            self.syncmpd.reactor.disconnect()
        except Exception as e:
            Logger.debug("Exception: "+format(e))
        return True

#########################
# fanart sync functions #
#########################
    def sync_fanart(self, result):
        from twisted.internet import reactor
        self.print_line("Syncing fanart")
        # rsync the files
        cmdline = ['rsync',
                   '-vruxhm',
                   self.synchost+':'+self.syncfanartpath+'/',
                   self.fanartpath]
        pp = Subproc(self.print_line)
        pp.deferred = Deferred()
        p = reactor.spawnProcess(pp, cmdline[0], cmdline, {})
        return pp.deferred

    def finish_fanart_sync(self, result):
        self.print_line("Fanart synced from synchost")
        return True

##########################
# ratings sync functions #
##########################
    def sync_export_ratings(self, result):
        self.print_line("Exporting ratings")
        return self.localmpd.protocol.sticker_find('song', '', 'rating')

    def handle_export_ratings(self, result):
        Logger.debug("Sync: handle_export_ratings")
        cb = []
        i = 1
        rlist = list(result)
        total = len(rlist)
        self.ratings_incoming('Export')
        for row in rlist:
            uri = Helpers.decodeFileName(row['file'])
            rating = str(row['sticker'].split('=')[1])
            cb.append(self.syncmpd.protocol.sticker_set(
                    'song',
                    uri,
                    'rating',
                    rating).addBoth(partial(
                            self.handle_rating_set,
                            'Export',
                            uri,
                            rating,
                            i,
                            total)))
            i += 1
        udl = DeferredList(cb, consumeErrors=True)
        return udl.addCallbacks(self.finish_export_ratings, self.errback)

    def finish_export_ratings(self, result):
        Logger.debug("Sync: finish_export_ratings")
        self.d3.callback(True)
        return True

    def sync_import_ratings(self, result):
        self.print_line("Importing ratings")
        return self.syncmpd.protocol.sticker_find('song', '', 'rating')

    def handle_import_ratings(self, result):
        Logger.debug("Sync: handle_import_ratings")
        cb = []
        i = 1
        rlist = list(result)
        total = len(rlist)
        self.ratings_incoming('Import')
        for row in rlist:
            uri = Helpers.decodeFileName(row['file'])
            rating = str(row['sticker'].split('=')[1])
            cb.append(self.localmpd.protocol.sticker_set(
                    'song',
                    uri,
                    'rating',
                    rating).addBoth(partial(
                            self.handle_rating_set,
                            'Import',
                            uri,
                            rating,
                            i,
                            total)))
            i += 1
        udl = DeferredList(cb, consumeErrors=True)
        return udl.addCallbacks(self.finish_import_ratings, self.errback)

    def finish_import_ratings(self, result):
        Logger.debug("Sync: finish_import_ratings")
        self.d4.callback(True)
        return True

    def handle_rating_set(self, sdir, uri, rating, done, total, result):
        self.show_ratings_progress(done, total, sdir)

########################
# music sync functions #
########################
    def sync_music(self, result):
        self.print_line("Syncing music using playlist ["+self.synclist+"]")
        # clear the local 'root' playlist
        (self.localmpd.protocol.playlistclear('root').
            addErrback(self.localmpd.handle_mpd_error))
        return self.syncmpd.protocol.listplaylist(self.synclist)

    def build_filelist(self, result):
        from twisted.internet import reactor
        Logger.debug("build_filelist: writing file/hash")
        # write synclist to a temp file, and a hash
        f = io.open(os.path.join(self.tmppath, 'rsync.inc'),
                    mode='w',
                    encoding="utf-8")
        for row in result:
            f.write(Helpers.decodeFileName(row)+"\n")
            self.filelist[Helpers.decodeFileName(row.rstrip())] = True
        f.close()
        # this whole block walks the filesystem and deletes any file that is
        # not in the synclist
        Logger.debug("build_filelist: deleting old files")
        for dirpath, dirnames, filenames in os.walk(
                Helpers.decodeFileName(self.basepath)):
            if len(filenames) > 0:
                rpath = dirpath[len(self.basepath+os.sep):]
                for filename in filenames:
                    fpath = os.path.join(
                            Helpers.decodeFileName(rpath),
                            Helpers.decodeFileName(filename))
                    apath = os.path.join(
                            Helpers.decodeFileName(dirpath),
                            Helpers.decodeFileName(filename))
                    if fpath not in self.filelist:
                        Logger.debug("Filesync: Deleting "+apath)
                        os.remove(Helpers.decodeFileName(apath))
        Logger.debug("build_filelist: removing empty folders")
        # remove empty folders
        Helpers.removeEmptyFolders(self.basepath)
        # rsync the files
        cmdline = ['rsync',
                   '-vruxhm',
                   '--files-from='+os.path.join(self.tmppath, 'rsync.inc'),
                   self.synchost+':'+self.syncbasepath+'/',
                   self.basepath]
        pp = Subproc(self.print_line)
        pp.deferred = Deferred()
        p = reactor.spawnProcess(pp, cmdline[0], cmdline, {})
        return pp.deferred

    def cleanup_music_sync(self, result):
        self.print_line("Cleaning up temp files and updating mpd database")
        # clean up
        os.remove(os.path.join(self.tmppath, 'rsync.inc'))
        self.localmpd.protocol.update()
        return True

    def mpd_idle_handler(self, result):
        for s in result:
            if format(s) == 'update':
                Logger.debug('mpd_idle_handler: Changed '+format(s))
                (self.localmpd.protocol.status().
                    addCallbacks(self.handle_update, self.errback))

    def handle_update(self, result):
        if 'updating_db' not in result:
            Logger.debug("handle_update: updating_db done")
            cb = []
            for k in sorted(self.filelist.keys()):
                cb.append(self.localmpd.protocol.playlistadd('root', k))
            udl = DeferredList(cb, consumeErrors=True)
            udl.addCallbacks(self.finish_update, self.errback)
        return True

    def finish_update(self, result):
        self.print_line("Music synced and playlist updated")
        self.d2.callback(True)
        return True


class Subproc(protocol.ProcessProtocol):
    """Class to handle subprocesses."""

    def __init__(self, printer):
        self.printer = printer

    def connectionMade(self):
        Logger.debug("Subproc: spawning subprocess")

    def processExited(self, reason):
        Logger.debug("Subproc: exited, status: "+format(reason.value.exitCode))
        self.deferred.callback(True)

    def outReceived(self, data):
        for line in data.split('\n'):
            if line:
                self.printer(line)
