import bpy,json,math
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
result={'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},'samples':{}}
for an in ['M4_idle','M4_reload','M4_reload_empty','M4_HK416_reload','M4_HK416_reload_empty','M4_HK416_equip_charge']:
 a=bpy.data.actions.get(an)
 if not a:continue
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];result['samples'][an]={}
 for f in [0,30,54,80,100,130,150]:
  if f>a.frame_range[1]:continue
  s.frame_set(f);bpy.context.view_layer.update()
  result['samples'][an][f]={b.name:{'basis_euler_deg':[round(math.degrees(x),1) for x in b.matrix_basis.to_euler()], 'parent':b.parent.name if b.parent else '', 'head':list(b.head),'tail':list(b.tail),'q':list(b.matrix.to_quaternion())} for b in r.pose.bones if b.name.endswith(('_l','_r')) and b.name.startswith(('hand','upperarm','lowerarm','thumb','index','middle','ring','pinky'))}
(O/'probe.json').write_text(json.dumps(result,indent=2))
print('PROBE_DONE')
