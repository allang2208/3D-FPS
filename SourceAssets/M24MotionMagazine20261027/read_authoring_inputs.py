import bpy, json
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig']; s=bpy.context.scene; ob=bpy.data.objects['M24_clip']
R={'magazine':{'matrix':[list(v) for v in ob.matrix_world],'vertices':[list(v.co) for v in ob.data.vertices],
 'polygons':[list(p.vertices) for p in ob.data.polygons],'uv':[list(v.uv) for v in ob.data.uv_layers.active.data],
 'normals':[list(n.vector) for n in ob.data.corner_normals]},'clips':{},'poses':{},'rest':{b.name:[list(v) for v in b.matrix_local] for b in r.data.bones}}
for role,frames in {'idle':[0],'reload':[0,15,21,30,38,40,48,60],'reload_empty':[38,40,54,77,94,110]}.items():
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 R['clips'][role]=list(a.frame_range)
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update()
  R['poses'][role+'_'+str(f)]={b.name:[list(v) for v in b.matrix] for b in r.pose.bones}
(O/'authoring_inputs.json').write_text(json.dumps(R,indent=2))
print('AUTHORING_INPUTS_SAVED',flush=True)
