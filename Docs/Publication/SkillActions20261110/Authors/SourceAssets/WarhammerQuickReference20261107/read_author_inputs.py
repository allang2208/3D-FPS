import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/WarhammerQuickReference20261107')
bpy.ops.wm.open_mainfile(filepath=str(p/'Backup/SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend'))
r=bpy.data.objects['SK_RusticPickaxe_Rig'];bpy.context.scene.frame_set(0)
res={'objects':[(o.name,o.type) for o in bpy.data.objects], 'fps':bpy.context.scene.render.fps,'action':r.animation_data.action.name,'bones':{n:{'pose':[list(row) for row in r.pose.bones[n].matrix],'rest':[list(row) for row in r.data.bones[n].matrix_local]} for n in ['WPN_root','hand_l','hand_r','lowerarm_l','lowerarm_r','upperarm_l','upperarm_r','clavicle_l','clavicle_r']}}
(p/'author-inputs.json').write_text(json.dumps(res,indent=2))
print(json.dumps({'fps':res['fps'],'action':res['action'],'positions':{n:list(r.pose.bones[n].matrix.translation) for n in res['bones']},'objects':res['objects']}))
