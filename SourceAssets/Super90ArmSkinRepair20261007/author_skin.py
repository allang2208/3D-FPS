"""Rebuild the Super90 V7 surface from its donor, preserving the native rig and motion."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(r'D:/FPS3D/FPSGAME');O=P/'SourceAssets/Super90ArmSkinRepair20261007';S=P/'SourceAssets/BenelliM4Super9020261006'
O.mkdir(exist_ok=True);B=O/'Before';B.mkdir(exist_ok=True)
editable=S/'Super90_Gameplay_Editable.blend'
if not (B/editable.name).exists():shutil.copy2(editable,B/editable.name)
bpy.ops.wm.open_mainfile(filepath=str(editable));s=bpy.context.scene;r=bpy.data.objects['SK_Super90']
r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
auth=json.loads((S/'authoring.json').read_text());rest={n:Matrix(m) for n,m in auth['native_rest'].items()}
for ob in list(s.objects):
    if ob.type=='MESH' and ob.name.startswith('Super90_V7_'):bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'),link=False) as (available,loaded):
    loaded.objects=list(available.objects)
bare_rig=next(o for o in loaded.objects if o and o.type=='ARMATURE')
oldrest={b.name:b.matrix_local.copy() for b in bare_rig.data.bones}
source=(S/'author_super90.py').read_text(encoding='utf-8-sig')
code=source[source.index('def mapped(n):'):source.index('# Keep source outfit separately')]
exec(compile(code,str(S/'author_super90.py'),'exec'),globals())
for ob in arms:ob.data.update()

exports={}
for label,objects in [
    ('SK_Super90_V7',[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]+[bpy.data.objects['12g_12gauge_0']]+arms),
    ('SK_Super90_BareArmsV7',arms)]:
    file=S/'Exports'/(label+'.fbx')
    if file.exists() and not (B/file.name).exists():shutil.copy2(file,B/file.name)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [r]+objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    exports[label]=str(file)
auth['v7_to_native_warp']={n:[list(x) for x in m] for n,m in warp.items()}
auth['arm_skin_mapping']='Upper-arm helpers share the parent segment warp; proximal forearm weights use lowerarm_aux'
(S/'authoring.json').write_text(json.dumps(auth,indent=2))
r.animation_data.action=bpy.data.actions['A_Super90_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=179;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editable))
(O/'authoring_receipt.json').write_text(json.dumps({'exports':exports,'animation_tracks_changed':False,
    'reference_skeleton_changed':False,'weapon_geometry_changed':False,'runtime_tested':False},indent=2))
print('SUPER90_ARM_SKIN_EXPORTED',flush=True)
