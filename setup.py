from distutils.core import setup

setup(
    name="kmpc",
    version="1.0dev",
    author="Chris Graham",
    author_email="eratosthene@gmail.com",
    packages=[
        "kmpc",
    ],
    package_data={'kmpc': ['kmpc.kv']},
    scripts=['bin/kmpc'],
    url="https://github.com/eratosthene/kmpc",
    license="Creative Commons Attribution-Noncommercial-Share Alike license",
    description="kmpc is a Kivy-based mpd client, primarily meant for use on a Raspberry Pi mounted in a car.",
    long_description=open('README.rst').read(),
)
