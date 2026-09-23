"""Assemble complete approved spaces. No generic shell builder, gameplay test or render."""
import gc,json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'Config/assembly.json').read_text(encoding='utf-8'))
MAN=json.loads((ROOT/'Authored/connections.json').read_text(encoding='utf-8'))
TARGET=CFG['target_map'];BASE='/Game/Dungeons/AuthoredExpansion20260922'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay is running; preserve session')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if dirty:raise RuntimeError('Preserve unsaved work: '+', '.join(p.get_name() for p in dirty[:8]))
if E.does_asset_exist(TARGET):raise RuntimeError('Target already exists; preserve it and resume from the saved stage')
receipt=dict(stage='importing',baseline=CFG['baseline_map'],map=TARGET,assets={},segments=[],tests_run=False)
(ROOT/'Receipts').mkdir(exist_ok=True)
def write(): (ROOT/'Receipts/assembly.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
for item in MAN:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    path=BASE+'/Meshes/'+item['name'];mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed: '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        material=u.load_asset(item['materials'][name]);mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['assets'][item['name']]=path
write()

# Preserve a UE-native copy of the rejected map; external actor references follow editor duplication.
old='/Game/GameMaps/L_Dungeon_Generated'
archive='/Game/Trash/DungeonGeneratedV1_20260922/L_Dungeon_Generated_Rejected'
if E.does_asset_exist(old) and not E.does_asset_exist(archive):
    a=E.duplicate_asset(old,archive)
    if not a:raise RuntimeError('Could not preserve rejected map')
    save(a)
    del a
asset=E.duplicate_asset(CFG['baseline_map'],TARGET)
if not asset:raise RuntimeError('Could not duplicate approved sample')
save(asset)
del asset
gc.collect()
if not ED.load_level(TARGET):raise RuntimeError('Cannot open owned expansion')
world=UE.get_editor_world()
originals=list(AA.get_all_level_actors())
art=[a for a in originals if not isinstance(a,(u.PlayerStart,u.PostProcessVolume))]
for a in art:
    a.set_editor_property('tags',list(a.get_editor_property('tags'))+[u.Name('SourceLabel:'+a.get_actor_label())])
copies=AA.duplicate_actors(art,world,u.Vector(0,0,0))
if len(copies)!=len(art):raise RuntimeError('Actor duplication incomplete; preserve live edit')

def source_label(a):
    return next(str(t).split(':',1)[1] for t in a.get_editor_property('tags') if str(t).startswith('SourceLabel:'))

for segment,group in zip(CFG['segments'],[art,copies]):
    delta=u.Transform()
    delta.set_editor_property('translation',u.Vector(*segment['location_cm']))
    delta.set_editor_property('rotation',u.Rotator(pitch=0,yaw=segment['yaw'],roll=0).quaternion())
    roots=set(group)
    initial={a:a.get_actor_transform() for a in group}
    for a in group:
        label=source_label(a)
        if a.get_attach_parent_actor() not in roots:
            a.modify()
            a.set_actor_transform(u.MathLibrary.compose_transforms(initial[a],delta),False,True)
        a.set_actor_label('DGN_'+segment['id']+'_'+label.removeprefix('DGN_'))
        a.set_folder_path('DungeonAuthoredExpansion/'+segment['id']+'/'+str(a.get_folder_path()).removeprefix('DungeonAtmosphereV2/'))
        for item in MAN:
            if item['actor']!=label:continue
            entry='EntryEnd' in label
            if (entry and segment['open_entry']) or (not entry and segment['open_exit']):
                a.get_component_by_class(u.StaticMeshComponent).set_static_mesh(u.load_asset(receipt['assets'][item['name']]))
    receipt['segments'].append(dict(id=segment['id'],actors=len(group),location_cm=segment['location_cm'],yaw=segment['yaw']))
link=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*CFG['connection']['location_cm']))
link.set_actor_label('DGN_Link_A_B');link.set_folder_path('DungeonAuthoredExpansion/Connections')
link.static_mesh_component.set_static_mesh(u.load_asset(receipt['assets']['SM_Sample_ServiceLink']))
link.static_mesh_component.set_collision_profile_name('BlockAll')
lamp=AA.spawn_actor_from_class(u.PointLight,u.Vector(2400,-1600,294))
lamp.set_actor_label('DGN_Link_InspectionLight');lamp.set_folder_path('DungeonAuthoredExpansion/Connections')
c=lamp.get_component_by_class(u.PointLightComponent)
c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(360);c.set_light_color(u.LinearColor(1,.69,.4,1));c.set_attenuation_radius(260);c.set_cast_shadows(True)
receipt['stage']='assembled'
write()
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('External actor save failed')
if not ED.save_current_level():raise RuntimeError('Map save failed; preserve live work')
receipt['stage']='map_saved';write()
print('AUTHORED_EXPANSION_SAVED',TARGET,'two full authored segments, one service connection')
