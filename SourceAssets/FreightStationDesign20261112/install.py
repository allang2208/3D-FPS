"""Install the design-point revisions in the user’s existing station sample."""
from pathlib import Path
from datetime import datetime
from collections import Counter
import shutil,json
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
TAG='FreightStation.Design20261112'
CLOTH='/Game/SceneTests/FreightStationDesign20261112/Meshes/SM_CartHandleCloth'
COTTON='/Game/Dungeons/TransitIncidentDetail20261010/Materials/M_IncidentDetail_Cotton'
LIB=u.EditorAssetLibrary
out=ROOT/'install-receipt.json'
def material(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
def import_cloth():
    if LIB.does_asset_exist(CLOTH):
        asset=material(CLOTH)
        if str(LIB.get_metadata_tag(asset,'FreightStation.Owner'))!=TAG:raise RuntimeError('Mesh name already in use')
        return asset
    fabric=material(COTTON)
    task=u.AssetImportTask();task.filename=str(ROOT/'SM_CartHandleCloth.fbx')
    task.destination_path,task.destination_name=CLOTH.rsplit('/',1)
    task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.FbxFactory()
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
    data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options=options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=material(CLOTH)
    mesh.modify();mesh.set_material(0,fabric);LIB.set_metadata_tag(mesh,'FreightStation.Owner',TAG)
    if not LIB.save_loaded_asset(mesh,False):raise RuntimeError('Cotton mesh save failed')
    return mesh

def backup():
    rel=TARGET.removeprefix('/Game/');content=PROJECT/'Content'
    dest=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for source in [content/(rel+'.umap')]+[content/t/rel for t in ('__ExternalActors__','__ExternalObjects__')]:
        if not source.exists():continue
        dst=dest/source.relative_to(PROJECT);dst.parent.mkdir(parents=True,exist_ok=True)
        if source.is_dir():shutil.copytree(source,dst)
        else:shutil.copy2(source,dst)
    return str(dest)

def current_receivers(world,plan,snapshot):
    bylabel={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    touched={r['source'] for r in plan['operations'] if r['source']}
    labels=touched|{k for k in snapshot if k in ('StationWorkshop_0_SM_SW_Walls','StationWorkshop_11_SM_SW_RepairCart','StationLine_WarehouseStationLink_0','StationLine_AbandonedCargoWarehouse_0') or k in ('StationLine_AbandonedTransitStation_1','StationLine_AbandonedTransitStation_16')}
    for label in labels:
        row=snapshot[label];a=bylabel.get(label)
        if not a or a.get_name()!=row['name']:raise RuntimeError('Receiver or prop changed: '+label)
        if label in touched and not any(str(t) in ('FreightStation.UnifiedPatina20261111','FreightWarehouse.EntranceSample20261111','FreightWarehouse.DerelictPass20261111') for t in a.tags):
            raise RuntimeError('Decoration ownership changed: '+label)
        actual=(a.get_actor_location().to_tuple(),a.get_actor_rotation().to_tuple(),a.get_actor_scale3d().to_tuple())
        if any(abs(p-q)>.02 for aa,bb in zip(actual,[row['p'],row['r'],row['s']]) for p,q in zip(aa,bb)):raise RuntimeError('Moved since design capture: '+label)
        if 'mesh' in row:
            component=a.get_component_by_class(u.StaticMeshComponent)
            if not component or component.static_mesh.get_path_name()!=row['mesh']:raise RuntimeError('Mesh changed: '+label)
        elif 'decal' in row:
            component=a.get_component_by_class(u.DecalComponent)
            if component.get_decal_material().get_path_name()!=row['decal'] or any(abs(x-y)>.02 for x,y in zip(component.get_editor_property('decal_size').to_tuple(),row['size'])):raise RuntimeError('Decal changed: '+label)
    return bylabel
def main():
    if out.exists() and json.loads(out.read_text('utf8')).get('stage')=='map_saved':
        print('FREIGHT_DESIGN_ALREADY_SAVED');return
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    plan=json.loads((ROOT/'construction.json').read_text('utf8'))
    snapshot=json.loads((ROOT/'scene-inputs.json').read_text('utf8'))['actors']
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active game')
    stems=tuple('/game/'+t+'/'+TARGET.removeprefix('/Game/').lower()+'/' for t in ('__externalactors__','__externalobjects__'))
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or any(p.get_name().lower().startswith(stems) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved edits')
    prior=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world or world.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Target not loaded')
    bylabel=current_receivers(world,plan,snapshot)
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    cloth=import_cloth()
    report={'stage':'working','map':TARGET,'backup':backup(),'concept':'01-concept.png','layout':'02-layout.png','points':plan['points'],'cloth':cloth.get_path_name(),'game_or_visual_tests':False}
    def record():out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    changes=[]; retired=[]
    with u.ScopedEditorTransaction('Warehouse and station concept design points'):
        for row in plan['operations']:
            key=row['point'];action=row['op'];label=row['source']
            if action=='retire':
                retired.append(label);continue
            point=u.Vector(*row['p']);pitch,yaw,roll=row['r'];rot=u.Rotator(pitch=pitch,yaw=yaw,roll=roll)
            if action=='move':
                actor=bylabel[label];actor.modify()
            else:
                source=bylabel.get(label);dec=source.get_component_by_class(u.DecalComponent) if source else None
                actor=api.spawn_actor_from_class(u.DecalActor if dec else u.StaticMeshActor,point,rot)
                if not actor:raise RuntimeError('Spawn failed at '+row['id'])
                actor.set_actor_label('FreightDesign_'+key+'_'+row['id'])
                if dec:
                    actor.get_component_by_class(u.DecalComponent).set_decal_material(dec.get_decal_material())
                else:
                    c=actor.static_mesh_component;original=source.static_mesh_component if source else None
                    c.set_static_mesh(original.static_mesh if original else cloth)
                    if original:
                        for i in range(original.get_num_materials()):c.set_material(i,original.get_material(i))
                    c.set_collision_profile_name('NoCollision');c.set_cast_shadow(True)
                    c.set_editor_property('ld_max_draw_distance',4200.)
                    c.set_mobility(u.ComponentMobility.STATIC)
            actor.set_actor_location(point,False,True);actor.set_actor_rotation(rot,True)
            if 's' in row:actor.set_actor_scale3d(u.Vector(*row['s']))
            if 'size' in row:
                c=actor.get_component_by_class(u.DecalComponent);c.modify();c.set_editor_property('decal_size',u.Vector(*row['size']))
                if action=='copy':c.set_editor_property('sort_order',2);c.set_editor_property('fade_screen_size',.0015)
            actor.set_folder_path('StationLine/Design20261112/'+key+'_'+plan['points'][key])
            tags=list(actor.tags)
            tags.extend(u.Name(v) for v in (TAG,'FreightDesign.Point'+key) if v not in [str(x) for x in tags])
            actor.set_editor_property('tags',tags)
            changes.append({'point':key,'action':action,'actor':actor.get_actor_label()})
        for label in retired:
            if not api.destroy_actor(bylabel[label]):raise RuntimeError('Retirement failed: '+label)
    external=[p for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().lower().startswith(stems)]
    if external and not u.EditorLoadingAndSavingUtils.save_packages(external,False):raise RuntimeError('External actors could not be saved')
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Map save failed')
    report.update(stage='map_saved',changes=changes,retired=retired,counts=dict(Counter(r['op'] for r in plan['operations'])),entry='open '+TARGET)
    record();print('FREIGHT_STATION_DESIGN_MAP_SAVED '+TARGET,flush=True)
    if prior and prior!=TARGET and not prior.startswith('/Temp/'):u.EditorLoadingAndSavingUtils.load_map(prior)
main()
