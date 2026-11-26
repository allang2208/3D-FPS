"""Read the saved front faces, repair the confirmed winding mismatch, then read back."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/IceArmor20261017/RuntimeVisibilityV4';OUT.mkdir(parents=True,exist_ok=True)
def inspect_mesh(name):
    asset=u.load_asset(name);dm=u.DynamicMesh();g=u.GeometryScript_AssetUtils
    if isinstance(asset,u.StaticMesh):dm,status=g.copy_mesh_from_static_mesh(asset,dm,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    else:dm,status=g.copy_mesh_from_skeletal_mesh(asset,dm,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not read '+name)
    samples=[]
    for ti in range(0,dm.get_triangle_count(),max(1,dm.get_triangle_count()//100)):
        vertices=[v for v in u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti) if isinstance(v,u.Vector)]
        normals=[v for v in u.GeometryScript_MeshQueries.get_triangle_normals(dm,ti) if isinstance(v,u.Vector)]
        a,b,c=vertices;cross=(b-a).cross(c-a);n=normals[0]
        length=cross.length()
        if length<1e-8:continue
        samples.append({'triangle':ti,'dot':cross.dot(n)/length,'cross':[cross.x/length,cross.y/length,cross.z/length],'normal':[n.x,n.y,n.z]})
    return {'asset':name,'triangles':dm.get_triangle_count(),'min_dot':min(v['dot'] for v in samples),'max_dot':max(v['dot'] for v in samples),'mean_cross_x':sum(v['cross'][0] for v in samples)/len(samples),'samples':samples[:8]}
BASE='/Game/Skills/IceArmor20261017/CrystalV2/'
rows=[inspect_mesh(name) for name in ('/Engine/BasicShapes/Plane',BASE+'SM_IceArmor_Clusters',BASE+'SK_IceArmor_Torso_0')]
(OUT/'winding-before.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('ICE_ARMOR_WINDING_BEFORE '+json.dumps([{k:v for k,v in row.items() if k!='samples'} for row in rows]),flush=True)
if rows[0]['max_dot']>-.99 or rows[1]['mean_cross_x']>=0:
    raise RuntimeError('Saved front-face convention does not match the diagnosed source mismatch; preserve assets.')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import import_ice_armor_winding_v4
names=[f'SK_IceArmor_{part}_{profile}' for part in ('Torso','Arms','Legs') for profile in range(3)]+['SM_IceArmor_Clusters','SM_IceArmor_Chip']
after=[inspect_mesh(BASE+name) for name in names]
(OUT/'winding-after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
for row in after:
    if row['max_dot']>-.98:raise RuntimeError('Saved ice face still disagrees with native UE winding: '+row['asset'])
if after[-2]['mean_cross_x']<=0:raise RuntimeError('The lens still faces away from the eye')
print('ICE_ARMOR_WINDING_V4_READBACK_OK '+str(len(after)),flush=True)
