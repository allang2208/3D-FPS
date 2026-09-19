import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
ob=bpy.data.objects['SM_BalancedRearGrip']
body={v for p in ob.data.polygons if 'Collar' not in ob.data.materials[p.material_index].name for v in p.vertices}
# Gun-root forward is -Y. Keep the receiver-derived collar anchored to the rifle.
for i in body:ob.data.vertices[i].co.y-=.005
bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(O/'SM_BalancedRearGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Editable.blend'))
(O/'adjustment.json').write_text(json.dumps({'family':'M4','part':'balanced_reargrip','body_translation_m':[0,-.005,0],'receiver_collar_translation_m':[0,0,0],'source':'../Editable.blend','game_tested':False},indent=2))
print('M4_BALANCED_FORWARD_FIT_EXPORTED',flush=True)
