"""Read source geometry and material inputs needed to author the entrance sample."""
from pathlib import Path
import json,gzip
import unreal as u
ROOT=Path(__file__).resolve().parent
(ROOT/'Geometry').mkdir(parents=True,exist_ok=True)
(ROOT/'SourceTextures').mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
paths=['/Game/UndergroundTunnel/Meshes/Props/'+n for n in
       ['SM_WoodPallet01'+v for v in 'abcdef']+
       ['SM_WoodCrate01a','SM_WoodCrate02a','SM_WallBracket01a','SM_WallBracket01b','Sm_Toolbox01a','SM_Dolly01a']]
paths += ['/Game/UndergroundTunnel/Meshes/Decals/SM_Decal_Junk0'+str(i)+'a' for i in range(1,8)]
paths += ['/Game/Dungeons/TransitIncidentDetail20261010/Meshes/SM_IncidentDetail_Paper'+str(i) for i in range(4)]
paths += ['/Game/Dungeons/CargoWarehouse20261001/RefineV2/Meshes/SM_CargoWarehouse_RackDecks_V2']
# The real map determines the current rack mesh path (the source author path changed historically).
scene=json.loads((ROOT.parent/'FreightWarehouseReview20261111/scene-inputs.json').read_text('utf8'))
paths=[p for p in paths if 'RackDecks_V2' not in p]
paths += [m['mesh'] for a in scene['maps']['current']['actors'] for m in a['meshes'] if any(s in m['mesh'] for s in ('RackDecks_V2','Racks_V2','CargoWarehouse_Signs_V2'))]
report={'meshes':{},'materials':{}}
def material(m):
    if not m:return None
    p=m.get_path_name()
    if p in report['materials']:return p
    r={'domain':str(m.get_base_material().get_editor_property('material_domain')),'base':m.get_base_material().get_path_name(),'scalar':{},'vector':{},'texture':{}}
    if isinstance(m,u.MaterialInstanceConstant):
        for name in L.get_scalar_parameter_names(m):r['scalar'][str(name)]=L.get_material_instance_scalar_parameter_value(m,name)
        for name in L.get_vector_parameter_names(m):
            c=L.get_material_instance_vector_parameter_value(m,name);r['vector'][str(name)]=[c.r,c.g,c.b,c.a]
        for name in L.get_texture_parameter_names(m):
            t=L.get_material_instance_texture_parameter_value(m,name);r['texture'][str(name)]=t.get_path_name() if t else None
    report['materials'][p]=r
    return p
for path in dict.fromkeys(paths):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required source asset not found '+path)
    b=obj.get_bounding_box()
    report['meshes'][obj.get_path_name()]={'min':list(b.min.to_tuple()),'max':list(b.max.to_tuple()),'materials':[material(s.material_interface) for s in obj.static_materials]}
    if any(t in path for t in ('WoodPallet','WoodCrate','RackDecks','Racks_V2','WallBracket')):
        dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(obj,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        q=u.GeometryScript_MeshQueries;ls=u.GeometryScript_List
        pl=next(v for v in q.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
        tl=next(v for v in q.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
        data={'vertices':[list(v.to_tuple()) for v in ls.convert_vector_list_to_array(pl)],'indices':[i for t in ls.convert_triangle_list_to_array(tl) for i in (t.x,t.y,t.z)]}
        with gzip.open(ROOT/'Geometry'/(obj.get_name()+'.json.gz'),'wt',encoding='utf8') as f:json.dump(data,f)
for name in ['MI_DecalDirt_02','MI_DecalDirt_03','MI_DecalDirt_04','MI_DecalWallCrack_01','MI_DecalDamage_01']:
    material(u.load_asset('/Game/HospitalCorridor/Materials/Decals/'+name))
material(u.load_asset('/Game/UndergroundTunnel/Materials/MI_Decal_RustStain01a'))
for name in ['T_DecalDirt_02_A','T_DecalDirt_03_A','T_DecalDirt_04_A','T_DecalCrack_01_A','T_DecalDamage_01_A']:
    t=u.load_asset('/Game/HospitalCorridor/Textures/Decals/'+name)
    task=u.AssetExportTask();task.object=t;task.filename=str(ROOT/'SourceTextures'/(name+'.png'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterPNG()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Input export failed '+name)
(ROOT/'authoring-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ENTRANCE_AUTHORING_INPUTS_READ',flush=True)
