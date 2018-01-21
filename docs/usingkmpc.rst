##############
Using ``kmpc``
##############

Here is a quick tour of the various tabs in kmpc and what everything does.

***********
Now Playing
***********

This is the default active tab when you first run kmpc. If there is no
currently playing music, you will see 'Playback Stopped'. If there is something
playing, it will look similar to this:

.. image:: images/mainwindow.png

Main Tab Navigation
===================

Across the top are the various tabs you can switch to. Each of these will be
explained in following sections.

Current Track Info
==================

Next is the artist name section, which is pulled from the track artist tag.
This will either be rendered in normal text, or a logo image pulled from the
fanart folder. If there is more than one artist, all artists will be shown.

After that is the track name, then the album name, with the release year in
brackets afterwards. This is pulled from the original year tag if it exists,
and pulled from mpd otherwise. 

Under this is a smaller line detailing the upcoming artist and track.

Bottom Section
==============

At the bottom left is the album cover, if it can be pulled from the cover image
tag, or a blank space otherwise. You can click on it to popup a larger view,
and click outside the popup to dismiss it.

In the middle is the current track time. The time displayed inside the slider
is the remaining time. On the left is the elapsed time, and on the right is the
total time.

Below that is the track number. This shows the current track and the total
number of tracks in the current playlist.

On the bottom right is the song rating. This will display a ? if the song has
not yet been rated, or the value from 0-10 in half-star increments of the song
rating as pulled from mpd. This does not check the rating tag of the file.

Backlight Controls
==================

On the far right of the screen, there are four buttons to control the
brightness of the Raspberry Pi touchscreen. These do nothing if the rpienable
flag is not set to true in the config file. They change the brightness from
brightest at the top to dimmest at the bottom.

Playback Controls
=================

Along the very bottom of the screen are the playback controls. From left to
right, they are as follows:

Previous Track
  Goes to the previous track.
Play/Pause
  Pauses if playing, plays if paused or stopped.
Next Track
  Goes to the next track.
Toggle Repeat Mode
  If on, the current playlist (if Single Mode is off) or track (if Single Mode
  is on) will repeat indefinitely.
Toggle Single Mode
  If Repeat Mode is on, the current song will repeat. If Repeat Mode is off,
  then playback will stop after the current song.
Toggle Random Mode
  The playlist will be played back in random order if on.
Toggle Consume Mode
  If on, the current song will be removed from the playlist after playback.

********
Playlist
********

.. image:: images/playlist.png

Function Buttons
================

Along the top, under the main tabs, are several function buttons. From left
right, they are as follows:

Clear
  Clears the playlist.
Delete
  Removes the currently selected track from the playlist.
Move
  Does nothing right now. Sorry.
Shuffle
  Shuffles all tracks on the playlist.
Swap
  Switch the position of two selected tracks. Must have exactly two tracks
  selected.
Save
  Saves the current playlist with a name.

List of Tracks
==============

Below the buttons is the list of tracks in the current playlist. This is
scrollable via touch, mousewheel, or click and drag. The currently playing
track is highlighted. Clicking on a track will select it for use with the above
function buttons. Long-pressing a track will start playing from that track.
