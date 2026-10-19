import unreal as u,json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018'
for d in ('Reports','Receipts','Authoring','Preview','Textures','SourceBefore'):(O/d).mkdir(parents=True,exist_ok=True)
R={'worlds':[],'components':[],'assets':{},'api':{},'dirty':[]}
R['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
for kind,world in [('editor',sub.get_editor_world()),('game',sub.get_game_world())]:
 if not world:continue
 R['worlds'].append({'kind':kind,'path':world.get_path_name()})
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
 for actor in actors:
  for c in actor.get_components_by_class(u.MeshComponent):
   mesh=c.get_editor_property('skeletal_mesh') if isinstance(c,u.SkeletalMeshComponent) else c.static_mesh if isinstance(c,u.StaticMeshComponent) else None
   if not mesh or '/Saiga12K/' not in mesh.get_path_name():continue
   row={'actor':actor.get_path_name(),'component':c.get_path_name(),'mesh':mesh.get_path_name(),'transform':str(c.get_world_transform()),'visible':c.is_visible(),'materials':[]}
   for i in range(c.get_num_materials()):
    m=c.get_material(i)
    mr={'slot':i,'path':m.get_path_name() if m else None,'base':m.get_base_material().get_path_name() if m else None}
    if isinstance(m,u.MaterialInstance):
     try:mr['scalars']={k:u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(m,k) for k in ('Metallic','Roughness','SourceColorWeight','SourceRoughnessWeight','GrainRoughness','MaskUVChannel')}
     except Exception as e:mr['parameter_read_error']=str(e)
    row['materials'].append(mr)
   R['components'].append(row)
R['api']['read_lod']=u.GeometryScriptMeshReadLOD.__doc__
R['api']['lod_enums']={n:str(getattr(u,n).__doc__) for n in dir(u) if n.startswith('GeometryScript') and 'LOD' in n}
for key,path in [('saiga','/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny'),('known_akm','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')]:
 a=u.load_asset(path);dm,st=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List
 _,vp,_=Q.get_all_vertex_positions(dm,False);vp=list(LS.convert_vector_list_to_array(vp));_,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(LS.convert_triangle_list_to_array(ts));rows={};slots=a.materials
 for ti,t in enumerate(ts):
  mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti);name=str(slots[mid].material_slot_name)
  q=[vp[t.x],vp[t.y],vp[t.z]];cross=(q[1]-q[0]).cross(q[2]-q[0]);length=cross.length()
  if length<1e-12:continue
  ns=[n for n in Q.get_triangle_normals(dm,ti) if isinstance(n,u.Vector)][:3]
  dot=sum(cross.dot(n)/length for n in ns)/len(ns);r=rows.setdefault(name,{'count':0,'negative':0,'sum_dot':0});r['count']+=1;r['negative']+=dot<0;r['sum_dot']+=dot
 R['assets'][key]={'path':a.get_path_name(),'triangle_normals':rows,'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else None,'base':s.material_interface.get_base_material().get_path_name() if s.material_interface else None} for s in slots]}
 R['api']['skeletal_lod_methods']=[n for n in dir(u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)) if 'lod' in n or 'build' in n]
(O/'Reports/live-before.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print(json.dumps({'worlds':R['worlds'],'saiga_components':len(R['components']),'dirty_packages':len(R['dirty']),'report':str(O/'Reports/live-before.json')}))
