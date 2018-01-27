.. _invocation:

##########
Invocation
##########

****
kmpc
****
This is the main program, accessed by either running ``kmpc`` from an installed
package or ``./runkmpc`` from within the root of the git repo. It depends on a
configuration directory (``~/.kmpc``) and a config file
(``~/.kmpc/config.ini``) that will be automatically created at first run. You
will need to edit this config file to add the correct values for various
variables. The following commandline options are accepted, as well as all the
default Kivy options::

  usage: kmpc [-h] [-q] [-d] [-n] [--helpkivy]

  optional arguments:
  -h, --help   show this help message and exit
  -q, --quiet  only print errors to console log
  -d, --debug  print debug messages to console log
  -n, --newconfig  write out default config file if it doesn't exist yet
  --helpkivy   Print Kivy's built-in argument list

***********
kmpcmanager
***********

This is the synchost manager program, accessed by either running
``kmpcmanager`` from an installed package or ``./runkmpcmanager`` from within
the root of the git repo. The synchost is a computer running at home that has
all the music and mpd running on it, as well as all the fanart. ``kmpcmanager``
provides an interface for downloading fanart for all files in mpd, setting up
an rsync file to sync with, and changing song ratings and copy flags. This also
depends on the config folder and file. The following commandline options are
accepted, as well as all the default Kivy options::

  usage: kmpcmanager [-h] [-q] [-d] [-n] [--helpkivy]

  optional arguments:
  -h, --help   show this help message and exit
  -q, --quiet  only print errors to console log
  -d, --debug  print debug messages to console log
  -n, --newconfig  write out default config file if it doesn't exist yet
  --helpkivy   Print Kivy's built-in argument list

