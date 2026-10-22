"""Requested extreme ankle/toe visual review using the checked native skin result."""
import importlib.util,sys
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
spec=importlib.util.spec_from_file_location('boot_review',Path(__file__).with_name('export_render.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
bpy.ops.wm.open_mainfile(filepath=str(R/'LeatherBoots_Continuous_Editable.blend'))
source=next(o for o in bpy.data.objects if o.type=='MESH');mats=list(source.data.materials);source.hide_render=True
d=read(R/'Authored/ue_leather_boots/Jason.json');d['positions']=np.load(R/'Review/posed_boot_positions.npy').tolist()
ob=m.make(d,'Checked_30deg_ankle_55deg_toe',mats,left=True);ob.location.x=-.15
# Deformed normals are calculated from the posed mesh for this review only.
ob.data.normals_split_custom_set([(0,0,0)]*len(ob.data.loops));ob.data.set_sharp_from_angle(angle=.85)
scene,cam,point=m.setup();scene.cycles.samples=64;scene.render.resolution_x=1300;scene.render.resolution_y=1100;cam.location=(.75,-.6,.35);point(cam,(.015,-.025,.17));cam.data.ortho_scale=.50;scene.render.filepath=str(R/'Review/Ankle_Toe_Flex_Check.png');bpy.ops.render.render(write_still=True)
print('LEATHER_BOOT_FLEX_REVIEW_RENDERED',flush=True)
