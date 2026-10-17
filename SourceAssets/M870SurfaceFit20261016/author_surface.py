"""Bake the surface-fitted grasp with a continuous low support elbow."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;PREV=O.parent/'M870GripADS20261016'
code=(PREV/'author_grip.py').read_text().split('tree=ast.parse')[0]
code=code.replace('range(-135,136,3)','range(-177,178,3)')
code=code.replace('across=max(0,ce.x+.025);raised=max(0,ce.z+.805)','across=max(0,ce.x+.10);raised=max(0,ce.z-min((canonical@w).z-.06,-.85))')
code=code.replace('score=wrist*wrist+4*overload*overload+.025*angle*angle+80*(across*across+raised*raised)','score=wrist*wrist+.5*overload*overload+.008*angle*angle+3000*(across*across+raised*raised)')
code=code.replace('axis=w-a;distance=axis.length;maxreach=.94*(l1+l2)', '''# Move the hidden shoulder only when the native two-bone circle cannot
    # reach this pump/melee pose with <= 30 degrees wrist bend. The shift is
    # the nearest point on the upper-arm sphere, not a wrist translation.
    df=hand.to_quaternion()@rest['hand_l'].to_quaternion().inverted()
    forward=(df@f0).normalized();v=a-w;parallel=v.dot(forward)
    perpendicular=v-forward*parallel;pv=perpendicular.length;angle=math.radians(30)
    lo=parallel*math.cos(angle)-pv*math.sin(angle);hi=parallel*math.cos(angle)+pv*math.sin(angle)
    target=(l1*l1-v.length_squared-l2*l2)/(2*l2)
    if pv>1.e-8 and (target<lo or target>hi):
        fd=forward*math.cos(angle)+perpendicular/pv*(math.sin(angle)*(1 if target>hi else -1))
        desired_elbow=w-fd*l2;new_a=desired_elbow+(a-desired_elbow).normalized()*l1
        shift=new_a-a
        if shift.length>.09:shift*=.09/shift.length
        a+=shift
    axis=w-a;distance=axis.length;maxreach=.94*(l1+l2)''')
code=code.replace('score=wrist*wrist+.5*overload', 'score=wrist*wrist+12*max(0,wrist-math.radians(32))**2+.5*overload')
exec(compile(code,str(PREV/'author_grip.py'),'exec'))
grip={n:Matrix(m) for n,m in json.loads((O/'optimized_grip.json').read_text())['grip'].items()}
shoulder_anchor=to_scene@Vector((-.22,-.08,-.94))
tree=ast.parse((BASE/'author_m870.py').read_text())
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('select','bake')]
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
authored={};exec(compile(ast.Module(body=selected,type_ignores=[]),str(BASE/'author_m870.py'),'exec'))
source_roles={k:v['action'] for k,v in json.loads((BASE/'authoring.json').read_text())['clips'].items()}
source_roles.update({k:v['action'] for k,v in json.loads((UC/'authoring.json').read_text())['clips'].items()})
source_actions={role:bpy.data.actions[name] for role,name in source_roles.items()};recipe={}
for role,action in source_actions.items():
 frames=int(round(action.frame_range[1]))+1;inputs=[];angles=[]
 for frame in range(frames):
  row=at(action,frame);inputs.append(row);angles.append(solve({n:m.copy() for n,m in row.items()})['elbow_angle'])
 angles=np.unwrap(angles).tolist();smooth=[]
 for i in range(frames):
  weights=[(j,math.exp(-.5*((j-i)/3.)**2)) for j in range(max(0,i-9),min(frames,i+10))]
  value=sum(angles[j]*w for j,w in weights)/sum(w for _,w in weights);edge=min(1.,i/9.,(frames-1-i)/9.)
  smooth.append(angles[i]*(1-edge)+value*edge)
 rows=[];stats=[]
 for frame,row in enumerate(inputs):
  data=solve(row,smooth[frame]);rows.append(row);stats.append(data)
 bake(role,rows);recipe[role]={'frames':frames,'input':action.name,'max_wrist_bend_deg':max(x['wrist_bend_deg'] for x in stats),'max_upper_roll_deg':max(abs(x['upper_roll_deg']) for x in stats),'elbow_angles':smooth}
 print('SURFACE_CLIP',role,recipe[role]['max_wrist_bend_deg'],recipe[role]['max_upper_roll_deg'],flush=True)
a=bpy.data.actions[authored['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
s.frame_start=0;s.frame_end=179;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_SurfaceFit_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':authored,'recipe':recipe,'grip_source':'optimized_grip.json','left_shoulder_canonical':[-.22,-.08,-.94],'scope':'13 active M870 roles; unchanged right hand, gun travel and event clock','runtime_tested':False},indent=2))
print('M870_SURFACE_AUTHORED',len(authored),flush=True)
