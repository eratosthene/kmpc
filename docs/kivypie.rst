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
   understand how you can connect to it. In particular, if it is not connected
   to ethernet, you'll need to connect a keyboard to run ``pipaos-setwifi`` in
   order to get wifi working. Everything else can be done via SSH.
#. Login with the credentials given in the FAQ. The rest of the guide will use
   the default user, however if you wish to add a new user and do everything
   with that it should be fine, just adjust accordingly.
#. Run ``sudo pip install kmpc[rpi]`` to install kmpc. This will pull in the
   Pi-specific dependencies.
