"""Prepare unchanged target skin and clean donor clips for native UE IK retargeting."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).parent
OUT=ROOT/'prepared'; OUT.mkdir(exist_ok=True)
scene=bpy.context.scene
scene.render.fps=30
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0

def clear():
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)
    for act in list(bpy.data.actions): bpy.data.actions.remove(act)

def activate(rig,action):
    rig.animation_data_create(); rig.animation_data.action=action
    if action and len(action.slots): rig.animation_data.action_slot=action.slots[0]
    for tr in rig.animation_data.nla_tracks: tr.mute=True

def export(path, rig, meshes, animated=False):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes: ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,
        object_types={'ARMATURE','MESH'},use_mesh_modifiers=True,
        add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=animated,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',
        path_mode='STRIP',embed_textures=False)

def metadata(rig,meshes):
    return {'object_matrix':[list(r) for r in rig.matrix_world],
        'bones':{b.name:{'parent':b.parent.name if b.parent else None,
                       'head':list(rig.matrix_world@b.head_local),
                       'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones},
        'meshes':[{'name':o.name,'vertices':len(o.data.vertices),
                   'materials':[m.name if m else '' for m in o.data.materials],
                   'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box]} for o in meshes]}

clear()
fbx=next((ROOT/'sources/meshy').glob('*.fbx'))
bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
rig.name='FatZombieRoot'
activate(rig,None)
for b in rig.pose.bones: b.matrix_basis=Matrix.Identity(4)
scene.frame_set(0); bpy.context.view_layer.update()
meta={'target':metadata(rig,meshes)}
export(OUT/'SK_FatZombie_Meshy.fbx',rig,meshes)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'FatZombie_Meshy_Source.blend'))

selected={'Zombie_Idle':'Idle','Zombie_Walk':'Walk','Zombie_Scratch':'Attack','Death_D':'Death'}
clear()
bpy.ops.import_scene.gltf(filepath=str(ROOT/'sources/human-base-animations.glb'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); rig.name='M2MRoot'
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
actions={}
for a in bpy.data.actions:
    for source,role in selected.items():
        if a.name==source or a.name.startswith(source+'_') or a.name.endswith('|'+source): actions[role]=a
if len(actions)!=4: raise RuntimeError('Donor action selection failed: '+str([a.name for a in bpy.data.actions]))
activate(rig,None)
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene.frame_set(0);bpy.context.view_layer.update()
meta['donor']=metadata(rig,meshes)
export(OUT/'SK_M2M_Source.fbx',rig,meshes)
meta['clips']={}
for source,role in selected.items():
    action=actions[role]; activate(rig,action)
    first,last=action.frame_range;scene.frame_start=round(first);scene.frame_end=round(last)
    # Export source timing untouched. UE produces separate final candidate sequences.
    export(OUT/('A_M2M_'+role+'.fbx'),rig,[],True)
    meta['clips'][role]={'source':source,'frames':[first,last],'fps':scene.render.fps,
                          'seconds':(last-first)/scene.render.fps,'loop':role in ['Idle','Walk']}
activate(rig,actions['Idle']); scene.frame_start=0; scene.frame_end=round(actions['Idle'].frame_range[1]);scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M2M_SelectedSources.blend'))
(ROOT/'authoring_inputs.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('FAT_ZOMBIE_PREPARED '+json.dumps({'target_bones':len(meta['target']['bones']),
    'source_bones':list(meta['donor']['bones']),'target_meshes':meta['target']['meshes'],'clips':meta['clips']}))
