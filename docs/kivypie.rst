#########################
Car Installation Tutorial
#########################

This document will guide you through a method of setting up a fully functional
touchscreen solution that can be mounted in your car. It uses KivyPie as the
base linux distro.

***********************
Step 1: Install KivyPie
***********************

#. Visit the `download site <http://kivypie.mitako.eu/kivy-download.html>`_ and
   download the latest build of KivyPie. Note that this project needs at least
   Kivy v1.10.0, so download accordingly.
#. Unzip the downloaded file and flash it to a MicroSD card. I recommend using
   `Etcher <https://etcher.io/>`_. Boot your Pi with this card.
#. Read the `KivyPie FAQ Page <http://kivypie.mitako.eu/kivy-faq.html>`_ to
   understand how you can connect to it. The latest version (as of this
   writing) has a new method to configure the network that doesn't seem to be
   documented however. If you need wifi, do the following:
   #. Power down the Pi and mount the SD card on your desktop.
   #. Edit the file ``interfaces`` in the root of the SD card.

   #. Change the line::

        wpa-ssid pipaos

      to::

        wpa-ssid <whatever-your-ssid-is>

   #. Change the line::

        wpa-psk pipa123pass

      to::

        wpa-psk <whatever-your-passphrase-is>

   #. Save the changes, eject the SD card, put it back in the Pi and boot.
#. Login with the credentials given in the FAQ, either with a physical
   keyboard or via SSH. The rest of the guide will use the default user,
   however if you wish to add a new user and do everything with that it should
   be fine, just adjust accordingly.
#. You'll need to expand your root volume to use the whole SD card. Run 
   
   ::
   
     sudo pipaos-config
   
   choose *Expand Filesystem*, hit enter a few times, let the Pi reboot, then
   log back in.
#. KivyPie mounts an extremely small tmpfs at /tmp, which interferes with pip's
   ability to install things. Run the following to remount /tmp temporarily
   during the install process::

     sudo mkdir /root/tmp
     sudo umount -l /tmp
     sudo mount --bind /tmp /root/tmp

********************
Step 2: Install kmpc
********************

#. As of this writing, the version of pip/setuptools on KivyPie is old. Run the
   following to update::
   
     sudo pip install --upgrade pip setuptools wheel

#. Run the following to install kmpc and pull in the Pi-specific dependencies::
   
     sudo pip install kmpc[rpi]

#. Run::

     kmpc

   This will generate the default config file. You should at least see an
   interface come up on the screen.

#. Optional: if you want a mouse cursor to show up on the screen (in case you
   are running with a keyboard and mouse), add the following to the *[modules]*
   section in the file ``~/.kivy/config.ini``::

     cursor =

******************
Step 3: Set up mpd
******************

#. Put some mp3 files on there somewhere. I suggest a USB thumb drive for ease
   of use, but in a pinch you can just put them on the SD card somewhere. The
   path to these files will henceforth be named *\<musicpath\>*.

#. Make sure your audio connection is working. Run ``speaker-test`` and listen
   for some output. If you are going to use HDMI for audio output rather than
   the headphone jack, you may need to run the following first::

     amixer cset numid=3 2
     sudo alsactl store

#. Run the following to install mpd::

     sudo apt-get update
     sudo apt-get install mpd mpc

#. Edit the file ``/etc/mpd.conf`` and set the ``music_directory`` variable to
   "*\<musicpath\>*". You can also set the ``replaygain`` variable to "album",
   "track" or "auto" and configure various other mpd settings. See
   https://www.musicpd.org/doc/user/config.html for further details.

#. Save the file and restart mpd::

     sudo systemctl restart mpd

#. Run the following to update the mpd database::

     mpc update

#. Edit the file ``~/.kmpc/config.ini`` and set the ``musicpath`` variable to
   *\<musicpath\>*

#. Save the file and run ``kmpc`` again. You should now be able to browse the
   library, add files to the playlist, and generally use the app.

*****************************
Step 4: Add fanart (optional)
*****************************

The directory structure for fanart is as follows, with *fanartpath* as the
root folder::

  fanartpath
  ├── 078a9376-3c04-4280-b7d7-b20e158f345d    # musicbrainz artistid
  │   ├── __Artist Name__                     # empty file, optional
  │   ├── artistbackground                    # player background images
  │   │   ├── 132224.jpg                      # you can have as many
  │   │   ├── 39392.jpg                       # as you want
  │   │   ├── 4679.jpg                        # or none at all
  │   │   ├── 4680.jpg                        # format is 1280x720 JPG
  │   │   └── 7578.jpg
  │   ├── logo                                # artist logo images
  │   │   ├── 130819.png                      # you can have as many
  │   │   ├── 45979.png                       # as you want
  │   │   ├── 15469.png                       # or none at all
  │   │   ├── 47981.png                       # format is transparent PNG
  │   │   ├── 39562.png                       # maximum 800x310
  │   │   └── 5624.png
  │   └── badge                               # artist badge images
  │       ├── 130819.png                      # you can have as many
  │       ├── 45979.png                       # as you want
  │       ├── 15469.png                       # or none at all
  │       ├── 47981.png                       # format is transparent PNG
  │       ├── 39562.png                       # squarish aspect ratio
  │       └── 5624.png
  └── 391c9402-6688-4c3d-8f3d-d320d31b4de9    # and so on
      ├── __Another Artist__
      └── logo
          └── 154355.png

Once you've added some art, edit the file ``~/.kmpc/config.ini`` and change the
``fanartpath`` variable to *fanartpath*, then restart kmpc. You should now see
logos and background images for the artists that have images in the fanart
folder.
