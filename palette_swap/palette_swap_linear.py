"""
For the meta-plugin PaletteSwapLinear
"""
# -*- coding: utf-8 -*-
from typing import List, Tuple

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import Gegl

from palette_swap import extract_linear_palette, apply_palette_map


def palette_swap_linear(
    image: Gimp.Image,
    layer_target: Gimp.Layer,
    layer_palette_old: Gimp.Layer,
    layer_palette_new: Gimp.Layer,
):
    """
    Given two different 1-pixel-high 'palette' layers,
    swaps the current layer's colours from the old to the new.

    :param image: The current image.
    :param layer_target: The target layer.
    :param layer_palette_old: The old palette, colours to be replaced.
    :param layer_palette_new: The new palette, colours to replace them with.
    :raises ValueError: If the palettes are differing lengths.
    """
    Gimp.progress_init(
        f"Swapping palette from {layer_palette_old.get_name()} to {layer_palette_new.get_name()} for {layer_target.get_name()}..."
    )

    # Remember current foreground
    original_foreground: Gegl.Color = Gimp.context_get_foreground()

    # Set up an undo group, so the operation will be undone in one step.
    image.undo_group_start()

    Gimp.progress_init(
        f"Finding {layer_palette_new.get_name()} palette..."
    )

    sorted_palette_new: List[Tuple[float, float, float]] = extract_linear_palette(
            layer=layer_palette_new,
            current_progress=0,
            progress_fraction=0.4
    )

    Gimp.progress_init(
        f"Finding {layer_palette_old.get_name()} palette...")

    sorted_palette_old: List[Tuple[float, float, float]] = extract_linear_palette(
        layer=layer_palette_old,
        current_progress=0.4,
        progress_fraction=0.4
    )

    if len(sorted_palette_new) != len(sorted_palette_old):
        raise ValueError("Palettes are differing lengths!")

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