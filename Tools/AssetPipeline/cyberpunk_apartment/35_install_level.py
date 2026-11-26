"""Save the playable apartment in-place. No PIE, game launch or default-map change."""
import json
import sys
from pathlib import Path
_current = Path(__file__).resolve().parents[3] / 'SourceAssets/CyberpunkApartmentRebuild20261022'
if (_current / 'installed.json').exists():
    import runpy
    runpy.run_path(str(_current / 'install_level.py'), run_name='__main__')
    raise SystemExit(0)
sys.path.insert(0,str(Path(__file__).parent))
from playable_config import ROOT, MAP, SCALE, COMPLEX, SPAWN_XY
import unreal as u

report={'stage':'loading','map':MAP,'scale':SCALE,'actors':[],'doors':[],
        'collision_proxies':[],'lights':[],'errors':[],'runtime_tested':False}
out=ROOT/'level_saved.json'
def persist():out.write_text(json.dumps(report,indent=2),encoding='utf-8')
def V(x,y,z):return u.Vector(x,y,z)
def R(pitch=0,yaw=0,roll=0):return u.Rotator(pitch=pitch,yaw=yaw,roll=roll)
def set_tags(obj,prop,tags):obj.set_editor_property(prop,[u.Name(t) for t in tags])

try:
    assets=json.loads((ROOT/'import_saved.json').read_text())
    if assets['stage']!='assets_saved':raise RuntimeError('Asset import is incomplete')
    authored=json.loads((ROOT/'authoring.json').read_text())
    meshes={n:u.load_asset(r['path']) for n,r in assets['meshes'].items()}
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Cannot load apartment')
    AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
    old_doors={'Door_Entry','Door_Living','Door_Master','Door_Kitchen','Door_Bath1',
               'Door_Bath2','Door_Bed2','Door_Bed3','Door_Balcony'}
    for a in actors:
        label=a.get_actor_label()
        if (label.startswith(('Floor_','FloorTile_','Threshold_','Rail_','CP_'))
            or label in old_doors or label in {'CollisionFloor','SlabFloor','BlockFloor_Apartment','BalconyLedge'}
            or isinstance(a,u.PlayerStart)):
            AA.destroy_actor(a)
    existing={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}

    for name,mesh in meshes.items():
        if name.startswith('DoorAsset_'):continue
        a=existing.get(name)
        if a is None:
            a=AA.spawn_actor_from_class(u.StaticMeshActor,V(0,0,0),R())
            a.set_actor_label(name)
        if not isinstance(a,u.StaticMeshActor):raise RuntimeError('Unexpected owner '+name)
        a.modify()
        comp=a.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_mobility(u.ComponentMobility.STATIC)
        a.set_actor_location(V(0,0,0),False,False)
        a.set_actor_rotation(R(),False)
        a.set_actor_scale3d(V(SCALE,SCALE,SCALE))
        # Glass rail and balcony frame collision are represented by continuous
        # exact boxes below; privacy walls are deliberately NOT traversal rails.
        blocking=name in COMPLEX and name!='S_balcony'
        comp.set_collision_profile_name(u.Name('BlockAll' if blocking else 'NoCollision'))
        comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if blocking else u.CollisionEnabled.NO_COLLISION)
        set_tags(a,'tags',['CyberpunkApartment.Playable125'])
        set_tags(comp,'component_tags',[])
        if name.startswith('CITY_') and name!='CITY_our_tower':
            comp.set_editor_property('cast_shadow',False)
        if 'micro' in name or 'clutter' in name:
            comp.set_editor_property('cast_shadow',False)
        if name=='CITY_fog':
            # glTF cannot encode the saved Blender volume shader: its exported
            # opaque cube must not become a room-sized solid haze box in UE.
            comp.set_visibility(False)
            a.set_actor_hidden_in_game(True)
        report['actors'].append({'label':name,'mesh':mesh.get_path_name(),'scale':SCALE,'collision':blocking})

    cube=u.load_asset('/Engine/BasicShapes/Cube.Cube')
    def proxy(label,centre,size,rail=False):
        a=AA.spawn_actor_from_class(u.StaticMeshActor,V(*(v*SCALE for v in centre)),R())
        a.set_actor_label('CP_'+label)
        c=a.static_mesh_component
        c.set_static_mesh(cube)
        c.set_mobility(u.ComponentMobility.STATIC)
        a.set_actor_scale3d(V(*(v*SCALE/100 for v in size)))
        c.set_collision_profile_name(u.Name('BlockAll'))
        c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        c.set_visibility(False)
        c.set_hidden_in_game(True)
        c.set_editor_property('cast_shadow',False)
        if rail:
            set_tags(a,'tags',['Traversal.GuardrailDrop'])
            set_tags(c,'component_tags',['Traversal.GuardrailDrop'])
        report['collision_proxies'].append(dict(label=a.get_actor_label(),centre=centre,size=size,rail=rail))
        return a
    proxy('Floor_Apartment',(800,-550,-19.8),(1600,1100,40))
    proxy('Floor_Balcony',(764,141,-23),(732,278,40))
    proxy('Floor_EntryLanding',(992,-1230,-19.8),(300,280,40))
    proxy('Threshold_Balcony',(755,0,-1.4),(110,34,3.2))
    proxy('Guardrail_Balcony',(764,278,54.75),(730,9,115.5),rail=True)
    for x in (398,1130):
        proxy('BalconyPrivacy_'+str(x),(x,142,107),(16,286,220))

    door_cls=u.load_class(None,'/Script/FPSGAME.ColdSteelSlidingDoor')
    if not door_cls:raise RuntimeError('Native sliding door class unavailable')
    for d in authored['doors']:
        a=AA.spawn_actor_from_class(door_cls,V(d['x']*SCALE,d['y']*SCALE,.25),R(yaw=d['yaw']))
        a.set_actor_label('Door_'+d['name'])
        a.set_editor_property('slide_distance_cm',d['slide_cm'])
        a.set_editor_property('slide_speed_cm',max(52.,d['slide_cm']/1.0))
        a.set_editor_property('auto_close_seconds',6.)
        parts={c.get_name():c for c in a.get_components_by_class(u.StaticMeshComponent)}
        frame=meshes['DoorAsset_'+d['name']+'_Frame']
        leaf=meshes['DoorAsset_'+d['name']+'_Leaf']
        parts['DoorFrame'].set_static_mesh(frame)
        b=frame.get_bounding_box()
        mid=(b.min+b.max)*.5
        parts['DoorFrame'].set_relative_location(V(-mid.x,-mid.y,-b.min.z),False,False)
        box=leaf.get_bounding_box()
        mid=(box.min+box.max)*.5
        half=(box.max-box.min)*.5
        for name,side in (('LeafLeft',-1),('LeafRight',1)):
            c=parts[name]
            c.set_static_mesh(leaf)
            c.set_relative_scale3d(V(1,.5,1))
            c.set_relative_location(V(-mid.x,side*half.y*.5-mid.y*.5,-box.min.z),False,False)
            c.set_collision_profile_name(u.Name('BlockAll'))
        set_tags(a,'tags',['CyberpunkApartment.Playable125'])
        report['doors'].append(dict(label=a.get_actor_label(),location=[d['x']*SCALE,d['y']*SCALE,.25],
            yaw=d['yaw'],scale=[1,1,1],width_cm=d['width_cm'],height_cm=d['height_cm'],slide_cm=d['slide_cm']))

    ps=AA.spawn_actor_from_class(u.PlayerStart,V(SPAWN_XY[0]*SCALE,-SPAWN_XY[1]*SCALE,100.25),R(yaw=90))
    ps.set_actor_label('PlayerStart_Apartment')
    ps.get_component_by_class(u.CapsuleComponent).set_capsule_size(42,96,False)
    report['spawn']={'position':[SPAWN_XY[0]*SCALE,-SPAWN_XY[1]*SCALE,100.25],
                     'yaw':90,'capsule_radius':42,'capsule_half_height':96,'floor_top':.25}
    settings=world.get_world_settings()
    mode=u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode')
    settings.set_editor_property('default_game_mode',mode)
    settings.set_editor_property('kill_z',-21000.)

    # Source-sized positions/radii; final world transform is applied explicitly
    # after mobility, so UE default root rotation cannot point ceiling lights up.
    lights=[
        ('L_living_key',(740,-315,280),6000,(1,.886,.745),600,90,12),
        ('L_living_fill',(1040,-430,278),1800,(.745,.824,1),420,40,12),
        ('L_corr',(560,-612,285),3200,(.784,.902,1),620,260,8),
        ('L_kitchen',(670,-815,270),3400,(1,.878,.729),450,110,12),
        ('L_master',(110,-260,280),3000,(1,.886,.769),450,45,10),
        ('L_bath',(376,-954,280),2000,(.922,.949,1),320,40,10),
        ('L_foyer',(992,-900,280),2400,(1,.910,.784),450,60,10),
        ('L_bed2',(1330,-290,280),2600,(.72,.82,1),500,75,10),
        ('L_bed3',(1340,-820,280),2600,(.72,.92,1),500,75,10),
        ('L_bath2',(150,-960,280),1800,(.92,.95,1),330,40,10),
        ('L_utility',(350,-738,280),900,(.84,.91,1),240,45,10),
        ('L_balcony',(760,200,282),1700,(.65,.82,1),460,150,8),
        ('L_entry_landing',(992,-1270,255),1400,(.72,.86,1),350,80,8),
    ]
    current={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.RectLight)}
    for label,pos,lumens,color,radius,width,height in lights:
        a=current.get(label) or AA.spawn_actor_from_class(u.RectLight,V(0,0,0),R())
        a.set_actor_label(label)
        c=a.get_component_by_class(u.RectLightComponent)
        c.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location(V(*(v*SCALE for v in pos)),False,False)
        a.set_actor_rotation(R(pitch=-90),False)
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        c.set_intensity(lumens*SCALE*SCALE)
        c.set_light_color(u.LinearColor(*color,1))
        c.set_editor_property('attenuation_radius',radius*SCALE)
        c.set_editor_property('source_width',width*SCALE)
        c.set_editor_property('source_height',height*SCALE)
        c.set_editor_property('cast_shadows',True)
        c.set_editor_property('max_draw_distance',4000.)
        c.set_editor_property('max_distance_fade_range',900.)
        report['lights'].append({'label':label,'position':[v*SCALE for v in pos],
                               'pitch':-90,'lumens':lumens*SCALE*SCALE,'radius':radius*SCALE})
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight):
        if a.get_actor_label()=='L_city_sky':
            c=a.get_component_by_class(u.DirectionalLightComponent)
            c.set_mobility(u.ComponentMobility.MOVABLE)
            a.set_actor_rotation(R(pitch=-28,yaw=200),False)

    # Preserve the subsequently installed bay exterior during a base rebuild.
    # Activate only from a real completed installation receipt, never a plan.
    bay_root=ROOT.parent/'CyberpunkBayBackdrop20261021'
    bay_receipt=bay_root/'installed.json'
    if bay_receipt.exists() and json.loads(bay_receipt.read_text())['stage']=='map_saved':
        import runpy
        bay=runpy.run_path(str(bay_root/'install_background.py'))
        report['bay_background']=bay['apply_saved_background'](world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
    report['stage']='map_saved'
    report['game_mode']=mode.get_path_name()
except Exception as exc:
    report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['stage']='failed'
    persist()
    raise
persist()
u.log('CYBERPUNK_PLAYABLE_MAP_SAVED')
