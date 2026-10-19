import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';D='/Game/Weapons/Saiga12K/Detail20261018'
old=json.loads((P/'SourceAssets/Saiga12KDetail20261018/Receipts/assets.json').read_text());L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List
R={'assets':{},'materials':{},'api':{'lod_types':{n:str(getattr(u.GeometryScriptLODType,n)) for n in dir(u.GeometryScriptLODType) if n.isupper()}}}
for key in old['bindings']:
 path=old['mesh'] if key=='native' else old['ext12'] if key=='ext12' else D+'/Attachments/SM_Saiga12K_'+key;a=u.load_asset(path);slots=a.materials if key=='native' else a.static_materials;row={'path':a.get_path_name(),'slots':{},'normals':{}};R['assets'][key]=row
 if key=='native':
  sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);row['build_settings']=str(sk.get_lod_build_settings(a,0));continue
 dm,st=G.copy_mesh_from_static_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+key)
 _,vp,_=Q.get_all_vertex_positions(dm,False);vp=list(LS.convert_vector_list_to_array(vp));_,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(LS.convert_triangle_list_to_array(ts))
 for ti,t in enumerate(ts):
  mid,_=u.GeometryScript_Materials.get_triangle_material_id(dm,ti);name=str(slots[mid].material_slot_name);cross=(vp[t.y]-vp[t.x]).cross(vp[t.z]-vp[t.x]);length=cross.length()
  if length<1e-12:continue
  ns=[n for n in Q.get_triangle_normals(dm,ti) if isinstance(n,u.Vector)][:3];dot=sum(cross.dot(n)/length for n in ns)/len(ns);r=row['normals'].setdefault(name,{'count':0,'positive':0,'sum_dot':0});r['count']+=1;r['positive']+=dot>0;r['sum_dot']+=dot
 for slot in slots:
  m=slot.material_interface;row['slots'][str(slot.material_slot_name)]=m.get_path_name() if m else None
  if not isinstance(m,u.MaterialInstanceConstant) or m.get_path_name() in R['materials']:continue
  R['materials'][m.get_path_name()]={'base':m.get_base_material().get_path_name(),'parent':m.parent.get_path_name(),'scalars':{str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)},'vectors':{str(n):[getattr(L.get_material_instance_vector_parameter_value(m,n),c) for c in 'rgba'] for n in L.get_vector_parameter_names(m)},'textures':{str(n):(L.get_material_instance_texture_parameter_value(m,n).get_path_name() if L.get_material_instance_texture_parameter_value(m,n) else None) for n in L.get_texture_parameter_names(m)}}
R['api']['orientation']={cl+'.'+n:str(getattr(getattr(u,cl),n).__doc__) for cl in ('GeometryScript_Normals','GeometryScript_MeshEdits','GeometryScript_MeshRepair') for n in dir(getattr(u,cl)) if 'reverse' in n or 'flip' in n}
(O/'Reports/parts-before.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_PARTS_READ',len(R['assets']),len(R['materials']))
