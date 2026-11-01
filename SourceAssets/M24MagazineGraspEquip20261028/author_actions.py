from pathlib import Path
exec(compile((Path(__file__).parent/'contact_pose.py').read_text().split("if __name__=='__main__':")[0],'contact','exec'))
grips=json.loads((O/'contact_grips.json').read_text())
def local_row(row):return {n:row[parents[n]].inverted()@row[n] if parents[n] else row[n] for n in names}
def mix_matrix(a,b,w):
 p,q,sc=a.decompose();pp,qq,ss=b.decompose();return Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
def mix_rows(a,b,w):
 al=local_row(a);bl=local_row(b);out={}
 for n in names:
  m=mix_matrix(al[n],bl[n],w);out[n]=out[parents[n]]@m if parents[n] else m
 return out
def interpolate(rows,f):
 f=max(0,min(len(rows)-1,f));i=int(f);return mix_rows(rows[i],rows[min(i+1,len(rows)-1)],f-i)
def grip_hand(row,family,w,closed,return_weight=0):
 g=grips[family];M=row['WPN_Magazine']@rest['WPN_Magazine'].inverted();h=M@Matrix(g['hand'])
 out=arm_to_hand(row,mix_matrix(row['hand_l'],h,w));original=local_row(row)
 for n in names:
  if n=='hand_l' or not under(n,'hand_l'):continue
  p,q,sc=original[n].decompose()
  if n in g['rotations']:
   digit=n.split('_')[0];j=int(n.split('_')[1]);cq=local_rest[n].to_quaternion()@Quaternion(g['rotations'][n])
   if digit=='thumb':oq=cq@Q(z=-8 if j==1 else -4)
   else:oq=local_rest[n].to_quaternion()@Q(z={1:5,2:15,3:8}[j])
   tq=oq.slerp(cq,closed);q=q.slerp(tq,w*(1-return_weight))
  out[n]=out[parents[n]]@Matrix.LocRotScale(p,q,sc)
 return out
report={'clips':{},'source_fps':30,'reload_clock':'Existing M24ReloadTiming; unchanged','mesh':'Existing saved V9/115 morphs; no geometry reimport','github':'drawm24.anim is root-only, 0.56666666 s; not imported','equip_cues':{'magazine_seat':34/30,'charge_pull':73/30,'charge_release':88/30},'runtime_tested':False}
final={};patch={};owned=['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l',*digits]
for role in ('reload','reload_empty','reload_mag10','reload_empty_mag10'):
 family='mag10' if role.endswith('_mag10') else 'base';rows=[]
 for f,old in enumerate(clips[role]):
  if 6<f<54:
   w=ease((f-6)/12)*(1-ease((f-44)/10));closed=ease((f-13)/7)*(1-ease((f-40)/4))
   row=grip_hand(old,family,w,closed)
  else:row=clone(old)
  rows.append(row)
 final[role]=rows;data=ue['clips'][role];tracks=[]
 for n in owned:
  values=[];last=None
  for f,row in enumerate(rows):
   loc=K@(row[parents[n]].inverted()@row[n])@K;p,q,sc=loc.decompose();bp,bq,bs=unpack(data['poses'][str(f)][names.index(n)])
   dp=p-bp;dq=q@bq.inverted();ds=sc-bs
   if last and dq.dot(last)<0:dq=-dq
   last=dq.copy();values.extend([*dp,dq.x,dq.y,dq.z,dq.w,*ds])
  tracks.append({'bone':n,'times':[f/30 for f in range(len(rows))],'values':values})
 patch[family+'/'+role]={'base':data['path'],'duration':(len(rows)-1)/30,'window':[6/30,54/30],'tracks':tracks}
# Equip: raise at the existing hip anchor, seat the attached magazine, then use
# the accepted cycle branch (including the latest support-arm root correction).
for family in ('base','mag10'):
 rows=[];idle=clips['idle'][0];cycle=clips['cycle']
 for f in range(107):
  if f<=18:row=interpolate(clips['equip'],f*24/18)
  elif f<48:
   row=clone(idle);w=ease((f-18)/12)*(1-ease((f-38)/10));closed=ease((f-24)/6)*(1-ease((f-36)/4))
   # 1.2 mm seating compression, resolved in the magazine's own rest frame.
   pulse=math.sin(math.pi*max(0,min(1,(f-30)/8)))**2 if 30<f<38 else 0
   delta=row['WPN_Magazine'].to_quaternion()@rest['WPN_Magazine'].to_quaternion().inverted()@Vector((0,0,.0012*pulse))
   for n in names:
    if under(n,'WPN_Magazine'):row[n].translation+=delta
   row=grip_hand(row,family,w,closed)
  else:
   row=interpolate(cycle,4+(f-48));row=mix_rows(idle,row,ease((f-48)/6)) if f<54 else row
  rows.append(row)
 rows[-1]=clone(idle);final['equip' if family=='base' else 'equip_mag10']=rows
(O/'reload_patch.json').write_text(json.dumps(patch))
(O/'final_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in final.items()}))
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'))
node=next(n for n in ast.parse((O.parent/'M24MotionMagazine20261027/author.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='export');exec(compile(ast.unparse(node),'export','exec'))
folder=O/'Export';folder.mkdir(exist_ok=True)
for role,rows in final.items():
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
 if role.startswith('equip'):
  path=folder/('A_M24_'+role+'.fbx');export(path,[r],True);report['clips'][role]['file']=str(path)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_GraspEquip_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
folder=O/'ActionContacts';folder.mkdir(exist_ok=True)
for role,frames in {'reload':[18,21,38,40,44],'reload_mag10':[21,38],'equip':[30,34,38,73]}.items():
 for f in frames:
  show(final[role][f],folder/f'{role}_{f}_contact.png','right',role.endswith('_mag10'))
print('M24_GRASP_EQUIP_AUTHORED',flush=True)
