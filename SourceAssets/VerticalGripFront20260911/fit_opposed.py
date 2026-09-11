"""Fit the thumb through a fixed hinge curl, bounded root swing and roll."""
import bpy,json,sys,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(O));from front_pose import apply
from inspect_pose import render
ORIG=json.loads((O/'before_bones.json').read_text())['original']
variant=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'vertical';title=variant.title();src=O/'RejectedForwardThumb'/'m4'/variant;D=O/'m4'/variant;D.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'m4'/variant/f'A_M4_{title}_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};basis={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
fit=json.loads((src/'fit_final.json').read_text());G=old['WPN_root']@Matrix(fit['grip_in_root']);H=old['hand_l'].copy();prefix='VG_' if variant=='vertical' else 'PH_';ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();faces={};ids={}
for digit in ['index','middle','ring','pinky','thumb']:
 ids[digit]={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids[digit] for i in t.vertices)]
hf=[tuple(t.vertices) for t in ob.data.loop_triangles if any(sum(g.weight for g in ob.data.vertices[i].groups if groups[g.group].endswith('_l') and groups[g.group].startswith(('index','middle','ring','pinky','thumb')))>.5 for i in t.vertices)]
gv=[];gf=[]
for part in s.objects:
 if part.type!='MESH' or not part.name.startswith(prefix):continue
 e=part.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();off=len(gv);gv.extend([e.matrix_world@v.co for v in m.vertices]);gf.extend([tuple(i+off for i in t.vertices) for t in m.loop_triangles]);e.to_mesh_clear()
gt=BVHTree.FromPolygons(gv,gf,all_triangles=True)
def pose(x):
 down,dy,dz,roll,pip,dip=x;p={n:m.copy() for n,m in old.items()};p['hand_l']=H.copy();p['hand_l'].translation-=G.to_3x3()@Vector((0,0,down*.001))
 yaw,elev=math.radians(dy),math.radians(dz);root_dir=G.to_3x3()@Vector((math.cos(elev)*math.cos(yaw),math.cos(elev)*math.sin(yaw),math.sin(elev)))
 for b in r.pose.bones:
  n=b.name
  if not n.endswith('_l') or not n.startswith(('index','middle','ring','pinky','thumb')):continue
  lr=rest[b.parent.name].inverted()@rest[n];q=basis[n].to_quaternion()
  if n.startswith('thumb'):
   j=int(n.split('_')[1]);m=p[b.parent.name]@lr
   if j==1:
    natural=m@Matrix(ORIG[n]['basis']);axis=(rest[n].inverted()@rest['thumb_02_l']).translation
    direction=(natural.to_3x3()@axis).normalized();q=direction.rotation_difference(root_dir)@natural.to_quaternion();q=Quaternion(root_dir,math.radians(roll))@q
    p[n]=Matrix.LocRotScale(m.translation,q,m.to_scale())
   else:p[n]=m@Quaternion((0,0,1),math.radians(pip if j==2 else dip)).to_matrix().to_4x4()
   continue
  p[n]=p[b.parent.name]@lr@q.to_matrix().to_4x4()
 apply(r,p,rest);return p
def evaluate(x):
 pose(x);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@z.co for z in m.vertices];trees={d:BVHTree.FromPolygons(v,f,all_triangles=True) for d,f in faces.items()};selfhit=sum(len(trees['thumb'].overlap(trees[d])) for d in ['index','middle','ring','pinky']);hit=len(BVHTree.FromPolygons(v,hf,all_triangles=True).overlap(gt));tipids=[i for i in ids['thumb'] if any(groups[g.group]=='thumb_03_l' and g.weight>.6 for g in ob.data.vertices[i].groups)];axis=(r.matrix_world.to_3x3()@r.pose.bones['thumb_03_l'].matrix.to_3x3()@(rest['thumb_02_l'].inverted()@rest['thumb_03_l']).translation).normalized();tipids=sorted(tipids,key=lambda i:v[i].dot(axis),reverse=True)[:16];gap=sum(trees['index'].find_nearest(v[i])[3] for i in tipids)/len(tipids);near=sum(sorted(gt.find_nearest(v[i])[3] for i in ids['thumb'])[:8])/8;e.to_mesh_clear()
 cost=(hit+selfhit)*20+abs(gap-.001)*400+max(near-.008,0)*100 + x[0]*.002 + (x[1]+45)**2*.00008+x[3]*x[3]*.00005+(x[4]-35)**2*.0002+(x[5]-35)**2*.0002
 return cost,hit,selfhit,gap,near
best=None
for down,dy,dz,roll,pip,dip in itertools.product([0],[-50,-30,-10],[10,25,35],[-15,0,15],[25,40,55],[25,40,55]):
 x=[down,dy,dz,roll,pip,dip];score=evaluate(x)
 if best is None or score[0]<best[0][0]:best=(score,x);print('THUMB_BEST',variant,best,flush=True)
lo=[0,-60,0,-25,25,25];hi=[2,5,40,25,55,55]
for steps in [[.5,5,5,5,5,5],[.25,2,2,2,2,2],[.1,1,1,1,1,1]]:
 for repeat in range(2):
  for k,step in enumerate(steps):
   for sign in [-1,1]:
    x=best[1].copy();x[k]+=step*sign
    if not lo[k]<=x[k]<=hi[k]:continue
    score=evaluate(x)
    if score[0]<best[0][0]:best=(score,x)
  print('THUMB_REFINE',variant,best,flush=True)
p=pose(best[1]);arm={'preserved_existing_arm':True};apply(r,p,rest);fit['hand_in_root']=[list(a) for a in p['WPN_root'].inverted()@p['hand_l']];fit['basis']={n:[list(a) for a in r.pose.bones[n].matrix_basis] for n in fit['basis']};fit['front_refinement']={'parameters':best[1],'metrics':best[0],'arm':arm,'method':'opposed thumb: original reference axial roll, bounded root swing, local MCP/IP flexion toward index'}
(D/'fit_final.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(D/'Fitted.blend'));render(r,fit,'opposed_'+variant);print('FRONT_FIT',variant,best,arm,flush=True)
