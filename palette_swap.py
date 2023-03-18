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
    layer, include_transparent, count_threshold,
    current_progress, progress_fraction,
):
    """
    Extracts a palette from an image, by finding the discrete RGB values
    and then sorting them by total R+G+B value.
    """
    palette_counts = {}
    
    region = layer.get_pixel_rgn(
        0, 0, layer.width, layer.height
    )
    progress_step = progress_fraction / layer.height

    for index_row in range(0, layer.height):
        for pixel in RowIterator(region[0:layer.width, index_row], layer.bpp):
            colour_rgb = pixel[0:3]

            if layer.has_alpha and pixel[3] == 0 and not include_transparent:
                continue

            elif colour_rgb not in palette_counts:
                palette_counts[colour_rgb] = 1

            else:
                palette_counts[colour_rgb] += 1

        gimp.progress_update(current_progress + progress_step * index_row)

    # Now we've counted all the pixel colours, discard outliers and sort
    palette = {}
    for colour_rgb, colour_count in palette_counts.items():
        colour_sum = sum(colour_rgb)

        if colour_count > count_threshold:
            if colour_sum in palette:
                if colour_rgb != palette[colour_sum]:
                    colour_duplicate = palette[colour_sum]
                    raise KeyError(
                        "Multiple colours in layer with same total RGB values: " + \
                        str(colour_rgb) + "(" + str(colour_count) + " pixels) and " + \
                        str(colour_duplicate) + "(" + str(palette_counts[colour_duplicate]) + " pixels). "
                        "Cannot automatically sort colours by brightness. " + \
                        "Try increasing the 'ignore colours with less than this many pixels' setting " + \
                        "to drop stray pixels."
                    )
            else:
                palette[colour_sum] = colour_rgb

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
    image, layer_orig, layer_palette, layer_sample
):
    """
    """
    gimp.progress_init(
        "Swapping palette from " + layer_palette.name + \
        " to " + layer_sample.name + " for " + layer_orig.name + "..."
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
        raise ValueError(
            "Sample palette is not 1-high! Use Palette to Layer to generate one."
        )

    gimp.progress_init("Finding " + str(layer_orig.name)+ " palette...")

    if layer_palette.height == 1:
        sorted_palette_old = extract_linear_palette(
            layer=layer_palette, current_progress=0.4, progress_fraction=0.4    
        ) 
    else:
        raise ValueError(
            "Sample palette is not 1-high! Use Palette to Layer to generate one."
        )

    if layer_palette.width != layer_sample.width:
        raise ValueError(
            "Palette to recolour and sample palette are different sizes."
        )

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


def palette_swap(
    image, layer_orig, layer_sample, include_transparent, light_first,
    count_threshold
):
    """
    """
    gimp.progress_init(
        "Swapping palette from " + layer_sample.name + " onto " + layer_orig.name + "..."
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
            count_threshold=count_threshold,
            current_progress=0, progress_fraction=0.4
        )     

    gimp.progress_init("Finding " + str(layer_orig.name)+ " palette...")

    sorted_palette_old = extract_sorted_palette(
        layer=layer_orig, include_transparent=include_transparent,
        count_threshold=count_threshold,
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


def palette_to_layer(
    image, layer_orig, palette_name, include_transparent, count_threshold
):
    """
    """
    gimp.progress_init(
        "Extracting palette from " + layer_orig.name + "..."
    )
    # Set up an undo group, so the operation will be undone in one step.
    pdb.gimp_undo_push_group_start(image)

    # Extract the palettes
    gimp.progress_init("Finding " + str(layer_orig.name)+ " palette...")

    sorted_palette = extract_sorted_palette(
        layer=layer_orig, include_transparent=include_transparent,
        count_threshold=count_threshold,
        current_progress=0.0, progress_fraction=1.0    
    )
    sorted_palette.reverse()


    layer_palette = pdb.gimp_layer_new(
        image, len(sorted_palette), 1, RGB_IMAGE, palette_name, 100.0, 
        LAYER_MODE_NORMAL
    )

    for column_index, colour_rgb in zip(range(0, len(sorted_palette)), sorted_palette):
        pdb.gimp_drawable_set_pixel(
            layer_palette, column_index, 0, 3, colour_rgb
        )

    pdb.gimp_image_insert_layer(image, layer_palette, None, 0)
    pdb.gimp_displays_flush()

    # Close the undo group.
    pdb.gimp_undo_push_group_end(image)


register(
    "python_fu_palette_swap",
    "Given a sample layer, ranks the brightness of colours in it, ranks colours in the current layer, and replaces colours in the current layer with their equivalent rank in the sample.",
    "Given a sample layer, ranks the brightness of colours in it, ranks colours in the current layer, and replaces colours in the current layer with their equivalent rank in the sample.",
    "Sam Mangham",
    "Sam Mangham",
    "2023",
    "Palette Swap...",
    "RGB*",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
        (PF_IMAGE, "image",       "Input image", None),
        (PF_DRAWABLE, "layer_old", "Layer to recolour.", None),
        (PF_DRAWABLE, "layer_new", "Layer to sample colours from.", None),
        (PF_BOOL,  "include_transparent",   "Whether or not to sample colours from transparent pixels.",   True),
        (PF_BOOL,  "light_first",   "Go from the lightest to darkest instead.\nNo effect if both have the same number of colours.",   False),
        (PF_INT, "count_threshold", "Ignore colours with less than this many pixels.", 0)
    ],
    [],
    palette_swap, menu="<Image>/Colors/Map")


register(
    "python_fu_palette_swap_linear",
    "Given two 1-pixel high layers, creates a map from the colours in one to the other, and applies it to the current layer.",
    "Given two 1-pixel high layers, creates a map from the colours in one to the other, and applies it to the current layer.",
    "Sam Mangham",
    "Sam Mangham",
    "2023",
    "Palette Swap Precise...",
    "RGB*",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
        (PF_IMAGE, "image",       "Input image", None),
        (PF_DRAWABLE, "layer_old", "Layer to recolour.", None),
        (PF_DRAWABLE, "layer_palette", "Palette to replace for the current layer.\nShould be 1-pixel high, and light to dark.", None),
        (PF_DRAWABLE, "layer_new", "Palette to replace colours with.\nShould be 1-pixel-high, and light to dark.", None),
    ],
    [],
    palette_swap_linear, menu="<Image>/Colors/Map")


register(
    "python_fu_palette_to_layer",
    "Given a layer, creates a 1-pixel high layer that contains the colours within it, sorted by RGB value.",
    "Given a layer, creates a 1-pixel high layer that contains the colours within it, sorted by RGB value.",
    "Sam Mangham",
    "Sam Mangham",
    "2023",
    "Palette to Layer...",
    "RGB*",      # Alternately use RGB, RGB*, GRAY*, INDEXED etc.
    [
        (PF_IMAGE, "image",       "Input image", None),
        (PF_DRAWABLE, "layer_old", "Layer to extract palette from.", None),
        (PF_STRING, "palette_name", "Palette layer name", "Palette"),
        (PF_BOOL,  "include_transparent",   "Whether or not to sample colours from transparent pixels.",   True),
        (PF_INT, "count_threshold", "Ignore colours with less than this many pixels.", 0)
    ],
    [],
    palette_to_layer, menu="<Image>/Colors/Map")


main()