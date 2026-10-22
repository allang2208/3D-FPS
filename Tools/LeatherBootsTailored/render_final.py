"""Refresh the final beauty view and icon after the vertex-finish range correction."""
import importlib.util,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
spec=importlib.util.spec_from_file_location('boot_review',Path(__file__).with_name('export_render.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
bpy.ops.wm.open_mainfile(filepath=str(R/'LeatherBoots_Continuous_Editable.blend'));source=next(o for o in bpy.data.objects if o.type=='MESH');mats=list(source.data.materials);source.hide_render=True;ob=m.make(read(R/'Authored/ue_leather_boots/Jason.json'),'Final_Boot',mats,left=True);ob.location.x=-.15
scene,cam,point=m.setup();cam.location=(.75,-1.2,.36);point(cam,(.015,-.07,.18));cam.data.ortho_scale=.48;scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.render.filepath=str(R/'Review/Boots_Detail.png');bpy.ops.render.render(write_still=True)
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA';scene.render.resolution_x=512;scene.render.resolution_y=768;scene.render.filepath=str(R/'ue_leather_boots.png');bpy.ops.render.render(write_still=True)
print('TAILORED_BOOT_FINAL_VIEW_REFRESHED',flush=True)
