##################################
config file ``~/.kmpc/config.ini``
##################################

This file contains several sections, and must be customized for your use. It
will be created with default values the first time ``kmpc`` is run.

[mpd] section
-------------

mpdhost
  Hostname or IP address that mpd is running on.
mpdport
  Port that mpd is running on.

[paths] section
---------------

musicpath
  Path to the folder containing music. This should be the same file tree that
  the mpd server connected above uses. kmpc uses direct file access to pull
  things like album art and extra id3 tags from the files.
fanartpath
  Path to the folder containing fanart. The directory structure for this folder
  is explained in another section.
tmppath
  Where temporary files should be written.

[sync] section
--------------

synchost
  Hostname or IP address of a host to sync with. This is useful if you have a
  main mpd server running at home and want to sync songs/ratings/fanart to your
  car. The ``kmpcmanager`` program is used to manage this synchost.
syncmusicpath
  The path to the music folder on the synchost.
syncfanartpath
  The path to the fanart folder on the synchost.

[flags] section
---------------

rpienable
  Set this to ``true`` if you are running this on a Pi and want to control
  Pi-specific features, such as the backlight. Set to ``false`` otherwise.

[api] section
-------------

fanarturl
  Url to the fanart.tv API. Set to the correct thing by default, you probably
  don't want to change this. Only used by ``kmpcmanager``.
api_key
  Set this to your personal fanart.tv API key. Only used by ``kmpcmanager``.

[songratings] section
---------------------

Customize the meaning of 0-10 stars. The defaults are probably good enough, but
feel free to change them to whatever you want. These are the strings that are
shown in the rating popup.
