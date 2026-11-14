"""Save only the entrance dressing sample into the existing freight/station map."""
from pathlib import Path
from datetime import datetime
import json,shutil,traceback,types
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
PLAN=json.loads((ROOT/'Config/layout.json').read_text('utf8'))
TARGET=PLAN['map'];TAG=PLAN['tag'];BASE='/Game/SceneTests/FreightWarehouseEntranceSample20261111'
REVISION='freight_entrance_sample_20261111';OWNER='FreightEntrance.Owner'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
(ROOT/'Receipts').mkdir(exist_ok=True)
RECEIPT=ROOT/'Receipts/install.json'
helper=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
helper=helper.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','').replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}").replace('FacilitySurface.Owner',OWNER)
scope=dict(ROOT=ROOT,BASE=BASE,REVISION=REVISION,canonical=lambda p:p.split('.')[0]);exec(compile(helper,'entrance_material_helpers','exec'),scope)
H=types.SimpleNamespace(**scope)
def materials():
    out={}
    # Preserve the original concrete's normal. Dust/scuff overlays intentionally
    # write only colour, opacity and roughness, with three different authored masks.
    for key,texture,tone,opacity,rough in [('Dust','T_DecalDirt_04_A',.85,.36,.96),('Scuff','T_DecalDirt_03_A',.65,.46,.84),('Damp','T_DecalDirt_02_A',.24,.25,.78)]:
        m=H.own('Materials/M_'+key);L.delete_all_material_expressions(m)
        m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        sample=H.node(m,'TextureSample',texture=u.load_asset('/Game/HospitalCorridor/Textures/Decals/'+texture),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        color=H.node(m,'Multiply');H.wire(sample,color,'A','RGB');H.wire(H.constant(m,tone),color,'B');H.output(color,'BASE_COLOR')
        alpha=H.node(m,'Multiply');H.wire(sample,alpha,'A','A');H.wire(H.constant(m,opacity),alpha,'B');H.output(alpha,'OPACITY')
        H.output(H.constant(m,rough),'ROUGHNESS');out[key]=H.save(m).get_path_name()
    for key,name in [('Crack','MI_DecalWallCrack_01'),('Damage','MI_DecalDamage_01')]:
        out[key]='/Game/HospitalCorridor/Materials/Decals/'+name+'.'+name
    return out
def blocking_mesh(source):
    path=BASE+'/Meshes/'+source.rsplit('/',1)[-1].split('.')[0]
    if E.does_asset_exist(path):
        mesh=u.load_asset(path)
        if E.get_metadata_tag(mesh,OWNER)!=REVISION:raise RuntimeError('Preserve existing '+path)
    else:mesh=E.duplicate_asset(source,path)
    mesh.modify();E.set_metadata_tag(mesh,OWNER,REVISION)
    body=mesh.get_editor_property('body_setup');body.modify()
    # Exact static geometry, confined outside the main path. No shared mesh edits.
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Packing collision asset save failed '+path)
    return mesh
def save_world(world):
    suffix=TARGET.removeprefix('/Game/').lower()
    prefixes=tuple('/game/'+folder+'/'+suffix+'/' for folder in ('__externalactors__','__externalobjects__'))
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    owned=[p for p in dirty if p.get_name()==TARGET or p.get_name().lower().startswith(prefixes)]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Subject actor package save failed')
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Subject map save failed')
    return [p.get_name() for p in owned]
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if any('/gamemaps/design/l_freighttransit_theme_subject/' in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved subject actors')
    if RECEIPT.exists() and json.loads(RECEIPT.read_text('utf8')).get('stage')=='map_saved':
        print('ENTRANCE_SAMPLE_ALREADY_SAVED',flush=True);return
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    relative=TARGET.removeprefix('/Game/')
    for path in [PROJECT/'Content'/(relative+'.umap')]+[PROJECT/'Content'/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__')]:
        if not path.exists():continue
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
        if path.is_dir():shutil.copytree(path,dest)
        else:shutil.copy2(path,dest)
    report={'stage':'preparing','map':TARGET,'backup':str(backup),'tests_run':False,'game_run':False,'rendered':False,'editor_started':False}
    def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    try:
        mats=materials();meshcache={}
        for r in PLAN['parts']:
            key=(r['mesh'],r['collision'])
            if key not in meshcache:meshcache[key]=blocking_mesh(r['mesh']) if r['collision']=='BlockAll' else u.load_asset(r['mesh'])
            if not meshcache[key]:raise RuntimeError('Missing sample mesh '+r['mesh'])
        report.update(stage='assets_saved',materials=mats,mesh_assets={a+'|'+b:m.get_path_name() for (a,b),m in meshcache.items()});record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        if not world:raise RuntimeError('Target map unavailable')
        actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        current=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
        names={a.get_name():a for a in current}
        original='/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete.MI_WallConcrete'
        for name in ['StaticMeshActor_21','StaticMeshActor_22','StaticMeshActor_23','StaticMeshActor_29','StaticMeshActor_32']:
            a=names[name]
            if a.static_mesh_component.get_material(0).get_path_name()!=original:raise RuntimeError('Original surface changed; preserve '+name)
        snapshot=json.loads((ROOT.parent/'FreightWarehouseReview20261111/scene-inputs.json').read_text('utf8'))['maps']['current']['actors']
        for r in snapshot:
            if r['name'] in ('StaticMeshActor_21','StaticMeshActor_22','StaticMeshActor_23','StaticMeshActor_36','StaticMeshActor_39','ColdSteelSceneContainer_20'):
                a=names[r['name']]
                actual=[list(a.get_actor_location().to_tuple()),list(a.get_actor_rotation().to_tuple()),list(a.get_actor_scale3d().to_tuple())]
                if any(abs(x-y)>.01 for aa,bb in zip(actual,[r['position'],r['rotation'],r['scale']]) for x,y in zip(aa,bb)):raise RuntimeError('Support placement changed; preserve '+r['name'])
        remove=set(PLAN['remove_labels']);removed=[]
        for a in current:
            tags=[str(t) for t in a.tags]
            if TAG in tags or (a.get_actor_label() in remove and 'FreightWarehouse.Weathering20261110' in tags):
                removed.append(a.get_actor_label());actors.destroy_actor(a)
        def named(a,r):
            a.set_actor_label('WarehouseEntrance_'+r['id']);a.set_folder_path('StationLine/WarehouseEntranceSample/'+r['group'])
            a.set_editor_property('tags',[u.Name(TAG),u.Name('AbandonedCargoWarehouse'),u.Name('StationLine.Subject')])
        for r in PLAN['parts']:
            pitch,yaw,roll=r['rotation'];a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*r['position']),u.Rotator(pitch=pitch,yaw=yaw,roll=roll))
            named(a,r);c=a.static_mesh_component;c.set_static_mesh(meshcache[(r['mesh'],r['collision'])]);a.set_actor_scale3d(u.Vector(*r['scale']))
            c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name(r['collision']);c.set_cast_shadow(r['shadow'])
            c.set_editor_property('ld_max_draw_distance',r['draw_distance'])
        for r in PLAN['decals']:
            pitch,yaw,roll=r['rotation'];a=actors.spawn_actor_from_class(u.DecalActor,u.Vector(*r['position']),u.Rotator(pitch=pitch,yaw=yaw,roll=roll))
            named(a,r);a.set_actor_location(u.Vector(*r['position']),False,True);a.set_actor_rotation(u.Rotator(pitch=pitch,yaw=yaw,roll=roll),True)
            c=a.get_component_by_class(u.DecalComponent);c.set_decal_material(u.load_asset(mats[r['material']]))
            c.set_editor_property('decal_size',u.Vector(*r['size']));c.set_editor_property('sort_order',4 if r['material'] in ('Crack','Damage') else 2)
            c.set_editor_property('fade_screen_size',.0015)
        report.update(stage='map_saved',saved_packages=save_world(world),removed_previous_dressing=removed,
                      installed_meshes=len(PLAN['parts']),installed_decals=len(PLAN['decals']),preserved=PLAN['preserve'],
                      entry_command='open '+TARGET)
        record();print('FREIGHT_ENTRANCE_SAMPLE_MAP_SAVED '+TARGET,flush=True)
        if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
    except Exception:
        report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
