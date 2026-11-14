"""Read the requested subject map and imported kit as environmental authoring inputs."""
from pathlib import Path
import json,gzip,hashlib
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
for name in ('Receipts','Geometry','Config'):(ROOT/name).mkdir(exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Requested subject unavailable')
report=dict(map=TARGET,actors=[],meshes={},materials={})
L=u.MaterialEditingLibrary

def material(obj):
    if not obj:return None
    path=obj.get_path_name()
    if path in report['materials']:return path
    base=obj.get_base_material();mi=isinstance(obj,u.MaterialInstanceConstant)
    row=dict(base=base.get_path_name(),domain=str(base.get_editor_property('material_domain')),scalars={},vectors={},textures={})
    report['materials'][path]=row
    for node in L.get_material_expressions(base):
        if isinstance(node,u.MaterialExpressionScalarParameter):
            key=str(node.get_editor_property('parameter_name'));row['scalars'][key]=float(L.get_material_instance_scalar_parameter_value(obj,key) if mi else node.get_editor_property('default_value'))
        elif isinstance(node,u.MaterialExpressionVectorParameter):
            key=str(node.get_editor_property('parameter_name'));v=L.get_material_instance_vector_parameter_value(obj,key) if mi else node.get_editor_property('default_value')
            row['vectors'][key]=[v.r,v.g,v.b,v.a]
        elif isinstance(node,(u.MaterialExpressionTextureSampleParameter2D,u.MaterialExpressionTextureObjectParameter)):
            key=str(node.get_editor_property('parameter_name'));tex=L.get_material_instance_texture_parameter_value(obj,key) if mi else node.get_editor_property('texture')
            row['textures'][key]=tex.get_path_name() if tex else None
    return path

def mesh(obj):
    path=obj.get_path_name()
    if path not in report['meshes']:
        box=obj.get_bounding_box()
        report['meshes'][path]=dict(min=list(box.min.to_tuple()),max=list(box.max.to_tuple()),
            slots=[dict(name=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None) for s in obj.static_materials])
    return path

source_meshes={}
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    p=actor.get_actor_location();center,extent=actor.get_actor_bounds(False)
    row=dict(name=actor.get_name(),label=actor.get_actor_label(),class_name=actor.get_class().get_name(),
             tags=[str(v) for v in actor.tags],position=list(p.to_tuple()),rotation=list(actor.get_actor_rotation().to_tuple()),
             scale=list(actor.get_actor_scale3d().to_tuple()),bounds_center=list(center.to_tuple()),bounds_extent=list(extent.to_tuple()),components=[])
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        path=mesh(c.static_mesh);t=c.get_world_transform()
        row['components'].append(dict(name=c.get_name(),mesh=path,position=list(t.translation.to_tuple()),rotation=list(t.rotation.rotator().to_tuple()),scale=list(t.scale3d.to_tuple()),
            materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],collision=str(c.get_collision_enabled())))
        if 'CargoWarehouse' in path and any(token in path for token in ('Floors','Walls','Structure','Dock','Stair')):
            source_meshes[path]=c.static_mesh
    report['actors'].append(row)

props=['SM_DebrisPile01a','SM_DebrisPile02a','SM_DebrisPile02b','SM_DebrisPile03a','SM_WoodPallet01a','SM_WoodPallet01b','SM_WoodPallet01d','SM_WoodPallet01e',
       'SM_WoodCrate01a','SM_WoodCrate02a','SM_Bucket01a','SM_Bucket01b','SM_Bucket01b_lid','SM_GasCan01a','SM_OilBottle01a','SM_Oildrum01a','SM_Oildrum01b',
       'SM_Paintcan01a','Sm_Toolbox01a','SM_Dolly01a','SM_WoodBoard01a','SM_WoodBoard01b','SM_WoodBoard01c','SM_WoodBoard01d','SM_WoodBoard01h','SM_WoodBoard01i',
       'Sm_Cinderblock01a','SM_MetalPanel01a','SM_MetalPanel01b']
decals=['SM_Decal_ConcreteDebris01a','SM_Decal_ConcreteDebris01b','SM_Decal_ConcreteDebris01c','SM_Decal_ConcreteDebris01d','SM_Decal_ConcreteDebris01g',
        'SM_Decal_MetalDebris01a','SM_Decal_MetalDebris01b','SM_Decal_MetalDebris01g','SM_Decal_Junk01a','SM_Decal_Junk03a','SM_Decal_Junk06a']
for folder,names in [('Props',props),('Decals',decals)]:
    for name in names:
        obj=u.load_asset('/Game/UndergroundTunnel/Meshes/'+folder+'/'+name)
        if not obj:raise RuntimeError('Imported asset missing '+name)
        mesh(obj)
(ROOT/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for name in ('MI_Env_ConcreteFloor01a','MI_Env_ConcreteFloor02a','MI_Env_2ly_ConcreteFloor01a','MI_Env_ConcreteWall01a','MI_Env_ConcreteWall01b','MI_Env_ConcreteWall06a',
             'MI_Decal_RustStain01a','MI_Decal_Debris01a','MI_Env_Decal_ConcreteDebris01a','MI_Env_Decal_JunkDebris01a','MI_Env_PDO_DebrisPile01a'):
    material(u.load_asset('/Game/UndergroundTunnel/Materials/'+name))
q=u.GeometryScript_MeshQueries;ls=u.GeometryScript_List
for path,obj in source_meshes.items():
    dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(obj,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    pl=next(v for v in q.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
    tl=next(v for v in q.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
    vertices=[list(v.to_tuple()) for v in ls.convert_vector_list_to_array(pl)]
    indices=[i for tri in ls.convert_triangle_list_to_array(tl) for i in (tri.x,tri.y,tri.z)]
    name=obj.get_name()+'_'+hashlib.sha1(path.encode()).hexdigest()[:7]+'.json.gz'
    with gzip.open(ROOT/'Geometry'/name,'wt',encoding='utf8') as f:json.dump(dict(vertices=vertices,indices=indices),f,separators=(',',':'))
    report['meshes'][path]['geometry']=name
(ROOT/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('FREIGHT_WEATHERING_INPUTS '+json.dumps(dict(actors=len(report['actors']),meshes=len(report['meshes']),materials=len(report['materials']),surfaces=len(source_meshes))),flush=True)
