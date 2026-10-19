"""Extend the current Saiga magazine along its measured centreline, in centimetres."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KMagazine20261017'
G=json.loads((O/'Input/factory.json').read_text());p=np.array(G['positions']);tri=np.array(G['triangles']);ns=np.array(G['normals']);uvs=np.array(G['uv0'])
# Corresponding outer-shell stations, excluding throat hardware and floorplate.
# These come from the current native source's longitudinal shell edges.
rear=np.array([[9.681,-1.983],[10.628,-7.267],[11.602,-10.528],[12.382,-13.174]])
front=np.array([[16.232,-.710],[18.047,-6.910],[19.157,-9.104],[20.043,-10.346]])
stations=(rear+front)*.5
fit=np.linalg.lstsq(np.c_[2*stations,np.ones(len(stations))],(stations*stations).sum(1),rcond=None)[0]
centre=fit[:2];radius=float(np.linalg.norm(stations-centre,axis=1).mean());extra=7.0;angle=extra/radius
cut_angle=math.asin((centre[1]+5.0)/radius)
tangent=np.array([0.,math.sin(cut_angle),-math.cos(cut_angle)])
cut=np.array([.08,centre[0]-radius*math.cos(cut_angle),centre[1]-radius*math.sin(cut_angle)])
origin=np.array([0.,*centre])
def rotate(v,a,point=True):
 v=np.array(v)-(origin if point else 0);c,s=math.cos(a),math.sin(a);out=np.array([v[0],v[1]*c-v[2]*s,v[1]*s+v[2]*c]);return out+(origin if point else 0)
def interp(a,b,t):
 return {'p':a['p']+(b['p']-a['p'])*t,'n':a['n']+(b['n']-a['n'])*t,'uv':a['uv']+(b['uv']-a['uv'])*t}
def clip(poly,upper):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=float(np.dot(a['p']-cut,tangent));db=float(np.dot(b['p']-cut,tangent));ina=da<=1e-8 if upper else da>=-1e-8;inb=db<=1e-8 if upper else db>=-1e-8
  if ina:out.append(a)
  if ina!=inb:out.append(interp(a,b,da/(da-db)))
 return out
verts=[];faces=[];normals=[];uv0=[];new_faces=[]
def emit(poly,added=False):
 for j in range(1,len(poly)-1):
  row=[poly[0],poly[j],poly[j+1]]
  if np.linalg.norm(np.cross(row[1]['p']-row[0]['p'],row[2]['p']-row[0]['p']))<1e-9:continue
  start=len(verts);verts.extend([v['p'].tolist() for v in row]);faces.append([start,start+1,start+2]);normals.append([v['n'].tolist() for v in row]);uv0.append([v['uv'].tolist() for v in row]);new_faces.append(added)
segments=0
for fi,tt in enumerate(tri):
 poly=[{'p':p[v].copy(),'n':ns[fi,k].copy(),'uv':uvs[fi,k].copy()} for k,v in enumerate(tt)]
 basis=np.stack((poly[1]['p']-poly[0]['p'],poly[2]['p']-poly[0]['p']),1)
 jac=np.stack((poly[1]['uv']-poly[0]['uv'],poly[2]['uv']-poly[0]['uv']),1)@np.linalg.pinv(basis)
 upper=clip(poly,True);lower=clip(poly,False);emit(upper)
 for v in lower:v['p']=rotate(v['p'],angle);v['n']=rotate(v['n'],angle,False)
 emit(lower)
 if len(upper)<3 or len(lower)<3:continue
 # The oriented boundary of the retained factory upper shell owns the sweep.
 edges=[(a,b) for a,b in zip(upper,upper[1:]+upper[:1]) if abs(np.dot(a['p']-cut,tangent))<1e-6 and abs(np.dot(b['p']-cut,tangent))<1e-6]
 if not edges:continue
 a,b=max(edges,key=lambda e:np.linalg.norm(e[0]['p']-e[1]['p']))
 if np.linalg.norm(a['p']-b['p'])<1e-7:continue
 segments+=1
 # UV derivatives are interpolated from this actual source triangle. The
 # upper shell's UVs remain exact; no unrelated receiver atlas is projected.
 def at(v,t):
  n=v['n']/max(np.linalg.norm(v['n']),1e-12);rad=v['p']-origin;velocity=np.array([0.,-rad[2],rad[1]])*angle
  correction=-n*np.dot(n,velocity);q=t*(1-t)*(1-2*t)
  pp=rotate(v['p']+correction*q,angle*t);nn=rotate(n,angle*t,False)
  return {'p':pp,'n':nn,'uv':v['uv']+(jac@velocity)*t}
 for j in range(20):
  lo=j/20;hi=(j+1)/20;emit([at(b,lo),at(a,lo),at(a,hi),at(b,hi)],True)

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
# Weld positions for UV island continuity, retaining every original corner normal.
unique={};points=[];mapping=[]
for v in verts:
 key=tuple(round(x,6) for x in v)
 if key not in unique:unique[key]=len(points);points.append((v[0],-v[1],v[2]))
 mapping.append(unique[key])
me=bpy.data.meshes.new('Saiga12K_Ext12');me.from_pydata(points,[],[[mapping[v] for v in f[::-1]] for f in faces]);me.update()
ob=bpy.data.objects.new('Saiga12K_Ext12',me);scene.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
for f in me.polygons:f.use_smooth=True
me.normals_split_custom_set([(v[0],-v[1],v[2]) for row in normals for v in row[::-1]])
me.uv_layers.new(name='UV0');me.uv_layers.new(name='UV1');uv=me.uv_layers['UV0']
for fi,f in enumerate(me.polygons):
 for li,v in zip(f.loop_indices,uv0[fi][::-1]):uv.data[li].uv=(v[0],1-v[1])
me.uv_layers.active_index=1
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.002,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
mat=bpy.data.materials.new('Saiga12K_MagazinePolymer_WS11');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.019,.019,.018,1);bs.inputs['Metallic'].default_value=0.;bs.inputs['Roughness'].default_value=.53;me.materials.append(mat)
frame=G['socket_frame_cm'];offset=np.array(frame['origin']);matrix=(np.array(frame['axes'])-offset).T
data={'source':G['source'],'positions':[],'root_positions':[],'triangles':[],'normals':[],'uv0':[],'uv1':[],'frame':'WPN_SOCKET_Magazine centimetres; runtime scale .01','uv_per_cm':{}}
for v in me.vertices:
 root=np.array([v.co.x,-v.co.y,v.co.z]);data['root_positions'].append(root.tolist());data['positions'].append((matrix@root+offset).tolist())
uv0_layer=me.uv_layers['UV0'];uv1_layer=me.uv_layers['UV1'];area=uvarea=0.
for f in me.polygons:
 ids=list(f.loop_indices)[::-1];data['triangles'].append([me.loops[i].vertex_index for i in ids]);data['normals'].append([(matrix@np.array([me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z])).tolist() for i in ids])
 for name,layer in [('uv0',uv0_layer),('uv1',uv1_layer)]:data[name].append([[float(layer.data[i].uv.x),1-float(layer.data[i].uv.y)] for i in ids])
 a,b,c=np.array(data['uv0'][-1]);uvarea+=abs(float(np.cross(b-a,c-a)))*.5;area+=f.area
data['uv_per_cm']['uv0']=math.sqrt(uvarea/area)
(O/'Authoring/magazine.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_Ext12.blend'),compress=True)
report={'source_triangles':len(tri),'triangles':len(faces),'extension_cm':extra,'retained_cut_root_cm':cut.tolist(),'curve_center_root_yz_cm':centre.tolist(),'curve_radius_cm':radius,'floorplate_rotation_degrees':math.degrees(angle),'source_section_segments':segments,'capacity':12,'runtime_tested':False}
(O/'Authoring/recipe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SAIGA_EXT12_GEOMETRY_SAVED',len(faces),flush=True)
# Independent mask for the new UV1. Factory gun/hand UVs are never rewritten.
sys.path.insert(0,str(P/'SourceAssets/WeaponSurface20260930/A762'));import bake_a762 as bake
bake.EDGE_RADIUS=.05;bake.RAYS=24;bake.setup_cycles();original=ob
copy=ob.copy();copy.data=ob.data.copy();copy.name='Saiga12K_Ext12_BAKE';scene.collection.objects.link(copy);original.hide_render=True;original.hide_set(True)
bake.select_only(copy);bake.densify(copy,max_edge=.30,rounds=5);bake.vertex_masks(copy)
image=bpy.data.images.new('Saiga_Ext12_Mask_Bake',1024,1024,alpha=True,float_buffer=True);image.colorspace_settings.name='Non-Color';bake.bake(copy,image,'UV1');report['mask']=bake.finish(image,O/'Textures/T_Saiga12K_Ext12_Mask.png')
report['complete']=True;(O/'Receipts/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SAIGA_EXT12_MASK_SAVED',flush=True)
