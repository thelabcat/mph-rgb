#!/usr/bin/env python3
"""Metroid Prime: Hunters RGB controller

Control the RGB lighting of your hardware with MPH weapon status.

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
import os
import subprocess
import tomllib
from typing import Sequence
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor  # , DeviceType
from PIL import Image

with open("config.toml", "rb") as f:
    CONFIG = tomllib.load(f)

# The pixel size of each Nintendo DS screen
DS_SCREEN_SIZE = (256, 192)

# The relative pixel size of the hybrid emulator display area
EMU_DISP_SIZE = DS_SCREEN_SIZE[0] * 3, DS_SCREEN_SIZE[1] * 2


"""
The original plan (was not followed precisely, only kept for historical purposes):

Select window.
Calculate position of two screens.
Start monitoring for game to enter first person.
While a game is in first person:
    Constantly watch for weapon changes.
    Monitor for any keypress that can change the weapon.
    When such a keypress occurs, go into the "changing" state, and wait for the next screenshot to arrive.
    If, by the time we have the screenshot, we have not been queued that there is a new weapon change, switch to the new one. Probably best handled by a thread.
"""

# Command to take a screenshot of the active window immediately and pipe it to stdout
STDOUT_MAGICFILE = "/proc/self/fd/1"
WAYLAND_COMMAND = "spectacle -abne -d 0 -o " + STDOUT_MAGICFILE
XORG_COMMAND = "scrot -iuo " + STDOUT_MAGICFILE

# Determine the correct command to use
if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
    # We are using Wayland
    SCSH_COMMAND = WAYLAND_COMMAND
    print("Detected Wayland.")
else:
    # We are probably using XOrg
    SCSH_COMMAND = XORG_COMMAND
    print("Did not detect Wayland, assuming XOrg.")


def get_screenshot(wholerender: bool = False) -> Image:
    """Get a screenshot of the game

    Args:
        wholerender (bool): Include the entire render rather than cropping to the hud screen.
            Defaults to False.

    Returns:
        shot (Image): The screenshot."""

    cp = subprocess.run(SCSH_COMMAND.split(), capture_output=True, check=True)
    buff = io.BytesIO(cp.stdout)
    img = Image.open(buff)
    img = img.crop((0, CONFIG["emuMenubarHeight"], *img.size))

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

    # Somehow, weapon detection failed
    return None


def multiple_choice(title: str, options: Sequence[str]) -> str:
    """Allow the user to choose between multiple options.
        Automatically selects a lone option.

    Args:
        title (str): The question at hand.
        options (Sequence[str]): A subscriptable of option strings.

    Returns:
        choice (str): The chosen option."""

    # The function can't work if there's no options to choose from!
    assert len(options) > 0, "Too few options"

    # If there's just one option, choose it automatically
    if len(options) == 1:
        print(f"Only one option for, \"{title}\", and that is \"{options[0]}\".")
        return options[0]

    # Find the 'biggest' option by length, and then find out how long it is.
    option_max_width = len(max(options, key=len))

    # We're going to show a number next to each option as well, so we'd better
    # get the visual length of the biggest number as well.
    num_width = len(str(len(options)))

    # Make sure we get a valid choice.
    # The return statements will exit this loop for us.
    while True:
        # Display the question and the options, and get an input
        print(title)

        for i, option in enumerate(options):
            # Line all the options and their numbering up
            print(f"{i + 1:0{num_width}d}··{option:·>{option_max_width}}")

        # Finally, ask the user for some input.
        entry = input("Choice: ")

        # Option was typed directly
        if entry in options:
            return entry

        # Number was typed
        if entry.isnumeric():
            try:
                return options[int(entry) - 1]

            # The number wasn't a valid option index
            except IndexError:
                print("Entered number does not match an option.")

        # Something was typed but it was invalid
        if entry:
            print("Invalid entry. Please type a number or the option itself.")


client = OpenRGBClient()

try:
    # Device selection code
    devices_by_name = {device.name: device for device in client.devices}
    name_choice = multiple_choice("Choose RGB device to use:", list(devices_by_name))
    device = devices_by_name[name_choice]

    # Memory for previous state, so we only send color changes when we need to
    prev_hunter = None
    prev_weapon = None

    # Initial color should assume no hunter is active
    device.set_color(RGBColor(0, 0, 0))

    # Program continues until interrupted
    print("Press Ctrl+C to stop the program when done playing.")
    while True:
        # Constantly scan the emulator screen
        screenshot = get_screenshot()

        # If not hunter is active, this will be None
        hunter = get_active_hunter(screenshot)

        # Hunter memory is mainly for debug. It's a weapon change we care about
        if hunter != prev_hunter:
            print("Hew hunter detected:", hunter)
            prev_hunter = hunter

        # Detect the current weapon in use, but only if a hunter is active.
        # If no hunter is active, the weapon will of course be None as well
        weapon = get_active_weapon(screenshot, hunter) if hunter else None

        # There has been a weapon change
        if weapon != prev_weapon:
            # Note the change to memory
            print("New weapon detected:", weapon)
            prev_weapon = weapon

            # Note: Weapon can only and will always be None if hunter is None
            # When there is no hunter/weapon, turn the lights off
            if not weapon:
                device.set_color(RGBColor(0, 0, 0))

            # Otherwise, set the appropiate color for the new weapon selection
            else:
                device.set_color(RGBColor(*CONFIG["weaponColorsShow"][weapon]))

# When we abort with Ctrl+C
finally:
    # We have to do this or the OpenRGB server keeps a ghost connection open indefinitely
    print("Disconnecting OpenRGB client")
    client.disconnect()
    print("Done.")
