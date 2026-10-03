"""Import, build and save the authored V4 parts in the four owned sample maps."""
import json,hashlib,re,shutil,sys
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'ScenePolishV4'
if json.loads((ROOT/'Config/room.json').read_text('utf8')).get('room_details_revision',0)>=5:
    current=ROOT/'Scripts/import_room_details_v5.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
CFG=json.loads((OUT/'Authored/room-polished.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/ScenePolishV4'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json';report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},materials=[],backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,rewards_deferred=True,random_pool_registered=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
sys.path.insert(0,str(ROOT/'Scripts'))
from build_scene_polish_materials_v4 import build_materials
report['materials'],outline=build_materials(ROOT,BASE);report['outline']=outline.get_path_name();record()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshes={};items={r['name']:r for r in MAN['objects']}
for item in MAN['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();mesh=u.load_asset(path)
    if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:
        raise RuntimeError('Preserve different existing asset '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.one_convex_hull_per_ucx=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+path)
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing finish '+item['materials'][key])
            mesh.set_material(index,material)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
        n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        n.fallback_percent_triangles=1.;n.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',n)
        if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite production build failed '+path)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+path)
    meshes[item['name']]=mesh;report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles']);record()
report['stage']='assets_saved';record()
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
def owned(a):return 'StaffLiving.Subject' in [str(t) for t in a.tags]
def loc(p,offset):return u.Vector((p[0]+offset[0])*100,-(p[1]+offset[1])*100,(p[2]+offset[2])*100)
def rot(p):return u.Rotator(pitch=0,yaw=-p['yaw_blender_deg'],roll=0)
def static(name,p,offset,rid):
    a=AA.spawn_actor_from_class(u.StaticMeshActor,loc(p['position'],offset),rot(p));c=a.static_mesh_component
    a.set_actor_label('StaffSubject_'+rid+'_'+p['id']);a.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(rid)])
    a.set_folder_path('StaffLiving/'+rid);c.set_static_mesh(meshes[name]);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if items[name]['collision'] else 'NoCollision')
    return a
targets=[(CFG['maps'][r['id']],[r],[[0,0,0]]) for r in CFG['rooms']]
targets.append((CFG['sample_map'],CFG['rooms'],CFG['preview_placements_m']))
for target,rooms,offsets in targets:
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load owned staff map '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if owned(a)}
    changed=[]
    for room,offset in zip(rooms,offsets):
        rid=room['id'];keys=set(MAN['prototypes'])-{'BookcaseBody','BookshelfBody','BookshelfDrawer'}
        keys.update(('Sofa','CoffeeTable'))
        labels={'StaffSubject_'+rid+'_'+p['id'] for p in room['furniture'] if p['prototype'] in keys}
        labels.update('StaffSubject_'+rid+'_'+k+'_Instances' for k in keys)
        for label in labels:
            if label in actors:AA.destroy_actor(actors.pop(label))
        for p in room['furniture']:
            if p['prototype'] not in keys:continue
            name=MAN['prototypes'].get(p['prototype'])
            if not name:
                name='SM_Staff_'+p['prototype'];meshes[name]=u.load_asset(CFG['ue_base']+'/Meshes/'+name);items[name]=dict(collision=True)
            if not meshes[name]:raise RuntimeError('Missing shared furniture '+name)
            static(name,p,offset,rid);changed.append(p['id'])
        edge='SM_Staff_'+rid+'_CarpetEdges_V4'
        if edge in meshes:
            label='StaffSubject_'+rid+'_CarpetEdges'
            if label in actors:AA.destroy_actor(actors.pop(label))
            static(edge,dict(id='CarpetEdges',position=[0,0,0],yaw_blender_deg=0),offset,rid)
        if rid=='StaffDormitory':
            for p in MAN['preview_placements']:
                a=actors.get('StaffSubject_'+rid+'_'+p['id'])
                if not a:raise RuntimeError('Preserve missing layout actor '+p['id'])
                a.set_actor_location_and_rotation(loc(p['position'],offset),rot(p),False,True)
                if isinstance(a,u.ColdSteelSceneContainer):
                    key=dict(Bookcase='BookcaseBody',Bookshelf='BookshelfBody').get(p['prototype'])
                    if key:a.body.set_static_mesh(meshes[MAN['prototypes'][key]])
                    if p['prototype']=='Bookshelf':a.door.set_static_mesh(meshes[MAN['prototypes']['BookshelfDrawer']])
            manager=actors.get('StaffSubject_StaffDormitory_LayoutVariantsV2')
            if not manager:raise RuntimeError('Preserve missing dormitory layout manager')
            manager.set_editor_property('layout_json',json.dumps(MAN['layouts'],ensure_ascii=False,separators=(',',':')))
            manager.set_actor_location(loc([0,0,0],offset),False,True)
    if target==CFG['sample_map']:
        if 'StaffSubject_Link_CarpetEdges' in actors:AA.destroy_actor(actors.pop('StaffSubject_Link_CarpetEdges'))
        edge='SM_Staff_Link_CarpetEdges_V4';static(edge,dict(id='CarpetEdges',position=[0,0,0],yaw_blender_deg=0),[16,0,0],'Link')
    for a in AA.get_all_level_actors():
        if not owned(a):continue
        if isinstance(a,u.ColdSteelSceneContainer):
            for c in (a.body,a.door):c.set_render_custom_depth(False);c.set_custom_depth_stencil_value(201)
        elif isinstance(a,u.PostProcessVolume) and 'ColdSteel.SceneContainer.Outline' in [str(t) for t in a.tags]:
            settings=a.get_editor_property('settings');blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',outline)
            blends=u.WeightedBlendables();blends.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',blends)
            a.set_editor_property('settings',settings)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',updated_static_placements=changed,focus_outline=True);record()
    u.log('STAFF_SCENE_POLISH_V4_MAP_SAVED '+target)

