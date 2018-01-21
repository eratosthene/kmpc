from setuptools import setup

import kmpc.version

VERSION = ".".join(map(str, kmpc.VERSION))

LICENSE = """\
Copyright (C) 2017-2018  Chris Graham <eratosthene@gmail.com>

kmpc is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

kmpc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.  You should have received a copy of the GNU Lesser General Public License
along with kmpc.  If not, see <http://www.gnu.org/licenses/>.\
"""

setup(
    version=VERSION,
    setup_cfg=True,
)
