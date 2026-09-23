"""Read the current editable reload's mechanical phases and left-arm inputs."""
import bpy,ast,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];rest={b.name:b.matrix_local.copy() for b in r.data.bones}
rows=[];prev=None;action=bpy.data.actions['A_SVD_reload']
for f in range(401):
 p=sample(r,action,f);W=p['WPN_root'];M=W.inverted()@p['WPN_SOCKET_Magazine'];H=W.inverted()@p['hand_l']
 A=p['upperarm_l'].translation;E=p['lowerarm_l'].translation;T=p['hand_l'].translation
 d=(T-E).normalized();v=p['hand_l'].to_quaternion()@rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
 row={'f':f,'mag_pos':list(M.translation),'mag_q':list(M.to_quaternion()),'hand_pos':list(H.translation),'hand_q':list(H.to_quaternion()),
  'wrist_axis_bend_deg':math.degrees(d.angle(v)),'reach_ratio':(T-A).length/((E-A).length+(T-E).length),
  'hand_mag_local': [list(x) for x in (M.inverted()@H)],'arm_local':{n:[list(x) for x in (p[r.data.bones[n].parent.name].inverted()@p[n])] for n in ['upperarm_l','lowerarm_l','hand_l']}}
 if prev:
  row['mag_step_deg']=math.degrees(M.to_quaternion().rotation_difference(prev[0].to_quaternion()).angle)
  row['hand_step_deg']=math.degrees(H.to_quaternion().rotation_difference(prev[1].to_quaternion()).angle)
  row['forearm_step_deg']=math.degrees(p['lowerarm_l'].to_quaternion().rotation_difference(prev[2].to_quaternion()).angle)
  for k in ['mag_step_deg','hand_step_deg','forearm_step_deg']:row[k]=min(row[k],360-row[k])
 rows.append(row);prev=(M,H,p['lowerarm_l'].copy())
(O/'motion_inputs.json').write_text(json.dumps({'rows':rows,'bones':{n:{'parent':r.data.bones[n].parent.name if r.data.bones[n].parent else None,'rest':[list(v) for v in m]} for n,m in rest.items()}},indent=2))
for f in [0,18,34,49,52,60,70,80,90,100,110,120,135,150,180,210,220,240,250,270,285,302,330,400]:
 x=rows[f];print('SVD_RELOAD_INPUT',f,'mag',x['mag_pos'],'bend',round(x['wrist_axis_bend_deg'],1),'reach',round(x['reach_ratio'],3),'step',round(x.get('forearm_step_deg',0),1),flush=True)
for key in ['wrist_axis_bend_deg','hand_step_deg','forearm_step_deg']:
 print('SVD_RELOAD_EXTREME',key,[(x['f'],round(x.get(key,0),2)) for x in sorted(rows,key=lambda row:row.get(key,0),reverse=True)[:8]],flush=True)
