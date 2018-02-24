from setuptools import setup

from kmpc.version import VERSION, VERSION_STR

setup(
    version=VERSION_STR,
    download_url='https://github.com/eratosthene/kmpc/archive/'
                 + VERSION_STR
                 + '.tar.gz',
    dependency_links=[
            'https://github.com/kivy/kivy/tarball/master#egg=kivy-1.10.0']
    setup_requires=['setuptools>=38.4.0'],
    setup_cfg=True
)
