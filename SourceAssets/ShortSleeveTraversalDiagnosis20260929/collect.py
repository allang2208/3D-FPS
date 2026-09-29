import json,unreal as u
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ShortSleeveTraversalDiagnosis20260929';c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
source='/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7.SK_Traversal_BareArmsV7'
paths={'shirt':c['items']['ue_field_sweater_charcoal']['rig_meshes']['Traversal'],'skin':c['profiles'][source]['native_bare_skin']}
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
for name,path in paths.items():
 mesh=u.load_asset(path);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
 _,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
 def tr(t):return dict(p=list(t.translation.to_tuple()),q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=list(t.scale3d.to_tuple()))
 _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps);_,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
 d=dict(source=path,rest={str(b.name):tr(b.world_transform) for b in bones},positions=[[p.x,p.y,p.z] for p in ps],triangles=[[t.x,t.y,t.z] for t in ts],weights=[],materials=[])
 for i in range(len(ps)):
  _,ws,valid=B.get_vertex_bone_weights(dm,i);d['weights'].append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
 for i in range(len(ts)):d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
 if name=='skin':
  d['poses']={};native=u.load_asset(source)
  for action,duration in [('Vault',.8),('Mantle',1.1),('Climb',2.25)]:
   clip=u.load_asset('/Game/Movement/Traversal/Native/A_Traversal_'+action);opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=native;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
   for fraction in [0,.2,.4,.6,.8,1]:
    time=duration*fraction;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
    d['poses'][action+'_'+str(time)]={str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bones}
 (R/(name+'.json')).write_text(json.dumps(d,separators=(',',':')))
 print('TRAVERSAL_DIAG_SOURCE',name,flush=True)
