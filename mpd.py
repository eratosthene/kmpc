# Python MPD client library using Twisted
#
# Copyright (C) 2008  J. Alexander Treuman <jat@spatialrift.net>
# Copyright (C) 2010  Jasper St. Pierre <jstpierre@mecheye.net>
# Copyright (C) 2010,2011  Oliver Mader <b52@reaktor42.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from functools import wraps
from os import getenv
from sys import argv, stdout
from types import GeneratorType

from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic

__all__ = [
    "MPD_HOST",
    "MPD_PORT",
    "MPDError",
    "ConnectionError",
    "ProtocolError",
    "CommandError",
    "CommandListError",
    "MPDProtocol",
    "MPDFactory"
]

debug = False

if "--debug" in argv:
    from twisted.python.log import startLogging
    startLogging(stdout)
    debug = True


MPD_HOST = getenv('MPD_HOST', '127.0.0.1')
MPD_PORT = int(getenv('MPD_PORT', 6600))

HELLO_PREFIX = "OK MPD "
ERROR_PREFIX = "ACK "
SUCCESS = "OK"
NEXT = "list_OK"

class MPDError(Exception):
    pass

class ConnectionError(MPDError):
    pass

class ProtocolError(MPDError):
    pass

class CommandError(MPDError):
    pass

class CommandListError(MPDError):
    pass


def iterator_wrapper(function):
    @wraps(function)
    def decorated_function(instance, *args, **kwargs):
        result = function(instance, *args, **kwargs)
        return result if instance.iterate else list(result)
    return decorated_function


