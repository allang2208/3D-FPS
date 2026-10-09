"""Import side-entry meshes, merge the live catalog and save; no generation test."""
from pathlib import Path
import unreal as u, json, runpy, importlib.util, shutil, hashlib, traceback
ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
OWNER='FacilityFlow20261007'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; facility save stopped before writing')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
previous=editor.get_editor_world() if editor else None
previous=previous.get_path_name().split('.')[0] if previous else None
report=dict(stage='preparing',map=TARGET,tests_run=False,game_run=False,generated=False,rendered=False,editor_opened=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest();dest=ROOT/'Snapshots'/path.relative_to(PROJECT).parent/(path.stem+'-'+digest[:12]+path.suffix)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    return str(dest)

try:
    record()
    # The source importer already assigns real material slots, imports authored
    # UCX hulls and builds Nanite. Only the new namespace is supplied to it.
    source=PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py'
    spec=importlib.util.spec_from_file_location('facility_entry_import_support',source)
    R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
    R.ROOT=ROOT;R.BASE='/Game/Dungeons/FacilityFlow20261007';R.OWNER=OWNER
    R.MAN=json.loads((ROOT/'geometry.json').read_text('utf8'));R.MAN['meshes']+=json.loads((ROOT/'sign-geometry.json').read_text('utf8'))['meshes']+json.loads((ROOT/'fixture-geometry.json').read_text('utf8'))['meshes']
    R.MAP='/Game/GameMaps/Design/FacilityFlowImportScope';R.report=dict(saved_assets=[]);R.record=lambda:None
    texture_file=ROOT/'Authored/T_FacilityRoutePairs.png';key=hashlib.sha256(texture_file.read_bytes()).hexdigest()
    texture_path=R.BASE+'/Textures/T_FacilityRoutePairs';texture=R.reuse(texture_path,key)
    if not texture:
        texture=R.imported(texture_path,texture_file);texture.set_editor_property('srgb',True)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);R.saved(texture,key)
    material_path=R.BASE+'/Materials/M_FacilityRoutePairs';material=R.reuse(material_path,key+':v1')
    if not material:
        material=R.A.create_asset('M_FacilityRoutePairs',R.BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        material.set_editor_property('used_with_instanced_static_meshes',True);material.set_editor_property('two_sided',True)
        slab=R.L.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels)
        slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        sample=R.L.create_material_expression(material,u.MaterialExpressionTextureSample);sample.set_editor_property('texture',texture);sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        rough=R.L.create_material_expression(material,u.MaterialExpressionConstant);rough.set_editor_property('r',.74)
        R.L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR);R.L.connect_material_expressions(sample,'RGB',slab,'BaseColor')
        R.L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS);R.L.connect_material_expressions(rough,'',slab,'Roughness')
        R.L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=R.L.recompile_material(material)
        if errors:raise RuntimeError('Route sign material compilation failed: '+str(errors))
        R.saved(material,key+':v1')
    R.meshes();report['saved_assets']=R.report['saved_assets'];report['stage']='assets_saved';record()
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Expected one production generator')
    generator=generators[0];rules=runpy.run_path(str(ROOT/'extend_catalog.py'))
    before=generator.get_editor_property('module_catalog_json');catalog=rules['extend'](json.loads(before))
    asset_cache={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
    # Persist both drawn and undrawn portal kits and every native interaction
    # dependency. Missing references stop installation instead of saving a shell.
    added=[m for m in catalog['modules'] if m['id'] in ('FacilityEntrancePassage','FacilityReceptionHall','FacilityTransit','EcoNursery','EcoHydroponics','EcoBiosphere','SwitchgearGallery','GeneratorHall','AccumulatorControl')]
    for path in sorted(set(rules['paths']([added,catalog['facility_flow']]))):
        obj=u.load_class(None,path) if path.startswith('/Script/') or path.endswith('_C') else u.load_asset(path)
        if not obj:raise RuntimeError('Required facility dependency missing: '+path)
        asset_cache[obj.get_path_name()]=obj
    report['backup_map']=backup(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap')
    (ROOT/'Snapshots/catalog-before-save.json').write_text(before,encoding='utf8')
    generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
    generator.set_editor_property('module_assets',list(asset_cache.values()));generator.set_editor_property('randomize_on_entry',True)
    restored=bool(catalog['facility_flow'].get('fixed_start_revision'))
    # Legacy service relocation applies only before the original-entry restore.
    # Reception transform is rigid and seed independent: [1880,-2882,94].
    services={'DGN_A_WorkbenchKit_Main':([-410,-3732,94],90),
              'DGN_Start_WarehouseCabinet':([-390,-3982,94],90),
              'DGN_Start_ShrineStatue':([-650,-2882,94],0)}
    report['removed_old_entry_actors']=[];report['relocated_services']=[]
    for actor in list(AA.get_all_level_actors()):
        if restored:break
        name=actor.get_actor_label()
        if name in services:
            pos,yaw=services[name];actor.modify();actor.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),True)
            actor.set_actor_location(u.Vector(*pos),False,True)
            origin,extent=actor.get_actor_bounds(False);p=actor.get_actor_location();p.z+=94-(origin.z-extent.z);actor.set_actor_location(p,False,True)
            report['relocated_services'].append(name);continue
        if isinstance(actor,u.PlayerStart):
            actor.modify();actor.set_actor_location(u.Vector(0,-200,190),False,True);actor.set_actor_rotation(u.Rotator(pitch=0,yaw=-90,roll=0),True);continue
        if actor.actor_has_tag('DungeonRouteGenerated') or name.startswith('DGN_A_') or name in ('DGN_Link_A_B','DGN_Link_InspectionLight'):
            report['removed_old_entry_actors'].append(name);AA.destroy_actor(actor)
    # Author only the fixed passage as a standing surface in the saved map.
    # BeginPlay replaces these owned preview actors during normal generation.
    entry=next(m for m in added if m['id']=='FacilityEntrancePassage')
    for p in entry['parts']:
        if restored:break
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,94),u.Rotator(pitch=0,yaw=0,roll=0))
        a.set_actor_label('FacilityFlow_Entry_'+p['mesh'].rsplit('_',1)[-1]);a.set_folder_path('Dungeon/FixedEntryPreview')
        a.set_editor_property('tags',[u.Name('DungeonRouteGenerated'),u.Name('DungeonFacilityEntryPreview')]);a.set_owner(generator)
        c=a.static_mesh_component;c.set_static_mesh(u.load_asset(p['mesh']));c.set_collision_profile_name('BlockAll' if p['collision'] else 'NoCollision')
    if restored:
        runpy.run_path(str(ROOT/'restore_original_entry.py'))['restore_scene'](world,generator,catalog,report)
    # Read-only generation receipts are written by the native assembler on entry.
    # Clear completion tags here; installing a recipe is not a generated preview.
    generator.set_editor_property('tags',[t for t in generator.tags if str(t) not in ('DungeonAssembly.Ready','DungeonAssembly.Failed')])
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
    (ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    report.update(stage='map_saved',revision=rules['REVISION'],hard_dependencies=len(asset_cache),theme_candidates=6,routes=3,themes_per_route=2,mandatory_theme_rooms=18)
    record();print('FACILITY_FLOW_PRODUCTION_SAVED',TARGET)
except Exception:
    report['error']=traceback.format_exc();record();raise
finally:
    if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        u.EditorLoadingAndSavingUtils.load_map(previous)
