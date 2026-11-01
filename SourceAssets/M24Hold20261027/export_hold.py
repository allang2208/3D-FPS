import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;X=O/'Exports'
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Hold_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
report=json.loads((O/'authoring.json').read_text())
def export(path,obs,anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=r;bpy.context.view_layer.update()
    assert all(abs(v-1)<1e-7 for v in r.scale)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=anim,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
        mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
for role,row in report['clips'].items():
    a=bpy.data.actions[row['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.render.fps=30;s.frame_start=0;s.frame_end=row['frames']-1;s.frame_set(0)
    path=X/'Animations'/('A_M24_'+role+'.fbx');export(path,[r],True);row['file']=str(path)
r.animation_data.action=None
for pb in r.pose.bones:pb.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
mod=json.loads((O.parent/'M24Modular20261027/authoring.json').read_text())
removed=set(n for row in mod['models'].values() for n in row['objects'])
obs=[o for o in s.objects if o.type=='MESH' and o.name not in removed]
report['mesh']=str(X/'SK_M24_HoldV9.fbx');export(Path(report['mesh']),[r,*obs])
report['max_corrective_delta_m']=max((p.co-b.co).length for k in skin.data.shape_keys.key_blocks[1:] for p,b in zip(k.data,skin.data.shape_keys.key_blocks[0].data))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_HOLD_EXPORTED',len(report['clips']),len(obs),report['max_corrective_delta_m'],flush=True)
