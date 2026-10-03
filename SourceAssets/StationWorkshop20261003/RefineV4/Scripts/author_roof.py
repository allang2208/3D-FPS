"""One roof slab fitted to the accepted office walls. No scene render or tests."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
sys.path.insert(0,str(PARENT/'Scripts'))
import geometry as g
g.OUT=ROOT/'Authored';g.OUT.mkdir(parents=True,exist_ok=True)
g.BASE='/Game/Dungeons/StationWorkshop20261003/RefineV4'
g.MAP['Concrete']='/Game/Dungeons/StationWorkshop20261003/RefineV3/Materials/M_Workshop_FlatConcrete'
# Wall centres span UE X 0..1000 and Y 0..700; thickness is 14 cm.
# Keep the bottom exactly at the wall top, with all slab thickness above it.
center=(5,-3.5,3.28);size=(10.14,7.14,.16)
g.box(center,size,'Concrete',0)
roof=g.emit('SM_SW_Roof_FittedV4',hulls=[(center,size)]);roof.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(g.OUT/'StationWorkshop_RoofFittedV4.blend'))
(g.OUT/'manifest.json').write_text(json.dumps(dict(objects=g.records,revision=4,
    wall_outer_bounds_cm=dict(min=[-7,-7,0],max=[1007,707,320]),
    roof_bounds_cm=dict(min=[-7,-7,320],max=[1007,707,336]),tests_run=False,rendered=False),indent=2),encoding='utf8')
print('STATION_ROOF_FITTED_V4_AUTHORED',flush=True)
