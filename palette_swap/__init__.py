"""
The common functions used by all palette swap procedures.
"""
# -*- coding: utf-8 -*-
from collections import defaultdict
from typing import Dict, List, Tuple

# --- DEBUG ---
# import debugpy
# import inspect
# import os
# import sys
#
# try:
#     debugpy.listen(("localhost", 5678))
#     debugpy.wait_for_client()
# except:
#     pass
#
# currentframe = os.path.dirname(inspect.getfile(inspect.currentframe()))
# sys.path.append(currentframe)
# sys.stderr = open(os.path.join(currentframe, "errors.txt"), 'w', buffering=1)
# sys.stdout = open(os.path.join(currentframe, "log.txt"), 'w', buffering=1)
# -------------

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gegl


def rgb_to_brightness(colour_rgb: Tuple[float, float, float]) -> float:
    """
    Converts an RGB value to perceptual brightness, using this equation:
    https://www.w3.org/TR/AERT/#color-contrast

    :param colour_rgb: The RGB colour, as a tuple.
    """
    return 0.299 * colour_rgb[0] + 0.587 * colour_rgb[1] +  0.114 * colour_rgb[2]


def extract_linear_palette(
        layer: Gimp.Layer,
        current_progress: float,
        progress_fraction: float,
) -> List[Tuple[float, float, float]]:
    """
    Extracts a palette from a 1-high row of pixels,
    assuming it's a sorted palette from light to dark.

    For some reason passing around Gegl.Color seems to mess up.
    so doing it in RGB values.

    :param layer: The layer to extract from.
    :param current_progress: The current % of the progress bar.
    :param progress_fraction: The % of the progress bar this functions should cover.
    :return: The palette, as a list of RGB colours.
    """
    # print("Extracting linear palette...")

    sorted_palette = []
    for index_width in range(0, layer.get_width()):
        sorted_palette.append(
            layer.get_pixel(0, index_width).get_rgba()[0:3]
        )

    sorted_palette.reverse()
    Gimp.progress_update(current_progress + progress_fraction)
    return sorted_palette


def extract_sorted_palette(
    layer: Gimp.Layer,
    include_transparent: bool,
    count_threshold: int,
    current_progress: float,
    progress_fraction: float,
) -> List[Tuple[float, float, float]]:
    """
    Extracts a palette from an image, by finding the discrete RGB values
    and then sorting them by total R+G+B value.

    For some reason, passing around Gegl.Color seems to mess up,
    so doing it in RGB values.

    :param layer: The layer to extract from.
    :param current_progress: The current % of the progress bar.
    :param progress_fraction: The % of the progress bar this functions should cover.
    :param include_transparent: Whether to sample colours from transparent pixels.
    :param count_threshold: Whether to ignore colours with < that many pixels.
    :return: The palette, as a list of RGB colours.
    """
    # print("Extracting sorted palette...")

    palette_counts: defaultdict = defaultdict(int)
    progress_step: float = progress_fraction / layer.get_height()

    for index_height in range(0, layer.get_height()):
        for index_width in range(0, layer.get_width()):
            pixel_colour = layer.get_pixel(
                index_width, index_height
            )
            pixel_rgba = pixel_colour.get_rgba()

            if include_transparent or layer.has_alpha() and pixel_rgba[3] > 0:
                palette_counts[pixel_rgba[0:3]] += 1

        Gimp.progress_update(current_progress + progress_step * index_height)

    # print(f"Sorted through pixels to build defaultdict: {palette_counts}")

    # Now we've counted all the pixel colours, sort and discard outliers.
    palette: Dict[Tuple[float, float, float]] = {}
    for colour_rgb, colour_count in palette_counts.items():
        colour_brightness = rgb_to_brightness(colour_rgb)

        if colour_count > count_threshold:
            if colour_brightness in palette and colour_rgb != palette[colour_brightness]:
                colour_duplicate = palette[colour_brightness]
                raise KeyError(
                    f"Multiple colours in layer with same brightness ({colour_brightness}): "
                    f"{colour_rgb} ({colour_count} pixels) and {colour_duplicate} ({palette_counts[colour_duplicate]} pixels. "
                    "Cannot automatically sort colours by brightness. "
                    "Try increasing the 'ignore colours with less than this many pixels' setting "
                    "to drop stray pixels."
                )
            else:
                palette[colour_brightness] = colour_rgb

    sorted_palette = [
        palette[key] for key in sorted(list(palette.keys()))
    ]
    return sorted_palette


def apply_palette_map(
    image: Gimp.Image,
    layer: Gimp.Layer,
    sorted_palette_old: List[Tuple[float, float, float]],
    sorted_palette_new: List[Tuple[float, float, float]],
    current_progress: float,
    progress_fraction: float,
):
    """
    Applies a colour mapping as given in two palette arrays.

    :param image: The current image.
    :param layer: The layer to extract from.
    :param sorted_palette_old: The old palette, colours to be replaced.
    :param sorted_palette_new: The new palette, colours to replace them with.
    :param current_progress: The current % of the progress bar.
    :param progress_fraction: The % of the progress bar this functions should cover.
    :param include_transparent: Whether to sample colours from transparent pixels.
    :param count_threshold: Whether to ignore colours with < that many pixels.
    """
    for index_colour, colour_old, colour_new in zip(
        range(0, len(sorted_palette_old)),
        sorted_palette_old,
        sorted_palette_new
    ):
        # print(f"Filling {colour_old} with {colour_new}")
        progress_step: float = progress_fraction / len(sorted_palette_old)

        image.select_color(
            Gimp.ChannelOps.REPLACE,
            layer,
            Gegl.Color.new(
                f"rgba({colour_old[0]},{colour_old[1]},{colour_old[2]},1)"
            )
        )
        Gimp.context_set_foreground(
            Gegl.Color.new(
                f"rgba({colour_new[0]},{colour_new[1]},{colour_new[2]},1)"
            )
        )
        layer.edit_fill(Gimp.FillType.FOREGROUND)
        Gimp.progress_update(current_progress + progress_step * index_colour)

    Gimp.displays_flush()
