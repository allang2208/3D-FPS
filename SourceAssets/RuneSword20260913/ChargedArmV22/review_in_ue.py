"""User-requested installed-arm inspection in a separate offscreen UE editor."""
import unreal as u,math,time,json,traceback
from pathlib import Path
P=Path(__file__).parent;OUT=P/'UEReview';OUT.mkdir(exist_ok=True)
D='/Game/Weapons/AzureRunesword20260913';state={'shot':0,'frame':0,'started':time.monotonic()};callback=None;receipt=[]
def props(obj,**kw):
    for k,v in kw.items():obj.set_editor_property(k,v)
def spawn(cls,pos=(0,0,0),rot=None):
    return u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator())
def finish(error=None):
    global callback
    if callback:u.unregister_slate_post_tick_callback(callback);callback=None
    (P/('ue_review_error.txt' if error else 'ue_review_receipt.json')).write_text(error or json.dumps(receipt,indent=2))
    u.SystemLibrary.quit_editor()
try:
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    for cmd in ['r.TextureStreaming 0','r.AntiAliasingMethod 2','r.ScreenPercentage 100','t.IdleWhenNotForeground 0']:
        u.SystemLibrary.execute_console_command(world,cmd)
    actor=spawn(u.SkeletalMeshActor,rot=u.Rotator(pitch=0.,yaw=90.,roll=0.));mesh=actor.skeletal_mesh_component
    mesh.set_mobility(u.ComponentMobility.MOVABLE);mesh.set_skeletal_mesh_asset(u.load_asset(D+'/SK_AzureRunesword_Manny'))
    mesh.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);mesh.set_update_animation_in_editor(True)
    mesh.set_enable_animation(True)
    props(mesh,visibility_based_anim_tick_option=u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES,pause_anims=False,no_skeleton_update=False)
    mesh.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    preview=actor.call_method('AddComponentByClass',(u.PoseableMeshComponent.static_class(),False,u.Transform(),False))
    preview.set_skinned_asset_and_update(mesh.skeletal_mesh_asset)
    preview.set_component_tick_enabled(True)
    props(preview,visibility_based_anim_tick_option=u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    # Isolate skin shape from stale offscreen ray-tracing shadow proxies.
    mesh.set_cast_shadow(False);preview.set_cast_shadow(False)
    mesh.set_visibility(False,False)
    for pos,power,width,color in [((0,-100,130),350,150,(1,.95,.88)),((50,110,50),200,120,(.82,.9,1)),((170,0,80),220,100,(1,1,1))]:
        light=spawn(u.RectLight,pos);light.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(40,0,-15)),False)
        lc=light.get_component_by_class(u.RectLightComponent);lc.set_mobility(u.ComponentMobility.MOVABLE);lc.set_intensity(power)
        lc.set_light_color(u.LinearColor(*color,1));props(lc,source_width=width,source_height=width,attenuation_radius=500.)
    sky=spawn(u.SkyLight);sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);sky.light_component.set_intensity(.6)
    cube=u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')
    if cube:props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=cube)
    capture=spawn(u.SceneCapture2D);cc=capture.get_component_by_class(u.SceneCaptureComponent2D)
    rt=u.RenderingLibrary.create_render_target2d(world,1280,720,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.035,.045,.06,1))
    fov=math.degrees(2*math.atan(math.tan(math.radians(75)*.5)*16/9))
    props(cc,texture_target=rt,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,capture_every_frame=False,capture_on_movement=False,fov_angle=fov,always_persist_rendering_state=True)
    pp=cc.get_editor_property('post_process_settings')
    props(pp,override_auto_exposure_method=True,auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,
          override_auto_exposure_bias=True,auto_exposure_bias=-2.5,override_auto_exposure_apply_physical_camera_exposure=True,
          auto_exposure_apply_physical_camera_exposure=False,override_motion_blur_amount=True,motion_blur_amount=0.,
          override_vignette_intensity=True,vignette_intensity=0.,override_bloom_intensity=True,bloom_intensity=0.)
    cc.set_editor_property('post_process_settings',pp)
    readback=[]
    for clip,duration in [('HeavyCharge',2.),('HeavyRelease',1.),('Slash1',1.775)]:
        seq=u.load_asset(D+'/A_RuneSword_'+clip)
        max_position=0.;max_angle=0.;max_scale=0.;samples=0
        for sample in range(round(duration*120)+1):
            at=min(duration,sample/120)
            poses=[]
            for kind in (u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED):
                options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh.skeletal_mesh_asset
                options.evaluation_type=kind
                poses.append(u.AnimPoseExtensions.get_anim_pose_at_time(seq,at,options))
            for bone in ['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_r','WPN_root']:
                a,b=[u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD) for pose in poses]
                av,bv=a.translation,b.translation
                max_position=max(max_position,math.sqrt((av.x-bv.x)**2+(av.y-bv.y)**2+(av.z-bv.z)**2))
                aq,bq=a.rotation,b.rotation
                dot=abs(aq.x*bq.x+aq.y*bq.y+aq.z*bq.z+aq.w*bq.w)
                max_angle=max(max_angle,math.degrees(2*math.acos(min(1.,dot))))
                av,bv=a.scale3d,b.scale3d
                max_scale=max(max_scale,abs(av.x-bv.x),abs(av.y-bv.y),abs(av.z-bv.z))
            samples+=1
        readback.append({'clip':seq.get_path_name(),'duration':seq.get_play_length(),'sample_rate':120,
                         'samples':samples,'max_raw_compressed_position_cm':max_position,
                         'max_raw_compressed_rotation_deg':max_angle,'max_raw_compressed_scale_delta':max_scale})
    (P/'ue_animation_readback.json').write_text(json.dumps(readback,indent=2))
    shots=[('charge_raised','HeavyCharge',.65,False),('charge_raised_joint','HeavyCharge',.65,True),
           ('charge_full','HeavyCharge',2.,False),('charge_full_joint','HeavyCharge',2.,True),
           ('heavy_strike','HeavyRelease',.06,False),('heavy_recovery','HeavyRelease',.4,False),
           ('fallback_raised','Slash1',.30,False)]
    def tick(dt):
        global rt
        try:
            if time.monotonic()-state['started']<12:return
            if time.monotonic()-state['started']>210:finish('Offscreen arm review exceeded 210 seconds');return
            shot=shots[state['shot']];state['frame']+=1;f=state['frame']
            if f==1:
                seq=u.load_asset(D+'/A_RuneSword_'+shot[1])
                # Unlike SetPosition alone, this engine entry also evaluates
                # the pose and refreshes bone transforms in an editor world.
                mesh.override_animation_data(seq,False,False,shot[2],0.)
                options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh.skeletal_mesh_asset
                options.evaluation_type=u.AnimDataEvalType.COMPRESSED
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,shot[2],options)
                for bone in u.AnimPoseExtensions.get_bone_names(pose):
                    preview.set_bone_transform_by_name(bone,u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD),u.BoneSpaces.COMPONENT_SPACE)
                # CPU skin extraction synchronously refreshes bone transforms,
                # which a PoseableMesh otherwise defers to a game-world tick.
                copy_options=u.GeometryScriptCopyMeshFromComponentOptions()
                lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.RENDER_DATA;lod.lod_index=0
                copy_options.requested_lod=lod
                u.GeometryScript_SceneUtils.copy_mesh_from_component(preview,u.DynamicMesh(),copy_options,False)
                if shot[3]:
                    points=[preview.get_socket_location(n) for n in ('upperarm_l','lowerarm_l','hand_l')]
                    target=u.Vector(sum(v.x for v in points)/3,sum(v.y for v in points)/3,sum(v.z for v in points)/3)
                    pos=u.Vector(target.x-70,target.y-60,target.z+24)
                    capture.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,target),False,True);cc.set_editor_property('fov_angle',44.)
                else:capture.set_actor_location_and_rotation(u.Vector(),u.Rotator(),False,True);cc.set_editor_property('fov_angle',fov)
                cc.set_editor_property('camera_cut_this_frame',True)
            mesh.set_position(shot[2],False)
            if f>=5:cc.capture_scene()
            if f==6:cc.set_editor_property('camera_cut_this_frame',False)
            if f>=30:
                u.RenderingLibrary.export_render_target(world,rt,str(OUT),shot[0]+'.png')
                receipt.append({'image':shot[0]+'.png','animation':D+'/A_RuneSword_'+shot[1],'time':shot[2],
                    'evaluation':'compressed animation sampled into poseable mesh',
                    'left_hand':str(preview.get_socket_location('hand_l')),'right_hand':str(preview.get_socket_location('hand_r')),
                    'blade_tip':str(preview.get_socket_location('Blade_Tip'))})
                state['shot']+=1;state['frame']=0
                if state['shot']==len(shots):finish()
        except Exception:finish(traceback.format_exc())
    callback=u.register_slate_post_tick_callback(tick)
except Exception:finish(traceback.format_exc())
