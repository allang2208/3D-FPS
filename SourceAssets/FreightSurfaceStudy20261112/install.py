"""Install a bounded, reversible material study and two editor-only comparison viewpoints."""
from pathlib import Path
from datetime import datetime
import math,json,shutil,runpy
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJ=ROOT.parents[1]
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
BASE='/Game/SceneTests/FreightSurfaceStudy20261112'
SRC=ROOT.parent/'FreightStationDesign20261112/scene-inputs.json'
REF=ROOT.parent/'FreightStationDesign20261112/01-concept.png'
TAG='FreightSurfaceStudy20261112'
RECEIPT=ROOT/'install-receipt.json'
E=u.EditorAssetLibrary
def backup():
    relative=TARGET.removeprefix('/Game/');content=PROJ/'Content'
    backup_dir=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for path in [content/(relative+'.umap')]+[content/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__')]:
        if path.exists():
            dest=backup_dir/path.relative_to(PROJ);dest.parent.mkdir(parents=True,exist_ok=True)
            if path.is_dir():shutil.copytree(path,dest)
            else:shutil.copy2(path,dest)
    return str(backup_dir)
def relief(material):
    name='SM_PackingConcreteRelief';path=BASE+'/Meshes/'+name
    if E.does_asset_exist(path):
        mesh=u.load_asset(path)
        if str(E.get_metadata_tag(mesh,'FreightStudy.Owner'))!=TAG:raise RuntimeError('Preserve existing '+path)
    else:
        task=u.AssetImportTask();task.filename=str(ROOT/(name+'.fbx'));task.destination_path=BASE+'/Meshes';task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.FbxFactory()
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.build_nanite=False;task.options=opts
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Relief import failed')
    mesh.modify();mesh.set_material(0,material);E.set_metadata_tag(mesh,'FreightStudy.Owner',TAG)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Relief asset save failed')
    return mesh
def record(d):RECEIPT.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def run():
    if RECEIPT.exists() and json.loads(RECEIPT.read_text('utf8')).get('stage')=='map_saved':return
    if Path(u.Paths.project_dir()).resolve()!=PROJ.resolve():raise RuntimeError('Wrong project')
    sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if sub and sub.get_game_world():raise RuntimeError('Preserve live gameplay')
    ex=tuple('/game/'+p+'/'+TARGET.removeprefix('/Game/').lower()+'/' for p in ('__externalactors__','__externalobjects__'))
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or any(p.get_name().lower().startswith(ex) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved map edits')
    old_world=sub.get_editor_world() if sub else None;previous=old_world.get_path_name().split('.')[0] if old_world else ''
    w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not w or w.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Target unavailable')
    world_actors=list(u.GameplayStatics.get_all_actors_of_class(w,u.Actor))
    bylabel={a.get_actor_label():a for a in world_actors}
    if any(TAG in [str(t) for t in a.tags] for a in world_actors):raise RuntimeError('An existing study layer is present')
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    original=json.loads(SRC.read_text('utf8'))['actors']
    old_label='WarehouseEntrance_Wall_PackingPlasterLoss';cart_label='StationWorkshop_11_SM_SW_RepairCart'
    old=bylabel[old_label];cart=bylabel[cart_label]
    card=old.get_component_by_class(u.DecalComponent);comp=cart.static_mesh_component
    for a,l in [(old,old_label),(cart,cart_label)]:
        row=original[l]
        if a.get_name()!=row['name'] or any(abs(v-t)>.02 for actual,expected in [(a.get_actor_location().to_tuple(),row['p']),(a.get_actor_rotation().to_tuple(),row['r']),(a.get_actor_scale3d().to_tuple(),row['s'])] for v,t in zip(actual,expected)):raise RuntimeError('Source pose changed: '+l)
    if str(card.get_decal_material().get_path_name())!=original[old_label]['decal']:raise RuntimeError('Packing damage changed')
    if comp.static_mesh.get_path_name()!=original[cart_label]['mesh'] or comp.get_material(0).get_path_name()!=original[cart_label]['bindings'][0]:raise RuntimeError('Cart binding changed')
    data={'stage':'building','map':TARGET,'backup':backup(),'concept':str(REF),'original_cart_material':comp.get_material(0).get_path_name(),'underlying_surface_slots_edited':0,'gameplay_or_visual_test':False,'camera_views':[]}
    record(data)
    surface,paint=runpy.run_path(str(ROOT/'materials.py'))['make']()
    mesh=relief(surface);data.update(stage='assets_saved',relief_mesh=mesh.get_path_name(),cart_material=paint.get_path_name());record(data)
    added=[]
    def new(cls,p,r,label):
        actor=api.spawn_actor_from_class(cls,u.Vector(*p),r)
        if not actor:raise RuntimeError('Spawn failed '+label)
        added.append(actor);actor.set_actor_label(label);actor.set_folder_path('StationLine/ReferenceSurfaceStudy')
        actor.set_editor_property('tags',[u.Name(TAG)]);return actor
    previous_visibility=card.get_editor_property('visible');previous_paint=comp.get_material(0)
    try:
        a=new(u.StaticMeshActor,[3079.,485.99,87.],u.Rotator(),'SurfaceStudy_PackingConcreteRelief')
        c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('NoCollision')
        c.set_cast_shadow(True);c.set_editor_property('ld_max_draw_distance',0.)
        for label,eye,look,fov in [('REF_01_PackingSurface',[2630.,28.,155.],[2958.,327.,79.],58.),
                                   ('REF_02_CartSurface',[8668.,-550.,149.],[8416.,-301.,59.],55.)]:
            delta=[v-t for v,t in zip(look,eye)]
            yaw=math.degrees(math.atan2(delta[1],delta[0]));pitch=math.degrees(math.atan2(delta[2],math.hypot(delta[0],delta[1])))
            a=new(u.CameraActor,eye,u.Rotator(pitch=pitch,yaw=yaw,roll=0),label)
            a.set_editor_property('is_editor_only_actor',True)
            cc=a.get_component_by_class(u.CameraComponent);cc.set_editor_property('field_of_view',fov)
            cc.set_editor_property('aspect_ratio',1.0);cc.set_editor_property('constrain_aspect_ratio',True)
            data['camera_views'].append(dict(label=label,eye=eye,pitch=pitch,yaw=yaw,horizontal_fov=fov,aspect_ratio=1.0))
        cart.modify();comp.modify();comp.set_material(0,paint)
        old.modify();card.modify();card.set_visibility(False,True)
        # Record actual comparison conditions without altering gameplay exposure.
        pp=bylabel.get('StationLine_Exposure')
        if pp:
            settings=pp.get_editor_property('settings')
            data['map_exposure']={key:str(settings.get_editor_property(key)) for key in ('auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','override_auto_exposure_min_brightness','override_auto_exposure_max_brightness')}
        external=[p for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().lower().startswith(ex)]
        if external and not u.EditorLoadingAndSavingUtils.save_packages(external,False):raise RuntimeError('Could not save external actors')
        if not u.EditorLoadingAndSavingUtils.save_map(w,TARGET):raise RuntimeError('Could not save the subject')
        data['stage']='map_saved';record(data)
    except Exception:
        comp.set_material(0,previous_paint);card.set_visibility(previous_visibility,True)
        for a in reversed(added):api.destroy_actor(a)
        raise
    if previous and previous!=TARGET and not previous.startswith('/Temp/'):u.EditorLoadingAndSavingUtils.load_map(previous)
    print('FREIGHT_REFERENCE_SURFACE_STUDY_SAVED '+TARGET,flush=True)
run()
