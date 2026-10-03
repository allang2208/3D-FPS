"""Produce native mixed-skin cartridge pinch anchors and the real yoke pivot."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
side=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
D=json.loads((O.parent/'RSH12Grip20261003'/('native_'+side+'.json')).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(B/'Donor'/side/'SK_DW715_Donor.fbx'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
S=Matrix.Diagonal((1,-1,1,1));cm=Matrix.Diagonal((.01,.01,.01,1))
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
row=min(D['clips']['single_0_1']['samples'],key=lambda x:abs(x['time']-1.80))
p={n:r.matrix_world.inverted()@S@cm@matrix(v)@S for n,v in row['world'].items()}
support='l' if side in ('single','r') else 'r'
caseverts=[];tipverts=[];casefaces=[];skin=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 to_rig=r.matrix_world.inverted()@ob.matrix_world
 groups={g.index:g.name for g in ob.vertex_groups}
 for v in ob.data.vertices:
  weights=[(groups[g.group],g.weight) for g in v.groups if g.weight>1e-7 and groups[g.group] in rest]
  if not weights:continue
  top=max(weights,key=lambda x:x[1])[0]
  if top=='WPN_Case_0':caseverts.append(list(rest[top].inverted()@to_rig@v.co))
  if top=='WPN_Round_0':tipverts.append(list(rest['WPN_Case_0'].inverted()@to_rig@v.co))
  if not(top.endswith('_'+support) and top.startswith(('thumb','index','middle'))):continue
  binds=[(n,w,list(rest[n].inverted()@to_rig@v.co)) for n,w in weights]
  point=sum(((p[n]@Vector(q))*w for n,w,q in binds),Vector())/sum(w for n,w,q in binds)
  skin.append(dict(bone=top,binds=binds,point=list(point)))
case_pose=p['WPN_Case_0'];inv=case_pose.inverted()
# Donor case axis from its principal extent, with case-surface candidates.
cv=[Vector(v) for v in caseverts]
axis=max(range(3),key=lambda i:max(v[i] for v in cv)-min(v[i] for v in cv))
lo=min(v[axis] for v in cv);hi=max(v[axis] for v in cv)
radial=[i for i in range(3) if i!=axis]
center=Vector(tuple((min(v[i] for v in cv)+max(v[i] for v in cv))*.5 for i in range(3)))
radius=max(math.hypot(v[radial[0]]-center[radial[0]],v[radial[1]]-center[radial[1]]) for v in cv)
anchors={}
for digit in ('thumb','index'):
 candidates=[]
 for sample in skin:
  if not sample['bone'].startswith(digit):continue
  q=inv@Vector(sample['point']);axial=max(lo+.003,min(hi-.003,q[axis]))
  rr=math.hypot(q[radial[0]]-center[radial[0]],q[radial[1]]-center[radial[1]])
  distance=math.hypot(rr-radius,q[axis]-axial)
  candidates.append((distance,sample))
 candidates.sort(key=lambda x:x[0]);selected=[v for _,v in candidates[:12]]
 anchors[digit]=[v['binds'] for v in selected]
 point=sum((Vector(v['point']) for v in selected),Vector())/len(selected)
 print('PINCH_ANCHOR',side,digit,'case_local',list(inv@point),'surface_gap_m',candidates[0][0],flush=True)
tip_center=sum((Vector(v) for v in tipverts),Vector())/len(tipverts)
forward=Vector();forward[axis]=1 if tip_center[axis]>center[axis] else -1
out=dict(side=side,support=support,anchors=anchors,donor_forward=list(forward),donor_case_axis=axis,donor_case_center=list(center),
         donor_case_extent=[lo,hi],donor_case_radius=radius,native_sample_seconds=row['time'])
(O/(side+'_contacts.json')).write_text(json.dumps(out),encoding='utf8')
print('NATIVE_PINCH_INPUT_SAVED',side,flush=True)
