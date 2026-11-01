import bpy,numpy as np,json,gzip,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
exec(compile((Path(__file__).parent/'motion.py').read_text().split("\nif __name__=='__main__':")[0],'motion','exec'))
assets=json.load(gzip.open(O/'saved_geometry.json.gz','rt'))
G=json.loads((O/'kaitlin_skin_geometry.json').read_text());P=np.array(G['positions'])*[.01,-.01,.01]
F=np.array([f['vertices'] for f in G['faces']]);W=np.zeros((len(P),len(names)))
for i,ws in G['weights'].items():
 for n,w in ws.items():
  if n in indices:W[int(i),indices[n]]=w
handbones=[j for j,n in enumerate(names) if under(n,'hand_r')]
hand=W[:,handbones].sum(1)>.5;arm=W[:,[j for j,n in enumerate(names) if n.endswith('_r')]].sum(1)>.5
labels=[]
for i in range(len(P)):
 n=names[int(np.argmax(W[i]))]
 labels.append(next((f for f in ('thumb','index','middle','ring','pinky') if n.startswith(f)),'palm'))
labels=np.array(labels);HP=np.c_[P,np.ones(len(P))];rest_inv={n:np.linalg.inv(np.array(m)) for n,m in rest.items()}
def skin(row,G=G,P=P,W=W):
 out=np.zeros((len(P),4));hp=np.c_[P,np.ones(len(P))]
 for j,n in enumerate(names):
  ids=np.where(W[:,j]>.000001)[0]
  if len(ids):out[ids]+=(hp[ids]@(np.array(row[n])@rest_inv[n]).T)*W[ids,j,None]
 return out[:,:3]
def source_pose(family,role,time):
 row,_=compose(entry(family,role),float(time));inverse=np.linalg.inv(np.array(row['WPN_root']@rest['WPN_root'].inverted()))
 p=skin(row);return (np.c_[p,np.ones(len(p))]@inverse.T)[:,:3],row
def geo(key):return np.array(assets[key]['positions'])*[.01,-.01,.01],np.array(assets[key]['triangles'])
trees={}
for key in ('Default','balanced','phantom','stable','receiver'):
 p,f=geo(key);trees[key]=BVHTree.FromPolygons(p,f,all_triangles=True)
directions=[Vector(v).normalized() for v in ((.810,.343,.476),(-.267,.886,.379),(.436,-.429,.791))]
def inside(tree,p):
 votes=0
 for d in directions:
  start=p.copy();n=0
  for k in range(30):
   loc,normal,index,distance=tree.ray_cast(start,d,2.)
   if loc is None:break
   n+=1;start=loc+d*.0000004
  votes+=n%2
 return votes>=2
def metric(X,key,ids=None,verify=True):
 if ids is None:ids=np.flatnonzero(hand)
 bvh=trees[key];result={'inside_over_1mm':0,'max_penetration_mm':0,'by_region':{},'deepest':None,'near_surface_under_2mm':0};depths=[]
 for i in ids:
  p=Vector(X[i]);loc,n,j,d=bvh.find_nearest(p)
  if d is None:continue
  if d<.002:result['near_surface_under_2mm']+=1
  inward=(p-loc).dot(n)<0
  if inward and (not verify or inside(bvh,p)):
   mm=d*1000;lab=labels[i];depths.append((mm,int(i)))
   if mm>1:result['inside_over_1mm']+=1
   group=result['by_region'].setdefault(lab,{'max_mm':0,'vertices_over_1mm':0});group['max_mm']=max(group['max_mm'],mm);group['vertices_over_1mm']+=int(mm>1)
 if depths:
  depth,i=max(depths);result['max_penetration_mm']=depth;result['deepest']={'id':i,'region':str(labels[i]),'source_position':X[i].tolist(),'weights':G['weights'][str(i)]}
 return result
def object_mesh(name,p,f,color):
 me=bpy.data.meshes.new(name);me.from_pydata(p,[],f);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.color=(*color,1)
 for poly in me.polygons:poly.use_smooth=True
 return ob
def render(X,tag,variant='Default',view='palm'):
 bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1400;s.render.resolution_y=1050;s.render.resolution_percentage=100
 s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('GripInspection');s.world.color=(.09,.11,.13)
 for key in ('receiver','front',variant):
  p,f=geo(key);object_mesh(key,p,f,(.14,.18,.21) if key!=variant else (.23,.25,.26))
 # The moving native trigger is drawn at its current saved reference geometry.
 # Its asset vertices are in component space; registered source maps agree at rest.
 host=assets['host'];h=np.array(host['positions'])*[.01,-.01,.01];hf=np.array(host['triangles']);hm=np.array(host['material_ids'])
 # Read actual native trigger from the retained source; it was not moved by the chassis pass.
 src=O.parent/'M24ReceiverContinuityV220261031/M24_ReceiverContinuityV2_Editable.blend'
 with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=['M24_trigger']
 ob=b.objects[0];bpy.context.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.color=(.36,.37,.38,1)
 object_mesh('ActualSavedKaitlinRightArm',X,F[arm[F].all(1)],(.64,.39,.24))
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=.205;s.camera=cam
 target=Vector((0,.022,.042))
 if view=='palm':cam.location=(.32,.25,.16)
 elif view=='back':cam.location=(-.34,-.06,.15)
 elif view=='trigger':cam.location=(.36,.02,.056)
 else:cam.location=(.30,-.24,.10)
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(tag+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':
 X,row=source_pose('skeleton_base','idle',0.)
 report={'baseline':{},'hand_source_bounds':[X[hand].min(0).tolist(),X[hand].max(0).tolist()],'grip_bounds':{},'hand_bone_in_source':list((row['WPN_root']@rest['WPN_root'].inverted()).inverted()@row['hand_r'].translation)}
 for key in ('Default','balanced','phantom','stable','receiver'):
  report['baseline'][key]=metric(X,key);p,f=geo(key);report['grip_bounds'][key]=[p.min(0).tolist(),p.max(0).tolist()]
 (O/'baseline_review.json').write_text(json.dumps(report,indent=2));print('BASELINE',json.dumps(report['baseline']),flush=True)
 for view in ('palm','back','trigger'):render(X,'idle_'+view,view=view)
