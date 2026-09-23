"""Separate the existing PKM wood/metal carry assembly into a rigid hinge bone."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'Accessories14/PKM_Modular_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
gun=r.data.bones['WPN_root'].matrix_local@fit
# Midpoint of the two source edges at the stem's narrow mounting end.
# The 28.596 mm straight mount runs along the barrel (source Y).
hinge=Vector(((.017711263+.020493)/2,(-.076371-.104967)/2,(.061686+.058370948)/2))
source=json.loads((O/'source_geometry.json').read_text())
wood=[Vector(v) for v in source['136']['points']]
center=sum(wood,Vector())/len(wood)
lever=center-hinge;lever.y=0
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.object.mode_set(mode='EDIT')
bone=r.data.edit_bones.new('PKM_CarryHandle');bone.parent=r.data.edit_bones['WPN_root'];bone.use_connect=False
bone.head=gun@hinge;bone.tail=bone.head+gun.to_3x3()@Vector((0,.03,0));bone.align_roll(gun.to_3x3()@Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
for idx in [75,136]:
    ob=bpy.data.objects[f'PKM_Part_{idx:03}']
    ob.vertex_groups.clear();group=ob.vertex_groups.new(name='PKM_CarryHandle')
    group.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
    ob['mechanical_bone']='PKM_CarryHandle'
    ob['carry_handle_part']='metal_stem' if idx==75 else 'wood_grip'
# Animation tracks remain independent; existing clips inherit this new rest bone.
r.data.pose_position='POSE';bpy.context.view_layer.update()
E=O/'Exports';E.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Belt08'));from mesh_export import export_mesh
export_mesh(r,E/'SK_PKM_Manny_Modular.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_CarryHandle_Editable.blend'))
report={'source':'Accessories14/PKM_Modular_Editable.blend','moving_parts':[75,136],
 'bone':'PKM_CarryHandle','parent':'WPN_root','hinge_gun_m':list(hinge),
 'axis_gun':[0,1,0],'mass_center_gun_m':list(center),'lever_root_ue_cm':[lever.x*100,0,lever.z*100],
 'mesh_asset':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
 'existing_animation_tracks_changed':False,'existing_materials_uv_normals_preserved':True}
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('PKM18_HANDLE_AUTHORED',json.dumps(report),flush=True)
