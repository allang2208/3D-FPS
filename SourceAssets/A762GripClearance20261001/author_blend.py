"""Apply the same local edit to the editable R08 source and export Phantom."""
import bpy,sys,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O));from author import deform
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'A762ReceiverGrip20261001/A762_ReceiverGrip08.blend'))
bpy.context.preferences.filepaths.save_version=0
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 if ob.name!='Body_ContinuousGrip08' and ob.get('target')!='phantom_reargrip':continue
 me=ob.data;co=np.array([tuple(v.co) for v in me.vertices]);li=np.array([l.vertex_index for l in me.loops]);ns=np.array([tuple(n.vector) for n in me.corner_normals])
 newco=deform(co);_,newns=deform(co[li],ns)
 me.vertices.foreach_set('co',newco.astype(np.float32).ravel());me.update();me.normals_split_custom_set(newns)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_GripClearance09.blend'))
bpy.ops.object.select_all(action='DESELECT');objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.get('target')=='phantom_reargrip']
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_A762_phantom_reargrip_R09.fbx'),use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
print('A762_CLEARANCE_EDITABLE_SAVED',flush=True)
