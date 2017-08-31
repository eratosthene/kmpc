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
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'player':
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'sticker':
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
                self.protocol.sticker_get('song',app.root.currfile,'rating').addCallback(app.root.update_mpd_sticker_rating).addErrback(app.root.handle_mpd_no_sticker)
            elif format(s) == 'options':
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            else:
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)

class MPDClientFactory(protocol.ClientFactory):
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
