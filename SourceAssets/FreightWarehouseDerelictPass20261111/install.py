"""Install the derelict art pass in the existing subject, preserving room/gameplay."""
from pathlib import Path
from datetime import datetime
import json,shutil,runpy,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
PLAN=json.loads((ROOT/'Config/layout.json').read_text('utf8'));INPUTS=json.loads((ROOT/'inputs.json').read_text('utf8'))
TARGET=PLAN['map'];TAG=PLAN['tag'];OLD='FreightWarehouse.Weathering20261110';ENTRANCE='FreightWarehouse.EntranceSample20261111'
M=runpy.run_path(str(ROOT/'materials.py'));E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
RECEIPT=ROOT/'Receipts/install.json';RECEIPT.parent.mkdir(exist_ok=True)
def blocking_mesh(source):
    path=M['BASE']+'/Meshes/'+source.rsplit('/',1)[-1].split('.')[0]
    if E.does_asset_exist(path):
        mesh=u.load_asset(path)
        if E.get_metadata_tag(mesh,M['OWNER'])!=M['REVISION']:raise RuntimeError('Preserve existing mesh '+path)
    else:mesh=E.duplicate_asset(source,path)
    mesh.modify();E.set_metadata_tag(mesh,M['OWNER'],M['REVISION'])
    body=mesh.get_editor_property('body_setup');body.modify();body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Collision mesh save failed '+path)
    return mesh
