"""Import the owned upper-room revision, update only the existing subject map."""
import json,re,sys,traceback,hashlib,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent;PROJECT=ROOT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(SOURCE/'Scripts'))
from layout import BASE,apply,interaction_specs
DATA=json.loads((ROOT/'manifest.json').read_text('utf8'))
SCENE=json.loads((SOURCE/'Config/scene.json').read_text('utf8'));CHANGES=apply(SCENE)
ROOM=next(r for r in SCENE['rooms'] if r['id']=='AccumulatorControl')
MAP='/Game/GameMaps/Design/L_PowerTheme20261004_Subject'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
TAG='PowerUpperControl20261005.Source'
report=dict(stage='preparing',saved_assets=[],replaced_meshes=[],moved_actors=[],interactions=[],map=MAP,
    tests_run=False,rendered=False,game_run=False,editor_opened=False,random_pool_registered=False)

def record():
    (ROOT/'Receipts').mkdir(exist_ok=True)
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
    value=u.load_asset(path)
    if not value:raise RuntimeError('Required existing asset missing: '+path)
    return value
def guard():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: no edit or save while playing')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved editor map')
    if not E.does_asset_exist(MAP):raise RuntimeError('Existing PowerTheme subject missing')
def world_location(p):
    q=[p[i]+ROOM['origin_m'][i] for i in range(3)]
    return u.Vector(q[0]*100,-q[1]*100,q[2]*100)
def place(actor,position,yaw):
    actor.modify();actor.set_actor_location(world_location(position),False,True)
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=-yaw,roll=0),True)
def move(label,p,yaw,actors):
    if label not in actors:raise RuntimeError('Expected control-room actor missing: '+label)
    actor=actors[label];place(actor,p,yaw)
    report['moved_actors'].append(dict(actor=label,position_m=p,yaw_deg=yaw))
def tag(actor,label):
    actor.set_actor_label(label);actor.set_folder_path('PowerTheme/AccumulatorControl/UpperControlRoom')
    actor.set_editor_property('tags',list(dict.fromkeys(list(actor.tags)+[u.Name('PowerTheme.Subject'),
        u.Name('PowerTheme.Room.AccumulatorControl'),u.Name('PowerTheme.UpperControl20261005')])))
    return actor
def upsert(cls,spec,actors):
    label='PowerTheme_'+spec['id'];actor=actors.get(label)
    if not actor:actor=tag(AA.spawn_actor_from_class(cls,world_location(spec['position_m']),u.Rotator()),label)
    place(actor,spec['position_m'],spec['yaw_deg']);return actor

