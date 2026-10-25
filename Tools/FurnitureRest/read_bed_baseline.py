"""Capture current bed routes, source/compressed poses and all eleven meshes."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedBaseline20261023'
REVIEW=OUT/'ReviewSaved';GEOMETRY=OUT/'Geometry'
REVIEW.mkdir(parents=True,exist_ok=True);GEOMETRY.mkdir(exist_ok=True)
configs={name:json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig'))
         for name in ('furniture_rest.json','apartment_furniture_rest.json')}
merged=json.loads(json.dumps(configs['furniture_rest.json']))
for key in ('types','clips'):merged[key].update(configs['apartment_furniture_rest.json'][key])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture']
for name,data in configs.items():(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
seed=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/RefineV2/authored.json').read_text())
assert body['body_mesh']==seed['mesh']
mesh=u.load_asset(seed['mesh'])
source={k:seed[k] for k in ('mesh','skeleton','names','parents','reference')};source['clips']={}
saved={k:seed[k] for k in ('mesh','skeleton','names','parents','reference')};saved['clips']={}
kinds={kind for kind,data in merged['types'].items() if data['lying']}
roles=[f'Rest.{kind}.{phase}' for kind in sorted(kinds) for phase in ('Enter','Idle','Exit')]
routes={role:body['clips'][role] for role in roles}
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
options={}
for key,mode in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=mode;options[key]=opt
for role,path in routes.items():
    clip=u.load_asset(path)
    if not clip or clip.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Bed clip mismatch '+role)
    duration=clip.get_play_length();frames={}
    for mode,rate in [('source',30),('compressed',15)]:
        count=round(duration*rate)+1;take=[]
        for j in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*j/(count-1),options[mode])
            take.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in source['names']])
        frames[mode]=take
    source['clips'][role]={'rate':30,'duration':duration,'frames':frames['source']}
    saved['clips'][role]={'duration':duration,'frames':frames['compressed'],'source_endpoints':[frames['source'][0],frames['source'][-1]],'asset':path,'evaluation':'compressed'}
    print('BED_BASELINE_POSE',role,flush=True)
(OUT/'authored.json').write_text(json.dumps(source,separators=(',',':')))
(REVIEW/'saved_poses.json').write_text(json.dumps(saved,separators=(',',':')))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def geometry(asset,skeletal=False):
    copier=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
    dm,status=copier(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Geometry copy '+asset.get_path_name())
    _,pv,_=Q.get_all_vertex_positions(dm,False);pv=L.convert_vector_list_to_array(pv)
    _,tv,_=Q.get_all_triangle_indices(dm,False);tv=L.convert_triangle_list_to_array(tv)
    data={'source':asset.get_path_name(),'positions':[xyz(v) for v in pv],'triangles':[xyz(t) for t in tv]}
    if skeletal:
        _,bones=B.get_all_bones_info(dm);data['bone_names']=[str(b.name) for b in bones];data['weights']=[]
        for i in range(len(pv)):
            _,ws,valid=B.get_vertex_bone_weights(dm,i);data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
    return data
(REVIEW/'body.json').write_text(json.dumps(geometry(mesh,True),separators=(',',':')))
index={};inventory=[]
for profile in merged['furniture']:
    if profile['slots'][0]['kind'] not in kinds:continue
    path=profile['mesh'];name=str(len(index))+'.json'
    (GEOMETRY/name).write_text(json.dumps(geometry(u.load_asset(path)),separators=(',',':')))
    index[path]=name;inventory.append(profile);print('BED_BASELINE_MESH',path,flush=True)
(GEOMETRY/'index.json').write_text(json.dumps(index,indent=2))
(OUT/'inventory.json').write_text(json.dumps({'types':sorted(kinds),'routes':routes,'furniture':inventory},ensure_ascii=False,indent=2),encoding='utf-8')
print('BED_BASELINE_COMPLETE',len(routes),len(index),flush=True)
