import bpy,ast,math,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];rest={b.name:b.matrix_local.copy() for b in r.data.bones};out=[]
l1=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).length;l2=(rest['hand_l'].translation-rest['lowerarm_l'].translation).length
rf=(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
for f in [18,34,49,60,90,110,140,160,180,200,220,240,260,280,302]:
 p=sample(r,bpy.data.actions['A_SVD_reload'],f);H=p['hand_l'];A=p['upperarm_l'].translation;T=H.translation
 d=H.to_quaternion()@rest['hand_l'].to_quaternion().inverted()@rf;E=T-d*l2
 ideal=E+(A-E).normalized()*l1;W=p['WPN_root'].inverted();shift=ideal-A
 axis=(T-A).normalized();dist=(T-A).length;phi=math.acos(max(-1,min(1,(l2*l2+dist*dist-l1*l1)/(2*l2*dist))))
 row={'frame':f,'shoulder_root':list(W@A),'hand_root':list(W@T),'ideal_elbow_root':list(W@E),'shoulder_shift_cm':list(shift*100),'zero_bend_min_shift_cm':shift.length*100,'best_fixed_shoulder_bend_deg':math.degrees(abs(axis.angle(d)-phi))}
 out.append(row);print('SVD_SUPPORT_INPUT',row,flush=True)
(O/'support_inputs.json').write_text(json.dumps(out,indent=2))
