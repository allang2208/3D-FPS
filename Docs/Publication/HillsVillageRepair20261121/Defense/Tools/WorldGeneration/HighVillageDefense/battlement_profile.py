"""Centimetre profile for the existing 3 m Meshy wall bay in Unreal's X/Z basis."""

import numpy as np


# Measured inside faces of the source merlons. The two 40 cm end returns
# make one 80 cm merlon when either end is snapped to its neighbour.
SOURCE_X = (-150., -83.5, -32.25, 0., 32.25, 83.5, 150.)
FINISHED_X = (-150., -110., -40., 0., 40., 110., 150.)
MERLONS = ((-150., -110.), (-40., 40.), (110., 150.))


def fit_crest_x(x, z):
    # Fade through the solid sill. The entire walk, both joint planes and all
    # vertices below the walk retain their positions, including fractured faces.
    blend = np.clip((z - 360.) / 33., 0., 1.)
    blend = blend * blend * (3. - 2. * blend)
    target = np.interp(x, SOURCE_X, FINISHED_X)
    return x + (target - x) * blend
