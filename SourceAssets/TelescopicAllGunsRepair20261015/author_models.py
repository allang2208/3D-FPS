"""Assemble original matched bodies with each current native interface, preserving corner data."""
import bpy,numpy as np,json,hashlib,shutil
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[1];X=O/'Working';F=O/'Final';F.mkdir(exist_ok=True)
D=json.loads((O/'inputs.json').read_text());R={'assets':{},'method':'original body with matched full-precision UV0 and corner normals; current per-host interfaces unchanged','gameplay_tested':False}
for key,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 bpy.ops.import_scene.fbx(filepath=str(P/'SourceAssets/TelescopicStockSurface20261014/Inputs'/(key+'.fbx')));baseline=next(o for o in bpy.context.scene.objects if o.type=='MESH')
 previous=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=row['export']);current=next(o for o in bpy.context.scene.objects if o not in previous and o.type=='MESH')
 plan=np.load(X/(key+'_plan.npz'));body_ids=set(plan['body_triangles'].tolist());body_slots=set(D['body_slots'][key]);body_normals=plan['normals'];body_uv=plan['uv0']
 # Keep all non-body geometry from the current, audited asset, not its historical source.
 groups=[(baseline,[f for f in baseline.data.polygons if f.index in body_ids],True),(current,[f for f in current.data.polygons if f.material_index not in body_slots],False)]
 uvcount=max(len(ob.data.uv_layers) for ob,_,_ in groups);color_names=list(dict.fromkeys(a.name for ob,_,_ in groups for a in ob.data.color_attributes))
 vertices=[];faces=[];mids=[];normals=[];uvs=[[] for _ in range(uvcount)];colors={n:[] for n in color_names};nonbody_count=0;fixed_invalid=[]
 for ob,polys,is_body in groups:
  me=ob.data;used=sorted({v for f in polys for v in f.vertices});remap={v:i+len(vertices) for i,v in enumerate(used)};vertices.extend(tuple(ob.matrix_world@me.vertices[v].co) for v in used)
  nm=ob.matrix_world.to_3x3().inverted().transposed()
  for f in polys:
   faces.append(tuple(remap[v] for v in f.vertices));mids.append(f.material_index)
   if not is_body:nonbody_count+=1
   for j,li in enumerate(f.loop_indices):
    n=Vector(body_normals[f.index,j]) if is_body else nm@me.corner_normals[li].vector
    if n.length<.9:
     n=nm@f.normal;fixed_invalid.append({'body':is_body,'face':f.index,'corner':j})
     if n.length<.9:raise RuntimeError('Unresolved zero normal '+key+' '+str(f.index))
    normals.append(tuple(n.normalized()))
    for channel in range(uvcount):
     v=body_uv[f.index,j] if is_body and channel==0 else me.uv_layers[channel].data[li].uv if channel<len(me.uv_layers) else (0,0)
     uvs[channel].append(tuple(v))
    for name in color_names:
     a=me.color_attributes.get(name);colors[name].append(tuple(a.data[li if a.domain=='CORNER' else me.loops[li].vertex_index].color) if a else (1,1,1,1))
 me=bpy.data.meshes.new('Matched_'+key);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new('SM_'+key+'_Telescopic_Matched',me);bpy.context.collection.objects.link(ob)
 for slot in row['slots']:
  mat=bpy.data.materials.new(slot['name']);me.materials.append(mat)
 for f,mid in zip(me.polygons,mids):f.material_index=mid;f.use_smooth=True
 for channel,values in enumerate(uvs):
  layer=me.uv_layers.new(name='UVmap_'+str(channel));layer.data.foreach_set('uv',np.asarray(values,dtype=np.float32).ravel())
 for name,values in colors.items():
  attr=me.color_attributes.new(name=name,type='FLOAT_COLOR',domain='CORNER');attr.data.foreach_set('color',np.asarray(values,dtype=np.float32).ravel())
 me.normals_split_custom_set(normals);me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
 # UV0 contains the correct bake for all body faces, including Super90's cut mouth.
 tri_uv=np.asarray(uvs[0]).reshape(-1,3,2);e0=tri_uv[:,1]-tri_uv[:,0];e1=tri_uv[:,2]-tri_uv[:,0];uvarea=abs(e0[:,0]*e1[:,1]-e0[:,1]*e1[:,0]);body=np.isin(mids,list(body_slots));collapsed=int(np.sum(body&(uvarea<2e-14)))
 if collapsed:raise RuntimeError('Restored source UV collapse '+key+' '+str(collapsed))
 for old in list(bpy.context.scene.objects):
  if old!=ob:bpy.data.objects.remove(old,do_unlink=True)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 out=F/key;out.mkdir(exist_ok=True);blend=out/(key+'_Matched_Editable.blend');fbx=out/('SM_'+key+'_Telescopic_Matched.fbx')
 bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 R['assets'][key]={'fbx':str(fbx),'blend':str(blend),'triangles':len(faces),'body_triangles':len(body_ids),'preserved_interface_triangles':nonbody_count,'uv0_collapsed_body_faces':collapsed,'uv_layers':uvcount,'vertex_colors':color_names,'localized_invalid_normal_repairs':fixed_invalid,'materials':[s['name'] for s in row['slots']]}
 (O/'production.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('MATCHED_MODEL_EXPORTED',key,len(faces),nonbody_count,'zero_normals',len(fixed_invalid),flush=True)
normal=P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/Textures/Normal_Game.png';outnormal=F/'T_TacticalStock_MatchedNormal.png';shutil.copy2(normal,outnormal)
R['normal']={'file':str(outnormal),'sha256':hashlib.sha256(outnormal.read_bytes()).hexdigest(),'strength':1};R['complete']=True;(O/'production.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
