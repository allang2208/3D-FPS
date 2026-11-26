"""Place identifiable foreground scans and author the tutorial's twenty-second shot."""
import json
import runpy
from pathlib import Path
import unreal as u

LEVEL = "/Game/ForestPathStudy/Maps/L_ForestPathForest"
ROOT = "/Game/ForestPathStudy"
seq_name = "LS_ForestPathWalk"
tools = u.AssetToolsHelpers.get_asset_tools()
lib = u.EditorAssetLibrary
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
scripts = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())) / "Scripts"
runpy.run_path(str(scripts / "author_scans.py"))
if not level.load_level(LEVEL):
    raise RuntimeError(LEVEL)
scene = actors.get_all_level_actors()
camera = next(a for a in scene if isinstance(a,u.CineCameraActor) and "15mm" in a.get_actor_label())
sun = next(a for a in scene if isinstance(a,u.DirectionalLight))
light = sun.get_component_by_class(u.DirectionalLightComponent)
light.set_mobility(u.ComponentMobility.MOVABLE)
sun.set_actor_rotation(u.Rotator(roll=-105.,pitch=-36.72957,yaw=125.80169),False)
light.set_intensity(10.)
light.set_light_source_angle(4.)
lens = camera.get_cine_camera_component()
post = lens.get_editor_property("post_process_settings")
for field,value in [
    ("bloom_method",u.BloomMethod.BM_FFT), ("bloom_intensity",.02),
    ("lens_flare_intensity",.01), ("vignette_intensity",.507998), ("film_grain_intensity",.5)
]:
    post.set_editor_property("override_" + field,True)
    post.set_editor_property(field,value)
lens.set_editor_property("post_process_settings",post)
packages = json.loads((Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/"forest-scan-assets.json").read_text("utf8"))

# Location and rotation were read from the author's Details panel while dressing the foreground.
# The source panel shows X/Y/Z rotation, equivalent to UE roll/pitch/yaw.
foreground = [
    ("rgfoh", "", (-9630.84,21773.459,-631.8626),(-10.15563,5.242229,-.937642),4.969066),
    ("rgAsy", "", (-9891.749,23188.752,-631.6000),(0.,0.,0.),3.679729),
    ("tg0qedqda", "", (-10635.54,23589.294,-613.8332),(0.,0.,0.),3.889596),
    ("tlljeeyva", "", (-10690.56,23745.115,-643.9372),(0.,0.,0.),5.065779),
    ("vepkcelqx", "", (-8671.259,22005.413,-608.4123),(-.59643,0.,86.185112),1.),
    ("vfspfcjaw", "", (-9009.194,22201.195,-590.8898),(0.,0.,0.),1.),
    ("tjtjfinia", "VarE", (-10346.03,21946.594,-579.0141),(0.,0.,0.),1.)
]
for key, variant, xyz, rpy, size in foreground:
    candidates = [x for x in packages.get(key, []) if "_nonue/" not in x.lower() and "_lod1" not in x.lower() and "_lod2" not in x.lower() and "_lod3" not in x.lower()]
    if variant:
        candidates = [x for x in candidates if variant.lower() in x.lower()]
    if not candidates:
        u.log_warning(f"No imported matching foreground mesh for {key} {variant}")
        continue
    label = "Tutorial foreground - " + key
    if any(a.get_actor_label() == label for a in scene):
        continue
    actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(*xyz), u.Rotator(roll=rpy[0],pitch=rpy[1],yaw=rpy[2]))
    mesh = u.load_asset(candidates[0])
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.set_actor_scale3d(u.Vector(size,size,size))
    actor.set_actor_label(label)
    actor.set_folder_path("Tutorial foreground")
    u.log(f"Placed {key} using {candidates[0]}")

# Preserve existing art if rerunning the foreground pass.
if not lib.does_asset_exist(f"{ROOT}/Sequence/{seq_name}"):
    lib.make_directory(f"{ROOT}/Sequence")
    seq = tools.create_asset(seq_name, f"{ROOT}/Sequence", u.LevelSequence, u.LevelSequenceFactoryNew())
    seq.set_display_rate(u.FrameRate(30,1))
    seq.set_playback_start(0)
    seq.set_playback_end(600)
    binding = seq.add_possessable(camera)
    cut = seq.add_track(u.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0,600)
    cut.set_camera_binding_id(seq.get_binding_id(binding))
    motion = binding.add_track(u.MovieScene3DTransformTrack).add_section()
    motion.set_range(0,600)
    channels = motion.get_all_channels()
    if len(channels) < 9:
        raise RuntimeError("Missing transform channels")
    # Start and final transforms from 38:12 / 81:02. Interior keys reconstruct the pan.
    start = (-10502.60,23732.50,-404.63)
    end = (-10152.06,21975.556,-423.6851)
    for frame,rpy in [(0,(0.,-13.,-77.725024)),(120,(0.,-3.5,-98.)),(268,(0.,2.,-109.)),(410,(0.,-3.,-51.)),(599,(.039188,6.525002,-56.32502))]:
        t = frame / 599.
        pos = tuple(a + (b-a)*t for a,b in zip(start,end))
        for channel,value in zip(channels[:9], pos + rpy + (1.,1.,1.)):
            channel.add_key(u.FrameNumber(frame),value,interpolation=u.MovieSceneKeyInterpolation.LINEAR)
    shake_name = "BP_ForestPathCameraShake"
    shake_path = f"{ROOT}/Sequence/{shake_name}"
    if lib.does_asset_exist(shake_path):
        shake_bp = u.load_asset(shake_path)
    else:
        factory = u.BlueprintFactory()
        factory.set_editor_property("parent_class",u.DefaultCameraShakeBase)
        shake_bp = tools.create_asset(shake_name,f"{ROOT}/Sequence",u.Blueprint,factory)
        u.BlueprintEditorLibrary.compile_blueprint(shake_bp)
    cls = shake_bp.generated_class()
    pattern = u.get_default_object(cls).get_root_shake_pattern()
    pattern.set_editor_property("duration",0.)
    pattern.set_editor_property("rotation_amplitude_multiplier",1.)
    pattern.set_editor_property("rotation_frequency_multiplier",.5)
    if not lib.save_loaded_asset(shake_bp,False):
        raise RuntimeError(shake_name)
    lens_binding = seq.add_possessable(lens)
    lens_binding.set_parent(binding)
    shake = lens_binding.add_track(u.MovieSceneCameraShakeTrack).add_section()
    shake.set_range(0,600)
    settings = shake.get_editor_property("shake_data")
    settings.set_editor_property("shake_class",cls)
    shake.set_editor_property("shake_data",settings)
    if not lib.save_loaded_asset(seq,False):
        raise RuntimeError(seq_name)
if not level.save_current_level():
    raise RuntimeError("Foreground level save failed")
runpy.run_path(str(scripts / "author_ground_cover.py"))
if not level.save_current_level():
    raise RuntimeError("Ground cover material binding save failed")
