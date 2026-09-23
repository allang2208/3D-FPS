import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Feed13/PKM_FiringFeed_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['PKM_Game_idle_Wrist12'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit
report={'fit':list(map(list,fit)),'bones':{},'objects':{}}
for b in r.pose.bones:
 if b.name in ['WPN_root','hand_l','hand_r','lowerarm_l','upperarm_l'] or b.name.startswith('PKM_') or b.name.startswith('WPN_'):
  report['bones'][b.name]={'rest':list(map(list,r.data.bones[b.name].matrix_local)),'pose':list(map(list,b.matrix)),'gun':list(map(list,(r.pose.bones['WPN_root'].matrix@fit).inverted()@b.matrix))}
for o in s.objects:
 if o.type!='MESH' or 'mechanical_bone' not in o or o.name.startswith('New_'):continue
 ps=[B.inverted()@v.co for v in o.data.vertices]
 report['objects'][o.name]={'bone':o.get('mechanical_bone'),'source':o.get('source_name'),'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)],'materials':[m.name for m in o.data.materials]}
(O/'authoring_frames.json').write_text(json.dumps(report,indent=2))
print('PKM14_SOURCE_FRAMES_READ',len(report['objects']),flush=True)
