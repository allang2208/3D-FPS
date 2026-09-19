"""Fit the supplied Meshy sword to the installed two-handed grip and export it.

Keeps Manny rest pose, skin weights and existing actions. No renders or tests.
"""
import bpy, json
from pathlib import Path
from mathutils import Matrix

P=Path(__file__).parent
OUT=P/'Export'
OUT.mkdir(exist_ok=True)
DONOR=P.parent/'RuneSword20260913/WristOutsideInspectV34/AzureRunesword_Manny_Editable.blend'
LOCOMOTION=P.parent/'RuneSword20260913/WeightLeftV5/AzureRunesword_Manny_Editable.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(DONOR))
scene=bpy.context.scene
rig=bpy.data.objects['SK_RuneSword_Rig']
arms=bpy.data.objects['SK_Manny_Arms_Export']
old=bpy.data.objects['RuneSword_Blade']
weapon_rest=rig.data.bones['WPN_root'].matrix_local.copy()
canonical=weapon_rest.inverted()@rig.matrix_world.inverted()@old.matrix_world
reference=[canonical@v.co for v in old.data.vertices]
tip=max(p.z for p in reference)
pommel=min(p.z for p in reference)
grip=[p for p in reference if -.15<p.z<-.06]
grip_width=max(p.x for p in grip)-min(p.x for p in grip)
grip_depth=max(p.y for p in grip)-min(p.y for p in grip)

# Append the current idle/locomotion actions; match their 240 Hz timeline to
# the 480 Hz authoring scene without changing playback duration or poses.
with bpy.data.libraries.load(str(LOCOMOTION),link=False) as (src,dst):
    dst.actions=[n for n in src.actions if n in {'A_RuneSword_Idle','A_RuneSword_Walk','A_RuneSword_Sprint'}]
for action in dst.actions:
    if not action: continue
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:
                        key.co.x*=2
                        key.handle_left.x*=2
                        key.handle_right.x*=2
    action.use_fake_user=True
for action in bpy.data.actions:
    if action.name.startswith('A_RuneSword_'):action.use_fake_user=True

for obj in list(scene.objects):
    if obj not in (rig,arms):bpy.data.objects.remove(obj,do_unlink=True)
source=next((P/'Original').rglob('*.fbx'))
before=set(scene.objects)
bpy.ops.import_scene.fbx(filepath=str(source))
sword=next(o for o in scene.objects if o not in before and o.type=='MESH')
sword.data.transform(sword.matrix_world)
sword.matrix_world=Matrix.Identity(4)
sword.name='SM_FrostCrystalSword'

# Contact datum is the crossguard, with +Z along the blade. Measurements come
# from the supplied hilt and the accepted donor grip, not overall mesh bounds.
guard_z=-.427
grip_center=(-.00092,.00118)
original_tip=max(v.co.z for v in sword.data.vertices)
original_bottom=min(v.co.z for v in sword.data.vertices)
blade_scale=tip/(original_tip-guard_z)
hilt_scale=pommel/(original_bottom-guard_z)
raw_grip=[v.co for v in sword.data.vertices if -.79<v.co.z<-.56]
radial_x=grip_width/(max(p.x for p in raw_grip)-min(p.x for p in raw_grip))
radial_y=grip_depth/(max(p.y for p in raw_grip)-min(p.y for p in raw_grip))
def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)
for vertex in sword.data.vertices:
    x,y,z=vertex.co
    blend=smooth((z+.865)/.035)*smooth((-.485-z)/.045)
    sx=blade_scale+(radial_x-blade_scale)*blend
    sy=blade_scale+(radial_y-blade_scale)*blend
    vertex.co=((x-grip_center[0])*sx,(y-grip_center[1])*sy,
               (z-guard_z)*(blade_scale if z>=guard_z else hilt_scale))

mat=bpy.data.materials.new('M_FrostCrystalSword')
mat.use_nodes=True
sword.data.materials.clear()
sword.data.materials.append(mat)
nodes=mat.node_tree.nodes
links=mat.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for suffix,socket in [('', 'Base Color'),('_normal','Normal'),('_metallic','Metallic'),('_roughness','Roughness')]:
    img=bpy.data.images.load(str(source.with_name(source.stem+suffix+'.png')),check_existing=True)
    img.colorspace_settings.name='sRGB' if not suffix else 'Non-Color'
    tex=nodes.new('ShaderNodeTexImage');tex.image=img
    if suffix=='_normal':
        normal=nodes.new('ShaderNodeNormalMap')
        links.new(tex.outputs['Color'],normal.inputs['Color'])
        links.new(normal.outputs['Normal'],bsdf.inputs[socket])
    else:links.new(tex.outputs['Color'],bsdf.inputs[socket])

def export(name,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
    bpy.ops.export_scene.fbx(filepath=str(OUT/name),use_selection=True,
        object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)

export('SM_FrostCrystalSword.fbx',[sword])
sword.data.transform(weapon_rest)
sword.parent=rig
sword.matrix_parent_inverse=Matrix.Identity(4)
group=sword.vertex_groups.new(name='WPN_root')
group.add(list(range(len(sword.data.vertices))),1.,'REPLACE')
modifier=sword.modifiers.new('Rigid weapon binding','ARMATURE');modifier.object=rig
sword.name='FrostCrystalSword_Blade'
active=rig.animation_data.action
rig.animation_data_clear()
rig.data.pose_position='REST'
export('SK_FrostCrystalSword_Manny.fbx',[arms,sword,rig])
rig.data.pose_position='POSE'
rig.animation_data_create()
idle=bpy.data.actions['A_RuneSword_Idle']
rig.animation_data.action=idle
rig.animation_data.action_slot=idle.slots[0]
scene.render.fps=480;scene.render.fps_base=1
scene.frame_start=0;scene.frame_end=round(idle.frame_range[1]);scene.frame_set(0)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrostCrystalSword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({
    'name':'寒晶·双手剑','item_id':'ue_frost_crystal_sword',
    'supplied_source':str(source),'arms_and_combat_source':str(DONOR),
    'locomotion_source':str(LOCOMOTION),'animation_fps':480,
    'grip_datum_original_z_m':guard_z,'blade_scale':blade_scale,'hilt_scale':hilt_scale,
    'grip_width_cm':grip_width*100,'grip_depth_cm':grip_depth*100,
    'blade_tip_cm':tip*100,'pommel_cm':pommel*100,
    'triangles':len(sword.data.polygons),
    'runtime_animations':'/Game/Weapons/AzureRunesword20260913',
    'actions':{a.name:{'frames':list(a.frame_range),'duration':float(a.frame_range[1]-a.frame_range[0])/480}
               for a in bpy.data.actions if a.name.startswith('A_RuneSword_')},
    'scope':'Mesh/hilt fit only; existing action curves, Manny rest, weights and combat timing retained.',
    'testing':'Not run; user will test.'
},ensure_ascii=False,indent=2),encoding='utf-8')
print('FROST_CRYSTAL_SWORD_EXPORTED',flush=True)