class MPDProtocol(basic.LineReceiver):

    delimiter = "\n"
    
    def __init__(self):
        self.iterate = True
        self.reset()

        self.commands = {
            # Status Commands
            "clearerror":           self.parse_nothing,
            "currentsong":          self.parse_object,
            "idle":                 self.parse_list,
            "noidle":               self.parse_nothing,
            "status":               self.parse_object,
            "stats":                self.parse_object,
            # Playback Option Commands
            "consume":              self.parse_nothing,
            "crossfade":            self.parse_nothing,
            "mixrampdb":            self.parse_nothing,
            "mixrampdelay":         self.parse_nothing,
            "random":               self.parse_nothing,
            "repeat":               self.parse_nothing,
            "setvol":               self.parse_nothing,
            "single":               self.parse_nothing,
            "replay_gain_mode":     self.parse_nothing,
            "replay_gain_status":   self.parse_object,
            # Playback Control Commands
            "next":                 self.parse_nothing,
            "pause":                self.parse_nothing,
            "play":                 self.parse_nothing,
            "playid":               self.parse_nothing,
            "previous":             self.parse_nothing,
            "seek":                 self.parse_nothing,
            "seekcur":              self.parse_nothing,
            "seekid":               self.parse_nothing,
            "stop":                 self.parse_nothing,
            # Playlist Commands
            "add":                  self.parse_nothing,
            "addid":                self.parse_item,
            "clear":                self.parse_nothing,
            "delete":               self.parse_nothing,
            "deleteid":             self.parse_nothing,
            "move":                 self.parse_nothing,
            "moveid":               self.parse_nothing,
            "playlistfind":         self.parse_songs,
            "playlistid":           self.parse_songs,
            "playlistinfo":         self.parse_songs,
            "playlistsearch":       self.parse_songs,
            "plchanges":            self.parse_songs,
            "plchangesposid":       self.parse_changes,
            "shuffle":              self.parse_nothing,
            "swap":                 self.parse_nothing,
            "swapid":               self.parse_nothing,
            # Stored Playlist Commands
            "listplaylist":         self.parse_list,
            "listplaylistinfo":     self.parse_songs,
            "listplaylists":        self.parse_playlists,
            "load":                 self.parse_nothing,
            "playlistadd":          self.parse_nothing,
            "playlistclear":        self.parse_nothing,
            "playlistdelete":       self.parse_nothing,
            "playlistmove":         self.parse_nothing,
            "rename":               self.parse_nothing,
            "rm":                   self.parse_nothing,
            "save":                 self.parse_nothing,
            # Database Commands
            "count":                self.parse_object,
            "find":                 self.parse_songs,
            "findadd":              self.parse_nothing,
            "list":                 self.parse_list,
            "listall":              self.parse_database,
            "listallinfo":          self.parse_database,
            "lsinfo":               self.parse_database,
            "search":               self.parse_songs,
            "update":               self.parse_item,
            "rescan":               self.parse_item,
            # Stickers
            "sticker get":          self.parse_sticker,
            "sticker set":          self.parse_nothing,
            "sticker delete":       self.parse_nothing,
            "sticker list":         self.parse_stickers,
            "sticker find":         self.parse_stickers_find,
            # Connection Commands
            "close":                None,
            "kill":                 None,
            "password":             self.parse_nothing,
            "ping":                 self.parse_nothing,
            # Audio Output Commands
            "disableoutput":        self.parse_nothing,
            "enableoutput":         self.parse_nothing,
            "outputs":              self.parse_outputs,
            # Reflection Commands
            "commands":             self.parse_list,
            "notcommands":          self.parse_list,
            "tagtypes":             self.parse_list,
            "urlhandlers":          self.parse_list,
            "decoders":             self.parse_decoders,
        }

    def __getattr__(self, attr):
        if attr not in self.commands:
            attr = attr.replace("_", " ")
        if attr not in self.commands:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, attr))
        return lambda *args: self.execute(attr, args, self.commands[attr])
    
    def execute(self, command, args, parser):
        if self.command_list and not callable(parser):
            raise CommandListError("%s not allowed in command list" % command)
        self.write_command(command, args)
        deferred = defer.Deferred()
        (self.state[-1] if self.command_list else self.state).append(deferred)
        if parser is not None:
            deferred.addCallback(parser)
            if self.command_list:
                deferred.addCallback(self.parse_command_list_item)
        return deferred
    
    def write_command(self, command, args=[]):
        parts = [command] + \
                ['"%s"' % escape(arg.encode('utf-8') if
                 isinstance(arg, unicode) else str(arg)) for arg in args]
        if debug:
            print "sending", parts
        self.sendLine(" ".join(parts))

    @iterator_wrapper
    def parse_pairs(self, lines, separator=": "):
        return (line.split(separator, 1) for line in lines)

    @iterator_wrapper
    def parse_list(self, lines):
        seen = None
        for key, value in self.parse_pairs(lines):
            if key != seen:
                if seen is not None:
                    raise ProtocolError("Expected key '%s', got '%s'" %
                                        (seen, key))
                seen = key
            yield value

    @iterator_wrapper
    def parse_playlist(self, lines):
        for key, value in self.read_pairs(lines, ":"):
            yield value

    @iterator_wrapper
    def parse_objects(self, lines, delimiters=[]):
        obj = {}
        for key, value in self.parse_pairs(lines):
            key = key.lower()
            if key in delimiters and obj:
                yield obj
                obj = {}
            if key in obj:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key], value]
                else:
                    obj[key].append(value)
            else:
                obj[key] = value
        if obj:
            yield obj

    def parse_object(self, lines):
        objs = list(self.parse_objects(lines))
        if not objs:
            return {}
        return objs[0]

    def parse_item(self, lines):
        pairs = list(self.parse_pairs(lines))
        if len(pairs) != 1:
            return
        return pairs[0][1]
    
    def parse_nothing(self, lines):
        return
    
    def parse_songs(self, lines):
        return self.parse_objects(lines, ["file"])

    def parse_playlists(self, lines):
        return self.parse_objects(lines, ["playlist"])

    def parse_database(self, lines):
        return self.parse_objects(lines, ["file", "directory", "playlist"])

    def parse_outputs(self, lines):
        return self.parse_objects(lines, ["outputid"])

    def parse_changes(self, lines):
        return self.parse_objects(lines, ["cpos"])

    def parse_decoders(self, lines):
        return self.parse_objects(lines, ["plugin"])

    def parse_sticker(self, lines):
        return self.parse_item(lines).split("=", 1)[1]

    def parse_stickers(self, lines):
        return dict(x.split("=", 1) for x in self.parse_list(lines))

    @iterator_wrapper
    def parse_stickers_find(self, lines):
        for x in self.parse_objects(lines, ["file"]):
            x["sticker"] = x["sticker"].split("=", 1)[1]
            yield x

    def parse_command_list_item(self, result):
        # TODO: find a better way to do this
        if type(result) == GeneratorType:
            result = list(result)
        self.command_list_results[0].append(result)
        return result

    def parse_command_list_end(self, lines):
        return self.command_list_results.pop(0)

    def command_list_ok_begin(self):
        if self.command_list:
            raise CommandListError("Already in command list")
        self.write_command("command_list_ok_begin")
        self.command_list = True
        self.command_list_results.append([])
        self.state.append([])

    def command_list_end(self):
        if not self.command_list:
            raise CommandListError("Not in command list")
        self.write_command("command_list_end")
        deferred = defer.Deferred()
        deferred.addCallback(self.parse_command_list_end)
        self.state[-1].append(deferred)
        self.command_list = False
        return deferred
    
    def reset(self):
        self.mpd_version = None
        self.command_list = False
        self.command_list_results = []
        self.buffer = []
        self.state = []

    def lineReceived(self, line):
        line = line.decode('utf-8')

        if debug:
            print "received", line

        command_list = self.state and isinstance(self.state[0], list)
        state_list = self.state[0] if command_list else self.state

        if line.startswith(HELLO_PREFIX):
            self.mpd_version = line[len(HELLO_PREFIX):].strip()
        
        elif line.startswith(ERROR_PREFIX):
            error = line[len(ERROR_PREFIX):].strip()

            if command_list:
                state_list[0].errback(CommandError(error))
                for state in state_list[1:-1]:
                    state.errback(CommandListError("An earlier command " \
                                                   "failed."))
                state_list[-1].errback(CommandListError(error))
                del self.state[0]
                del self.command_list_results[0]
            else:
                state_list.pop(0).errback(CommandError(error))
        
        elif line == SUCCESS or (command_list and line == NEXT):
            parser = state_list.pop(0).callback(self.buffer[:])
            self.buffer = []

            if command_list and line == SUCCESS:
                del self.state[0]
                
        else:
            self.buffer.append(line)


class MPDFactoryProtocol(MPDProtocol):
    def connectionMade(self):
        if callable(self.factory.connectionMade):
            self.factory.connectionMade(self)

    def connectionLost(self, reason):
        if callable(self.factory.connectionLost):
            self.factory.connectionLost(self, reason)
    

class MPDFactory(protocol.ReconnectingClientFactory):
    protocol = MPDFactoryProtocol
    connectionMade = None
    connectionLost = None


def escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')    

# vim: set expandtab shiftwidth=4 softtabstop=4 textwidth=79:
