"""Dense anatomical metrics and rendered native/UE-compressed contact poses."""
from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import gzip,numpy as np,sys
from mathutils.bvhtree import BVHTree
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Before'
folder=O/'Review'/label;folder.mkdir(parents=True,exist_ok=True)
source=O/'Review/compressed.json.gz' if label=='Compressed' else O/'authored.json.gz'
with gzip.open(source,'rt') as f:data=json.load(f)
rate=data['rate'];skin=bpy.data.objects['M24_V9_BareArms'];r.matrix_world=Matrix.Identity(4)
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text();exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
tree=ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full');exec(compile(ast.unparse(node),'morphs','exec'))
with bpy.data.libraries.load(str(O/'M24_Bipod_Editable.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('M24Bipod_')]
parts=dst.objects
for ob in parts:s.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.color=(.7,.43,.13,1)
for n in ('M24_silencer','M24_ExtraScope_Lowpoly','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly','M24_bullet','M24_Magazine10'):bpy.data.objects[n].hide_render=True
bpy.data.objects['M24_clip'].hide_render=False
geo=json.loads((O/'geometry.json').read_text());pivots=[K.to_3x3()@Vector(geo['parts'][k]['pivot_cm'])/100 for k in ('LegA','LegB')];tips=[K.to_3x3()@Vector(v)/100 for v in geo['tips_cm']]
closed=[tips[i].normalized().rotation_difference(Vector((-.005 if i==0 else .005,tips[i].length,0)).normalized()) for i in (0,1)]
def sample_pose(t,family='base'):
 frames=data['clips'][family]['frames'];f=min(t*rate,len(frames)-1);i=min(int(f),len(frames)-2);w=f-i;row={}
 for j,n in enumerate(names):
  a,b=unpack(frames[i][j]),unpack(frames[i+1][j]);local=K@Matrix.LocRotScale(a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w))@K
  row[n]=row[parents[n]]@local if parents[n] else local
 return row
def set_pose(row,t,frame=Matrix.Identity(4)):
 r.matrix_world=frame;r.animation_data_clear()
 for n,m in row.items():
  loc=row[parents[n]].inverted()@m if parents[n] else m;r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
 root=frame@row['WPN_root']@rest['WPN_root'].inverted()
 for ob in parts:
  i=0 if '_LegA_' in ob.name else 1 if '_LegB_' in ob.name else -1
  q=closed[i].slerp(Quaternion(),ease((t-(.45 if i==0 else 1.20))/.40)) if i>=0 else Quaternion()
  ob.matrix_world=root@Matrix.LocRotScale(pivots[i] if i>=0 else Vector(),q,Vector((1,1,1)))
 bpy.context.view_layer.update();morphs_full()
metrics=[];start=sample_pose(0);baseline={n:start[parents[n]].inverted()@m if parents[n] else m for n,m in start.items()};previous=None
for i in range(round((len(data['clips']['base']['frames'])-1)/rate*240)+1):
 t=i/240;row=sample_pose(t);a=row['lowerarm_l'].translation-row['upperarm_l'].translation;b=row['hand_l'].translation-row['lowerarm_l'].translation;c=row['middle_01_l'].translation-row['hand_l'].translation
 local={n:row[parents[n]].inverted()@m if parents[n] else m for n,m in row.items()}
 errors={n:(local[n].translation-baseline[n].translation).length*1000 for n in names if n.endswith('_l') and n not in ('clavicle_l','ik_hand_l')}
 jump=max((math.degrees(2*math.acos(min(1,abs(previous[n].normalized().dot(local[n].to_quaternion().normalized()))))) for n in names if n.endswith('_l')),default=0) if previous else 0
 previous={n:m.to_quaternion() for n,m in local.items()}
 metrics.append({'t':t,'elbow_degrees':angle(a,b),'wrist_axis_degrees':angle(b,c),'bone_length_error_mm':max(errors.values()),'angular_step_degrees':jump,'wrist_cm':list(C@row['hand_l'].translation),'elbow_cm':list(C@row['lowerarm_l'].translation)})
s.render.resolution_x=720;s.render.resolution_y=480
for t in (0,.32,.45,.65,.85,1.02,1.20,1.40,1.60,1.78,1.92,2.05):
 row=sample_pose(t)
 for view in ('fps','left'):
  if view=='fps':
   set_pose(row,t,cs@C);cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
  else:
   set_pose(row,t);root=row['WPN_root']@rest['WPN_root'].inverted();target=(row['hand_l'].translation+row['lowerarm_l'].translation)*.5+root.to_3x3()@Vector((.02,.035,.025))
   cam.location=target+root.to_3x3()@Vector((-.43,-.20,.16));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.48
  s.render.filepath=str(folder/(f'{t:.3f}_{view}.png'));bpy.ops.render.render(write_still=True)
(folder/'geometry.json').write_text(json.dumps(metrics,indent=2));print('M24_BIPOD_REVIEW_READY',label,flush=True)
