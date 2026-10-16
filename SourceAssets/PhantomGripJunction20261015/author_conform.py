import bpy,bmesh,json,sys,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,kdtree
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());key=sys.argv[sys.argv.index('--')+1];row=D['assets'][key];cfg=json.loads((O/'profiles.json').read_text())[key];slot=cfg['body_slot'];join=cfg['join'];limit=cfg['limit'];center=np.array(cfg['center']);N=len(cfg['delta']);HK=Matrix(json.loads((O.parent/'HK416Reworked20260930/authoring.json').read_text())['root_matrix'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.import_scene.fbx(filepath=row['fbx']);ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;xf=(HK.inverted() if key=='HK416' else Matrix.Identity(4))@ob.matrix_world;norm=[tuple((xf.to_3x3().inverted().transposed()@n.vector).normalized()) for n in me.corner_normals];me.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);me.normals_split_custom_set(norm)
oldpoints=np.array([tuple(v.co) for v in me.vertices]);oldmids=[f.material_index for f in me.polygons];old_materials=[m.name for m in me.materials]
# Current FBX keeps the used material slots in source order; pad unused inventory only at export.
for i,m in enumerate(me.materials):m.name=row['slots'][i]['name']
na=me.attributes.new('JoinCornerNormal','FLOAT_VECTOR','CORNER');na.data.foreach_set('vector',np.asarray(norm,dtype=np.float32).ravel())
body_ids={i for f in me.polygons if f.material_index==slot for i in f.vertices};normsum={i:Vector() for i in body_ids}
for f in me.polygons:
 if f.material_index==slot:
  for li in f.loop_indices:normsum[me.loops[li].vertex_index]+=Vector(norm[li])
kd=kdtree.KDTree(len(body_ids));body_list=list(body_ids)
for i,vi in enumerate(body_list):kd.insert(me.vertices[vi].co,i)
kd.balance()
bm=bmesh.new();bm.from_mesh(me);layer=bm.loops.layers.float_vector['JoinCornerNormal'];native_faces=[f for f in bm.faces if f.material_index!=slot];edges={e for f in native_faces for e in f.edges};verts={v for f in native_faces for v in f.verts}
bmesh.ops.bisect_plane(bm,geom=list(verts)+list(edges)+native_faces,dist=1e-8,plane_co=(0,0,join),plane_no=(0,0,1))
native_vertices={v for f in bm.faces if f.material_index!=slot for v in f.verts};delta=np.array(cfg['delta']);slope=np.array(cfg['slope_delta']);maxmove=0.;moved=0
def at(a,angle):
 f=(angle%(2*math.pi))/(2*math.pi)*N;i=int(f);w=f-i;return a[i%N]*(1-w)+a[(i+1)%N]*w
for v in native_vertices:
 if v.co.z>=limit:continue
 rel=np.array([v.co.x,v.co.y])-center;r=np.linalg.norm(rel)
 if r<1e-6:continue
 angle=math.atan2(rel[1],rel[0]);t=max(0,min(1,(v.co.z-join)/(limit-join)));d=at(delta,angle);s=at(slope,angle)
 # The end rim matches both measured radius and slope; the upper native neck stays exact.
 shift=d*(2*t**3-3*t*t+1)+s*(limit-join)*(t**3-2*t*t+t)
 if v.co.z<join:shift=d+s*(v.co.z-join)
 shift=max(-.0015,min(.0015,shift));v.co.x+=rel[0]/r*shift;v.co.y+=rel[1]/r*shift;maxmove=max(maxmove,abs(shift));moved+=abs(shift)>1e-9
bm.normal_update()
for f in bm.faces:
 if f.material_index==slot:continue
 for l in f.loops:
  if not join-.00001<=l.vert.co.z<limit:continue
  old=l[layer];w=max(0,min(1,(limit-l.vert.co.z)/(limit-join)));w=w*w*(3-2*w)
  rel=np.array([l.vert.co.x,l.vert.co.y])-center;theta=math.atan2(rel[1],rel[0]);r=at(cfg['body_radius'],theta);rt=at(cfg['body_radius_derivative'],theta);rz=at(cfg['body_z_slope'],theta);c,s=math.cos(theta),math.sin(theta);target=Vector((rt*s+r*c,-rt*c+r*s,-r*rz)).normalized()
  if target.dot(old)>.25:l[layer]=old.lerp(target,w).normalized()
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(me);bm.free()
norm=[tuple(n.vector.normalized()) if n.vector.length>1e-9 else (0,0,1) for n in me.attributes['JoinCornerNormal'].data]
for f in me.polygons:f.use_smooth=True
me.normals_split_custom_set(norm)
if key=='HK416':me.transform(HK)
while len(me.materials)<len(row['slots']):me.materials.append(bpy.data.materials.new(row['slots'][len(me.materials)]['name']))
ob.name=row['path'].rsplit('/',1)[1];bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;out=O/'Exports';out.mkdir(exist_ok=True);fbx=out/(key+'.fbx');blend=out/(key+'.blend')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False);bpy.ops.wm.save_as_mainfile(filepath=str(blend))
r={'fbx':str(fbx),'blend':str(blend),'body_slot':slot,'triangles':len(me.polygons),'join':join,'native_preserved_above':limit,'moved_native_vertices':int(moved),'max_displacement_mm':maxmove*1000,'whole_body_unchanged':True,'native_contact':'Current upper mounting surface unchanged','preserved_interface_triangles':'Native upper surface unchanged; lower transition conforms to current body'};(O/(key+'_authoring.json')).write_text(json.dumps(r,indent=2));print('JUNCTION_CONFORMED',key,r,flush=True)
