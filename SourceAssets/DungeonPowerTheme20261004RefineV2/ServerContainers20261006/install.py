"""Import two split server meshes and replace the matching static map actors."""
import json,re,sys,traceback,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent;PROJECT=ROOT.parents[2]
DATA=json.loads((ROOT/'manifest.json').read_text('utf8'));BASE=DATA['base']
MAP='/Game/GameMaps/Design/L_PowerTheme20261004_Subject';TAG='PowerServerContainer20261006.Source'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='preparing',map=MAP,saved_assets=[],containers=[],tests_run=False,rendered=False,game_run=False,random_pool_registered=False)

def record():
    (ROOT/'Receipts').mkdir(exist_ok=True)
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Required asset missing '+path)
    return result
def guard():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: stop play before editing the loaded map')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved map changes')
def patch_loaded_map():
    body=asset(BASE+'/Meshes/SM_Power_ServerContainer_Body')
    door=asset(BASE+'/Meshes/SM_Power_ServerContainer_Cartridge')
    original_meshes={'/Game/Dungeons/DataArchive20260930/EquipmentV1/Meshes/SM_Archive_ServerRack_V1',
        '/Game/Dungeons/PowerTheme20261004/TextCards20261005/Meshes/SM_Archive_ServerRack_V1'}
    changed=[]
    for old in list(AA.get_all_level_actors()):
        label=old.get_actor_label()
        if not label.startswith('PowerTheme_'):continue
        existing=isinstance(old,u.ColdSteelSceneContainer) and str(old.get_editor_property('container_id')).startswith('PowerTheme20261004RefineV2.Server.')
        comp=old.get_component_by_class(u.StaticMeshComponent)
        path=comp.static_mesh.get_path_name().split('.')[0] if comp and comp.static_mesh else ''
        if not existing and path not in original_meshes:continue
        transform=old.get_actor_transform();folder=old.get_folder_path();tags=list(old.tags)
        if existing:actor=old;actor.modify()
        else:
            actor=AA.spawn_actor_from_class(u.ColdSteelSceneContainer,old.get_actor_location(),old.get_actor_rotation())
            if not actor:raise RuntimeError('Native container creation failed '+label)
        actor.root_component.set_mobility(u.ComponentMobility.MOVABLE)
        actor.body.set_mobility(u.ComponentMobility.MOVABLE);actor.door.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_transform(transform,False,True)
        actor.body.set_static_mesh(body);actor.door.set_static_mesh(door)
        actor.body.set_editor_property('override_materials',[]);actor.door.set_editor_property('override_materials',[])
        actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('BlockAllDynamic')
        actor.body.set_cast_shadow(True);actor.door.set_cast_shadow(True)
        actor.door_hinge.set_relative_location(u.Vector(*DATA['hinge_ue_cm']),False,True)
        actor.door.set_relative_location(u.Vector(),False,True)
        identity='PowerTheme20261004RefineV2.Server.'+label.removeprefix('PowerTheme_')
        for key,value in dict(container_id=identity,caption='服务器模块',storage_pages=1,
            opening_motion=u.ColdSteelContainerMotion.DRAWER,drawer_travel=u.Vector(*DATA['travel_ue_cm']),
            opening_duration=DATA['opening_seconds'],initial_open_fraction=0.).items():actor.set_editor_property(key,value)
        actor.set_editor_property('tags',list(dict.fromkeys(tags+list(actor.tags)+[u.Name('ColdSteel.SceneContainer'),u.Name('PowerTheme.ServerContainer20261006')])))
        actor.set_folder_path(folder)
        if not existing:AA.destroy_actor(old)
        actor.set_actor_label(label)
        p=actor.get_actor_location();r=actor.get_actor_rotation()
        changed.append(dict(actor=label,container_id=identity,world_position_cm=[p.x,p.y,p.z],yaw_ue=r.yaw,travel_cm=DATA['travel_ue_cm']))
    if not changed:raise RuntimeError('No PowerTheme server actors found; no map was saved')
    return changed

def finish_prior_doors():
    # Complete the already-authorized last turn without rebuilding its layout.
    updated=[]
    for actor in AA.get_all_level_actors():
        if actor.get_actor_label().startswith('PowerTheme_UpperControlDoor') and isinstance(actor,u.ColdSteelDoor):
            actor.modify();actor.set_editor_property('open_angle_degrees',85.0);updated.append(actor.get_actor_label())
    return updated

def main():
    guard();record()
    if not E.does_asset_exist(MAP):raise RuntimeError('PowerTheme subject missing')
    snapshot=ROOT/'Snapshots/L_PowerTheme20261004_Subject.before.umap';snapshot.parent.mkdir(exist_ok=True)
    if not snapshot.exists():shutil.copy2(PROJECT/'Content/GameMaps/Design/L_PowerTheme20261004_Subject.umap',snapshot)
    for item in DATA['meshes']:
        path=item['mesh'];fingerprint=item['sha256']
        if E.does_asset_exist(path):
            mesh=asset(path)
            if E.get_metadata_tag(mesh,TAG)!=fingerprint:raise RuntimeError('Preserve different server asset '+path)
        else:
            options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
            options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
            data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.one_convex_hull_per_ucx=True
            data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
            task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path,task.destination_name=path.rsplit('/',1)
            task.automated=True;task.replace_existing=False;task.save=False;task.options=options;task.factory=u.FbxFactory()
            AT.import_asset_tasks([task]);mesh=asset(path)
            for i,slot in enumerate(mesh.get_editor_property('static_materials')):
                name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,asset(item['materials'][name]))
            build=SM.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
            build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
            SM.set_lod_build_settings(mesh,0,build)
            mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
            settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True
            mesh.set_editor_property('nanite_settings',settings)
            if settings.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
            E.set_metadata_tag(mesh,TAG,fingerprint)
            if not E.save_loaded_asset(mesh,False):raise RuntimeError('Asset save failed '+path)
        report['saved_assets'].append(path);record()
    report['stage']='assets_saved';record();guard()
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_editor_world() if editor else None
    if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Cannot load PowerTheme map')
    report['containers']=patch_loaded_map();report['prior_doors_completed']=finish_prior_doors()
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Server container map save failed')
    report['stage']='map_saved';record()
    if report['prior_doors_completed']:
        previous=SOURCE/'UpperControlRoom20261005/Receipts/install.json'
        data=json.loads(previous.read_text('utf8'));data['door_swing']='Native approach-dependent swing; positive 85 degree speed contract, 0.55 seconds'
        data['door_configuration_saved_on']='2026-10-06';previous.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    u.log('POWER_SERVER_CONTAINERS_MAP_SAVED '+str(len(report['containers'])))
if __name__=='__main__':
    try:main()
    except Exception:
        report['error']=traceback.format_exc();record();raise
