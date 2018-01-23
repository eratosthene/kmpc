# python-mpd2: Python MPD client library
#
# Copyright (C) 2008-2010  J. Alexander Treuman <jat@spatialrift.net>
# Copyright (C) 2012  J. Thalheim <jthalheim@gmail.com>
# Copyright (C) 2016  Robert Niederreiter <rnix@squarewave.at>
#
# python-mpd2 is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-mpd2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with python-mpd2.  If not, see <http://www.gnu.org/licenses/>.

from kmpc.mpd.base import CommandError
from kmpc.mpd.base import CommandListError
from kmpc.mpd.base import ConnectionError
from kmpc.mpd.base import IteratingError
from kmpc.mpd.base import MPDClient
from kmpc.mpd.base import MPDError
from kmpc.mpd.base import PendingCommandError
from kmpc.mpd.base import ProtocolError
from kmpc.mpd.base import VERSION

try:
    from kmpc.mpd.twisted import MPDProtocol
except ImportError:
    class MPDProtocol:
        def __init__(self):
            raise "No twisted module found"
