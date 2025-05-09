"""
For the meta-plugin PaletteSwapSimple
"""
# -*- coding: utf-8 -*-
from typing import List, Tuple

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import Gegl

from palette_swap import extract_linear_palette, extract_sorted_palette, apply_palette_map


def palette_swap_simple(
    image: Gimp.Image,
    layer_target: Gimp.Layer,
    layer_sample: Gimp.Layer,
    include_transparent: bool,
    light_first: bool,
    count_threshold: int,
):
    """
    Given a target layer, and a sample layer, replaces the palette of the target with that of the sample.

    :param image: The current image.
    :param layer_target: The target layer, to be re-coloured.
    :param layer_sample: The layer to take the colour palette from.
    :param include_transparent: Whether to sample colours from transparent pixels.
    :param count_threshold: Whether to ignore colours with < that many pixels.
    :param light_first: Whether to match colours lightest-to-lightest first. Defaults to darkest-to-darkest.
    """
    Gimp.progress_init(
        f"Swapping palette from {layer_sample.get_name()} onto {layer_target.get_name()}..."
    )

    # Remember current foreground
    original_foreground: Gegl.Color = Gimp.context_get_foreground()

    # print("Got foreground...")
    # Set up an undo group, so the operation will be undone in one step.
    image.undo_group_start()
    # print("Started Undo Group...")

    # Extract the palettes.
    Gimp.progress_init(
        f"Finding {layer_sample.get_name()} palette..."
    )
    # print("Initialised progress bar...")


    if layer_sample.get_height() == 1:
        # print("Extracting linear palette...")
        sorted_palette_new = extract_linear_palette(
            layer=layer_sample,
            current_progress=0, progress_fraction=0.4
        )
    else:
        # print("Extracting sorted palette...")
        sorted_palette_new = extract_sorted_palette(
            layer=layer_sample,
            include_transparent=include_transparent,
            count_threshold=count_threshold,
            current_progress=0, progress_fraction=0.4
        )
    # print("Found palette new...")

    Gimp.progress_init(
        f"Finding {layer_target.get_name()} palette..."
    )

    sorted_palette_old: List[Tuple[float, float, float]] = extract_sorted_palette(
        layer=layer_target,
        include_transparent=include_transparent,
        count_threshold=count_threshold,
        current_progress=0.4, progress_fraction=0.4
    )
    # print("Found palette old...")

    if light_first:
        sorted_palette_old.reverse()
        sorted_palette_new.reverse()

    apply_palette_map(
        image=image,
        layer=layer_target,
        sorted_palette_old=sorted_palette_old,
        sorted_palette_new=sorted_palette_new,
        current_progress=0.8, progress_fraction=0.2
    )

    # Return original foreground colour
    Gimp.context_set_foreground(original_foreground)
    Gimp.Selection.none(image)

    # Close the undo group.
    image.undo_group_end()


