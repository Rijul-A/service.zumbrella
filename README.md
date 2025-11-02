service.zumbrella
================

A Kodi service addon that automatically manages audio streams and subtitles based on your preferences.

Features
--------

* **Automatic Audio Stream Selection**: Automatically selects the best audio stream matching your preferred language when playback starts
* **Automatic Subtitle Activation**: Intelligently activates subtitles based on your language preference, with smart filtering of forced subtitles

How It Works
------------

When video playback starts, the service:

1. Detects available audio streams and selects one matching your preferred language
2. Filters out forced subtitles and activates the best matching subtitle track

Configuration
-------------

The addon includes two settings:

* **Debug mode**: Enable verbose logging for troubleshooting
* **Preferred language**: Set your preferred language code (e.g., `eng`, `spa`, `fre`, `deu`)

Subtitle Selection Priority
---------------------------

When multiple subtitles are available, the service applies the following priority:

1. Default subtitle track
2. Internal subtitle matching preferred language (non-forced)
3. Internal subtitle without language tag (non-forced)
4. Any subtitle matching preferred language
5. Any subtitle without language tag

Audio Stream Selection Priority
-------------------------------

When multiple audio streams are available:

1. Stream matching preferred language
2. Stream without language tag
3. Default stream

Requirements
------------

* Kodi Matrix (v19) or later
* Python 3.0.0+

Installation
------------

1. Copy the addon folder to your Kodi addons directory
2. Enable the service addon in Kodi Settings > Add-ons > My Add-ons > Services
3. Configure your preferred language in the addon settings
