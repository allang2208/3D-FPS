"""Create a lean game asset, generate its LODs and save the existing M25 Blueprint binding."""
from pathlib import Path
import sys, traceback, shutil
sys.path.insert(0, str(Path(__file__).resolve().parent))
from author_common import *

record = dict(revision=REV, stage='started', saved=[], runtime_tested=False, rendered=False,
              triangle_targets=TARGETS, screen_sizes=SCREENS, ray_tracing_min_lod=1)
def stage(name):
    record['stage'] = name
    write_receipt('asset_receipt.json', record)
    u.log('M25_OPTIMIZATION ' + name)

try:
    production_context()
    skeleton = load(BASE + '/SK_M25_VortexCoffer_Skeleton')
    physics = load(BASE + '/PA_M25_HitSurface_V01')
    mesh = owned(DEST + '/' + GAME_NAME)
    if mesh is None:
        stage('importing_reduced_game_source')
        cvar = 'Interchange.FeatureFlags.Import.FBX'
        old = u.SystemLibrary.get_console_variable_int_value(cvar)
        u.SystemLibrary.execute_console_command(None, cvar + ' 0')
        try:
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
            options.import_as_skeletal = True
            options.import_mesh = True
            options.import_animations = False
            options.import_materials = False
            options.import_textures = False
            options.create_physics_asset = False
            options.skeleton = skeleton
            data = options.skeletal_mesh_import_data
            data.set_editor_property('normal_import_method', u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            data.set_editor_property('use_t0_as_ref_pose', False)
            data.set_editor_property('update_skeleton_reference_pose', False)
            data.set_editor_property('import_mesh_lo_ds', False)
            task = u.AssetImportTask()
            task.filename = str(FBX)
            task.destination_path = DEST
            task.destination_name = GAME_NAME
            task.options = options
            task.automated = True
            task.save = False
            task.replace_existing = False
            TOOLS.import_asset_tasks([task])
            mesh = load(DEST + '/' + GAME_NAME)
            if mesh.get_editor_property('skeleton') != skeleton:
                raise RuntimeError('Import did not retain the original skeleton')
            slots = list(mesh.get_editor_property('materials'))
            material = load(BASE + '/Materials/M_M25_MeshySurface')
            for slot in slots:
                slot.set_editor_property('material_interface', material)
            mesh.set_editor_property('materials', slots)
            mesh.set_editor_property('physics_asset', physics)
            mesh.set_editor_property('enable_per_poly_collision', False)
            record['saved'].append(save(mesh))
        finally:
            u.SystemLibrary.execute_console_command(None, cvar + ' ' + str(old))
    if LIB.get_metadata_tag(mesh, 'M25.GameLODsComplete') != REV + '.AppliedAllLODs':
        stage('generating_game_lods')
        settings = lod_settings('DA_M25_GameLODs_V01', TARGETS, keep_base=True)
        previous_count = EDITOR.get_lod_count(mesh)
        mesh.call_method('SetLODSettings', (settings,))
        if not EDITOR.regenerate_lod(mesh, len(TARGETS), True, False):
            raise RuntimeError('Game LOD generation failed')
        if previous_count < len(TARGETS):
            # Newly added LODs initially inherit their predecessor's settings.
            # Apply the authored groups once all LODInfo entries exist.
            mesh.call_method('SetLODSettings', (settings,))
            if not EDITOR.regenerate_lod(mesh, len(TARGETS), True, False):
                raise RuntimeError('Applying individual LOD budgets failed')
        mesh.set_editor_property('ray_tracing_min_lod', 1)
        LIB.set_metadata_tag(mesh, 'M25.GameLODsComplete', REV + '.AppliedAllLODs')
        record['saved'].append(save(mesh))
    record['mesh'] = mesh_receipt(mesh)
    # Record actual production geometry counts, using render LODs rather than imported source data.
    triangles = []
    for index in range(EDITOR.get_lod_count(mesh)):
        dynamic = u.DynamicMesh()
        read_lod = u.GeometryScriptMeshReadLOD()
        read_lod.set_editor_property('lod_type', u.GeometryScriptLODType.RENDER_DATA)
        read_lod.set_editor_property('lod_index', index)
        result, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            mesh, dynamic, u.GeometryScriptCopyMeshFromAssetOptions(), read_lod)
        if outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot record generated LOD geometry: ' + str(index))
        triangles.append(dynamic.get_triangle_count())
    record['mesh']['triangles_by_lod'] = triangles
    stage('binding_game_mesh')
    bp_file = PROJECT / 'Content/Monsters/VortexCofferM25/BP_VortexCofferM25.uasset'
    backup = ROOT / 'BackupBeforeOptimization/BP_VortexCofferM25.uasset'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(bp_file, backup)
    bp = load(BASE + '/BP_VortexCofferM25')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    actor = u.get_default_object(bp.generated_class())
    actor.set_editor_property('visual_mesh', mesh)
    component = actor.get_editor_property('mesh')
    component.set_skeletal_mesh_asset(mesh)
    component.set_physics_asset(physics)
    # Finish the already requested movement tuning in the same Blueprint save.
    stage('saving_requested_movement_settings')
    reference = load('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler')
    ref = u.get_default_object(reference.generated_class())
    refmove = ref.get_editor_property('character_movement')
    move = actor.get_editor_property('character_movement')
    speed = float(ref.get_editor_property('walk_speed'))
    actor.set_editor_property('walk_speed', speed)
    actor.set_editor_property('animation_walk_speed', 16.0)
    motion = dict(max_walk_speed=speed,
                  max_acceleration=float(refmove.get_editor_property('max_acceleration')),
                  braking_deceleration_walking=float(refmove.get_editor_property('braking_deceleration_walking')))
    for key, value in motion.items():
        move.set_editor_property(key, value)
    yaw = float(refmove.get_editor_property('rotation_rate').yaw)
    move.set_editor_property('rotation_rate', u.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
    LIB.set_metadata_tag(bp, 'M25.MovementRevision', 'M25Movement20261004V2')
    record['saved'].append(save(bp))
    movement = dict(revision='M25Movement20261004V2', stage='assets_saved',
                    saved=[bp.get_path_name()], runtime_tested=False, rendered=False,
                    actor_settings=dict(walk_speed=speed, animation_walk_speed=16.0),
                    movement_settings=motion, rotation_rate_yaw_deg_s=yaw,
                    animation_rate_at_full_speed=speed / 16.0,
                    animation_cycle_at_full_speed_s=2.8 / (speed / 16.0),
                    authoring_script=str(ROOT / 'import_and_bind.py'), reference=reference.get_path_name(),
                    reference_turning_note='M10 uses a separate eight-leg movement solver; M25 retains its own movement and uses the configured RotationRate')
    write_receipt('../MovementV02/asset_receipt.json', movement)
    record['movement'] = movement
    record.update(blueprint=bp.get_path_name(), backup=str(backup),
                  original_mesh_retained=BASE + '/SK_M25_VortexCoffer',
                  animation_and_combat='Existing skeleton, animations, bite/magic channels, mouth weakpoint and hit physics retained',
                  texture_detail='Existing UVs and normal/basecolor/metallic-roughness maps retained; no new normal bake',
                  native_build='Not required: asset-only changes',
                  user_acceptance='Not tested or rendered; user will assess appearance, motion and performance')
    stage('assets_saved_and_bound')
except Exception:
    record['error'] = traceback.format_exc()
    stage('production_failed')
    raise