# Update the editable module draft with the same meshes and transforms.
for filename in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/filename,backup/filename)
draft_path=ROOT/'Config/modules-draft.json';draft=json.loads(draft_path.read_text('utf8'))
for module in draft['modules']:
    room=next(r for r in CFG['rooms'] if r['id']==module['id']);byid={p['id']:p for p in room['furniture']}
    patchkeys=set(MAN['prototypes'])-{'BookcaseBody','BookshelfBody','BookshelfDrawer'};patchkeys.update(('Sofa','CoffeeTable'))
    # Existing static prop records retain IDs; newly added tables/racks receive IDs.
    for p in room['furniture']:
        if p['prototype'] not in patchkeys:continue
        name=MAN['prototypes'].get(p['prototype'],'SM_Staff_'+p['prototype'])
        meshpath=items[name]['asset'] if name in MAN['prototypes'].values() else CFG['ue_base']+'/Meshes/'+name
        part=next((x for x in module['parts'] if x.get('id')==p['id']),None)
        if part is None:part=dict(id=p['id'],materials=[]);module['parts'].append(part)
        x,y,z=p['position'];part.update(mesh=meshpath,position=[x*100,-y*100,z*100],yaw=-p['yaw_blender_deg'],collision=items[name]['collision'])
    edge='SM_Staff_'+module['id']+'_CarpetEdges_V4'
    if edge in items:
        module['parts']=[p for p in module['parts'] if p.get('id')!='CarpetEdges']
        module['parts'].append(dict(id='CarpetEdges',mesh=items[edge]['asset'],position=[0,0,0],yaw=0,collision=False,materials=[]))
    if module['id']=='StaffDormitory':
        poses={p['id']:p for p in MAN['preview_placements']}
        for c in module['scene_containers']:
            slot=c.get('layout_slot') or c['container_id'].split('.',1)[1];p=poses.get(slot)
            if not p:continue
            c.update(position=p['position_cm'],yaw=p['yaw_ue'])
            key=dict(Bookcase='BookcaseBody',Bookshelf='BookshelfBody').get(p['prototype'])
            if key:c['body']=items[MAN['prototypes'][key]]['asset']
            if p['prototype']=='Bookshelf':c['door']=items[MAN['prototypes']['BookshelfDrawer']]['asset']
        module['layout_variants']=MAN['layouts']
        module['variable_static_furniture']=[dict(mesh=CFG['ue_base']+'/Meshes/SM_Staff_'+p['prototype'],layout_slot=p['id'],position=p['position_cm'],yaw=p['yaw_ue']) for p in MAN['preview_placements'] if p['prototype'] in ('Desk','Chair')]
    module['scene_polish_revision']=4
draft.update(scene_polish_revision=4,dormitory_layout_revision=4,container_outline=outline.get_path_name())
draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',billiard_tables=2,cue_racks=3,tv_width_m=3.4,updated_maps=len(report['maps']),open_command='open '+CFG['sample_map']);record()
u.log('STAFF_SCENE_POLISH_V4_DELIVERY_SAVED')
