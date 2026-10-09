"""Rebake the source motion into the already shipped native mesh bind."""
import bpy,json,math,sys,shutil
from pathlib import Path
from mathutils import Matrix

P=Path(r'D:/FPS3D/FPSGAME');O=P/'SourceAssets/Super90PoseRepair20261007';S=P/'SourceAssets/BenelliM4Super9020261006'
source_script=S/'author_super90.py'
scope={'__file__':str(source_script)}
exec(compile(source_script.read_text(encoding='utf-8-sig').split('# Preserve source UVs')[0],str(source_script),'exec'),scope)
rawclips=scope['rawclips']
auth=json.loads((S/'authoring.json').read_text())
intended={n:Matrix(m) for n,m in auth['native_rest'].items()}
editable=S/'Super90_Gameplay_Editable.blend'
backup=O/'Super90_BeforePoseRepair.blend'
if not backup.exists():shutil.copy2(editable,backup)
bpy.ops.wm.open_mainfile(filepath=str(editable));r=bpy.data.objects['SK_Super90'];scene=bpy.context.scene
native={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
correction={n:intended[n].inverted()@native[n] for n in native}
sys.path.insert(0,str(P/'SourceAssets/M1911RevolverInspect20260927'));import author_support as support
r.animation_data.action=None
for name in ['A_Super90_'+kind for kind in auth['clips']]:
    if name in bpy.data.actions:bpy.data.actions.remove(bpy.data.actions[name])
scene.render.fps=60
receipt={'kept_mesh_bind':True,'clips':{},'runtime_tested':False,'visual_accepted':False,
         'gun_up_axis_local_ue':[0,-1,0],'gun_up_axis_local_blender':[0,1,0]}

def bake(kind,rows):
    local=[]
    for raw in rows:
        desired=dict(raw);desired['VM_Root']=Matrix.Identity(4)
        for n in auth['markers_source']:
            desired[n]=desired['WPN_root']@intended['WPN_root'].inverted()@intended[n]
        pose={n:desired[n]@correction[n] for n in native}
        entry={}
        for n in native:
            p=parents[n];ref_parent=native[p] if p else Matrix.Identity(4);pose_parent=pose[p] if p else Matrix.Identity(4)
            entry[n]=((ref_parent.inverted()@native[n]).inverted()@(pose_parent.inverted()@pose[n])).decompose()
        local.append(entry)
    support.DURATION=(len(rows)-1)/60
    action=support.bake_action(r,scene,'A_Super90_'+kind,local,list(range(len(rows))))
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    file=Path(auth['clips'][kind]['fbx'])
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    receipt['clips'][kind]={'fbx':str(file),'duration':support.DURATION,'frames':len(rows)}

labels={'M4_Idle':'idle','M4_Walk':'walk','M4_Run':'run','M4_Fire':'fire','M4_Fire_LastRoundCheck':'fire_last',
        'M4_ReloadOne_type1':'reload_one','M4_ReloadFull_type1':'reload_full','M4_ReloadOne_type2':'reload_empty'}
for source,kind in labels.items():bake(kind,rawclips[source])
idle=rawclips['M4_Idle'][0]
rows=[]
for f in range(37):
    t=f/36;w=1-t*t*(3-2*t);delta=Matrix.Translation((0,-.12*w,-.20*w))@Matrix.Rotation(.25*w,4,'X')
    rows.append({n:delta@m for n,m in idle.items()})
bake('equip',rows);bake('inspect',rawclips['M4_Fire_LastRoundCheck'][22:])
rows=[]
for f in range(43):
    t=f/42;pulse=math.sin(math.pi*t)**2;delta=Matrix.Translation((0,.23*pulse,.03*pulse))@Matrix.Rotation(-.13*pulse,4,'X')
    rows.append({n:delta@m for n,m in idle.items()})
bake('quick_melee',rows)
r.animation_data.action=bpy.data.actions['A_Super90_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=179;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editable))
receipt['source_idle_wrists_cm']={n:list(idle[n].translation*100) for n in ('hand_l','hand_r')}
receipt['source_idle_wrist_separation_cm']=(idle['hand_l'].translation-idle['hand_r'].translation).length*100
receipt['native_binding_rest']={n:[list(row) for row in m] for n,m in native.items()}
auth['bake_binding_rest']=receipt['native_binding_rest']
auth['pose_basis']='Source deformation transported from native_rest to bake_binding_rest'
(S/'authoring.json').write_text(json.dumps(auth,indent=2))
(O/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SUPER90_NATIVE_BIND_ANIMATIONS_REBAKED',len(receipt['clips']),flush=True)
