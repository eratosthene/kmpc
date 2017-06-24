import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.logger import Logger
from mpd import MPDProtocol
from twisted.internet import protocol

class MPDFactoryProtocol(MPDProtocol):
    def connectionMade(self):
        if callable(self.factory.connectionMade):
            self.factory.connectionMade(self)
    def connectionLost(self, reason):
        if callable(self.factory.connectionLost):
            self.factory.connectionLost(self, reason)

class MPDIdleHandler(object):

    def __init__(self, protocol):
        self.protocol = protocol

    def __call__(self, result):
        app=App.get_running_app()

        # notify various subsystems based on what changed
        for s in result:
            Logger.info('MPDIdleHandler: Changed '+format(s))
            if format(s) == 'playlist':
                self.protocol.playlistinfo().addCallback(app.root.ids.playlist_tab.populate_playlist).addErrback(app.root.ids.playlist_tab.handle_mpd_error)
                # force a reload of nextsong if playlist changes
                app.root.nextsong = None
            elif format(s) == 'player':
                # update everything 'currentsong' can tell us, cascade it down too
                self.protocol.currentsong().addCallback(app.root.update_mpd_currentsong).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'sticker':
                pass

        # the following is done no matter what, so that now playing updates at least every second
        # update everything 'status' can tell us
        self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
        self.protocol.status().addCallback(app.root.ids.playlist_tab.update_mpd_status).addErrback(app.root.ids.playlist_tab.handle_mpd_error)

#### this stuff all needs to only happen on Changed events above and on first run, plz fix kthx

        # if 'status' said there is a next track, update that too
#        if app.root.nextsong:
#            self.protocol.playlistinfo(app.root.nextsong).addCallback(app.root.update_mpd_nextsong).addErrback(app.root.handle_mpd_error)
#        else:
#            app.root.ids.next_track_label.text = ''
#            app.root.ids.next_song_artist_label.text = ''

class MPDClientFactory(protocol.ReconnectingClientFactory):
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None

    def buildProtocol(self, addr):
        Logger.debug('MPDClientFactory: buildProtocol')
        protocol = self.protocol()
        protocol.factory = self
        protocol.idle_result = MPDIdleHandler(protocol)
        return protocol

    def clientConnectionFailed(self, connector, reason):
        Logger.error('Connection failed - goodbye!: '+format(reason))

    def clientConnectionLost(self, connector, reason):
        Logger.error('Connection lost - goodbye!: '+format(reason))
