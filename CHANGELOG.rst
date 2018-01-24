###############
kmpc Change Log
###############

******************
0.5.5 - 2018-01-24
******************

- Fixed a bug in how the sync method was handling unicode filenames.

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
