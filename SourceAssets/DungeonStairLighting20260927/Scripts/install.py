"""Save stair fixtures and existing stair lights only; never regenerate or play the map."""
import json,math,re,shutil,sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
UNDERGROUND=ROOT.parent/'DungeonUnderground20260923'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
BASE='/Game/Dungeons/Underground20260923/Meshes'
MESH=BASE+'/SM_RS_StairDrop1080_Fixtures'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if UE.get_game_world():raise RuntimeError('Preserve active game; stair lighting save pending')
dirty_maps=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
initial_dirty={p.get_name() for p in dirty_maps+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}
if dirty_maps or MESH in initial_dirty:raise RuntimeError('Preserve unsaved map or stair fixture mesh')
previous_world=UE.get_editor_world()
previous_map=previous_world.get_path_name().split('.')[0] if previous_world else None
for folder in ('Before','Receipts'):(ROOT/folder).mkdir(exist_ok=True)
for package,suffix in ((MESH,'.uasset'),(TARGET,'.umap')):
    source=PROJECT/'Content'/(package.removeprefix('/Game/')+suffix)
    backup=ROOT/'Before'/source.name
    if source.exists() and not backup.exists():shutil.copy2(source,backup)

sys.path.insert(0,str(UNDERGROUND/'Scripts'))
from lighting_layout import light_records,specs
lights=light_records();lamp_specs=specs()
item=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))['objects'][0]
old_mesh=u.load_asset(MESH)
if not old_mesh:raise RuntimeError('Missing original stair fixture mesh')
old_slots={str(s.material_slot_name):s.material_interface for s in old_mesh.get_editor_property('static_materials')}
nanite=old_mesh.get_editor_property('nanite_settings').copy()
materials={}
for name,path in item['materials'].items():
    material=old_slots.get(name) or u.load_asset(path)
    if not material:raise RuntimeError('Missing lamp material '+path)
    materials[name]=material
report={'stage':'preparing','revision':'stair-platform-lights-20260927','map':TARGET,'mesh':MESH,
        'lamps_per_module':len(lights),'modules':[],'runtime_tested':False,'compiled':False}
def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
record()

task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE;task.destination_name=item['name']
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
options.import_as_skeletal=False;options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task.options=options;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset(MESH)
if not mesh or not task.get_objects():raise RuntimeError('Fixture mesh import failed')
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
    mesh.set_material(index,materials[name])
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
def preserve_dirty(material):
    if material.get_path_name().split('.')[0] in initial_dirty:raise RuntimeError('Preserve unsaved lamp material '+material.get_path_name())
for material in materials.values():ensure_material_usage(material,preserve_dirty)
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
nanite.enabled=True;nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED
nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0.
mesh.set_editor_property('nanite_settings',nanite)
if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Fixture Nanite build failed')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Fixture mesh save failed')
report['stage']='mesh_saved';record()

world=previous_world if previous_map==TARGET else u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load dungeon map for lighting edit')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one authored generator')
g=generators[0]
original=g.get_editor_property('module_catalog_json')
backup=ROOT/'Before/map-catalog.json'
if not backup.exists():backup.write_text(original,encoding='utf-8')
catalog=json.loads(original)
module=next(m for m in catalog['modules'] if m['id']=='StairDrop1080')
module['lights']=lights;module['lighting_revision']=report['revision']
layout=json.loads(g.get_editor_property('layout_manifest_json') or '{}')
nodes=[n for n in layout.get('nodes',[]) if n['module']=='StairDrop1080']
actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
plans=[]
for node in nodes:
    tag='DungeonModule.%s.StairDrop1080'%node['id']
    old=sorted([a for a in actors if isinstance(a,u.PointLight) and a.actor_has_tag(tag)],key=lambda a:a.get_name())
    if len(old)<len(lights):raise RuntimeError('Existing stair lighting is incomplete; no automatic regeneration')
    plans.append((node,tag,old))
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
for node,tag,old in plans:
    angle=math.radians(node['yaw']);c,s=math.cos(angle),math.sin(angle)
    origin=node['origin'];scale=node.get('scale',[1,1,1])
    for actor,spec,lamp in zip(old,lights,lamp_specs):
        x,y,z=[v*k for v,k in zip(spec['position'],scale)]
        position=u.Vector(origin[0]+c*x-s*y,origin[1]+s*x+c*y,origin[2]+z)
        actor.modify();actor.set_actor_location(position,False,True)
        actor.set_actor_rotation(u.Rotator(pitch=0,yaw=node['yaw']-lamp['yaw'],roll=0),True)
        actor.set_actor_label('DGN_StairLight_%s_%s'%(node['id'],spec['id']))
        tags=[t for t in actor.tags if not str(t).startswith('DungeonLight.')]
        actor.tags=tags+[u.Name('DungeonLight.key')]
        component=actor.get_component_by_class(u.PointLightComponent);component.modify()
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        component.set_intensity(spec['intensity']);component.set_attenuation_radius(spec['radius'])
        component.set_light_color(u.LinearColor(*spec['color'],1.));component.set_cast_shadows(True)
        component.set_source_radius(5);component.set_source_length(60)
        component.set_editor_property('max_draw_distance',2400.)
        component.set_editor_property('max_distance_fade_range',500.)
    for actor in old[len(lights):]:
        if not AA.destroy_actor(actor):raise RuntimeError('Could not retire old stair light '+actor.get_name())
    report['modules'].append({'id':node['id'],'before':len(old),'after':len(lights),'removed':len(old)-len(lights)})
if not E.save_loaded_asset(world,False):raise RuntimeError('Dungeon map save failed')
report['stage']='map_saved';record()
# Keep the current map's other module updates when persisting the source catalog.
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
if not globals().get('BACKGROUND',False) and previous_map and previous_map!=TARGET:
    u.EditorLoadingAndSavingUtils.load_map(previous_map)
print('STAIR_LIGHTING_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
