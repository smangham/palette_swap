"""
For the meta-plugin PaletteToLayer
"""
# -*- coding: utf-8 -*-
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import Gegl

from palette_swap import extract_sorted_palette


def palette_to_layer(
    image: Gimp.Image,
    layer_sample: Gimp.Layer,
    layer_name: str,
    include_transparent: bool,
    count_threshold: int,
):
    """
    Creates a 1-pixel-high 'palette' layer from the current image's selected layer.

    :param image: The current image.
    :param layer_sample: The layer to sample colours from.
    :param layer_name: The name of the new layer.
    :param include_transparent: Whether to sample colours from transparent pixels.
    :param count_threshold: Whether to ignore colours with < that many pixels.
    :raises ValueError: If the palettes are differing lengths.
    """
    # Set up an undo group, so the operation will be undone in one step.
    image.undo_group_start()

    # Extract the palettes
    Gimp.progress_init(
        f"Finding {layer_sample.get_name()} palette..."
    )

    sorted_palette: Gimp.Layer = extract_sorted_palette(
        layer=layer_sample,
        include_transparent=include_transparent,
        count_threshold=count_threshold,
        current_progress=0.0, progress_fraction=1.0
    )
    sorted_palette.reverse()
    # print(f"Extracted palette: {sorted_palette}")

    layer_palette: Gimp.Layer = Gimp.Layer.new(
        image,
        width=len(sorted_palette),
        name=layer_name,
        height=1,
        type=Gimp.ImageType.RGB_IMAGE,
        opacity=100.0,
        mode=Gimp.LayerMode.NORMAL_LEGACY,
    )
    # print("Created new layer...")

    for column_index, colour_rgb in zip(range(0, len(sorted_palette)), sorted_palette):
        print(
            f"Setting colour {colour_rgb}"
        )
        layer_palette.set_pixel(
            x_coord=column_index,
            y_coord=0,
            color=Gegl.Color.new(
                f"rgba({colour_rgb[0]},{colour_rgb[1]},{colour_rgb[2]},1)"
            )
        )

    # print("Set colours...")
    image.insert_layer(layer_palette, None, 0)
    Gimp.displays_flush()

    # print("Set active layer...")

    # Close the undo group.
    image.undo_group_end()
