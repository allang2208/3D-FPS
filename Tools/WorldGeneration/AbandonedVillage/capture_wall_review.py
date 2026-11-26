"""Temporary neutral-light inspection of saved walls; never save the review setup."""
import json,math,sys,os
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=root/'SourceAssets/TemperateHillsVillage'
out=source/'WallReview20261114'
detail=os.environ.get('WALL_REVIEW_DETAIL')=='1'
if detail:
    out=out/'Detail';out.mkdir(exist_ok=True)
background=os.environ.get('WALL_REVIEW_COMMANDLET')=='1'
batch_start=int(os.environ.get('WALL_REVIEW_START','0'))
batch_size=int(os.environ.get('WALL_REVIEW_COUNT','24'))
capture_dir=out/'CapturesLit'
plan=json.loads((source/'layout.json').read_text(encoding='utf-8'))
wanted=[i for w in plan['yard_walls'] for i in w['native_instances']]
sys.path.insert(0,str(root/'Tools/WorldGeneration/AbandonedVillage'))
from layout_geometry import house_geometry,rotate
kit=json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
houses=[house_geometry(h,kit[h[2]],plan['house_scale']) for h in plan['houses']]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Active game: preserve current scene')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Unsaved map: preserve changes')
previous=editor.get_editor_world().get_path_name().split('.')[0]
camera=editor.get_level_viewport_camera_info()
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
if previous==level:raise RuntimeError('Village already open: keep current editor setup')
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Cannot load village')
if background:
    # A commandlet does not run the normal renderer frame lifecycle; repeated
    # captures otherwise accumulate VSM page tables. Inspection-only settings.
    for command in ('r.Shadow.Virtual.Enable 0','r.AntiAliasingMethod 1'):
        u.SystemLibrary.execute_console_command(world,command)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
helpers=[]
report=dict(saved_world=level,instances=[],meshes={},views=[])
def xyz(v):return [v.x,v.y,v.z]
def spawn(cls,location=u.Vector(),rotation=u.Rotator()):
    actor=actors.spawn_actor_from_class(cls,location,rotation,transient=True)
    if not actor:raise RuntimeError('Could not spawn inspection helper')
    helpers.append(actor);return actor
