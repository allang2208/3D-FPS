"""Validate the fitted feed tower and unchanged animation contracts in the editable source."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M4_Drum_Reload_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
drum=bpy.data.objects['SM_M4_LargeDrum'];data=json.loads((OUT/'build.json').read_text())
inv=Matrix(data['source_to_component']).inverted()
original=bpy.data.objects[data['original_magazine']]
new=[inv@v.co for v in drum.data.vertices]
top=[inv@v.co for v in original.data.vertices if (inv@v.co).z>data['cut']+.001]
max_fit=max(min((p-q).length for q in new) for p in top)
assert max_fit<1e-5,(max_fit,'feed contour differs from current M4 magazine')
triangles=sum(len(p.vertices)-2 for p in drum.data.polygons)
assert triangles==13908
assert len(drum.data.materials)==3
left={b.name for b in r.data.bones if b.name=='upperarm_l' or any(p.name=='upperarm_l' for p in b.parent_recursive)}
report={'triangles':triangles,'materials':len(drum.data.materials),'feed_contour_max_error_m':max_fit,'clips':[]}
def action(name,t):
 a=bpy.data.actions[name];r.animation_data.action=a
 if len(a.slots):r.animation_data.action_slot=a.slots[0]
 s.frame_set(t);bpy.context.view_layer.update()
for source,target,end in [('M4_reload_FingerCurl','A_M4_DrumReload',188),('M4_reload_empty_BoltRelease','A_M4_DrumReloadEmpty',228)]:
 error=0;step=0;prev=None
 for t in range(end+1):
  action(source,t);poses={b.name:b.matrix.copy() for b in r.pose.bones};hand=r.pose.bones['hand_l'].head.copy()
  action(target,t)
  for b in r.pose.bones:
   if b.name not in left:
    error=max(error,max(abs(b.matrix[i][j]-poses[b.name][i][j]) for i in range(4) for j in range(4)))
  delta=r.pose.bones['hand_l'].head-hand
  if prev is not None:step=max(step,(delta-prev).length)
  prev=delta
 assert error<1e-4,(target,error,'non-support-arm animation changed')
 assert step<.006,(target,step,'support-hand correction jumps between frames')
 report['clips'].append({'clip':target,'frames_checked':end+1,'unmodified_bone_max_matrix_error':error,'max_hand_correction_step_cm':step*100})
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print('M4_DRUM_SOURCE_VALIDATION_PASS',report)
