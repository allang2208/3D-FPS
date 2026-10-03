"""Install the corrected bathroom footprint, kettle and audited typography."""
import json,hashlib,re,shutil,sys
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'WallInsetV6'
if json.loads((ROOT/'Config/room.json').read_text('utf8')).get('coffee_polish_revision',0)>=7:
    current=ROOT/'Scripts/import_coffee_polish_v7.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
CFG=json.loads((OUT/'Authored/room-inset.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/WallInsetV6'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json';report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},materials=[],backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,requested_font_audit=True)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
sys.path.insert(0,str(ROOT/'Scripts'))
from build_wall_inset_materials_v6 import build_materials
report['materials']=build_materials(ROOT,BASE);record()
v4=ROOT/'Scripts/import_scene_polish_v4.py';code=v4.read_text('utf8')
mesh_code=code[code.index('u.SystemLibrary.execute_console_command'):code.index('AA=u.get_editor_subsystem')]
mesh_code=mesh_code.replace("        n=mesh.get_editor_property('nanite_settings').copy();", "        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item['simple_collision_hulls'] else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)\n        n=mesh.get_editor_property('nanite_settings').copy();")
exec(compile(mesh_code,str(v4),'exec'))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
def owned(a):return 'StaffLiving.Subject' in [str(t) for t in a.tags]
def loc(p,off):return u.Vector((p[0]+off[0])*100,-(p[1]+off[1])*100,(p[2]+off[2])*100)
def rot(p):return u.Rotator(pitch=0,yaw=-p['yaw_blender_deg'],roll=0)
def destroy(actors,label):
    if label in actors:AA.destroy_actor(actors.pop(label))
def shared(proto):
    if proto in MAN['prototypes']:
        name=MAN['prototypes'][proto];return meshes[name],items[name]['collision']
    if proto=='Toilet':path=CFG['ue_base']+'/RoomDetailsV5/Meshes/SM_Staff_Toilet_V5'
    elif proto in ('WashBasin','Mirror'):path=CFG['ue_base']+'/ScenePolishV4/Meshes/SM_Staff_'+proto+'_V4'
    else:path=CFG['ue_base']+'/Meshes/SM_Staff_'+proto
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing approved fixture '+path)
    return mesh,proto in ('Toilet','WashBasin')
def static(p,off,rid):
    mesh,collision=shared(p['prototype']);a=AA.spawn_actor_from_class(u.StaticMeshActor,loc(p['position'],off),rot(p))
    a.set_actor_label('StaffSubject_'+rid+'_'+p['id']);a.set_folder_path('StaffLiving/'+rid)
    a.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(rid)])
    c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');return a
def font_scale(a,c,quads):
    # All installed text meshes are unparented static actors. Audit the actual
    # serialized scale, which can otherwise squash a correctly authored atlas.
    s=a.get_actor_scale3d();nonuniform=max(abs(s.x),abs(s.y),abs(s.z))-min(abs(s.x),abs(s.y),abs(s.z))>.001
    return dict(label=a.get_actor_label(),mesh=c.get_editor_property('static_mesh').get_path_name(),
        actor_scale=[s.x,s.y,s.z],nonuniform_scale=nonuniform,font_quads=quads)
