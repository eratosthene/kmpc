Installation
============

Install from PyPi
-----------------
::
  
  pip install kmpc

This should install all dependencies, although you may have trouble if you haven't gotten Kivy set up properly first. Kivy needs a bunch of different libraries installed to support various hardware, so if you are, say, installing this on a Mac, you'll probably want to make sure Kivy is working before installing kmpc. Two executables, ``kivy`` and ``kivymanager`` will be installed.

Install from source
-------------------

First, make sure Kivy is up and running. I recommend installing `KivyPie <http://kivypie.mitako.eu/>`_ if you are running this on a Pi as it already has Kivy ready to go. You can also simply run::

  pip install kivy

and hope for the best. Next, install the other dependencies::

  pip install Twisted
  pip install mutagen
  pip install gitpython

This should be all you need to run the python code directly. There are two convenience scripts in the source directory, ``runkmpc`` and ``runkmpcmanager``, which should allow you to run the programs directly from the git checkout. Once you are satisfied that is working, you can install by running ``python setup.py install``, which will install the ``kmpc`` and ``kmpcmanager`` executables.
