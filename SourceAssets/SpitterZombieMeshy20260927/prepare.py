"""Prepare the original Meshy skin and local CC0 donor actions for native IK."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'prepared';OUT.mkdir(exist_ok=True)
PROJECT=ROOT.parents[1]
scene=bpy.context.scene
scene.render.fps=30
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def clear():
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for a in list(bpy.data.actions):bpy.data.actions.remove(a)

def active(rig,action):
    rig.animation_data_create();rig.animation_data.action=action
    if action and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True

def export(path,rig,meshes,animated=False):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=animated,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        path_mode='STRIP',embed_textures=False)

clear()
fbx=ROOT/'Meshy/rig/downloads/result_rigged_character_fbx_url.fbx'
bpy.ops.import_scene.fbx(filepath=str(fbx))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name='SpitterRoot'
meshes=[o for o in bpy.data.objects if o.type=='MESH']
active(rig,None)
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene.frame_set(0);bpy.context.view_layer.update()
report={'target_bones':{b.name:{'parent':b.parent.name if b.parent else None,
    'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones},
    'mesh_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
    'bounds':[[list(o.matrix_world@Vector(v)) for v in o.bound_box] for o in meshes],
    'donors':{}}
export(OUT/'SK_SpitterZombie.fbx',rig,meshes)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_Meshy_Source.blend'))

selections={
    'human-base-animations.glb':{'Zombie_Idle':'Idle','Zombie_Walk':'Walk','Death_D':'Death','Hit_Chest':'Stagger','Hit_Knockback':'Hit_Knockback','LayToIdle':'LayToIdle','ProneToIdle':'ProneToIdle'},
    'human-addon-animations.glb':{'Dizzy':'Dizzy'},
}
for filename,selection in selections.items():
    clear();scene.render.fps=30
    source=PROJECT/'SourceAssets/Mutant3Meshy20260915/sources'/filename
    if not source.exists():source=PROJECT/'SourceAssets/FatZombieMeshy20260913/sources'/filename
    bpy.ops.import_scene.gltf(filepath=str(source))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name='M2MRoot'
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    if not (OUT/'SK_M2M_Source.fbx').exists():
        active(rig,None)
        for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update();export(OUT/'SK_M2M_Source.fbx',rig,meshes)
    names=[a.name for a in bpy.data.actions]
    report['donors'][filename]={'file':str(source),'available_actions':names,'selected':{}}
    for name,role in selection.items():
        action=next((a for a in bpy.data.actions if a.name==name or a.name.startswith(name+'_') or a.name.endswith('|'+name)),None)
        if action is None:continue
        active(rig,action)
        first,last=action.frame_range;scene.frame_start=round(first);scene.frame_end=round(last)
        export(OUT/('A_M2M_'+role+'.fbx'),rig,[],True)
        report['donors'][filename]['selected'][role]={'name':action.name,'seconds':(last-first)/30}
    (ROOT/'authoring_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPITTER_PREPARED',report['mesh_triangles'],list(report['target_bones']),flush=True)
