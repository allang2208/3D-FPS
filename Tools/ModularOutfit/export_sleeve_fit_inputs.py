"""Read the existing sleeve surface and requested clothing-simulation state."""
import json
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925/FittedSleevesV1'
ROOT.mkdir(parents=True,exist_ok=True)
config=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
report={}
for source,profile in config['profiles'].items():
    name=profile['rig_profile'];path=profile['shirt'];asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing sleeve source '+name)
    clothes=asset.get_editor_property('mesh_clothing_assets')
    report[name]={'mesh':path,'clothing_assets':[c.get_path_name() for c in clothes]}
    if name!='M4':continue
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read original sleeve mesh')
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    weights=[];uv=[];normals=[]
    for vi in range(len(ps)):
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing sleeve weights')
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for fi in range(len(ts)):
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,fi)
        if not valid:raise RuntimeError('Missing sleeve UV')
        uv.append([[v.x,v.y] for v in (a,b,c)])
        _,a,b,c,valid=Q.get_triangle_normals(dm,fi)
        if not valid:raise RuntimeError('Missing sleeve normals')
        normals.append([xyz(v) for v in (a,b,c)])
    data={'source':path,'positions':[xyz(v) for v in ps],'triangles':[xyz(t) for t in ts],
          'weights':weights,'uv':uv,'normals':normals,
          'bones':{str(b.name):{'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),
                   'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation)
                           for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones}}
    (ROOT/'M4_shirt_before.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
witch=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
if not witch:raise RuntimeError('Missing current Witch asset')
report['Witch']={'mesh':witch.get_path_name(),'clothing_assets':[c.get_path_name() for c in witch.get_editor_property('mesh_clothing_assets')]}
(ROOT/'cloth-state-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('SLEEVE_INPUTS_SAVED',len(report),'cloth counts',{k:len(v['clothing_assets']) for k,v in report.items()},flush=True)
