from setuptools import setup

from kmpc.version import VERSION, VERSION_STR

setup(
    version=VERSION_STR,
    download_url='https://github.com/eratosthene/kmpc/archive/'
                 + VERSION_STR
                 + '.tar.gz',
    setup_requires=['setuptools>=38.4.0'],
    setup_cfg=True
)
