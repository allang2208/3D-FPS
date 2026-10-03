"""Build the editable freight-to-station line from saved production descriptors."""
import json,math
from pathlib import Path
import unreal as u
def main():
    ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent.parents[1]
    OUT=PROJECT/'SourceAssets/DungeonStationLine20261002'
    for folder in ('Config','Receipts'): (OUT/folder).mkdir(parents=True,exist_ok=True)
    TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.EditorAssetLibrary.does_asset_exist(TARGET):
        receipt=OUT/'Receipts/install.json'
        if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='map_saved':
            print('STATION_LINE_ALREADY_SAVED',flush=True);return
        raise RuntimeError('Preserve existing station-line map')
    catalog=json.loads((PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').read_text('utf8'))
    byid={m['id']:m for m in catalog['modules']}
    AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:raise RuntimeError('New station-line world unavailable')
    world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
    placements=[dict(id='FreightTransfer_WarehouseLink',position=[0,-900,0],yaw=90),
        dict(id='Transit',position=[1980,0,0],yaw=90,scale=[1,.2,1],name='FreightWarehouseSeam'),
        dict(id='AbandonedCargoWarehouse',position=[3760,-900,0],yaw=0),
        dict(id='Transit',position=[5460,-1400,0],yaw=90,name='WarehouseStationLink'),
        dict(id='AbandonedTransitStation',position=[7760,-1400,0],yaw=0)]
    counts=dict(mesh_actors=0,lights=0,raised_progression_gates=0)

    def transformed(p,pose):
        s=pose.get('scale',[1,1,1]);a=math.radians(pose['yaw']);x,y,z=[p[i]*s[i] for i in range(3)]
        return u.Vector(x*math.cos(a)-y*math.sin(a)+pose['position'][0],x*math.sin(a)+y*math.cos(a)+pose['position'][1],z+pose['position'][2])

    def named(actor,label,room):
        actor.set_actor_label('StationLine_'+label);actor.set_folder_path('StationLine/'+room)
        actor.set_editor_property('tags',[u.Name('StationLine.Subject'),u.Name(room)]);return actor

    def static(part,pose,label):
        mesh=u.load_asset(part['mesh'])
        if not mesh:raise RuntimeError('Missing approved scene mesh '+part['mesh'])
        rot=u.Rotator(pitch=part.get('pitch',0),yaw=pose['yaw']+part.get('yaw',0),roll=part.get('roll',0))
        actor=named(AA.spawn_actor_from_class(u.StaticMeshActor,transformed(part.get('position',[0,0,0]),pose),rot),label,pose.get('name',pose['id']))
        c=actor.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll' if part.get('collision',True) else 'NoCollision')
        c.set_mobility(u.ComponentMobility.STATIC)
        for i,path in enumerate(part.get('materials',[])):
            if path:c.set_material(i,u.load_asset(path))
        s=pose.get('scale',[1,1,1]);ps=part.get('scale',[1,1,1]);actor.set_actor_scale3d(u.Vector(*(s[i]*ps[i] for i in range(3))))
        if part.get('guardrail_drop'):actor.set_editor_property('tags',[*actor.tags,u.Name('Traversal.GuardrailDrop')])
        counts['mesh_actors']+=1;return actor

    for pose in placements:
        m=byid[pose['id']];prefix=pose.get('name',pose['id'])
        for i,p in enumerate(m['parts']):static(p,pose,prefix+'_'+str(i))
        if m.get('progression_gate'):
            p=dict(m['progression_gate'],collision=True)
            p['position']=[p['position'][i]+p['travel'][i] for i in range(3)]
            static(p,pose,prefix+'_RaisedGate');counts['raised_progression_gates']+=1
        for i,l in enumerate(m['lights']):
            actor=named(AA.spawn_actor_from_class(u.PointLight,transformed(l['position'],pose)),prefix+'_Light_'+str(i),prefix)
            c=actor.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
            c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(l['intensity'])
            c.set_editor_property('attenuation_radius',l['radius']);c.set_editor_property('cast_shadows',l.get('cast_shadows',True))
            c.set_editor_property('max_draw_distance',l.get('max_draw_distance_cm',3400))
            c.set_editor_property('max_distance_fade_range',l.get('fade_range_cm',500))
            c.set_editor_property('indirect_lighting_intensity',l.get('indirect_lighting_intensity',.7))
            c.set_light_color(u.LinearColor(*l['color'],1));counts['lights']+=1
        # Reuse the existing skeletal chest props where the line's authored rooms contain them.
        for i,p in enumerate(m.get('props',[])):
            actor=named(AA.spawn_actor_from_class(u.SkeletalMeshActor,transformed(p['position'],pose),
                u.Rotator(pitch=0,yaw=pose['yaw']+p.get('yaw',0),roll=0)),prefix+'_Prop_'+str(i),prefix)
            c=actor.skeletal_mesh_component;c.set_skeletal_mesh_asset(u.load_asset(p['skeletal_mesh']))
            c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);c.play_animation(u.load_asset(p['closed_animation']),False)
            for index,path in p.get('material_overrides',{}).items():c.set_material(int(index),u.load_asset(path))
            actor.set_actor_scale3d(u.Vector(*p.get('scale',[1,1,1])))
    # Close only the two exposed endpoints; all internal doorways remain continuous.
    for label,p,s in [('StartCap',[0,0,140],[.12,3,2.8]),('EndCap',[8185,-3350,140],[3,.12,2.8])]:
        static(dict(mesh='/Engine/BasicShapes/Cube',position=p,scale=s,collision=True,
            materials=['/Game/Dungeons/StaffLiving20261002/Materials/M_Staff_OlivePaint']),
            dict(id='PreviewCaps',position=[0,0,0],yaw=0),label)
    start=named(AA.spawn_actor_from_class(u.PlayerStart,u.Vector(100,0,105),u.Rotator(pitch=0,yaw=0,roll=0)),'PlayerStart','Environment')
    pp=named(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector()),'Exposure','Environment')
    pp.set_editor_property('unbound',True);settings=pp.get_editor_property('settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',.7),
        ('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',.7),
        ('override_auto_exposure_bias',True),('auto_exposure_bias',-.05),('override_bloom_intensity',True),('bloom_intensity',.25)]:
        settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Station-line map save failed')
    data=dict(map=TARGET,sequence=['FreightTransfer_WarehouseLink','AbandonedCargoWarehouse','AbandonedTransitStation'],
        placements=placements,source_catalog='SourceAssets/DungeonRoutes20260922/Config/catalog.json',
        mode='editable scenery refinement, opened freight gate',player_start=[100,0,105],return_map='/Game/GameMaps/DayNight_Lighting')
    (OUT/'Config/line.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    report=dict(stage='map_saved',map=TARGET,counts=counts,tests_run=False,rendered=False,game_run=False,editor_opened=False,
        generation_executed='authored fixed scene saved only; no random layout run')
    (OUT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('STATION_LINE_SUBJECT_SAVED '+TARGET,flush=True)

main()
