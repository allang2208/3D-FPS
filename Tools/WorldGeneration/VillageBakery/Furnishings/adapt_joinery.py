"""Bakery variants of the village kitchen station's timber, tenons and forged hooks."""
from pathlib import Path
import math
import sys

import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'SourceAssets/HillsVillageBakery/Furnishings'
sys.path.insert(0, str(HERE.parents[1]/'VillageTavern/KitchenStations'))
from geometry import Station, X, Y, Z

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
for name in ('Oak', 'OiledOak', 'Sawn', 'Endgrain', 'Iron'):
    bpy.data.materials.new(name)

# Bread rests on these raised slats; the gaps ventilate its underside. Carry
# holes are cut into the side rails by splitting them around their openings.
tray = Station('BreadBoard', 63031)
tray.name = 'SM_BakeryCoolingBoard'
for x in (-22, 22):
    tray.box((x, 0, .9), (4.2, 35., 1.8), 'Oak', .23)
for i in range(13):
    x = (i-6)*4.85
    tray.box((x, 0, 2.9), (4.18, 35.5, 2.2), 'Sawn', .28)
    for y in (-14.1, 14.1):
        tray.turned((x, y, 3.94),(x, y, 4.02),[(0, .34),(1,.32)],'Endgrain',8)
for side in (-1, 1):
    x = side*31.95
    tray.box((x,0,2.9),(2.55,36.5,2.1),'OiledOak',.27)
    for y in (-12.5,12.5):
        tray.box((x,y,4.65),(2.55,11.5,2.0),'OiledOak',.32)
    tray.box((x,0,6.3),(2.55,36.5,1.4),'OiledOak',.29)
tray.export(OUT,(0,0,0))

# A narrow peg rail with two individual bent hooks and a split-back hanging
# cleat carries the peel on the wall. The peel's thin leading edge points down.
peel = Station('HearthPeel', 91352)
peel.name = 'SM_BakeryPeelHanger'
peel.box((1.0,0,124.), (3.5,42.,10.), 'Oak', .38)
peel.box((1.0,0,46.), (3.5,25.,5.), 'Oak', .24)
for y in (-16.5,16.5):
    peel.turned((2.6,y,124.),(3.4,y,124.),[(0,.93),(.55,1.12),(1,.62)],'Iron',9)
for y in (-3.1,3.1):
    peel.tube([(2.4,y,123.),(5.5,y,123.),(10.,y,124.2),(11.,y,125.8)],.67,'Iron')
peel.turned((7.3,0,39.), (7.3,0,164.),
            [(0,2.0),(.025,2.7),(.10,2.4),(.67,1.55),(.92,1.83),(.965,2.6),(1,1.75)],
            'Sawn',18)
# Four facets per section give the shaved blade a crowned spine, tapered into
# the throat. The square mortise lets the shaft enter the face of this blank.
sections = [(0,8.3,.34,.56),(2.1,14.8,.45,.74),(5.,16.4,.58,1.03),
            (19.,16.0,.72,1.52),(29.,13.1,.82,1.8),(35.,7.2,.95,2.0),(44.,2.3,1.26,2.05)]
rings = [[(7.3,-w,z),(7.3+edge,w*-.87,z),(7.3+mid,0,z),
          (7.3+edge,w*.87,z),(7.3,w,z),(7.3-edge*.62,w*.87,z),
          (7.3-mid*.68,0,z),(7.3-edge*.62,-w*.87,z)] for z,w,edge,mid in sections]
peel.rings(rings,'Sawn',Z,.09,False)
for z in (33.5,37.2):
    peel.turned((7.2,0,z),(9.15,0,z),[(0,.56),(1,.52)],'Endgrain',10)
# A recessed oak peg sits between the outer hooks and stops the handle rolling.
peel.turned((2.7,0,46.),(5.8,0,46.),[(0,1.1),(1,1.05)],'Endgrain',12)
# A cut notch at the upper haft sits over the two fingers of the iron fork.
for side in (-1,1):
    peel.beam((7.3,side*1.2,129.),(7.3,side*4.6,125.),1.8,2.7,'Sawn',.20)
peel.export(OUT,(2.2,0,0))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BakeryJoinery.blend'))
