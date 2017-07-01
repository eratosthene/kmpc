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
