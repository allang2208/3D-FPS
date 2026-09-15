"""Adapt owned Epic projectile geometry into a pointed 54 cm ice spear; no render."""
import bpy,math
from pathlib import Path
from mathutils import Vector
p=Path('D:/FPS3D/FPSGAME/SourceAssets/IceSpike20260915')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(p/'SM_SimpleProjectile.fbx'))
ob=next(o for o in bpy.data.objects if o.type=='MESH')
coords=[ob.matrix_world@v.co for v in ob.data.vertices]
ob.matrix_world.identity()
for v,c in zip(ob.data.vertices,coords):
    x,y,z=c;angle=math.atan2(z,y)
    if x<.01:
        nx=-.27;scale=3.2
    elif x<.025:
        nx=-.12;scale=6.1*(1+.085*math.sin(angle*3+.7))
    else:
        nx=.27;scale=.055
    v.co=Vector((nx,y*scale,z*scale*.90))
for f in ob.data.polygons:f.use_smooth=False
ob.name='SM_IceSpike';ob.data.name='IceSpikeAdaptedMesh'
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.wm.save_as_mainfile(filepath=str(p/'IceSpike.blend'))
bpy.ops.export_scene.fbx(filepath=str(p/'SM_IceSpike.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
