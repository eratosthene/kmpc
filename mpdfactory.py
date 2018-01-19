import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.logger import Logger
from mpd import MPDProtocol
from twisted.internet import protocol

class MPDFactoryProtocol(MPDProtocol):
    """Factory for MPDProtocol."""
    def connectionMade(self):
        """Call the connectionMade override."""
        if callable(self.factory.connectionMade):
            self.factory.connectionMade(self)
    def connectionLost(self, reason):
        """Call the connectionLost override."""
        if callable(self.factory.connectionLost):
            self.factory.connectionLost(self, reason)

class MPDIdleHandler(object):
    """Handler class for mpd idle command."""

    def __init__(self, protocol):
        """Set this class's protocol to the one that was passed in."""
        self.protocol = protocol

    def __call__(self, result):
        """Handle results from mpd idle command."""
        app=App.get_running_app()

        # notify various subsystems based on what changed
        for s in result:
            Logger.info('MPDIdleHandler: Changed '+format(s))
            if format(s) == 'playlist':
                # playlist was changed, ask mpd for playlist info
                self.protocol.playlistinfo().addCallback(app.root.ids.playlist_tab.populate_playlist).addErrback(app.root.ids.playlist_tab.handle_mpd_error)
                # force a reload of nextsong if playlist changes
                app.root.nextsong = None
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'player':
                # player was changed, ask mpd for player status
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'sticker':
                # song rating sticker was changed, ask mpd for current song rating
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
                self.protocol.sticker_get('song',app.root.currfile,'rating').addCallback(app.root.update_mpd_sticker_rating).addErrback(app.root.handle_mpd_no_sticker)
            elif format(s) == 'options':
                # some playback option was changed, ask mpd for player status
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)
            elif format(s) == 'message':
                # an mpd message was received, ask mpd what it was
                self.protocol.readmessages().addCallback(app.root.handle_mpd_message).addErrback(app.root.handle_mpd_error)
            else:
                # default if none of the above, ask mpd for player status
                self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)

class MPDClientFactory(protocol.ClientFactory):
    """Factory for MPDClient."""
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None

    def buildProtocol(self, addr):
        """Hook up protocol and idle handler."""
        Logger.debug('MPDClientFactory: buildProtocol')
        protocol = self.protocol()
        protocol.factory = self
        protocol.idle_result = MPDIdleHandler(protocol)
        return protocol

    def clientConnectionFailed(self, connector, reason):
        """mpd connection failed for some reason."""
        Logger.error('Connection failed - goodbye!: '+format(reason))

    def clientConnectionLost(self, connector, reason):
        """mpd connection lost for some reason."""
        Logger.error('Connection lost - goodbye!: '+format(reason))
