"""Export current production geometry and material inputs for stock authoring."""
import unreal as u
import json, gzip, hashlib
from pathlib import Path
O = Path(__file__).parent
P = O.parents[1]
I = O / 'Inputs'
I.mkdir(exist_ok=True)
# Production material groups survive package reloads; editor metadata need not.
# Keep the pre-split recovery inputs rather than overwriting them with a later
# export whose triangle material indices have already been reassigned.
current=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
if any(str(s.material_slot_name).startswith('S90_FactoryStock_') for s in current.materials):
    raise RuntimeError('Stocks already installed. Reuse the retained Inputs and inputs.json; do not overwrite the pre-split baseline.')
sources = json.loads((P/'SourceAssets/M16UniversalAttachments20260920/sources.json').read_text())
paths = {'super90': '/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'}
paths.update({k: sources[k]['source'] for k in ('skeleton','core_stock','qr_performance','tactical_telescopic')})
paths['legendary_adjustable_tactical_stock'] = '/Game/Weapons/LegendaryStock20261006/Fitted/SM_TacticalStock_M4'
L = u.MaterialEditingLibrary
report = {'assets': {}, 'materials': {}}
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key, path in paths.items():
    if path in dirty: raise RuntimeError('Unsaved authoring input: '+path)
    obj = u.load_asset(path)
    if not obj: raise RuntimeError(path)
    slots = obj.materials if key == 'super90' else obj.static_materials
    report['assets'][key] = {'path':path, 'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(), 'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]}
    task = u.AssetExportTask()
    task.object=obj; task.filename=str(I/(key+'.fbx')); task.automated=True; task.prompt=False; task.replace_identical=True
    task.options=u.FbxExportOption(); task.options.level_of_detail=False
    if not u.Exporter.run_asset_export_task(task): raise RuntimeError(str(task.errors))
    for slot in slots:
        mat=slot.material_interface; mp=mat.get_path_name()
        if mp in report['materials']: continue
        row={'class':mat.get_class().get_name()}; report['materials'][mp]=row
        if isinstance(mat,u.MaterialInstanceConstant):
            row['parent']=mat.parent.get_path_name()
            row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(mat,n) for n in L.get_scalar_parameter_names(mat)}
            row['vectors']={str(n):[getattr(L.get_material_instance_vector_parameter_value(mat,n),c) for c in ('r','g','b','a')] for n in L.get_vector_parameter_names(mat)}
            row['textures']={str(n):(L.get_material_instance_texture_parameter_value(mat,n).get_path_name() if L.get_material_instance_texture_parameter_value(mat,n) else None) for n in L.get_texture_parameter_names(mat)}
        else:
            row['textures']={}
            for j,n in enumerate(L.get_material_expressions(mat)):
                try:
                    tex=n.get_editor_property('texture')
                    if tex: row['textures'][str(j)]=tex.get_path_name()
                except Exception: pass
mesh=u.load_asset(paths['super90']); G=u.GeometryScript_AssetUtils; Q=u.GeometryScript_MeshQueries
mats,indices,names,status=G.get_lod_material_list_from_skeletal_mesh(mesh,u.GeometryScriptMeshReadLOD())
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Native mesh export failed')
_,pos,_=Q.get_all_vertex_positions(dm,False); pos=u.GeometryScript_List.convert_vector_list_to_array(pos)
_,tri,_=Q.get_all_triangle_indices(dm,False); tri=u.GeometryScript_List.convert_triangle_list_to_array(tri)
ids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))]
with gzip.open(I/'native_geometry.json.gz','wt',encoding='utf-8') as f:
    json.dump({'positions':[[v.x,v.y,v.z] for v in pos],'triangles':[[v.x,v.y,v.z] for v in tri],'materials':ids,'slot_names':[str(n) for n in names],'slot_indices':list(indices)},f)
(O/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_STOCK_INPUTS_EXPORTED',list(paths))
