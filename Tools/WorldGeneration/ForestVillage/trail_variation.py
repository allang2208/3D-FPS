"""Deterministic curves and signed road paint, in world metres."""
import numpy as np
from scipy.interpolate import PchipInterpolator


def fade(a, b, value):
    t = np.clip((value-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)


def stations(xy):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]


def bends(along, seed, spacing, amplitude):
    rng = np.random.default_rng(seed)
    knots = [0.]
    while knots[-1] < along[-1]:
        knots.append(knots[-1] + rng.uniform(.78, 1.25)*spacing)
    side = rng.choice([-1., 1.]) * (-1.)**np.arange(len(knots))
    return PchipInterpolator(knots, side*rng.uniform(.45, 1.,len(knots))*amplitude)(along)


def gate_curve(xy, s):
    tangent = np.gradient(xy, axis=0)
    tangent /= np.maximum(1.e-8, np.linalg.norm(tangent, axis=1))[:,None]
    normal = np.c_[-tangent[:,1], tangent[:,0]]
    envelope = fade(30.,52.,s)*(1.-fade(s[-1]-40.,s[-1]-18.,s))
    # Pull the approach off the straight south wall. Keep the gate throat,
    # original fork and the hand-painted Landscape join in their surveyed poses.
    south_wall = fade(-6.,22.,xy[:,0])*(1.-fade(65.,82.,xy[:,0]))
    offset = bends(s, 14491, 31., 6.8)
    offset = offset*(1.-south_wall) + (offset*.75-7.2)*south_wall
    return xy + normal*(envelope*offset)[:,None]


def road_paint(xy, along, index, x, y, distance, seed):
    tangent = np.gradient(xy,axis=0)
    tangent /= np.maximum(1.e-8,np.linalg.norm(tangent,axis=1))[:,None]
    left = (y-xy[index,1])*tangent[index,0]-(x-xy[index,0])*tangent[index,1]
    # Use radial distance at the two caps so the centreline cannot paint beyond its ends.
    lateral = np.copysign(distance,left)
    widths = [2.84 + bends(along,seed+i,15.,.68) + bends(along,seed+9+i,5.5,.24) for i in range(2)]
    width = np.where(left<0,widths[0][index],widths[1][index])
    edge = 1.-fade(width-.85,width+.55,abs(lateral))
    station = along[index]
    wear = .5+.5*np.sin(station*.29+1.7*np.sin(.079*station)+lateral*.63)
    center = (1.-fade(.15,1.05,abs(lateral-.28*np.sin(.12*station))))
    return edge*(1.-.18*center*wear-.13*(1.-edge)*wear)
