# Metroid Prime: Hunters RGB
This program sets your PC's RGB lighting based on what weapon you are using in an emulated play of the Nintendo DS game, _Metroid Prime: Hunters_.
<blockquote class="imgur-embed-pub" lang="en" data-id="a/oqLmzRI"  ><a href="//imgur.com/a/oqLmzRI">MPH-RGB demo</a></blockquote><script async src="//s.imgur.com/min/embed.js" charset="utf-8"></script>

## Prerequisites:
- You will need [OpenRGB](https://openrgb.org/) to be running. If it does not support your RGB hardware, this program will not work.
- [OpenRGB's SDK](https://openrgb.org/sdk.html) server needs to be running, but don't worry, starting it just a quick button press from inside OpenRGB: Under the "SDK Server" tab, click "Start Server". There are settings within OpenRGB to make it start at login with the server if you so desire.
- You can't use just any DS emulator. Because the program uses screenshots, it's heavily reliant on the GUI sizing and "Hybrid" layout of [MelonDS](https://melonds.kuribo64.net/). All of that sizing still exists in [MelonPrimeDS](https://github.com/makinori/melonPrimeDS). I recommend using MelonPrimeDS, specifically [the Livetek release](https://github.com/makinori/melonPrimeDS/releases/tag/livetek-release).
- Once MelonDS or MelonPrimeDS is running, go to the menubar and choose "View" -> "Screen layout" -> "Hybrid". Everything else defers to regular setup for that emulator.
- You need a screenshot tool, either [scrot](https://github.com/resurrecting-open-source-projects/scrot) for XOrg, or [KDE Spectacle](https://apps.kde.org/spectacle/) for Wayland. My program will try to figure out which one it needs.

## Python Dependencies
This program relies on the following non-native Python packages:
- [OpenRGB-Python](https://pypi.org/project/openrgb-python/)
- [Pillow](https://pypi.org/project/pillow/)

You can install these all at once by running `python -m pip install -r requirements.txt` within the downloaded repository folder.

## Legal
Copyright 2026 Wilbur Jaywright dba Marswide BGL.

This file is part of MPH-RGB.

MPH-RGB is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

MPH-RGB is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with MPH-RGB. If not, see <https://www.gnu.org/licenses/>.

## S.D.G.