try:
    mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for actor in actors.get_all_level_actors():
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=comp.static_mesh
            if not mesh or 'StoneWall' not in mesh.get_name():continue
            path=mesh.get_path_name()
            if path not in report['meshes']:
                body=mesh.get_editor_property('body_setup')
                geometry=body.get_editor_property('agg_geom')
                boxes=[];convex=[]
                for b in geometry.get_editor_property('box_elems'):
                    r=b.get_editor_property('rotation')
                    boxes.append(dict(center=xyz(b.get_editor_property('center')),rot=[r.pitch,r.yaw,r.roll],
                        size=[b.get_editor_property(a) for a in ('x','y','z')]))
                for c in geometry.get_editor_property('convex_elems'):
                    convex.append(c.export_text())
                report['meshes'][path]=dict(collision_type=str(body.get_editor_property('collision_trace_flag')),
                    simple_collision_count=(mesh_editor.get_simple_collision_count(mesh) if mesh_editor else len(boxes)),boxes=boxes,convex=convex)
            for index in range(comp.get_instance_count()):
                t=comp.get_instance_transform(index,True);r=t.rotation.rotator()
                report['instances'].append(dict(actor=actor.get_actor_label(),index=index,mesh=path,
                    pos=xyz(t.translation),rot=[r.pitch,r.yaw,r.roll],scale=xyz(t.scale3d),
                    collision_profile=str(comp.get_collision_profile_name()),collision_enabled=str(comp.get_collision_enabled()),
                    materials=[comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]))
    (out/'current-scene.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

    floor=spawn(u.StaticMeshActor)
    floor.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'))
    floor.static_mesh_component.set_editor_property('receives_decals',False)
    floor.static_mesh_component.set_material(0,u.load_asset('/Engine/BasicShapes/BasicShapeMaterial'))
    floor.set_actor_scale3d(u.Vector(110,85,1))
    if detail:
        # Recreate the saved ground material and runtime cache bindings at the
        # village's flat local datum. This remains a disposable inspection world.
        floor.static_mesh_component.set_visibility(False)
        floor=spawn(u.DynamicMeshActor)
        ground_component=floor.get_dynamic_mesh_component()
        ground_component.set_mobility(u.ComponentMobility.MOVABLE)
        ground_mesh=ground_component.get_dynamic_mesh()
        u.GeometryScript_Primitives.append_rectangle_xy(ground_mesh,u.GeometryScriptPrimitiveOptions(),u.Transform(),11000.,8500.,110,85)
        u.GeometryScript_VertexColors.set_mesh_constant_vertex_color(ground_mesh,u.LinearColor(0,0,0,1),u.GeometryScriptColorFlags(),True)
        uv=u.GeometryScript_UVs
        uv.set_num_uv_sets(ground_mesh,3)
        for channel in (1,2):
            uv.copy_uv_set(ground_mesh,0,channel)
            uv.scale_mesh_u_vs(ground_mesh,channel,u.Vector2D(0,0),u.Vector2D(0,0),u.GeometryScriptMeshSelection())
        ground_component.set_material(0,u.load_asset('/Game/WorldGeneration/TemperateHills/M_TemperateGround'))
        ground_component.set_editor_property('receives_decals',True)
        textures=[]
        for name in ('RVT_VillageSurface','RVT_VillageHeight'):
            texture=u.load_asset('/Game/WorldGeneration/TemperateHills/EcologyUpgrade/'+name)
            if not texture:raise RuntimeError('Missing saved ground cache '+name)
            volume=spawn(u.RuntimeVirtualTextureVolume,u.Vector(-11000,-10000,-5000))
            volume.root_component.set_mobility(u.ComponentMobility.MOVABLE)
            volume.set_actor_scale3d(u.Vector(22000,20000,10000))
            volume.virtual_texture_component.set_editor_property('virtual_texture',texture)
            textures.append(texture)
        ground_component.set_editor_property('runtime_virtual_textures',textures)
        ground_component.set_editor_property('virtual_texture_render_pass_type',u.RuntimeVirtualTextureMainPassType.ALWAYS)
    review_lights=[]
    for pitch,yaw,intensity in ((-35,-55,4.),(-55,125,2.)):
        sun=spawn(u.DirectionalLight,u.Vector(0,0,3000),u.Rotator(pitch=pitch,yaw=yaw))
        light=sun.get_component_by_class(u.DirectionalLightComponent)
        light.set_mobility(u.ComponentMobility.MOVABLE);light.set_intensity(intensity)
        light.set_cast_shadows(intensity>2.)
        review_lights.append(sun)
    sky=spawn(u.SkyLight,u.Vector(0,0,1000))
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    sky.light_component.set_intensity(1.)
    capture=spawn(u.SceneCapture2D)
    capture.root_component.set_mobility(u.ComponentMobility.MOVABLE)
    cc=capture.capture_component2d
    cc.capture_every_frame=False;cc.capture_on_movement=False
    cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    cc.fov_angle=75.
    rt=u.RenderingLibrary.create_render_target2d(world,1280,800,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    cc.texture_target=rt
    if detail:
        # Show-only capture removes camera occluders after their relationship to
        # the walls was recorded in the complete-context captures. No actors edited.
        cc.set_editor_property('primitive_render_mode',u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
        visible=[floor]
        boundary_actors={i['actor'] for i in report['instances'] if abs(i['scale'][2]-.8)<.001}
        for actor in actors.get_all_level_actors():
            if actor in helpers:continue
            meshes=[c.static_mesh for c in actor.get_components_by_class(u.InstancedStaticMeshComponent)]
            if actor.get_actor_label() in boundary_actors or any(m and 'Rock' in m.get_name() for m in meshes):visible.append(actor)
        for actor in visible:cc.show_only_actor_components(actor)
        lamp=spawn(u.PointLight)
        lamp.root_component.set_mobility(u.ComponentMobility.MOVABLE)
        lamp.light_component.set_cast_shadows(False)
        lamp.light_component.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        lamp.light_component.set_intensity(20.)
        lamp.light_component.set_editor_property('attenuation_radius',1000.)
    pp=cc.get_editor_property('post_process_settings')
    pp.set_editor_property('override_auto_exposure_method',True)
    pp.set_editor_property('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True)
    pp.set_editor_property('auto_exposure_apply_physical_camera_exposure',False)
    pp.set_editor_property('override_auto_exposure_bias',True);pp.set_editor_property('auto_exposure_bias',0.)
    cc.set_editor_property('post_process_settings',pp)
    views=[]
    # Cover both faces of every boundary instance, not only representative models.
    root_views=set();profiles=set()
    for index,inst in enumerate(wanted):
        profile=(inst['mesh'],inst['rot'][2])
        if profile not in profiles:profiles.add(profile);root_views.add(index)
    root_views.update((11,24,83,148))
    for index in range(len(wanted)):
        inst=wanted[index];x,y,_=inst['pos'];angle=math.radians(inst['rot'][1])
        # B's surviving above-ground masonry is left of its original long rubble-tail pivot.
        if 'PieceB' in inst['mesh']:
            x-=65*inst['scale'][0]*math.cos(angle);y-=65*inst['scale'][1]*math.sin(angle)
        nx,ny=-math.sin(angle),math.cos(angle)
        for sign in (1,-1):
            for distance in (270,220,160,120):
                ex,ey=x+nx*sign*distance,y+ny*sign*distance
                blocked=False
                for house in houses:
                    dx,dy=rotate(ex/100-house['center'][0],ey/100-house['center'][1],-house['angle'])
                    blocked|=abs(dx)<house['half'][0]+.3 and abs(dy)<house['half'][1]+.3
                if not blocked:break
            eye=u.Vector(ex,ey,155)
            target=u.Vector(x,y,60)
            views.append((f'wall_{index:03d}_{"a" if sign==1 else "b"}',eye,target))
            if index in root_views:
                eye=u.Vector(x+nx*sign*min(distance,180),y+ny*sign*min(distance,180),65)
                views.append((f'root_{index:03d}_{"a" if sign==1 else "b"}',eye,u.Vector(x+nx*sign*12,y+ny*sign*12,8)))
except Exception:
    for actor in reversed(helpers):actors.destroy_actor(actor)
    if not background:
        u.EditorLoadingAndSavingUtils.load_map(previous)
        if camera:editor.set_level_viewport_camera_info(*camera)
    raise

state=dict(frame=0,view=-1,handle=None)
def finish(error=None):
    if state['handle']:u.unregister_slate_post_tick_callback(state['handle'])
    try:
        for actor in reversed(helpers):actors.destroy_actor(actor)
        if not background:
            if not u.EditorLoadingAndSavingUtils.load_map(previous):raise RuntimeError('Restore previous map failed')
            if camera:editor.set_level_viewport_camera_info(*camera)
    except Exception as exc:error=str(exc)
    report['capture_setup']=('Saved ground material with RVT writer and receivers; walls/rocks show-only to remove camera occluders; camera point fill. ' if detail else 'Neutral temporary ground. ')+'Local Z=0; actual saved materials; camera-facing inspection lights and manual exposure; legacy shadows only for this commandlet; not a live seeded-world screenshot'
    report['error']=error;report['restored']=previous
    (out/f'captures-lit-{batch_start:03d}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (out/f'capture-complete-{batch_start:03d}.json').write_text(json.dumps(dict(success=not error,views=len(report['views']),total_views=len(views),error=error)),encoding='utf-8')
def tick(_delta):
    try:
        state['frame']+=1
        # Let editor shader/texture/Nanite work settle before evaluating the saved surfaces.
        if state['view']==-1:
            if state['frame']<120:return
            state['view']=0;state['frame']=0
        name,eye,target=views[state['view']]
        if state['frame']==0:
            capture.set_actor_location(eye,False,True)
            capture.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,target),False)
        cc.capture_scene()
        if state['frame']<12:return
        u.RenderingLibrary.export_render_target(world,rt,str(capture_dir),name+'.png')
        report['views'].append(dict(name=name,eye=xyz(eye),target=xyz(target)))
        state['view']+=1;state['frame']=-1
        if state['view']>=len(views):finish()
    except Exception as exc:finish(str(exc))
capture_dir.mkdir(exist_ok=True)
if detail:
    selected=set(json.loads((out/'selected-views.json').read_text(encoding='utf-8')))
    views=[v for v in views if v[0] in selected or v[0].startswith('root_')]
if background:
    try:
        # Existing native baker finishes shader/asset compilation, streams textures,
        # sends end-of-frame updates and advances renderer frames without gameplay.
        # Tiny scratch cubemaps are never saved and only warm the captures.
        for view_index,(name,eye,target) in enumerate(views[batch_start:batch_start+batch_size],batch_start):
            yaw=u.MathLibrary.find_look_at_rotation(eye,target).yaw
            review_lights[0].set_actor_rotation(u.Rotator(pitch=-35,yaw=yaw-25),False)
            review_lights[1].set_actor_rotation(u.Rotator(pitch=-30,yaw=yaw+25),False)
            capture.set_actor_location(eye,False,True)
            capture.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,target),False)
            if detail:lamp.set_actor_location(eye+u.Vector(0,0,35),False,True)
            if detail:cc.capture_scene()
            warm=u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,[floor],
                '/Game/WorldGeneration/TemperateHills/AbandonedVillage/ReviewScratch/WallReviewWarm',eye,64)
            if not warm:raise RuntimeError('Offline renderer preparation failed')
            for _ in range(4):cc.capture_scene()
            u.RenderingLibrary.export_render_target(world,rt,str(capture_dir),name+'.png')
            report['views'].append(dict(name=name,eye=xyz(eye),target=xyz(target)))
            print('WALL_VIEW_EXPORTED',name)
        finish()
    except Exception as exc:
        finish(str(exc));raise
else:
    state['handle']=u.register_slate_post_tick_callback(tick)
    print('WALL_REVIEW_SCHEDULED',len(views),'The outer batch retains the UE mutex until capture-complete.json')
