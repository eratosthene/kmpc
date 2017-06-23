import kivy
kivy.require('1.10.0')
from kivy.app import App
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
        for s in result:
            Logger.info('MPDIdleHandler: Changed '+format(s))

        app=App.get_running_app()
        # update everything 'status' can tell us
        self.protocol.status().addCallback(app.root.update_mpd_status).addErrback(app.root.handle_mpd_error)

       # update everything 'currentsong' can tell us
        self.protocol.currentsong().addCallback(app.root.update_mpd_currentsong).addErrback(app.root.handle_mpd_error)

      # if 'status' said there is a next track, update that too
        if app.root.nextsong:
            self.protocol.playlistinfo(app.root.nextsong).addCallback(app.root.update_mpd_nextsong).addErrback(app.root.handle_mpd_error)
        else:
            app.root.ids.next_track_label.text = ''
            app.root.ids.next_song_artist_label.text = ''

class MPDClientFactory(protocol.ReconnectingClientFactory):
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None

    def buildProtocol(self, addr):
        protocol = self.protocol()
        protocol.factory = self
        protocol.idle_result = MPDIdleHandler(protocol)
        return protocol
