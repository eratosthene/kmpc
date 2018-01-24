.. _kivypie:

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
   however if you wish to add a new user, set a password,  and do everything
   with that it should be fine, just adjust accordingly.

#. Run the following to give your user password-less sudo access::

     cat << EOF | sudo tee /etc/sudoers.d/$USER
       $USER ALL=(ALL:ALL) NOPASSWD:ALL
     EOF

#. You'll need to expand your root volume to use the whole SD card. Run::
   
     sudo pipaos-config
   
   choose *Expand Filesystem*, hit enter a few times, let the Pi reboot, then
   log back in.
#. KivyPie mounts an extremely small tmpfs at /tmp, which interferes with pip's
   ability to install things. Run the following to remount /tmp temporarily
   during the install process::

     sudo mkdir /root/tmp
     sudo umount -l /tmp
     sudo mount --bind /tmp /root/tmp

#. If you don't want the rainbow screen to show on boot, edit the file
   ``/boot/config.txt`` and add ``disable_splash=1`` to the end of it.

#. Run this to update your packages::
   
     sudo apt-get update

#. Run this to set your locale::

     export LANG=en_US.UTF-8
     sudo apt-get install -y locales
     sudo sed -i -e "s/# $LANG.*/$LANG.UTF-8 UTF-8/" /etc/locale.gen
     sudo dpkg-reconfigure --frontend=noninteractive locales
     sudo update-locale LANG=$LANG

********************
Step 2: Install kmpc
********************
#. Install some dependencies::

     sudo apt-get -y install sqlite3

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

#. Make sure your audio connection is working. Run ``amixer sset 'PCM' 0`` to
   turn the audio volume up, then run ``speaker-test`` and listen for some
   output.

#. Run the following to install mpc, as it is needed for testing and by the
   sync function::

     sudo apt-get -y install mpc

#. The version of mpd in the repo as of this writing is super old and buggy, so
   we're going to compile from source. Change *\<musicpath\>* in the below text
   to your musicpath. Here's the commands::

     export MUSICPATH=<musicpath>
     wget https://www.musicpd.org/download/mpd/0.19/mpd-0.19.21.tar.xz
     tar xf mpd-0.19.21.tar.xz
     cd mpd-0.19.21/
     sudo apt-get -y install g++ libboost-dev libicu-dev libglib2.0-dev \
       libsqlite3-dev libmpdclient-dev libexpat1-dev \
       libid3tag0-dev libflac-dev libaudiofile-dev libmad0-dev libmp3lame-dev \
       libasound2-dev libcurl4-gnutls-dev libsystemd-daemon-dev \
       libfaad-dev libmpg123-dev libavcodec-dev libsndfile-dev libvorbis-dev \
       libavformat-dev libavutil-dev
     ./configure \
       --enable-werror --prefix=/usr --sysconfdir=/etc \
       --with-systemdsystemunitdir=/etc/systemd/system --enable-systemd-daemon \
       --enable-database --enable-sqlite --enable-libmpdclient --enable-expat \
       --enable-alsa --disable-oss --enable-icu --enable-glib \
       --enable-flac --enable-audiofile --enable-dsd --enable-mad --enable-id3 --enable-curl \
       --enable-mms=no --enable-smbclient=no --enable-nfs=no --enable-zlib=no --enable-bzip2=no \
       --enable-roar=no --enable-ao=no --enable-vorbis=yes --enable-wavpack=no --enable-gme=no \
       --enable-lame-encoder=no --enable-shine-encoder=no \
       --enable-twolame-encoder=no --enable-vorbis-encoder=no --enable-wave-encoder=no \
       --enable-modplug=no --enable-mpc=no --enable-mpg123=yes --enable-openal=no \
       --enable-opus=no --enable-sidplay=no --enable-shout=no --enable-adplug=no \
       --enable-sndfile=yes --enable-wildmidi=no --enable-soundcloud=no --enable-ffmpeg=yes \
       --enable-jack=no --enable-pulse=no --enable-lsr=no --enable-soxr=no --enable-fluidsynth=no \
       --enable-cdio-paranoia=no \
       --enable-recorder-output=no --enable-httpd-output=no --enable-solaris-output=no \
       --enable-libwrap=no --enable-upnp=no --enable-neighbor-plugins=no --with-zeroconf=no \
       --enable-aac
     make
     sudo make install
     sudo useradd -M mpd
     sudo usermod -L mpd
     sudo usermod -G audio mpd
     sudo mkdir -p /var/{lib,log}/mpd
     sudo mkdir -p /var/lib/mpd/playlists
     sudo chown -R mpd:audio /var/{lib,log}/mpd
     cat << EOF | sudo tee /etc/mpd.conf
       music_directory         "$MUSICPATH"
       playlist_directory      "/var/lib/mpd/playlists"
       db_file                 "/var/lib/mpd/database"
       log_file                "/var/log/mpd/mpd.log"
       pid_file                "/var/lib/mpd/pid"
       state_file              "/var/lib/mpd/state"
       sticker_file            "/var/lib/mpd/sticker.sql"
       user                    "mpd"
       group                   "audio"
       bind_to_address         "127.0.0.1"
     EOF
     sudo chown -R $USER:audio "$MUSICPATH"
     sudo systemctl enable mpd
     sudo systemctl start mpd

