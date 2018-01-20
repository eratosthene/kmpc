from setuptools import setup, find_packages
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
    name="kmpc",
    version=VERSION,
    author="Chris Graham",
    author_email="eratosthene@gmail.com",
    packages=find_packages(),
    package_data={'':['resources/*']},
    include_package_data=True,
    scripts=['bin/kmpc','bin/kmpcmanager'],
    url="https://github.com/eratosthene/kmpc",
    license="GNU Lesser General Public License v3 (LGPLv3)",
    description="kmpc is a Kivy-based mpd client, primarily meant for use on a Raspberry Pi mounted in a car.",
    long_description=open('README.rst').read(),
    install_requires=[
        "cython == 0.25.*",
        "kivy == 1.10.*",
        "twisted == 17.9.*",
        "mutagen == 1.*",
        "gitpython == 2.1.*"
    ],
)