def patch_loaded_map():
    actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
    for item in DATA['meshes']:
        if not item['previous_mesh']:continue
        label='PowerTheme_'+item['name']
        actor=actors.get(label)
        if not actor:raise RuntimeError('Expected room mesh actor missing: '+label)
        component=actor.get_component_by_class(u.StaticMeshComponent)
        actor.modify();component.modify();component.set_static_mesh(asset(item['mesh']))
        # These are newly grouped architecture slots; bind by the imported
        # slot name rather than reusing a numeric override from the old group.
        component.set_editor_property('override_materials',[])
        component.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
        component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if item['collision'] else u.CollisionEnabled.NO_COLLISION)
        component.set_cast_shadow(item['cast_shadow'])
        if item['kind']=='Rails':
            for obj,prop in ((actor,'tags'),(component,'component_tags')):
                obj.set_editor_property(prop,list(dict.fromkeys(list(obj.get_editor_property(prop))+[u.Name('Traversal.GuardrailDrop')])))
        report['replaced_meshes'].append(dict(actor=label,mesh=item['mesh']))
    for p in ROOM['authored_parts']+ROOM['reused_parts']:
        if p['id'] in CHANGES['moved_parts'] and not p.get('container_id'):
            move('PowerTheme_'+p['id'],p['position_m'],p.get('yaw_deg',0),actors)
    for p in ROOM['scene_containers']:
        if p['id'].startswith(('PPE_03','PPE_04','Records_02')):
            move('PowerTheme_AccumulatorControl_'+p['id'],p['position_m'],p.get('yaw_deg',0),actors)
    for p in ROOM['lights']:
        if p['id'] in CHANGES['moved_lights']:
            move('PowerTheme_AccumulatorControl_'+p['id'],p['position_m'],0,actors)
    specs=interaction_specs(SCENE)
    for spec in specs['glass']:
        actor=upsert(u.WardGlassWindow,spec,actors);pane=actor.get_editor_property('glass_pane');pane.modify()
        prefix=BASE+'/Meshes/SM_Power_UpperControl'+spec['kind']
        pane.set_static_mesh(asset(prefix+'PaneV5'));pane.set_cast_shadow(False)
        pane.set_editor_property('receives_decals',False)
        for key,path in dict(fracture_mesh=prefix+'FractureV5',
            fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
            impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',
            break_sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0').items():pane.set_editor_property(key,asset(path))
        pane.set_editor_property('pane_dimensions',u.Vector(spec['width_m']*100,spec['height_m']*100,.8))
        report['interactions'].append(dict(actor=actor.get_actor_label(),type='breakable_glass'))
    for spec in specs['doors']:
        actor=upsert(u.ColdSteelDoor,spec,actors)
        comp={c.get_name():c for c in actor.get_components_by_class(u.SceneComponent)}
        frame,leaf,hinge=[comp[k] for k in ('DoorFrame','DoorLeaf','DoorHinge')]
        frame.set_static_mesh(None);frame.set_collision_profile_name('NoCollision');frame.set_visibility(False)
        mesh=asset(spec['leaf_mesh']);leaf.set_static_mesh(mesh)
        positive=spec['positive_hinge'];sign=1 if positive else -1
        leaf.set_relative_rotation(u.Rotator(pitch=0,yaw=180 if positive else 0,roll=0),False,True)
        box=mesh.get_bounding_box();center=(box.min+box.max)*.5;extent=(box.max-box.min)*.5
        hinge.set_relative_location(u.Vector(0,sign*extent.y,0),False,True)
        leaf.set_relative_location(u.Vector(-center.x,-sign*extent.y-center.y,extent.z-center.z),False,True)
        for key,value in dict(hinge_on_positive_y=positive,open_angle_degrees=spec['open_angle_degrees'],open_seconds=.55,auto_close_seconds=0).items():actor.set_editor_property(key,value)
        report['interactions'].append(dict(actor=actor.get_actor_label(),type='interactive_sprint_push_door'))
    return dict(meshes=report['replaced_meshes'],moved=report['moved_actors'],interactions=report['interactions'])

def main():
    guard();record()
    # Retain the saved pre-edit map as a scoped recoverable snapshot.
    original=PROJECT/'Content/GameMaps/Design/L_PowerTheme20261004_Subject.umap'
    snapshot=ROOT/'Snapshots/L_PowerTheme20261004_Subject.before.umap'
    snapshot.parent.mkdir(exist_ok=True)
    if not snapshot.exists():shutil.copy2(original,snapshot)
    for item in DATA['meshes']:
        path=item['mesh'];key=item['sha256']
        if E.does_asset_exist(path):
            mesh=asset(path)
            if E.get_metadata_tag(mesh,TAG)!=key:raise RuntimeError('Preserve different saved upper-room mesh: '+path)
            report['saved_assets'].append(path);continue
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.one_convex_hull_per_ucx=True
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path,task.destination_name=path.rsplit('/',1)
        task.automated=True;task.replace_existing=False;task.save=False;task.options=options;task.factory=u.FbxFactory()
        AT.import_asset_tasks([task]);mesh=asset(path)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
            mesh.set_material(i,asset(item['materials'][name]))
        build=SM.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        SM.set_lod_build_settings(mesh,0,build)
        body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
        settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True
        mesh.set_editor_property('nanite_settings',settings)
        if settings.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed: '+item['name'])
        E.set_metadata_tag(mesh,TAG,key)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed: '+path)
        report['saved_assets'].append(path);record()
    report['stage']='assets_saved';record();guard()
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Cannot load existing subject map')
    patch_loaded_map()
    E.set_metadata_tag(world,'PowerTheme.UpperControlRevision','20261005')
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Subject map save failed')
    report['stage']='map_saved';record()
    u.log('POWER_UPPER_CONTROL_MAP_SAVED meshes=%s moved=%s interactions=%s'%(len(report['replaced_meshes']),len(report['moved_actors']),len(report['interactions'])))
if __name__=='__main__':
    try:main()
    except Exception:
        report['error']=traceback.format_exc();record();raise
