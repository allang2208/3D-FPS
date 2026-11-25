"""Export one skinned mesh and one take per FBX using identical bone axes and units."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix

out = Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageStable/HorsesR7/Exchange'
jump_only = '--stable-jump' in sys.argv
if jump_only:
    out = out.parents[1]/'JumpR13'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=30
scene.unit_settings.system='METRIC'
bpy.ops.import_scene.gltf(filepath=str(out/('Warhorse_Jump.glb' if jump_only else 'Warhorse_Stable.glb')))
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH' and o.find_armature()==rig)
actions={a.name:a for a in bpy.data.actions}
rig.animation_data.use_nla=False
rig.animation_data.action=None
rig.name='Armature'
for b in rig.pose.bones: b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
args=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
          apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
          axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,path_mode='STRIP')
if not jump_only:
    bpy.ops.export_scene.fbx(filepath=str(out/'SK_StableWarhorse.fbx'),bake_anim=False,**args)
mesh.select_set(False)
clips={}
native={'idle_loop':'Idle','walk_loop':'Walk','canter_loop':'Canter','rear':'Rear'}
keys = ('HurdleJump',) if jump_only else (*native,'Q_Feed','Q_Idle','Q_IdleLook','Q_HeadLow','Q_LeadWalk')
for key in keys:
    a=actions[key]
    rig.animation_data.action=a
    rig.animation_data.action_slot=a.slots[0]
    scene.frame_start=0
    scene.frame_end=round(a.frame_range[1])
    scene.frame_set(0)
    name='A_Warhorse_'+native.get(key,key)
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),bake_anim=True,
                             bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0,bake_anim_force_startend_keying=True,**args)
    source = 'Quaternius Jump_toIdle on Warhorse' if jump_only else ('Literock Studios' if key in native else 'Quaternius with Warhorse support gait')
    clips[name]=dict(frames=scene.frame_end,fps=30,source=source)
(out/'clips.json').write_text(json.dumps(clips,indent=2),encoding='utf-8')
