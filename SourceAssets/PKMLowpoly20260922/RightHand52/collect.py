from pathlib import Path
import unreal as u,json,hashlib
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/PKMLowpoly20260922/RightHand52');I=P/'Inputs'
base='/Game/Weapons/PKMLowpoly20260922';mesh=u.load_asset(base+'/Accessories14/SK_PKM_Manny_Modular')
def pack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
config=json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
profile=next(v for v in config['profiles'].values() if v['rig_profile']=='PKM')
bare=u.load_asset(profile['native_bare_skin'])
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries
m,status=G.copy_mesh_from_skeletal_mesh(bare,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Bare mesh read failed')
_,bones=B.get_all_bones_info(m);names=[str(b.name) for b in bones];bn={b.index:str(b.name) for b in bones}
_,vs,_=Q.get_all_vertex_positions(m,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs)
_,ts,_=Q.get_all_triangle_indices(m,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
ids=sorted({v for t in ts for v in (t.x,t.y,t.z)});mp={v:i for i,v in enumerate(ids)};weights=[]
for vi in ids:
 _,ws,valid=B.get_vertex_bone_weights(m,vi);weights.append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
data=dict(asset=bare.get_path_name(),bones={str(b.name):dict(pack(b.world_transform),index=b.index,parent=b.parent_index) for b in bones},positions=[[vs[i].x,vs[i].y,vs[i].z] for i in ids],weights=weights,triangles=[[mp[v] for v in (t.x,t.y,t.z)] for t in ts])
(I/'bare.json').write_text(json.dumps(data,separators=(',',':')))
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.RAW
manifest=[]
for family in ['base','vertical','canted','prism','angled']:
 path=base+('/Animations/A_PKM_reload_empty' if family=='base' else '/Accessories14/Animations/'+family+'/A_PKM_'+family+'_reload_empty')
 anim=u.load_asset(path)
 if not anim:raise RuntimeError(path)
 count=anim.get_editor_property('data_model_interface').get_number_of_keys();frames=[]
 for i in range(count):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,anim.get_play_length()*i/(count-1),opt)
  frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
 disk=Path('D:/FPS3D/FPSGAME/Content')/(path.removeprefix('/Game/')+'.uasset')
 clip=dict(asset=path,duration=anim.get_play_length(),frames=frames,source_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),family=family)
 (I/(family+'.json')).write_text(json.dumps(clip,separators=(',',':')))
 manifest.append(dict(family=family,asset=path,keys=count,source_sha256=clip['source_sha256']))
 print('PKM52_READ',family,count,flush=True)
(P/'inputs.json').write_text(json.dumps(manifest,indent=2));print('PKM52_INPUTS_COMPLETE')
root=Path('D:/FPS3D/FPSGAME');outfits=root/'SourceAssets/ModularOutfit20260925';snapshot=[]
paths=[profile['native_bare_skin'],base+'/Accessories14/SK_PKM_Manny_Modular']+[config['items'][item]['rig_meshes']['PKM'] for item in ['ue_field_gloves','ue_field_gloves_black','ue_field_sweater']]
for path in paths:
 disk=root/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');snapshot.append(dict(asset=path,sha256=hashlib.sha256(disk.read_bytes()).hexdigest()))
(P/'mesh_inputs.json').write_text(json.dumps(snapshot,indent=2))
for family in ['BarePalmV7','HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']:
 (I/(family+'_source.json')).write_bytes((outfits/family/'Authored/PKM.json').read_bytes())
