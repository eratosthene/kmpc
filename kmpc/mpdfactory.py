import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.logger import Logger
from kmpc.mpd import MPDProtocol
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

class MPDClientFactory(protocol.ReconnectingClientFactory):
    """Factory for MPDClient."""
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None

    def __init__(self,idlehandler=None,**kwargs):
        self.idlehandler=idlehandler

    def buildProtocol(self, addr):
        """Hook up protocol and idle handler."""
        Logger.debug('MPDClientFactory: buildProtocol')
        protocol = self.protocol()
        protocol.factory = self
        if callable(self.idlehandler):
            protocol.idle_result = self.idlehandler
        return protocol

    def clientConnectionFailed(self, connector, reason):
        """mpd connection failed for some reason."""
        Logger.error('Connection failed - goodbye!: '+format(reason))

    def clientConnectionLost(self, connector, reason):
        """mpd connection lost for some reason."""
        Logger.error('Connection lost - goodbye!: '+format(reason))
