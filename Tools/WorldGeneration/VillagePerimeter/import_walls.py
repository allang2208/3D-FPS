"""Create and save the requested village perimeter kit; production only, no map/PIE."""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/HillsVillagePerimeter20261117'
DEST='/Game/WorldGeneration/TemperateHills/VillagePerimeter'
OWNER='HillsVillagePerimeter20261117'
E=u.EditorAssetLibrary
E.make_directory(DEST)
source=json.loads((OUT/'wall-mesh-source.json').read_text(encoding='utf-8'))
materials={name:u.load_asset(path) for name,path in {
    'Mortar':'/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A',
    'YardField':'/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelYardField',
    'YardSlate':'/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelYardSlate',
    'YardCap':'/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelYardCap'}.items()}
if not all(materials.values()):raise RuntimeError('The accepted chapel stone materials are required')
transition=runpy.run_path(str(Path(__file__).with_name('ground_transition.py')))
receivers={}
materials={slot:(material if slot=='Mortar' else transition['contact_material'](material,receivers)) for slot,material in materials.items()}
report={'saved':[],'gameplay_started':False,'rendered':False,'reference':'existing chapel courtyard stone materials and fieldstone geometry'}
for role,geometry in source.items():
    path=DEST+'/SM_VillageWall'+role
    asset=u.load_asset(path) if E.does_asset_exist(path) else None
    if asset and E.get_metadata_tag(asset,'VillagePerimeterOwner')!=OWNER:
        raise RuntimeError('Preserve unowned asset '+path)
    dynamic=u.DynamicMesh()
    active=[]
    for slot,data in geometry['groups'].items():
        if not data['triangles']:continue
        buf=u.GeometryScriptSimpleMeshBuffers()
        buf.vertices=[u.Vector(*p) for p in data['vertices']]
        buf.normals=[u.Vector(*p) for p in data['normals']]
        buf.uv0=[u.Vector2D(*p) for p in data['uv0']]
        buf.uv1=[u.Vector2D(*p) for p in data['uv1']]
        buf.triangles=[u.IntVector(*p) for p in data['triangles']]
        u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buf,material_id=len(active))
        active.append(slot)
    if not asset:
        asset,result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,path,
            u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                enable_collision=True,enable_nanite=False))
        if not asset or result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh production failed '+path)
    nanite=asset.get_editor_property('nanite_settings');nanite.enabled=True
    nanite.fallback_percent_triangles=1.0;nanite.fallback_relative_error=0.0
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        replace_materials=True,new_materials=[materials[slot] for slot in active],new_material_slot_names=active,
        apply_nanite_settings=True,new_nanite_settings=nanite)
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,asset,options,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh/material production failed '+path)
    slots=list(asset.get_editor_property('static_materials'))
    for index,slot in enumerate(slots):
        slot.set_editor_property('material_slot_name',active[index])
        info=slot.get_editor_property('uv_channel_data')
        info.set_editor_property('bOverrideDensities',True)
        info.set_editor_property('LocalUVDensities',[100.,170.,0.,0.])
    asset.set_editor_property('static_materials',slots)
    body=asset.get_editor_property('body_setup');aggregate=body.get_editor_property('agg_geom')
    boxes=[]
    for part in geometry['collision_boxes']:
        box=u.KBoxElem();box.set_editor_property('center',u.Vector(*part['center']))
        for axis,value in zip(('x','y','z'),part['size']):box.set_editor_property(axis,value)
        boxes.append(box)
    aggregate.set_editor_property('box_elems',boxes)
    body.set_editor_property('agg_geom',aggregate)
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    E.set_metadata_tag(asset,'VillagePerimeterOwner',OWNER)
    E.set_metadata_tag(asset,'VillagePerimeterStyle','repaired' if role.startswith(('Repaired','PierRepaired')) else 'ruined')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+path)
    report['saved'].append({'path':asset.get_path_name(),'triangles':geometry['triangles'],
        'collision_boxes':len(boxes),'materials':{slot:materials[slot].get_path_name() for slot in active},'nanite':True})
    (OUT/'asset-production.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    u.log('VILLAGE_PERIMETER_SAVED '+path)
u.log('VILLAGE_PERIMETER_PRODUCTION_COMPLETE '+str(len(report['saved'])))
