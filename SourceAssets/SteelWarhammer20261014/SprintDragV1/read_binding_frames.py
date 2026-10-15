import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/Pickaxe_BareArmsV7.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');native={b.name:b.matrix_local.copy() for b in rig.data.bones}
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];names=['clavicle_l','upperarm_l','lowerarm_l','hand_l','index_01_l','clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root']
out={n:{'native_translation':list(native[n].translation),'author_translation':list(rig.data.bones[n].matrix_local.translation),'distance_m':(native[n].translation-rig.data.bones[n].matrix_local.translation).length,'axis_rotation_degrees':native[n].to_quaternion().rotation_difference(rig.data.bones[n].matrix_local.to_quaternion()).angle*57.2958} for n in names}
(P/'binding_frames.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