targets=[(CFG['maps'][r['id']],[r],[[0,0,0]]) for r in CFG['rooms']]
targets.append((CFG['sample_map'],CFG['rooms'],CFG['preview_placements_m']))
for target,rooms,offsets in targets:
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load owned sample '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if owned(a)};updated=[];font_audit=[]
    for room,off in zip(rooms,offsets):
        rid=room['id'];prefix='StaffSubject_'+rid+'_'
        for item in MAN['architectures']:
            if item['room_id']!=rid:continue
            a=actors.get(item['actor_label'])
            if not a:raise RuntimeError('Preserve missing original room layer '+item['actor_label'])
            c=a.get_component_by_class(u.StaticMeshComponent)
            if not c:raise RuntimeError('Missing room mesh component')
            c.set_static_mesh(meshes[item['name']]);c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
            if item['font_quads']:font_audit.append(font_scale(a,c,item['font_quads']))
            updated.append(item['actor_label'])
        keys={'Noticeboard'}
        if rid=='StaffRecreation':
            keys.update(('ElectricKettle','KettlePower','BathroomInterior'))
            destroy(actors,prefix+'BathroomShell')
        for k in keys:destroy(actors,prefix+k+'_Instances')
        for p in room['furniture']:
            if p['prototype'] in keys:
                destroy(actors,prefix+p['id']);a=static(p,off,rid);updated.append(a.get_actor_label())
                item=items[MAN['prototypes'][p['prototype']]]
                if item['font_quads']:font_audit.append(font_scale(a,a.static_mesh_component,item['font_quads']))
            elif rid=='StaffRecreation' and p['id'] in ('Toilet','BathroomSink','BathroomMirror','BathroomLamp'):
                a=actors.get(prefix+p['id'])
                if a:a.set_actor_location_and_rotation(loc(p['position'],off),rot(p),False,True)
                else:a=static(p,off,rid)
                updated.append(a.get_actor_label())
        if rid=='StaffRecreation':
            a=actors.get(prefix+'Light_Bathroom')
            if not a:a=AA.spawn_actor_from_class(u.PointLight,loc([12.20,10.10,3.25],off))
            a.set_actor_label(prefix+'Light_Bathroom');a.set_actor_location(loc([12.20,10.10,3.25],off),False,True)
            a.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(rid),u.Name('Dungeon.Light.Fill')]);a.set_folder_path('StaffLiving/'+rid)
            c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
            c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(440.)
            c.set_editor_property('attenuation_radius',370.);c.set_editor_property('cast_shadows',False)
            c.set_editor_property('max_draw_distance',1400.);c.set_editor_property('max_distance_fade_range',300.)
            c.set_editor_property('indirect_lighting_intensity',.10);c.set_light_color(u.LinearColor(.79,.87,.82,1))
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',changed=updated,typography_scale_audit=font_audit)
    record();u.log('STAFF_WALL_INSET_V6_MAP_SAVED '+target)
for filename in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/filename,backup/filename)
dp=ROOT/'Config/modules-draft.json';draft=json.loads(dp.read_text('utf8'))
for module in draft['modules']:
    rid=module['id'];room=next(r for r in CFG['rooms'] if r['id']==rid)
    arch={a['kind']:a for a in MAN['architectures'] if a['room_id']==rid}
    for part in module['parts']:
        basename=part.get('mesh','').rsplit('/',1)[-1]
        for kind,item in arch.items():
            if basename in ('SM_Staff_'+room['prefix']+'_'+kind,'SM_Staff_'+room['prefix']+'_'+kind+'_V4'):
                part.update(mesh=item['asset'],materials=[],collision=item['collision'])
    module['parts']=[p for p in module['parts'] if p.get('id')!='BathroomShell' and not p.get('mesh','').endswith('/SM_Staff_BathroomShell_V5')]
    for p in room['furniture']:
        if p['prototype'] not in MAN['prototypes'] and p['id'] not in ('Toilet','BathroomSink','BathroomMirror','BathroomLamp'):continue
        part=next((q for q in module['parts'] if q.get('id')==p['id']),None)
        if part is None:part=dict(id=p['id']);module['parts'].append(part)
        mesh,collision=shared(p['prototype']);part.update(mesh=mesh.get_path_name().split('.')[0],materials=[],collision=collision,
            position=[p['position'][0]*100,-p['position'][1]*100,p['position'][2]*100],yaw=-p['yaw_blender_deg'])
    if rid=='StaffRecreation':
        cell=dict(min=[900,-1200,0],max=[1500,-800,550])
        if cell not in module['cells']:module['cells'].append(cell)
        module['author_walk_rects_m']=room['walk_rects_m'];module['toilet_location']=CFG['toilet_location']
        module['lights']=[l for l in module['lights'] if l['id']!='Bathroom']
        l=next(l for l in room['lights'] if l['id']=='Bathroom')
        module['lights'].append(dict(l,position=[1220,-1010,325]))
draft.update(wall_inset_revision=6,typography_geometry_audit='WallInsetV6/Authored/typography-geometry-audit.json')
dp.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
fontaudit=json.loads((OUT/'Authored/typography-audit.json').read_text('utf8'))
geomaudit=json.loads((OUT/'Authored/typography-geometry-audit.json').read_text('utf8'))
report.update(stage='samples_saved',typography=dict(atlas_panels=len(fontaudit['panels']),geometry_quads=len(geomaudit['font_quads']),
    anisotropic_geometry_quads=geomaudit['anisotropic_quads'],overflow_runs=fontaudit['overflow_runs']),
    current_authored_source=CFG['current_authored_source'],native_changes=False,native_build_required=False,
    random_pool_registered=False,rewards_deferred=True);record()
u.log('STAFF_WALL_INSET_V6_DELIVERY_SAVED')