def save_world(w):
    stem=TARGET.removeprefix('/Game/').lower();prefixes=tuple('/game/'+folder+'/'+stem+'/' for folder in ('__externalactors__','__externalobjects__'))
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    owned=[p for p in dirty if p.get_name()==TARGET or p.get_name().lower().startswith(prefixes)]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Subject actor save failed')
    if not u.EditorLoadingAndSavingUtils.save_map(w,TARGET):raise RuntimeError('Subject save failed')
    return [p.get_name() for p in owned]
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if any('/gamemaps/design/l_freighttransit_theme_subject/' in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved subject actors')
    if RECEIPT.exists() and json.loads(RECEIPT.read_text('utf8')).get('stage')=='map_saved':
        print('DERELICT_PASS_ALREADY_SAVED',flush=True);return
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');relative=TARGET.removeprefix('/Game/')
    for p in [PROJECT/'Content'/(relative+'.umap')]+[PROJECT/'Content'/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__')]:
        if not p.exists():continue
        dst=backup/p.relative_to(PROJECT);dst.parent.mkdir(parents=True,exist_ok=True)
        if p.is_dir():shutil.copytree(p,dst)
        else:shutil.copy2(p,dst)
    report={'stage':'preparing','target':TARGET,'backup':str(backup),'reference':PLAN['reference'],
            'game_run':False,'tests_run':False,'rendered':False,'editor_started':False,'original_surface_bindings_modified':False}
    def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    try:
        materials=M['build']();cache={}
        for r in PLAN['parts']:
            key=(r['mesh'],r['collision'])
            if key not in cache:cache[key]=blocking_mesh(r['mesh']) if r['collision']=='BlockAll' else u.load_asset(r['mesh'])
            if not cache[key]:raise RuntimeError('Missing source mesh '+r['mesh'])
        report.update(stage='assets_saved',materials=materials);record()
        w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        if not w:raise RuntimeError('Target unavailable')
        actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        current=list(u.GameplayStatics.get_all_actors_of_class(w,u.Actor));byname={a.get_name():a for a in current}
        original='/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete.MI_WallConcrete'
        for name in ['StaticMeshActor_21','StaticMeshActor_22','StaticMeshActor_23','StaticMeshActor_29','StaticMeshActor_32']:
            if byname[name].static_mesh_component.get_material(0).get_path_name()!=original:raise RuntimeError('Preserve changed concrete binding '+name)
        for r in INPUTS['actors']:
            if r['name'] in ('StaticMeshActor_21','StaticMeshActor_22','StaticMeshActor_23','StaticMeshActor_36','StaticMeshActor_39') or OLD in r['tags'] or ENTRANCE in r['tags']:
                a=byname.get(r['name'])
                if not a or a.get_actor_label()!=r['label']:raise RuntimeError('Preserve changed scene object '+r['label'])
                actual=[list(a.get_actor_location().to_tuple()),list(a.get_actor_rotation().to_tuple()),list(a.get_actor_scale3d().to_tuple())]
                if any(abs(x-y)>.01 for aa,bb in zip(actual,[r['position'],r['rotation'],r['scale']]) for x,y in zip(aa,bb)):raise RuntimeError('Preserve moved object '+r['label'])
        removed=[];survivors=[]
        for a in current:
            tags=[str(v) for v in a.tags]
            if TAG in tags or (OLD in tags and a.get_actor_label() in PLAN['remove_labels']):
                removed.append(a.get_actor_label());actors.destroy_actor(a)
            else:survivors.append(a)
        changed_decals=[];changed_props=[]
        for a in survivors:
            tags=[str(v) for v in a.tags]
            if OLD not in tags and ENTRANCE not in tags:continue
            for c in a.get_components_by_class(u.DecalComponent):
                old=c.get_decal_material().get_name();kind=None
                if old in ('M_Dust','M_Scuff','M_Damp','MI_Dust','MI_Scuff','MI_Damp','MI_Oil'):kind=old.split('_',1)[1]
                elif 'Runoff_' in a.get_actor_label():kind='Leak'
                if kind in materials:
                    a.modify();c.modify();c.set_decal_material(u.load_asset(materials[kind]));changed_decals.append(a.get_actor_label())
            for c in a.get_components_by_class(u.StaticMeshComponent):
                if not c.static_mesh:continue
                state='Settled' if any(s in a.get_actor_label() for s in ('Rack','DockWest','Storage','Broken','EmptyReturn')) else 'Handled'
                for slot in range(c.get_num_materials()):
                    source=c.get_material(slot)
                    if source and '/UndergroundTunnel/Materials/MI_Prop_' in source.get_path_name():
                        variant=M['prop_variant'](source,state)
                        if variant!=source:a.modify();c.modify();c.set_material(slot,variant);changed_props.append(a.get_actor_label())
                if OLD in tags and any(n in c.static_mesh.get_name() for n in ('WoodPallet','WoodCrate','Oildrum')):
                    a.modify();c.modify();c.set_static_mesh(blocking_mesh(c.static_mesh.get_path_name()));c.set_collision_profile_name('BlockAll')
        def named(a,r):
            a.set_actor_label('WarehouseDerelict_'+r['id']);a.set_folder_path('StationLine/WarehouseDerelict/'+r['group'])
            a.set_editor_property('tags',[u.Name(TAG),u.Name('AbandonedCargoWarehouse'),u.Name('StationLine.Subject')])
        for r in PLAN['parts']:
            pitch,yaw,roll=r['rotation'];a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*r['position']),u.Rotator(pitch=pitch,yaw=yaw,roll=roll));named(a,r)
            c=a.static_mesh_component;c.set_static_mesh(cache[(r['mesh'],r['collision'])]);a.set_actor_scale3d(u.Vector(*r['scale']))
            c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name(r['collision']);c.set_cast_shadow(r['shadow']);c.set_editor_property('ld_max_draw_distance',r['draw_distance'])
            for i in range(c.get_num_materials()):
                s=c.get_material(i)
                if s and '/UndergroundTunnel/Materials/MI_Prop_' in s.get_path_name():c.set_material(i,M['prop_variant'](s,'Settled'))
        for r in PLAN['decals']:
            pitch,yaw,roll=r['rotation'];a=actors.spawn_actor_from_class(u.DecalActor,u.Vector(*r['position']),u.Rotator(pitch=pitch,yaw=yaw,roll=roll));named(a,r)
            a.set_actor_location(u.Vector(*r['position']),False,True);a.set_actor_rotation(u.Rotator(pitch=pitch,yaw=yaw,roll=roll),True)
            c=a.get_component_by_class(u.DecalComponent);c.set_decal_material(u.load_asset(materials[r['material']]))
            c.set_editor_property('decal_size',u.Vector(*r['size']));c.set_editor_property('sort_order',4 if r['material']=='Damage' else 2);c.set_editor_property('fade_screen_size',.0015)
        report.update(stage='map_saved',saved_packages=save_world(w),removed_labels=removed,added_meshes=len(PLAN['parts']),added_decals=len(PLAN['decals']),
                      updated_patina_decals=changed_decals,updated_native_prop_materials=sorted(set(changed_props)),
                      preserved=['accepted entrance mesh layout','original wall/floor bindings','original structure and cargo','all lights and postprocess','containers and gameplay','spawn and main route'],entry_command='open '+TARGET)
        record();print('FREIGHT_DERELICT_PASS_MAP_SAVED '+TARGET,flush=True)
        if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
    except Exception:
        report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
