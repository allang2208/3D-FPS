import bpy, json, math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'M4_DrumGrip_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
names=[b.name for b in r.pose.bones if b.name.endswith('_l') or b.name.startswith('WPN')]
def sample(action,end):
 a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 out=[]
 for t in range(end+1):
  s.frame_set(t);bpy.context.view_layer.update()
  out.append({n:{'local':[list(v) for v in r.pose.bones[n].matrix_basis], 'head':list(r.pose.bones[n].head),'tail':list(r.pose.bones[n].tail)} for n in names})
 return out
from mathutils import Matrix
report={'bones':{n:{'parent':r.data.bones[n].parent.name if r.data.bones[n].parent else None,'rest':[list(v) for v in r.data.bones[n].matrix_local]} for n in names},'clips':{}}
for clip,end in [('reload',126),('reload_empty',162)]:
 source=sample('M4_HK416_'+clip,end);bad=sample('A_M4_DrumGrip_'+clip,end)
 rows=[]
 for n in names:
  maxima={'rotation_delta_deg':(0,0),'translation_delta_cm':(0,0),'scale_delta':(0,0),'frame_step_deg':(0,0)}
  for t in range(end+1):
   p,q,z=Matrix(source[t][n]['local']).decompose();P,Q,Z=Matrix(bad[t][n]['local']).decompose()
   vals={'rotation_delta_deg':math.degrees(q.rotation_difference(Q).angle),'translation_delta_cm':(p-P).length*100,'scale_delta':(z-Z).length}
   vals['rotation_delta_deg']=min(vals['rotation_delta_deg'],360-vals['rotation_delta_deg'])
   if t:
    angle=math.degrees(Matrix(bad[t-1][n]['local']).to_quaternion().rotation_difference(Q).angle)
    vals['frame_step_deg']=min(angle,360-angle)
   for k,v in vals.items():
    if v>maxima[k][0]:maxima[k]=(v,t)
  rows.append({'bone':n,**maxima})
 report['clips'][clip]=rows
 for n in ['hand_l','WPN_SOCKET_Magazine']:
  print('POSITION_STEPS',clip,n,sorted([(round((Vector(bad[t][n]['head'])-Vector(bad[t-1][n]['head'])).length*100,3),t,round((Vector(source[t][n]['head'])-Vector(source[t-1][n]['head'])).length*100,3)) for t in range(1,end+1)],reverse=True)[:8])
 (OUT/(clip+'_samples.json')).write_text(json.dumps({'source':source,'rejected':bad}))
report['rest_hand']={n:{'head':list(r.data.bones[n].head_local),'tail':list(r.data.bones[n].tail_local)} for n in names if n.startswith(('hand','index','middle','ring','pinky','thumb','upperarm','lowerarm'))}
(OUT/'deformation_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({c:sorted(v,key=lambda x:x['rotation_delta_deg'][0],reverse=True)[:12] for c,v in report['clips'].items()},indent=2))
