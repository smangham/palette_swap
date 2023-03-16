#!/usr/bin/env python
"""
palette_swap.py
Created by Sam Mangham 2023/3/16, licensed GPLv3
"""
import struct
from gimpfu import *


class RowIterator:
    """
    Borrowed from the `colorxhtml.py` script
    """
    def __init__(self, row, bpp):
        self.row = row
        self.bpp = bpp

        self.start = 0
        self.stop = bpp

        self.length = len(row)
        self.fmt = 'B' * bpp

    def __iter__(self):
        return iter(self.get_pixel, None)

    def get_pixel(self):
        if self.stop > self.length:
            return None

        pixel = struct.unpack(self.fmt, self.row[self.start:self.stop])

        self.start += self.bpp
        self.stop += self.bpp

        return pixel
    

def extract_linear_palette(layer, current_progress, progress_fraction):
    """
    Extracts a palette from a 1-high row of pixels,
    assuming it's a sorted palette from light to dark
    """
    sorted_palette = []
    region = layer.get_pixel_rgn(
        0, 0, layer.width, layer.height
    )
    for pixel in RowIterator(region[0:layer.width, 0], layer.bpp):
        sorted_palette.append(pixel[0:3])

    sorted_palette.reverse()
    gimp.progress_update(current_progress + progress_fraction)
    return sorted_palette


def extract_sorted_palette(
    layer, include_transparent, current_progress, progress_fraction
):
    """
    Extracts a palette from an image, by finding the discrete RGB values
    and then sorting them by total R+G+B value.
    """
    palette = {}
    region = layer.get_pixel_rgn(
        0, 0, layer.width, layer.height
    )
    progress_step = progress_fraction / layer.height

    for index_row in range(0, layer.height):
        for pixel in RowIterator(region[0:layer.width, index_row], layer.bpp):
            colour_rgb = pixel[0:3]
            colour_sum = sum(colour_rgb)

            if layer.has_alpha and pixel[3] == 0 and not include_transparent:
                continue

            elif colour_sum in palette:
                if palette[colour_sum] != colour_rgb:
                    raise KeyError(
                        "Multiple colours with same sum value, cannot palette swap."
                    )
            else:
                palette[colour_sum] = colour_rgb

        gimp.progress_update(current_progress + progress_step * index_row)

    sorted_palette = [
        palette[key] for key in sorted(list(palette.keys()))
    ]
    return sorted_palette


def apply_palette_map(
    image, layer, sorted_palette_old, sorted_palette_new, 
    current_progress, progress_fraction
):
    """
    Applies a colour mapping as given in two palette arrays
    """
    for index_colour, colour_old, colour_new in zip(
        range(0, len(sorted_palette_old)), 
        sorted_palette_old, 
        sorted_palette_new
    ):
        progress_step = progress_fraction / len(sorted_palette_old)

        pdb.gimp_by_color_select(
            layer, colour_old, 0, CHANNEL_OP_REPLACE, False, False, 0, False
        )
        pdb.gimp_context_set_foreground(
            colour_new
        )
        pdb.gimp_edit_bucket_fill(
            layer, BUCKET_FILL_FG, LAYER_MODE_ERASE, 
            100.0, 0.0, False,  # Opacity, threshold, sample merged layers
            0, 0  # x, y, both invalid as we have a selection
        )
        pdb.gimp_edit_bucket_fill(
            layer, BUCKET_FILL_FG, LAYER_MODE_BEHIND,
            100.0, 0.0, False,  # Opacity, threshold, sample merged layers
            0, 0  # x, y, both invalid as we have a selection
        )

        gimp.progress_update(current_progress + progress_step * index_colour)

    gimp.displays_flush()


def palette_swap_linear(
    image, layer_orig, layer_palette, layer_sample, include_transparent, light_first
):
    """
    """
    gimp.progress_init(
        "Swapping palette from " + layer_palette.name + \
        " to " + layer_orig.name + " onto " + layer_orig.name + "..."
    )

    # Remember current foreground
    original_foreground = pdb.gimp_context_get_foreground()

    # Set up an undo group, so the operation will be undone in one step.
    pdb.gimp_undo_push_group_start(image)
    
    gimp.progress_init("Finding " + str(layer_sample.name)+ " palette...")
    
    if layer_sample.height == 1:
        sorted_palette_new = extract_linear_palette(
            layer=layer_sample, current_progress=0, progress_fraction=0.4
        ) 
    else:
        pdb.gimp_message(
            "Sample palette is not 1-high! Extracting colours from image and sorting automatically."
        )
        sorted_palette_new = extract_sorted_palette(
            layer=layer_sample, include_transparent=include_transparent,
            current_progress=0, progress_fraction=0.4
        )     

    gimp.progress_init("Finding " + str(layer_orig.name)+ " palette...")

    if layer_palette.height == 1:
        sorted_palette_old = extract_linear_palette(
            layer=layer_palette, current_progress=0.4, progress_fraction=0.4    
        ) 
    else:
        pdb.gimp_message(
            "Original image palette is not 1-high! Extracting colours from image and sorting automatically."
        )
        sorted_palette_old = extract_sorted_palette(
            layer=layer_palette, include_transparent=include_transparent,
            current_progress=0.4, progress_fraction=0.4    
        )

    if light_first:
        sorted_palette_old.reverse()
        sorted_palette_new.reverse()

    apply_palette_map(
        image=image, layer=layer_orig,
        sorted_palette_old=sorted_palette_old, 
        sorted_palette_new=sorted_palette_new,
        current_progress=0.8, progress_fraction=0.2
    )

    # Return original foreground colour
    pdb.gimp_context_set_foreground(original_foreground)
    pdb.gimp_selection_none(image)

    # Close the undo group.
    pdb.gimp_undo_push_group_end(image)


