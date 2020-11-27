"""
Color definitions for Facet color scheme.
"""

import logging
from typing import Tuple

from matplotlib.colors import LinearSegmentedColormap, to_rgba

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "RgbaColor",
    "RGBA_BLACK",
    "RGBA_WHITE",
    "RGBA_DARK_GREY",
    "RGBA_GREY",
    "RGBA_DARK_BLUE",
    "RGBA_LIGHT_BLUE",
    "RGBA_LIGHT_GREEN",
    "COLORMAP_FACET",
    "text_contrast_color",
]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Type definitions
#

#: RGBA color type for use in ``MatplotStyle`` classes
RgbaColor = Tuple[float, float, float, float]


#
# Constants
#

# color constants

#: black
RGBA_BLACK: RgbaColor = to_rgba("black")

#: white
RGBA_WHITE: RgbaColor = to_rgba("white")

#: Facet dark grey
RGBA_DARK_GREY: RgbaColor = to_rgba("#3d3a40")

#: Facet grey
RGBA_GREY: RgbaColor = to_rgba("#9a9a9a")

#: Facet dark blue
RGBA_DARK_BLUE: RgbaColor = to_rgba("#295e7e")

#: Facet blue
RGBA_LIGHT_BLUE: RgbaColor = to_rgba("#30c1d7")

#: Facet green
RGBA_LIGHT_GREEN: RgbaColor = to_rgba("#43fda2")

_COLOR_CONFIDENCE = "#295e7e"
_COLOR_MEDIAN_UPLIFT = "#30c1d7"


#: standard colormap for Facet
COLORMAP_FACET = LinearSegmentedColormap.from_list(
    name="facet",
    colors=[
        (0, RGBA_DARK_GREY),
        (0.25, RGBA_DARK_BLUE),
        (0.65, RGBA_LIGHT_BLUE),
        (1.0, RGBA_LIGHT_GREEN),
    ],
)


#
# Functions
#


def text_contrast_color(bg_color: RgbaColor) -> RgbaColor:
    """
    Get a text color that maximises contrast with the given background color.

    Returns white for background luminance < 50%, and black otherwise.
    The alpha channel of the text color is the same as the background color's.

    :param bg_color: RGBA encoded background color
    :return: the contrasting text color
    """
    fill_luminance = sum(bg_color[:3]) / 3
    text_color = RGBA_WHITE if fill_luminance < 0.5 else RGBA_BLACK
    if len(bg_color) > 3:
        text_color = (*text_color[:3], bg_color[3])
    return text_color


# check consistency of __all__

__tracker.validate()
