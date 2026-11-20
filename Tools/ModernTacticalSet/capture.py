"""Read current native binding references for this new equipment family."""
import gc,json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/Integration';I=R/'Inputs'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
c=read(P/'Content/ColdSteelData/modular_outfits.json');b=read(P/'Content/ColdSteelData/player_body.json')
for name in ['modular_outfits.json','player_body.json','items.json']:
    (I/name).write_bytes((P/'Content/ColdSteelData'/name).read_bytes())
refs={}
for rig,path in c['items']['ue_original_gloves']['rig_meshes'].items():refs['Gloves_'+rig]=path
refs['Body_Jason']=c['profiles'][b['body_mesh']]['native_bare_skin']
female=c['body_variants']['kaitlin'];fb=b['body_variants']['kaitlin']
refs['Body_Kaitlin']=female['profiles'][fb['body_mesh']]['native_bare_skin']
refs['Gloves_Kaitlin']=female['items']['ue_original_gloves']['rig_meshes']['Kaitlin']
rows={};G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
for key,path in refs.items():
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing source '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm)
    def xyz(v):return [v.x,v.y,v.z]
    data=dict(source=path,skeleton=asset.skeleton.get_path_name(),bones=[dict(name=str(v.name),index=v.index,parent=v.parent_index,position=xyz(v.world_transform.translation),axes=[xyz(v.world_transform.transform_location(a)-v.world_transform.translation) for a in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for v in bones],materials=[m.material_interface.get_path_name() if m.material_interface else '' for m in asset.materials])
    file=I/(key+'.json');file.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');rows[key]=dict(file=str(file),asset=path)
    del dm,asset;gc.collect();u.SystemLibrary.collect_garbage();print('TS01_BIND_SOURCE',key,flush=True)
(R/'captured.json').write_text(json.dumps(dict(completed=True,rows=rows),indent=2),encoding='utf-8')
# Inventory is handled by the project's native commandlet in grant_inventory.ps1.
print('TS01_CAPTURE_COMPLETE',len(rows),flush=True)
