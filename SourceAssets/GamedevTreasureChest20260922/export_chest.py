"""Export the original gamedev chest with a rigid rear-hinge rig; no render or test."""
import bpy, json, math, shutil
from pathlib import Path
from mathutils import Vector, Matrix

HERE=Path(__file__).parent
OUT=HERE/'Authored'; OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
PACK=SOURCE/'tools/ai-gen/_settlement_building_pack_20260821'
for state in ('closed','open'):
    name=f'dungeon_chest_{state}'
    shutil.copy2(PACK/name/(name+'_model.blend'),OUT/(name+'_original.blend'))
    shutil.copy2(SOURCE/'assets/terrain'/('chest_closed.png' if state=='closed' else 'chest_opened.png'),HERE/(state+'_reference.png'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'dungeon_chest_open_original.blend'))
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=.01
scene.render.fps=30
hinge=bpy.data.objects['DungeonChest_RearHingePivot']; root=hinge.parent
source_angle=hinge.rotation_euler.x
inverse=root.matrix_world.inverted()
source_hinge=inverse @ hinge.matrix_world.translation
hinge.rotation_euler.x=0
bpy.context.view_layer.update()
source_objects=[o for o in scene.objects if o.name.startswith('DungeonChest_') and o.type in {'MESH','CURVE'}]
source_records=[]
SCALE=.65  # Compact treasure prop; separate from the full-size ritual warehouse chest.
def mapped(p): return Vector((-p.y*SCALE,p.x*SCALE,p.z*SCALE))
hinge_point=mapped(source_hinge)
recipes={'Treasure_BlackIron':((.055,.052,.048),.76,.43),
         'Treasure_AntiqueGold':((.48,.30,.10),.88,.32),
         'Treasure_Interior':((.009,.011,.013),.08,.86)}
materials={}
for name,(color,metal,rough) in recipes.items():
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    materials[name]=m
parts=[];dg=bpy.context.evaluated_depsgraph_get()
for original in source_objects:
    lid=False;ancestor=original.parent
    while ancestor:
        if ancestor==hinge:lid=True;break
        ancestor=ancestor.parent
    for mod in original.modifiers:
        if mod.type=='BEVEL':mod.segments=max(3,mod.segments)
    dg.update();evaluated=original.evaluated_get(dg)
    mesh=bpy.data.meshes.new_from_object(evaluated,depsgraph=dg)
    transform=inverse @ original.matrix_world
    for v in mesh.vertices:v.co=mapped(transform @ v.co)
    old_names=[s.material.name if s.material else '' for s in original.material_slots]
    name='Treasure_AntiqueGold' if any('Brass' in n for n in old_names) else 'Treasure_BlackIron'
    if any(n in original.name for n in ('Interior','Lining','Keyhole')):name='Treasure_Interior'
    mesh.materials.clear();mesh.materials.append(materials[name]);mesh.update()
    while mesh.uv_layers:mesh.uv_layers.remove(mesh.uv_layers[0])
    uv=mesh.uv_layers.new(name='UV0_Physical')
    for polygon in mesh.polygons:
        polygon.material_index=0
        axis=max(range(3),key=lambda i:abs(polygon.normal[i]))
        for li in polygon.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co/100
            uv.data[li].uv=(p.y,p.z) if axis==0 else (p.x,p.z) if axis==1 else (p.x,p.y)
    obj=bpy.data.objects.new(original.name+'_UE',mesh);scene.collection.objects.link(obj)
    group=obj.vertex_groups.new(name='Lid' if lid else 'Root');group.add(list(range(len(mesh.vertices))),1.0,'REPLACE')
    parts.append(obj)
    source_records.append(dict(source=original.name,bone=group.name,material=name,vertices=len(mesh.vertices)))
for o in list(scene.objects):
    if o not in parts:bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for p in parts:p.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh_object=bpy.context.object;mesh_object.name='SK_GamedevTreasureChest'
scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tri=mesh_object.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
arm_data=bpy.data.armatures.new('GamedevTreasureChestRig');arm=bpy.data.objects.new('GamedevTreasureChestRig',arm_data);scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;mesh_object.select_set(False);arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root_bone=arm_data.edit_bones.new('Root');root_bone.head=(0,0,0);root_bone.tail=(0,0,10)
lid_bone=arm_data.edit_bones.new('Lid');lid_bone.head=hinge_point;lid_bone.tail=hinge_point+Vector((0,0,10));lid_bone.parent=root_bone
bpy.ops.object.mode_set(mode='OBJECT')
mesh_object.parent=arm;mod=mesh_object.modifiers.new('RigidHinge','ARMATURE');mod.object=arm
pb=arm.pose.bones['Lid'];pb.rotation_mode='QUATERNION'
# The source hinge rotates about source X, which maps to our +Y axis.
lid_axis=arm_data.bones['Lid'].matrix_local.to_3x3().inverted() @ Vector((0,1,0))
from mathutils import Quaternion
pose_rotation=Quaternion(lid_axis,source_angle)

def select_rig():
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh_object.select_set(True);bpy.context.view_layer.objects.active=arm
def export_rig(name,animated=False):
    select_rig()
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,
        bake_anim=animated,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.0)
export_rig('SK_GamedevTreasureChest')
for name,rotation in [('A_TreasureChest_ClosedPose',Quaternion()),('A_TreasureChest_OpenPose',pose_rotation)]:
    arm.animation_data_clear();pb.rotation_quaternion=rotation
    for frame in (1,2):pb.keyframe_insert(data_path='rotation_quaternion',frame=frame)
    arm.animation_data.action.name=name;scene.frame_start=1;scene.frame_end=2;scene.frame_set(1)
    export_rig(name,True)
arm.animation_data_clear();pb.rotation_quaternion=Quaternion();scene.frame_set(1);bpy.context.view_layer.update()
closed_points=[v.co.copy() for v in mesh_object.data.vertices]
mins=[min(p[i] for p in closed_points) for i in range(3)];maxs=[max(p[i] for p in closed_points) for i in range(3)]
for name,rotation in [('SM_TreasureChest_Closed',Quaternion()),('SM_TreasureChest_Open',pose_rotation)]:
    pb.rotation_quaternion=rotation;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    static_mesh=bpy.data.meshes.new_from_object(mesh_object.evaluated_get(dg),depsgraph=dg)
    static=bpy.data.objects.new(name,static_mesh);scene.collection.objects.link(static)
    bpy.ops.object.select_all(action='DESELECT');static.select_set(True);bpy.context.view_layer.objects.active=static
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        mesh_smooth_type='FACE',bake_anim=False)
    bpy.data.objects.remove(static,do_unlink=True)
pb.rotation_quaternion=Quaternion();select_rig();bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GamedevTreasureChest_UE.blend'))
manifest=dict(source=str(PACK),source_open_degrees=abs(math.degrees(source_angle)),scale_from_original=SCALE,
    unit='cm',forward='+X',triangles=len(mesh_object.data.polygons),bounds_min=mins,bounds_max=maxs,
    collision_extent=[(b-a)/2 for a,b in zip(mins,maxs)],collision_center=[(a+b)/2 for a,b in zip(mins,maxs)],
    components=source_records,pose_clips='Two endpoint poses, not a recreated opening animation',rendered=False,tested=False)
(HERE/'export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('TREASURE_CHEST_EXPORTED '+json.dumps({k:v for k,v in manifest.items() if k!='components'}))
