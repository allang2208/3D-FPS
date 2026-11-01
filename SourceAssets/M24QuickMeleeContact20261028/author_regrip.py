"""M24 club-style stock-neck regrip, preserving the stock-led weapon path."""
from pathlib import Path
exec(compile((Path(__file__).parent/'solve_right.py').read_text().split("\nif __name__=='__main__':")[0],'solve','exec'))
from mathutils import Euler
M=rest['WPN_root']@idle['WPN_root'].inverted();native={n:M@m for n,m in idle.items()};_,idle_local=pose('idle',0)
grip=json.loads((O/'club_surface_fit.json').read_text())
club={'hand_r':Matrix(grip['hand'])}
digits=[f'{d}_{j:02d}_r' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
closed={};opened={}
for n in digits:
 d,j,_=n.split('_');j=int(j);q=idle_local[n].to_quaternion();e=(local_rest[n].inverted()@idle_local[n]).to_euler()
 if d=='index':
  e=(local_rest[f'middle_{j:02d}_r'].inverted()@idle_local[f'middle_{j:02d}_r']).to_euler();e.z+=math.radians(3 if j==1 else 7)
 elif d!='thumb':e.z+=math.radians(7 if j==2 else 3)
 closed[n]=local_rest[n].to_quaternion()@e.to_quaternion()
 relax=(local_rest[n].inverted()@idle_local[n]).to_euler()
 if d not in ('thumb','index'):relax.z=math.radians({1:-10,2:-20,3:3}[j])
 elif d=='index':pass
 else:relax.z-=math.radians(9 if j==1 else 5)
 opened[n]=local_rest[n].to_quaternion()@relax.to_quaternion()
closed={n:Quaternion(q) for n,q in grip['rotations'].items()}
path_fit=json.loads((O/'transition_fit.json').read_text()) if (O/'transition_fit.json').exists() else None
def weight(t):return ease((t-.03)/.11)*(1-ease((t-.45)/.23))
def regrip(original,t):
 row=clone(original);w=weight(t);root=row['WPN_root']@rest['WPN_root'].inverted()
 a=native['hand_r'];b=club['hand_r'];p,q,sc=a.decompose();pp,qq,ss=b.decompose()
 # Move outside and below the neck before crossing to the club grip.
 # A straight wrist interpolation would send the opening palm through the stock.
 c1=Vector((.31,-.105,-.04));c2=Vector((.07,-.17,-.12))
 pos=p*(1-w)**3+c1*(3*(1-w)**2*w)+c2*(3*(1-w)*w*w)+pp*w**3
 pos.z-=.11*math.sin(math.pi*w)**2
 turn_weight=ease((w-.25)/.65)
 hand=Matrix.LocRotScale(pos,q.slerp(qq,turn_weight),sc.lerp(ss,w));fitted_rotations={}
 if path_fit:
  index=max(0,min(len(path_fit)-2,bisect.bisect_right([v['w'] for v in path_fit],w)-1));aa,bb=path_fit[index],path_fit[index+1];mix=(w-aa['w'])/(bb['w']-aa['w'])
  ap,aq,asc=Matrix(aa['hand']).decompose();bp,bq,bsc=Matrix(bb['hand']).decompose()
  # A continuous wrist path through surface-fitted control poses.
  p0=Matrix(path_fit[max(0,index-1)]['hand']).translation;p3=Matrix(path_fit[min(len(path_fit)-1,index+2)]['hand']).translation
  pos=.5*((2*ap)+(-p0+bp)*mix+(2*p0-5*ap+4*bp-p3)*mix**2+(-p0+3*ap-3*bp+p3)*mix**3)
  hand=Matrix.LocRotScale(pos,aq.slerp(bq,mix),asc.lerp(bsc,mix))
  fitted_rotations={n:Quaternion(aa['rotations'][n]).slerp(Quaternion(bb['rotations'][n]),mix) for n in digits}
 row['hand_r']=root@hand
 release=ease((t-.005)/.025) if t<.14 else ease((.72-t)/.04);close=ease((w-.55)/.45)
 for n in names:
  if n=='hand_r' or not under(n,'hand_r'):continue
  lp,lq,ls=idle_local[n].decompose()
  if n in digits:lq=lq.slerp(fitted_rotations[n],release) if fitted_rotations else lq.slerp(opened[n],release).slerp(closed[n],close)
  row[n]=row[parents[n]]@Matrix.LocRotScale(lp,lq,ls)
 if 'ik_hand_r' in row:row['ik_hand_r']=row['hand_r'].copy()
 return row
keys=[0,.03,.05,.07,.085,.10,.12,.14,.20,.25,.325,.40,.45,.50,.55,.60,.62,.64,.66,.68,.78,.9];fitted=[]
for t in keys:
 old,_=pose('quick_melee',t);row=regrip(old,t);w=weight(t);choices=[]
 if w<1e-6:best={'offset_cm':[0,0,0],'phi':0.,'score':0.,'bend':0.,'roll':0.,'capsule_penetration_cm':[]}
 else:
  for off in ((0,0,0),(0,0,-3),(0,3,-3),(3,0,-3),(0,0,-6),(3,3,-6)):
   for phi in range(-150,151,5):
    value=solve(row,off,phi)
    if not value:continue
    # Keep the selected elbow circle side coherent through the transition.
    continuity=.001*(phi-fitted[-1]['phi'])**2 if fitted else 0
    choices.append((value['score']+continuity,value))
  best=min(choices,key=lambda v:v[0])[1]
 fitted.append({'t':t,**best});print('REGRIP_KEY',json.dumps(fitted[-1]),flush=True)
def params(t):
 i=max(0,min(len(fitted)-2,bisect.bisect_right(keys,t)-1));a,b=fitted[i],fitted[i+1];w=ease((t-a['t'])/(b['t']-a['t']))
 return Vector(a['offset_cm']).lerp(Vector(b['offset_cm']),w),a['phi']*(1-w)+b['phi']*w
final={};patch={};report={'duration':.9,'contact':.25,'fps':120,'grip':'Right hand wraps the stock neck; index joins the grip. Left hand and weapon path unchanged.','keys':fitted,'runtime_tested':False,'clips':{}}
for family in ('base','mag10'):
 rows=[];times=[i/120 for i in range(109)];tracks={n:[] for n in names};last={}
 for t in times:
  old,_=pose('quick_melee',t,family);row=regrip(old,t);off,phi=params(t)
  if weight(t)>1e-6:
   result=solve(row,off,phi,True)
   if result is None:raise ValueError('Regrip outside native arm reach '+str(t))
   row,detail=result
  elif t<=.005 or t>=.72:row=clone(old)
  rows.append(row);_,raw=pose('quick_melee',t,family,False)
  for n in names:
   local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];p,q,sc=(K@local@K).decompose();bp,bq,bs=(K@raw[n]@K).decompose();dq=q@bq.inverted()
   if n in last and dq.dot(last[n])<0:dq=-dq
   last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(sc-bs)])
 final[family]=rows;patch[family]={'base':ue['clips']['quick_melee']['path'],'duration':.9,'tracks':[{'bone':n,'times':times,'values':values} for n,values in tracks.items()]}
(O/'quick_melee_patch.json').write_text(json.dumps(patch));(O/'final_poses.json').write_text(json.dumps({family:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for family,rows in final.items()}))
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node).replace('s.render.fps = 30','s.render.fps = 120').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 120'),'bake','exec'))
for family,rows in final.items():
 role='quick_melee' if family=='base' else 'quick_melee_mag10';r.animation_data_clear();a=bpy.data.actions.get('A_M24_'+role)
 if a:bpy.data.actions.remove(a)
 bake(role,rows);bpy.data.actions['A_M24_'+role].use_fake_user=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ClubGrip_Editable.blend'));(O/'authoring.json').write_text(json.dumps(report,indent=2));print('M24_CLUB_GRIP_AUTHORED',flush=True)
