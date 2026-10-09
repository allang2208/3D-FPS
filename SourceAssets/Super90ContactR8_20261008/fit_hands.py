"""Bounded contact fitting on the current V7 skin; never changes mesh weights."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;author=O.parent/'Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
rest=s['rest'];idle=s['idle'];I=Matrix.Identity(4)
gun=bpy.data.objects['Super90_body'];gun.data.calc_loop_triangles()
mv=s['G0']@s['R0'].inverted()
tree=BVHTree.FromPolygons([mv@gun.matrix_world@v.co for v in gun.data.vertices],[tuple(t.vertices) for t in gun.data.loop_triangles],all_triangles=True)
skin={}
for side in ('l','r'):
    selected=['hand_'+side]+s['finger_names'][side];names=list(rest);verts=[];weights=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or not ob.name.startswith('Super90_V7_'):continue
        for v in ob.data.vertices:
            wg={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
            if sum(wg.get(n,0) for n in selected)<.98:continue
            verts.append([*(ob.matrix_world@v.co),1]);weights.append([wg.get(n,0) for n in names])
    # Deterministic stride retains all fingers; full surface verification follows.
    vs=np.array(verts)[::3];ws=np.array(weights)[::3];r={n:np.asarray(rest[n].inverted()) for n in names}
    skin[side]=(names,vs,ws,r)

def points(side,hand,locals):
    names,vs,ws,r=skin[side]
    carry=hand@idle['hand_'+side].inverted()
    world={n:carry@idle[n] for n in names};world['hand_'+side]=hand
    for n in s['finger_names'][side]:world[n]=world[s['parents'][n]]@locals[n]
    result=np.zeros((len(vs),3))
    for j,n in enumerate(names):
        if np.any(ws[:,j]):result+=(vs@(np.asarray(world[n])@r[n]).T)[:,:3]*ws[:,j,None]
    return result

def distances(vs):
    out=[]
    for v in vs:
        point=Vector(v);loc,n,_,d=tree.find_nearest(point)
        inside=0
        if d<.02:
            for direction in (Vector((1,.137,.071)).normalized(),Vector((.113,1,.193)).normalized(),Vector((.097,.157,1)).normalized()):
                origin=point.copy();hits=0
                for _ in range(24):
                    hit,_,_,distance=tree.ray_cast(origin,direction,2.)
                    if hit is None:break
                    hits+=1;origin=hit+direction*.00001
                inside+=hits%2
        out.append(-d if inside>=2 else d)
    return np.asarray(out)

def solve(initial,steps,bounds,evaluate,label):
    x=np.array(initial,dtype=float);best,stats=evaluate(x);initial_stats=stats
    for scale in (1.,.5,.25):
      for _ in range(7):
        changed=False
        for j,step in enumerate(steps):
          for sign in (-1,1):
            trial=x.copy();trial[j]=np.clip(trial[j]+sign*step*scale,*bounds[j]);cost,st=evaluate(trial)
            if cost<best-1e-10:x,best,stats=trial,cost,st;changed=True
        if not changed:break
      print('CONTACT_FIT',label,scale,x.tolist(),stats,flush=True)
    return x,{'before':initial_stats,'after':stats,'cost':best}

digits=('thumb','index','middle','ring','pinky')
right_local={n:idle[s['parents'][n]].inverted()@idle[n] for n in s['finger_names']['r']}
def right_pose(x):
    hand=idle['hand_r'].copy();hand.translation+=mv.to_3x3()@Vector(x[:3])
    q=Quaternion((1,0,0),math.radians(x[3]))@Quaternion((0,1,0),math.radians(x[4]))@Quaternion((0,0,1),math.radians(x[5]))
    hand=Matrix.LocRotScale(hand.translation,q@hand.to_quaternion(),hand.to_scale());local={}
    for n,original in right_local.items():
        t=x[6+digits.index(n.split('_')[0])] if 'metacarpal' not in n else 0
        local[n]=s['mix'](original,s['local_rest'][n],t)
    return hand,local
def right_cost(x):
    hand,local=right_pose(x);ds=distances(points('r',hand,local));pen=np.maximum(0.,.0005-ds)
    # Keep the palm near the handle and preserve the accepted hand shape.
    cost=float(np.mean(pen**2)*1e6 + np.max(pen)**2*30000 + np.dot(x[:3],x[:3])*900 + np.dot(x[3:6],x[3:6])*.00015 + np.dot(x[6:],x[6:])*.015)
    return cost,{'inside_samples':int(sum(ds<-.0004)),'max_nearest_inside_mm':float(max(0.,-min(ds))*1000),'mean_gap_mm':float(np.mean(np.maximum(ds,0))*1000)}
starts=[[0]*11,[.00525,.003,-.0045,1.5,-4.5,0,0,.22,.3,.08,.16]]+[[dx,dy,dz,0,0,0,0,.12,.12,.12,.12] for dx in (-.01,0,.01) for dy in (-.01,0,.01) for dz in (-.01,0,.01)]
start=min(starts,key=lambda v:right_cost(np.asarray(v))[0])
x,right_report=solve(start,[.003]*3+[3]*3+[.08]*5,[(-.018,.018)]*3+[(-12,12)]*3+[(0,.50)]*5,right_cost,'right')
hand,local=right_pose(x)
out={'right_hand_in_idle':[list(r) for r in hand],'right_finger_local':{n:[list(r) for r in m] for n,m in local.items()},'right_parameters':x.tolist(),'right_fit':right_report}

# Release with the thumb pad, keeping the other fingers curled away from the
# receiver. Fit in the gun's idle frame so every count shares the same contact.
f=158;p=s['pose'](f,7,True)[0];move=p['WPN_root']@s['G0'].inverted();base=move.inverted()@p['hand_l'];catch=idle['WPN_BoltCatch'].translation
normal=mv.to_3x3()@Vector((1,0,0));normal.normalize()
surface,_,_,_=tree.ray_cast(catch+normal*.06,-normal,.10)
if surface is not None:catch=surface
def press_pose(x):
    local={n:s['mix'](s['open_fingers'][n],s['handle_fingers'][n],.15 if n.startswith('thumb') else x[3]) for n in s['finger_names']['l']}
    w={'hand_l':I}
    for n in s['finger_names']['l']:w[n]=w[s['parents'][n]]@local[n]
    thumb=[]
    for v in s['skin_input']['vertices']:
        if v['id'] not in s['thumb_ids']:continue
        thumb.append(sum((w[n]@rest[n].inverted()@Vector(v['p'])*wt for n,wt in v['weights'].items()),Vector()))
    pad=sum(thumb,Vector())/len(thumb)
    # Point the bulk of the palm away from the receiver before fitting roll.
    palm=Vector(np.mean(points('l',I,local),axis=0))-pad
    q0=(base.to_quaternion()@palm).rotation_difference(normal)@base.to_quaternion()
    q=Quaternion(normal,math.radians(x[0]))@Quaternion(s['forward'],math.radians(x[1]))@Quaternion(s['up'],math.radians(x[2]))@q0
    hand=Matrix.LocRotScale(catch+normal*.001-q@pad,q,Vector((1,1,1)))
    return hand,local,pad
def press_cost(x):
    hand,local,pad=press_pose(x);ds=distances(points('l',hand,local));pen=np.maximum(0.,.0007-ds)
    # Favor a compact side contact over laying the palm across the receiver.
    cost=float(np.mean(pen**2)*1e6+np.dot(x[1:3],x[1:3])*.000015+(x[3]-.65)**2*.015)
    return cost,{'inside_samples':int(sum(ds<-.0004)),'max_nearest_inside_mm':float(max(0.,-min(ds))*1000),'finger_grasp':float(x[3])}
starts=[[roll,0,0,curl] for roll in range(-150,181,30) for curl in (.3,.65,.95)]
start=min(starts,key=lambda v:press_cost(np.asarray(v))[0])
y,press_report=solve(start,[10,5,5,.1],[(-180,180),(-35,35),(-35,35),(.2,1)],press_cost,'empty_release')
hand,local,pad=press_pose(y)
out.update({'press_hand_in_idle':[list(r) for r in hand],'press_finger_local':{n:[list(r) for r in m] for n,m in local.items()},'press_thumb_pad':list(pad),'press_parameters':y.tolist(),'press_fit':press_report})
(O/'hand_fit.json').write_text(json.dumps(out,indent=2));print('HAND_FIT_SAVED',flush=True)
