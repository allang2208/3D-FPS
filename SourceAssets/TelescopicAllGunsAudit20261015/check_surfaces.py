"""Inspect all exported stocks and render their effective primary structural normal."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'capture.json').read_text());V=O/'Preview';V.mkdir(exist_ok=True)
R={'scope':'10 catalog users of tactical_telescopic','read_only':True,'render':'Blender, constant metal, effective primary structural normal only; not complete UE material or host assembly','assets':{}}
body_slots={'M4':[0,1,2],'AKM':[0,1,2],'QBZ191':[0,1,2],'M16':[1,2,3],'HK416':[0,1,2],'A762':[1,2,3],'PKM':[1,2,3],'SVD':[0,1,2],'LMG201':[1,2,3],'Super90':[0,1,2]}
for key,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 bpy.ops.import_scene.fbx(filepath=row['export']);obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];stats={'meshes':[],'uses_R2':False,'body_collapsed_uv0_faces':0,'invalid_corner_normals':0}
 body_names={row['slots'][i]['material'].split('.')[-1] for i in body_slots[key]}
 rubber_name=row['slots'][body_slots[key][2]]['material'].split('.')[-1]
 points=[];rubber=[]
 for ob in obs:
  me=ob.data;coords=np.asarray([tuple(v.co) for v in me.vertices]);tris=np.asarray([list(f.vertices) for f in me.polygons]);norm=np.asarray([tuple(n.vector) for n in me.corner_normals])
  body_ids={i for i,m in enumerate(me.materials) if m and any(m.name==n or m.name.startswith(n+'_') or m.name.startswith(n+'.') for n in body_names)}
  body=np.asarray([f.material_index in body_ids for f in me.polygons]);p3=coords[tris];area=np.linalg.norm(np.cross(p3[:,1]-p3[:,0],p3[:,2]-p3[:,0]),axis=1)/2
  uvstats=[]
  for layer in me.uv_layers:
   uv=np.asarray([tuple(c.uv) for c in layer.data]).reshape(-1,3,2);a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0];uvarea=abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
   uvstats.append({'name':layer.name,'collapsed_nondegenerate_body_faces':int(np.sum(body&(area>1e-12)&(uvarea<1e-14)))})
  invalid=int(np.sum(~np.isfinite(norm).all(axis=1)|(np.linalg.norm(norm,axis=1)<.9)))
  stats['invalid_corner_normals']+=invalid;stats['body_collapsed_uv0_faces']+=uvstats[0]['collapsed_nondegenerate_body_faces'] if uvstats else int(body.sum())
  stats['meshes'].append({'triangles':len(me.polygons),'material_face_counts':{m.name:sum(f.material_index==i for f in me.polygons) for i,m in enumerate(me.materials)},'uv_layers':uvstats,'invalid_corner_normals':invalid})
  for f in me.polygons:
   if not body[f.index]:continue
   for vi in f.vertices:
    p=ob.matrix_world@me.vertices[vi].co;points.append(tuple(p))
    if me.materials[f.material_index].name.startswith(rubber_name):rubber.append(tuple(p))
  for i,mat in enumerate(list(me.materials)):
   source=next((s['material'] for s in row['slots'] if mat and (mat.name==s['material'].split('.')[-1] or mat.name.startswith(s['material'].split('.')[-1]+'.'))),None)
   normal=None
   if source:
    samples=D['materials'][source]['normal_samples']
    primary=next((s['texture'] for s in samples if s.get('texture') and any(n in s['texture'] for n in ('T_TacticalStock_Normal_Game','T_M16_Telescopic_MatchedNormal'))),None)
    if primary:
     normal=D['textures'][primary].get('source_file');stats['uses_R2']|='StructuralDetail_R2' in (normal or '')
   m=bpy.data.materials.new('Audit_'+str(i));m.use_nodes=True;nodes=m.node_tree.nodes;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.16,.17,.18,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.32
   if normal:
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(normal,check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=me.uv_layers[0].name;nm=nodes.new('ShaderNodeNormalMap');nm.uv_map=uv.uv_map
    links=m.node_tree.links;links.new(uv.outputs[0],tex.inputs['Vector']);links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal'])
   me.materials[i]=m
 pts=np.asarray(points);cov=np.cov(pts[:,:2].T);values,vectors=np.linalg.eigh(cov);axis=vectors[:,-1]
 if len(rubber) and np.dot(np.asarray(rubber).mean(axis=0)[:2]-pts.mean(axis=0)[:2],axis)<0:axis=-axis
 angle=math.atan2(axis[1],axis[0]);rot=Matrix.Rotation(-angle,4,'Z')
 for ob in obs:ob.matrix_world=rot@ob.matrix_world
 allpoints=[ob.matrix_world@v.co for ob in obs for v in ob.data.vertices]
 lo=Vector(tuple(min(p[i] for p in allpoints) for i in range(3)));hi=Vector(tuple(max(p[i] for p in allpoints) for i in range(3)));center=(lo+hi)/2;scale=max((hi-lo).x/ .86,(hi-lo).z/.50)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
 world=bpy.data.worlds.new('AuditWorld');world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.22,.24,.27,1);bg.inputs[1].default_value=.6;scene.world=world
 def aim(ob):ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
 for name,offset,power,size in [('Key',(-.3,-1.1,1.2),8,1.25),('Fill',(.7,-1.1,.28),3,.8),('Rim',(.5,.65,1),7,.9)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=power*(scale/.28)**2;d.shape='DISK';d.size=size*scale;ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=center+Vector(offset)*scale;aim(ob)
 cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);cam.location=center+Vector((.3,-2.3,.18))*scale;cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.data.clip_start=.001;aim(cam);scene.camera=cam
 scene.render.filepath=str(V/(key+'.png'));bpy.ops.render.render(write_still=True)
 stats['preview']=scene.render.filepath;stats['unchanged_since_R1']=row['unchanged_since_R1'];stats['matches_accepted_M16']=row['matches_accepted_M16'];R['assets'][key]=stats
 (O/'surface_audit.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SURFACE_AUDIT',key,stats['uses_R2'],stats['body_collapsed_uv0_faces'],flush=True)
