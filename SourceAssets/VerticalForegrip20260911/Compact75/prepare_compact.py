import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'TightGrip/A_M4_Vertical_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
f=json.loads((O.parent/'TightGrip/fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);old=G.copy();G.translation+=G.to_3x3()@Vector((0,0,.0007));ob=next(o for o in s.objects if o.name.startswith('VG_'));world=ob.matrix_world.copy();before=np.array([list(old.inverted()@world@v.co) for v in ob.data.vertices]);after=before*.75
for v,p in zip(ob.data.vertices,after):v.co=world.inverted()@G@Vector(p)
ob.parent=None;ob.matrix_world=world
f['grip_matrix']=[list(row) for row in G];f['grip_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@G]
(O/'fit_final.json').write_text(json.dumps(f,indent=2));(O/'model_scale.json').write_text(json.dumps({'before_m':np.ptp(before,axis=0).tolist(),'after_m':np.ptp(after,axis=0).tolist(),'ratio':(np.ptp(after,axis=0)/np.ptp(before,axis=0)).tolist(),'mount_raise_m':.0007},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
import shutil
shutil.copy2(O/'M4_Vertical_Fitted.blend',O/'Compact_Baseline.blend');shutil.copy2(O/'fit_final.json',O/'fit_baseline.json')
# Export in the unchanged runtime mount frame; measured seating offset is in mesh vertices.
mesh=ob.data.copy();static=bpy.data.objects.new('SM_VerticalForegrip',mesh);s.collection.objects.link(static)
for v,p in zip(mesh.vertices,after):v.co=Vector(p)+Vector((0,0,.0007))
bpy.ops.object.select_all(action='DESELECT');static.select_set(True);bpy.context.view_layer.objects.active=static
bpy.ops.export_scene.fbx(filepath=str(O/'SM_VerticalForegrip.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)


