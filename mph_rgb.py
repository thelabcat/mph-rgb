#!/usr/bin/env python3
"""Metroid Prime: Hunters RGB controller

Control the RGB lighting of my stuff with MPH weapon status.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.

S.D.G.
"""

import io
import subprocess
from typing import Sequence
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor  # , DeviceType
from PIL import Image
import tomllib

with open("config.toml", "rb") as f:
    CONFIG = tomllib.load(f)

# The pixel size of each Nintendo DS screen
DS_SCREEN_SIZE = (256, 192)

# The relative pixel size of the hybrid emulator display area
EMU_DISP_SIZE = DS_SCREEN_SIZE[0] * 3, DS_SCREEN_SIZE[1] * 2

# The pixel height of the MelonPrimeDS emulator menu bar
EMU_MENUBAR_HEIGHT = 25

"""
Select window.
Calculate position of two screens.
Start monitoring for game to enter first person.
While a game is in first person:
    Constantly watch for weapon changes.
    Monitor for any keypress that can change the weapon.
    When such a keypress occurs, go into the "changing" state, and wait for the next screenshot to arrive.
    If, by the time we have the screenshot, we have not been queued that there is a new weapon change, switch to the new one. Probably best handled by a thread.
"""

# Command to take a screenshot and pipe it to stdout
SCSH_COMMAND = "spectacle -abne -d 0 -o /proc/self/fd/1"


def get_screenshot(wholerender: bool = False) -> Image:
    """Get a screenshot of the game

    Args:
        wholerender (bool): Include the entire render rather than cropping to the hud screen.
            Defaults to False.

    Returns:
        shot (Image): The screenshot."""

    cp = subprocess.run(SCSH_COMMAND.split(), capture_output=True)
    buff = io.BytesIO(cp.stdout)
    img = Image.open(buff)
    img = img.crop((0, EMU_MENUBAR_HEIGHT, *img.size))

    # Find how much the DS screen is being scaled
    factor = min((img.width / EMU_DISP_SIZE[0], img.height / EMU_DISP_SIZE[1]))

    # Get the actual size of the render on screen
    correct_size = EMU_DISP_SIZE[0] * factor, EMU_DISP_SIZE[1] * factor

    # Find out how much black is around the render
    margins = max((img.size[0] - correct_size[0], 0)) / 2, max((img.size[1] - correct_size[1], 0)) / 2

    # Crop off the black margins, and the unwanted displays
    return img.crop((
        margins[0] + factor * DS_SCREEN_SIZE[0] * 2,
        margins[1] + factor * DS_SCREEN_SIZE[1] * (not wholerender),
        img.width - margins[0],
        img.height - margins[1],
        ))


def distance(vec1: Sequence, vec2: Sequence = None) -> float:
    """Get the distance between two vectors

    Args:
        vec1 (Sequence): The first vector.
        vec2 (Sequence): The second vector.
            Defaults to origin in first vector's space.

    Returns:
        distance (float): The distance between the vectors."""

    # Default the second vector to the space origin
    if not vec2:
        vec2 = [0] * len(vec1)

    # Make sure the vectors are appropriate sizes
    #assert len(vec1) == len(vec2), \
    #    f"Cannot compute distance between vectors in different number of dimensions, {len(vec1)} and {len(vec2)}"

    return sum((p2 - p1) ** 2 for p1, p2 in zip(vec1, vec2)) ** 0.5


def color_sense(screenshot: Image, coords: Sequence, color: Sequence) -> bool:
    """Determine if a color is at the given location on the HUD, taking scale into account

    Args:
        screenshot (Image): The HUD screenshot.
        coords (Sequence): The coordinates to look at.
        color: (Sequence): The color to look for.

    Returns:
        result (bool): Is the color matching within tolerance?"""

    # Scale the coordinates and clip them to the screenshot size
    factor = screenshot.width / CONFIG["scale"][0]
    scaled_coords = tuple(max((min((int(coords[i] * factor + 0.5), screenshot.size[i] - 1)), 0)) for i in range(2))

    # Actually do the detection
    return distance(screenshot.getpixel(scaled_coords), color) < CONFIG["colorTolerance"]


def get_active_hunter(screenshot: Image) -> str | None:
    """Detect the currently active hunter

    Args:
        screenshot (Image): The current lower display screenshot.

    Returns:
        result (str | None): The detected hunter's name, or None if not in first-person."""

    # check for each hunter's HUD
    for hunter, specs in CONFIG["hunterSpecs"].items():
        if color_sense(screenshot, specs["isHudCoords"], specs["isHudColor"]):
            return hunter

    # No hunter HUD was found
    return None


def get_active_weapon(screenshot: Image, hunter: str = None) -> str:
    """Get the current active weapon

    Args:
        screenshot (Image): The current screenshot of the lower screen.
        hunter (str): The name of the currently active hunter.
            Defaults to None, auto-detect.

    Returns:
        weapon (str | None): The currently active weapon by TOML name, or None."""

    # Try to detect the hunter if we were not passed one
    hunter = hunter or get_active_hunter(screenshot)

    # No hunter was passed and we didn't detect one
    if not hunter:
        return None

    # Detect main weapon category
    main_weapon = None
    for weapon, coords in CONFIG["hunterSpecs"][hunter]["mainWeaponCoords"].items():
        if color_sense(screenshot, coords, CONFIG["hunterSpecs"][hunter]["mainWeaponSenseColor"]):
            main_weapon = weapon

    # No weapon was active. We are probably in map.
    if not main_weapon:
        return None

    # Either power beam or missiles is active
    if main_weapon != "third":
        return main_weapon

    # A third special weapon is active
    for weapon, coords in CONFIG["hunterSpecs"][hunter]["thirdWeaponCoords"].items():
        if color_sense(screenshot, coords, CONFIG["hunterSpecs"][hunter]["thirdWeaponSenseColors"][weapon]):
            return weapon


client = OpenRGBClient()
for device in client.devices:
    if "Dell" in device.name:
        break

prev_hunter = None
prev_weapon = None
device.set_color(RGBColor(0, 0, 0))

while False:
    screenshot = get_screenshot()
    hunter = get_active_hunter(screenshot)
    if hunter != prev_hunter:
        print("Hew hunter detected:", hunter)
        prev_hunter = hunter
    weapon = get_active_weapon(screenshot, hunter) if hunter else None
    if weapon != prev_weapon:
        print("New weapon detected:", weapon)
        prev_weapon = weapon
        if not weapon:
            device.set_color(RGBColor(0, 0, 0))
        else:
            device.set_color(RGBColor(*CONFIG["weaponColorsShow"][weapon]))
