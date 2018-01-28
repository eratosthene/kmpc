.. _changelog:

###############
kmpc Change Log
###############

********************
0.6.0.1 - 2018-01-27
********************

- Bugfix release, I missed a couple of config file changes, oops.

******************
0.6.0 - 2018-01-27
******************

- Added album name and release year(s) to cover popup.
- Load album covers from tags with PIL directly first, to allow for resizing in
  case it is too large for a texture to hold. (`issue #7
  <https://github.com/eratosthene/kmpc/issues/7>`_)
- Changed to a ReconnectingClientFactory to prevent issues when long-running
  mpd commands are run. (part of `issue #9
  <https://github.com/eratosthene/kmpc/issues/9>`_)
- Added a line to the mpd.conf file in the car install doc to prevent mpd
  crashing when loading a long playlist. (part of `issue #9
  <https://github.com/eratosthene/kmpc/issues/9>`_)
- Revamped the way config file handling works to use Kivy's built-in Config
  class. You can now edit config settings from within the app. (`issue #17
  <https://github.com/eratosthene/kmpc/issues/17>`_)

******************
0.5.9 - 2018-01-26
******************

- Added -V/--version command line option to print version number. (`issue #55
  <https://github.com/eratosthene/kmpc/issues/55>`_)
- Added -n/--newconfig command line option to generate default config file.
  (`issue #38 <https://github.com/eratosthene/kmpc/issues/38>`_)
- Issue #57 wasn't actually fixed, just masked. Pretty sure it's fixed now.

******************
0.5.8 - 2018-01-26
******************

- Missed a few lines in the mpd revamp, this fixes it. (`issue #57
  <https://github.com/eratosthene/kmpc/issues/57>`_)

******************
0.5.7 - 2018-01-26
******************

- Revamped mpd connection handling to be less crashy. (`issue #35
  <https://github.com/eratosthene/kmpc/issues/35>`_)
- Documented permissions change necessary to control Pi screen backlight.
  (`issue #45 <https://github.com/eratosthene/kmpc/issues/45>`_)
- Added setuptools>=30.3.0 to the setup_requires section of setup.cfg. (`issue
  #36 <https://github.com/eratosthene/kmpc/issues/36>`_)
- Added artblacklist section to config.ini. (`issue #27
  <https://github.com/eratosthene/kmpc/issues/27>`_)

******************
0.5.6 - 2018-01-25
******************

- Changed the scan all for art function in the manager to schedule the requests
  once per second for every row instead of skipping rows that already had some
  art. (`issue #26 <https://github.com/eratosthene/kmpc/issues/26>`_)
- Changed the year display to on top of the cover art to save some space.
- Added a config file setting for originalyear display. (`issue #16
  <https://github.com/eratosthene/kmpc/issues/16>`_)
- Added new settings popup to house things as config tab is going to be used
  for actual config file editing eventually. (`issue #6
  <https://github.com/eratosthene/kmpc/issues/6>`_)
- Added ability to click on artist logo to change it to another one. (`issue #5
  <https://github.com/eratosthene/kmpc/issues/5>`_)
- Added sudo to reboot and shutdown commands. (`issue #43
  <https://github.com/eratosthene/kmpc/issues/43>`_)
- Added docs for full installation to car Pi!

******************
0.5.5 - 2018-01-24
******************

- Fixed a bug in how the sync method was handling unicode filenames. (`issue
  #39 <https://github.com/eratosthene/kmpc/issues/39>`_)

******************
0.5.4 - 2018-01-22
******************

- Fixed a bug in the mpd module. This is why you should test things before
  releasing them to the public.

******************
0.5.3 - 2018-01-22
******************

- Fixed fanart.tv to use baked-in developer key and optional client key (`issue
  #28 <https://github.com/eratosthene/kmpc/issues/28>`_)
- Fixed paths to use portable path separator instead of '/' (`issue #23
  <https://github.com/eratosthene/kmpc/issues/23>`_)
- Changed musicbrainz access to use the musicbrainzngs library (`issue #14
  <https://github.com/eratosthene/kmpc/issues/14>`_)
- Pulling art for an artist will no longer re-download logos that have been
  manually moved to the badge folder

******************
0.5.2 - 2018-01-21
******************

- Added exception handling for non-existent artist cache file (`issue #13
  <https://github.com/eratosthene/kmpc/issues/13>`_)
- Added -q/--quiet command line option (`issue #21
  <https://github.com/eratosthene/kmpc/issues/21>`_)
- Fixed all temp files to honor config.ini values (`issue #12
  <https://github.com/eratosthene/kmpc/issues/12>`_)
- Changed artlog.txt in kmpcmanager to be optional (`issue #4
  <https://github.com/eratosthene/kmpc/issues/4>`_)

******************
0.5.1 - 2018-01-20
******************

- First public release
