import bpy,json
import numpy as np
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'HairNativeCombR9';O=R/'Authored'
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_NativeComb_R9.blend'))
for name in ['Nun_LowBun_Core_R5','Nun_LowBun_Loose_R5']:
 p=np.load(O/(name+'_points.npy'));curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=1
 ob=bpy.data.objects.new(name,curve);bpy.context.scene.collection.objects.link(ob);ob['groom_group_id']=0;ob['groom_guide']=0
 for strand in p:
  sp=curve.splines.new('POLY');sp.points.add(len(strand)-1);sp.points.foreach_set('co',np.c_[strand,np.ones(len(strand))].ravel())
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.wm.alembic_export(filepath=str(O/(name+'.abc')),start=1,end=1,selected=True,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.)
 ob.hide_render=True
 print('NATIVE_GROOM_EXPORTED',name,len(p),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_NativeComb_R9.blend'))