def palette_swap(image, layer_orig, layer_sample, include_transparent, light_first):
    """
    """
    gimp.progress_init(
        "Swapping palette from " + layer_orig.name + " onto " + layer_orig.name + "..."
    )

    # Remember current foreground
    original_foreground = pdb.gimp_context_get_foreground()

    # Set up an undo group, so the operation will be undone in one step.
    pdb.gimp_undo_push_group_start(image)

    # Extract the palettes.

    
    gimp.progress_init("Finding " + str(layer_sample.name)+ " palette...")
    
    if layer_sample.height == 1:
        sorted_palette_new = extract_linear_palette(
            layer=layer_sample, current_progress=0, progress_fraction=0.4
        ) 
    else:
        sorted_palette_new = extract_sorted_palette(
            layer=layer_sample, include_transparent=include_transparent,
            current_progress=0, progress_fraction=0.4
        )     

    gimp.progress_init("Finding " + str(layer_orig.name)+ " palette...")

    sorted_palette_old = extract_sorted_palette(
        layer=layer_orig, include_transparent=include_transparent,
        current_progress=0.4, progress_fraction=0.4    
    )
    
    if light_first:
        sorted_palette_old.reverse()
        sorted_palette_new.reverse()

    apply_palette_map(
        image=image, layer=layer_orig,
        sorted_palette_old=sorted_palette_old, 
        sorted_palette_new=sorted_palette_new,
        current_progress=0.8, progress_fraction=0.2
    )

    # Return original foreground colour
    pdb.gimp_context_set_foreground(original_foreground)
    pdb.gimp_selection_none(image)

    # Close the undo group.
    pdb.gimp_undo_push_group_end(image)


register(
    "python_fu_palette_swap",
    "Given an image, ranks the brightness of colours in it, ranks colours in the current layer, and replaces colours in the current layer with their equivalent rank in the sample.",
    "Given an image, ranks the brightness of colours in it, ranks colours in the current layer, and replaces colours in the current layer with their equivalent rank in the sample.",
    "Sam Mangham",
    "Sam Mangham",
    "2023",
    "Palette Swap...",
    "RGB*",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
        (PF_IMAGE, "image",       "Input image", None),
        (PF_DRAWABLE, "layer_old", "Layer to recolour.", None),
        (PF_DRAWABLE, "layer_new", "Layer to sample colours from.\nShould be 1 pixel high, and light to dark.", None),
        (PF_BOOL,  "include_transparent",   "Whether or not to sample colours from transparent pixels.",   True),
        (PF_BOOL,  "light_first",   "Go from the lightest to darkest instead.\nNo effect if both have the same number of colours.",   False)
    ],
    [],
    palette_swap, menu="<Image>/Colors/Map")


register(
    "python_fu_palette_swap_linear",
    "Given a 1-pixel-high palette going from light to dark to map from, and another to map to, applies that map to the current layer.",
    "Given a 1-pixel-high palette going from light to dark to map from, and another to map to, applies that map to the current layer.",
    "Sam Mangham",
    "Sam Mangham",
    "2023",
    "Palette Swap subset...",
    "RGB*",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
        (PF_IMAGE, "image",       "Input image", None),
        (PF_DRAWABLE, "layer_old", "Layer to recolour.", None),
        (PF_DRAWABLE, "layer_palette", "Palette to replace for the current layer.\nShould be 1-pixel high, and light to dark.", None),
        (PF_DRAWABLE, "layer_new", "Layer to sample colours from.\nShould be 1-pixel-high, and light to dark.", None),
        (PF_BOOL,  "include_transparent",   "Whether or not to sample colours from transparent pixels.",   True),
        (PF_BOOL,  "light_first",   "Go from the lightest to darkest instead.\nNo effect if both have the same number of colours.",   False)
    ],
    [],
    palette_swap_linear, menu="<Image>/Colors/Map")

main()