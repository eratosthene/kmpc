.. _readme:

######
Readme
######

**********
About kmpc
**********

kmpc is a `Kivy <https://kivy.org/>`_-based mpd client, primarily meant for use
on a `Raspberry Pi <https://www.raspberrypi.org/>`_ paired with the `official
7" touchscreen
<https://www.raspberrypi.org/products/raspberry-pi-touch-display/>`_ mounted in
a car. Using a combination of a fast-booting distro with Kivy installed (such
as `KivyPie <http://kivypie.mitako.eu/>`_), it is possible to have music
playing in a few seconds after boot, and a GUI touch interface ready to use in
a few seconds more. kmpc is meant to run directly on the framebuffer, with no
need for X.

Full documentation can be found on `ReadTheDocs
<http://kmpc.readthedocs.io/>`_.

********************
Runtime requirements
********************

kmpc depends on the following python packages:

- `Kivy <https://kivy.org/>`_
- `Twisted <https://github.com/twisted/twisted>`_
- `mutagen <https://github.com/quodlibet/mutagen>`_
- `musicbrainzngs <https://github.com/alastair/python-musicbrainzngs>`_
- `rpi-backlight <https://github.com/linusg/rpi-backlight>`_ (if you want to
  control the backlight on a Raspberry Pi touchscreen)

In addition, there must be an `mpd <https://www.musicpd.org/>`_ server running
that kmpc can connect to via TCP.


