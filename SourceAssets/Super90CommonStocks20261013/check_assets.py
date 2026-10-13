"""Requested closeout: read production stocks without changing assets or player state."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];R={'assets':{},'errors':[],'gameplay_tested':False}
saved=json.loads((O/'install_receipt.json').read_text())
catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
native=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
R['native_slots']=[str(s.material_slot_name) for s in native.materials]
R['native_section_tag']=u.EditorAssetLibrary.get_metadata_tag(native,'Super90StockSection')
expected={'S90_FactoryStock_TTI_Benelli_M4','S90_FactoryStock_S90_Rubber','S90_FactoryStock_S90_Polymer'}
R['factory_sections_present']=expected.issubset(R['native_slots'])
if not R['factory_sections_present']:R['errors'].append('Factory stock material groups missing')
R['native_sha256']=hashlib.sha256((P/'Content/Weapons/Super90/Cransh20261006/SK_Super90_V7.uasset').read_bytes()).hexdigest()
for key,row in saved['meshes'].items():
    mesh=u.load_asset(row['path'])
    if not mesh:R['errors'].append('Missing mesh '+key);continue
    mats=[s.material_interface for s in mesh.static_materials]
    R['assets'][key]={'asset':mesh.get_path_name(),'materials':[m.get_path_name() if m else None for m in mats],'lod_count':mesh.get_num_lods()}
    if not all(mats):R['errors'].append('Missing material '+key)
    options=[o for o in weapon['options']['stock'] if o['id']==key]
    if len(options)!=1:R['errors'].append('Catalog option mismatch '+key)
    if not (P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/('stock_'+key+'.png')).exists():R['errors'].append('Missing shared icon '+key)
    for m in mats:
        if m and 'DefaultMaterial' in m.get_path_name():R['errors'].append('Fallback material '+key)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
dm,status=G.copy_mesh_from_skeletal_mesh(native,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read production native geometry')
_,pos,_=Q.get_all_vertex_positions(dm,False);pos=u.GeometryScript_List.convert_vector_list_to_array(pos)
_,tri,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tri)
ids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))]
data={'positions':[[v.x,v.y,v.z] for v in pos],'triangles':[[v.x,v.y,v.z] for v in tri],'materials':ids,'slot_names':R['native_slots']}
with gzip.open(O/'current_geometry_check.json.gz','wt',encoding='utf-8') as f:json.dump(data,f)
task=u.AssetExportTask();task.object=native;task.filename=str(O/'current_native_check.fbx');task.automated=True;task.prompt=False;task.replace_identical=True
task.options=u.FbxExportOption();task.options.level_of_detail=False
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export native comparison')
R['ok']=not R['errors'];(O/'asset_check.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('SUPER90_STOCK_ASSET_CHECK',R['ok'],R['errors'],R['native_section_tag'],len(R['assets']))