#. See https://www.musicpd.org/doc/user/config.html for further details on the
   ``/etc/mpd.conf`` file. You might want to add 'replaygain' variables, for example.

#. Restart mpd::

     sudo systemctl restart mpd

#. Run the following to update the mpd database::

     mpc update

#. Edit the file ``~/.kmpc/config.ini`` and set the ``musicpath`` variable to
   *\<musicpath\>*

#. Save the file and run ``kmpc`` again. You should now be able to browse the
   library, add files to the playlist, and generally use the app.

*******************
Step 4: Run at Boot
*******************

The easiest way to get kmpc running at boot time is by using a systemd user
unit. Run the following commands::

  mkdir -p ~/.config/systemd/user

  cat > ~/.config/systemd/user/kmpc.service <<EOL
  [Unit]
  Description=kmpc

  [Service]
  ExecStart=/usr/local/bin/kmpc
  Restart=always

  [Install]
  WantedBy=default.target
  EOL

  systemctl --user enable kmpc
  sudo loginctl enable-linger sysop # substitute your username if you used a new one

*****************************
Step 5: Add Fanart (optional)
*****************************

The directory structure for fanart is as follows, with *\<fanartpath\>* as the
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

Once you've added some art, do the following

#. Edit the file ``~/.kmpc/config.ini`` and change the ``fanartpath`` variable
   to *\<fanartpath\>*.

#. Run::
     sudo chown -R $USER:audio <fanartpath>
     systemctl --user restart kmpc

You should now see logos and background images for the artists that have images
in the fanart folder.

*****************************
Step 6: Setup Sync (optional)
*****************************

See the section on :ref:`usingkmpcmanager` to learn how the manager program
interacts with the synchost. The basic gist of it is this:

#. Have a Linux box running in your house, connected the same wifi that the car
   Pi will be able to connect to. This will be called the *synchost*.
#. Have mpd running on it, and fully updated.
#. Use ``kmpcmanager`` to automatically download all the fanart and manage the
   ratings and copy_flags for all your tracks.
#. Edit the file ``~/.kmpc/config.ini`` on your car Pi and change the variables
   in the [synchost] section. See the section on :ref:`config` for details.
#. Run ``ssh-keygen`` and hit enter on all the defaults. This creates a public
   key for this user.
#. Insert the contents of ``~/.ssh/id_rsa.pub`` on the car Pi into the
   ``~/.ssh/authorized_keys`` file on the *synchost* as whatever user you have
   set up there.
#. Edit the file ``~/.ssh/config`` and add the following::

     Host <synchost>                        # this should match config.ini
       HostName <IP_address_or_hostname>    # real ip address or hostname
       User <synchost_username>             # a user on <synchost>

Now you should be able to use the Sync button in the Config tab to
automatically sync all music, fanart, and song ratings with the *synchost*.
