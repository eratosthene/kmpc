.. _plugins:

#######
Plugins
#######

Plugins are accessed via the System Tab:

.. image:: images/system.png

Upon clicking the Plugins button, you are presented with a list of all
available plugins in the ``~/.kmpc/plugins`` folder:

.. image:: images/plugins.png

Pictured are some plugins that are available at
`https://github.com/eratosthene/kmpc-plugins
<https://github.com/eratosthene/kmpc-plugins>`_.

**********************
Plugin Folder Contents
**********************

Inside the ``~/.kmpc/plugins`` folder, there should be one or more folders
named for each plugin. Each plugin folder must contain at least two files named
``plugin.py`` and ``plugin.kv``::

  plugins
  ├── kivypiewifi
  │   ├── plugin.kv
  │   └── plugin.py
  └── osxwifi
      ├── plugin.kv
      └── plugin.py

plugin.py
=========

This file contains the logic for a plugin, written in python. You can import
whatever you want, and it will have access to any global variables in the kmpc
application, including App. The only requirement is to have at least one class
named <pluginname>PluginContent, that is a subclass of some Kivy widget. So,
for example, the *kivypiewifi* plugin has the following in it:

.. code-block:: python

  class kivypiewifiPluginContent(BoxLayout):

Do whatever needs to be done, just make sure you are doing things in a
non-blocking manner. I prefer to use the twisted reactor and its associated
methods for this.

plugin.kv
=========

This file contains the presentation for a plugin, written in kv. It should
should contain at least the default kv declaration, an import for the plugin's
class, and a definition of that class. For example, the *kivypiewifi* plugin
has the following in it:

.. code-block:: python

  #:kivy 1.10.0
  #:import kivypiewifiPluginContent plugin.kivypiewifiPluginContent

  ... (skipping a few lines)

  <kivypiewifiPluginContent>:
    (here iss where the kv definition for your plugin goes)

*******
Running
*******

When you click on a plugin in kmpc to run it, the following things happen:

#. The *Choose Plugin to Run* popup is closed.
#. A new full screen popup is opened, with a Close button at the bottom.
#. The plugin's PluginContent class is instantiated, and placed inside the
   popup.
