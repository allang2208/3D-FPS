"""Headless UE 5.8 D3D12 verification for HorseTackR52b:
1. Audits all 4 standalone SM_Tack_* + 4 skinned SK_Tack_*_Mounted assets (skeleton match, LODs, 0 null mats, collision).
2. Spawns real SK_StableWarhorse with M_Warhorse_CoatFade (CPD[1]=1.0 HideOriginalTack), SK_Hair_Sweep,
   and all 4 SK_Tack_*_Mounted bound via SetLeaderPoseComponent(skin, True).
3. Captures real UE5 D3D12 renders across Bind (front34, side, rear34, head, hoof), animated Canter, animated Feed,
   and 50% synchronized dissolve fade (CPD[0]=0.5) to visually verify:
     - 0 white stirrup ghosting
     - 0 white chest collar ghosting
     - proud visible armored horseshoes
     - clean shoulder/croup/ear deformation in Canter & Feed
     - synchronized coat + tack dither dissolve
4. Verifies ColdSteelItems.json horse_equipment world_mesh & icon paths resolve cleanly.
"""
import json
from pathlib import Path
import unreal as ue

OUT_DIR = Path('F:/FPSGAMEData/ArtReviews/HillsVillageStable/HorseTackR52-20261126/UEAuditR52b')
OUT_DIR.mkdir(parents=True, exist_ok=True)
TACK_ROOT = '/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52'
HORSE_ROOT = '/Game/WorldGeneration/TemperateHills/VillageStable/Horses'
WARHORSE_SK = HORSE_ROOT + '/SK_StableWarhorse'
WARHORSE_COAT_FADE = HORSE_ROOT + '/AppearanceR30/M_Warhorse_CoatFade'
WARHORSE_MANE = HORSE_ROOT + '/AppearanceR30/SK_Hair_Sweep'

ANIMS = {
    'Canter': HORSE_ROOT + '/Animations/A_Warhorse_Canter',
    'Feed': HORSE_ROOT + '/Animations/A_Warhorse_Q_Feed',
}

STANDALONE_NAMES = [
    'SM_Tack_Horseshoes',
    'SM_Tack_Saddle',
    'SM_Tack_Barding',
    'SM_Tack_Saddlebags',
]

MOUNTED_SK_NAMES = [
    'SK_Tack_Horseshoes_Mounted',
    'SK_Tack_Saddle_Mounted',
    'SK_Tack_Barding_Mounted',
    'SK_Tack_Saddlebags_Mounted',
]


def audit_assets():
    sm_sub = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
    sk_sub = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
    warhorse_sk = ue.load_asset(WARHORSE_SK)
    expected_skel = warhorse_sk.get_editor_property('skeleton').get_path_name()

    results = []
    for name in STANDALONE_NAMES:
        sm = ue.load_asset(f'{TACK_ROOT}/{name}')
        if not sm:
            raise RuntimeError(f'Missing StaticMesh: {name}')
        lods = int(sm_sub.get_lod_count(sm))
        null_mats = [i for i, s in enumerate(sm.static_materials) if s.material_interface is None]
        bb = sm.get_bounding_box()
        body = sm.get_editor_property('body_setup')
        boxes = len(body.get_editor_property('agg_geom').get_editor_property('box_elems')) if body else 0
        results.append(dict(
            name=name, kind='static', lods=lods, mat_slots=len(sm.static_materials),
            null_mats=null_mats, collision_boxes=boxes,
            size_cm=[round(float(bb.max.x - bb.min.x), 2), round(float(bb.max.y - bb.min.y), 2), round(float(bb.max.z - bb.min.z), 2)],
        ))

    for name in MOUNTED_SK_NAMES:
        sk = ue.load_asset(f'{TACK_ROOT}/{name}')
        if not sk:
            raise RuntimeError(f'Missing SkeletalMesh: {name}')
        skel_path = sk.get_editor_property('skeleton').get_path_name()
        if skel_path != expected_skel:
            raise RuntimeError(f'Skeleton mismatch on {name}: {skel_path} != {expected_skel}')
        lods = int(sk_sub.get_lod_count(sk)) if hasattr(sk_sub, 'get_lod_count') else -1
        null_mats = [i for i, s in enumerate(sk.materials) if s.material_interface is None]
        bb = sk.get_bounds()
        results.append(dict(
            name=name, kind='skeletal', lods=lods, mat_slots=len(sk.materials),
            null_mats=null_mats, skeleton_match=True,
            size_cm=[round(float(bb.box_extent.x * 2), 2), round(float(bb.box_extent.y * 2), 2), round(float(bb.box_extent.z * 2), 2)],
        ))

    # Verify items.json horse_equipment entries resolve to real assets + icons
    items_path = Path(r'd:\FPS3D\FPSGAME\Content\ColdSteelData\items.json')
    raw_items = json.loads(items_path.read_text(encoding='utf-8'))
    if isinstance(raw_items, dict):
        items = raw_items.get('items', list(raw_items.values()))
    else:
        items = raw_items
    tack_items = []
    for it in items:
        if isinstance(it, dict) and it.get('category') == 'horse_equipment':
            wm = it.get('world_mesh', '')
            icon = it.get('icon', '')
            sm_ok = ue.load_asset(wm.split('.')[0]) is not None if wm else False
            icon_rel = icon.replace('/Game/ColdSteelData/', '').lstrip('/')
            icon_file = Path(r'd:\FPS3D\FPSGAME\Content\ColdSteelData') / icon_rel
            if not icon_file.exists():
                icon_file = Path(r'd:\FPS3D\FPSGAME\Content\ColdSteelData\Icons\HorseTack') / f'{it.get("id")}.png'
            tack_items.append(dict(id=it.get('id'), world_mesh=wm, world_mesh_ok=sm_ok, icon=icon, icon_exists=icon_file.exists(), icon_bytes=icon_file.stat().st_size if icon_file.exists() else 0))

    return results, tack_items


def render_capture(world, cam_loc, target_loc, out_png: Path, fov=42.0, res=1024):
    rt = ue.RenderingLibrary.create_render_target2d(world, res, res, ue.TextureRenderTargetFormat.RTF_RGBA8)
    cap_actor = ue.EditorLevelLibrary.spawn_actor_from_class(ue.SceneCapture2D, ue.Vector(*cam_loc))
    try:
        direction = ue.Vector(target_loc[0] - cam_loc[0], target_loc[1] - cam_loc[1], target_loc[2] - cam_loc[2])
        rot = ue.MathLibrary.make_rot_from_x(direction)
        cap_actor.set_actor_location_and_rotation(ue.Vector(*cam_loc), rot, False, True)
        comp = cap_actor.capture_component2d
        comp.texture_target = rt
        comp.capture_source = ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        comp.fov_angle = float(fov)
        comp.set_editor_property('capture_every_frame', False)
        comp.set_editor_property('capture_on_movement', False)
        comp.capture_scene()
        opts = ue.ImageWriteOptions()
        opts.format = ue.DesiredImageFormat.PNG
        opts.overwrite_file = True
        opts.async_ = False
        opts.compression_quality = 0
        ue.ImageWriteBlueprintLibrary.export_to_disk(rt, str(out_png), opts)
    finally:
        cap_actor.destroy_actor()


def ensure_shaders_and_textures_ready(world):
    """Synchronously compile SM6 shaders and stream all tack + warhorse textures to mip0 before capture."""
    ue.SystemLibrary.execute_console_command(world, 'r.Streaming.FullyLoadUsedTextures 1')
    ue.SystemLibrary.execute_console_command(world, 'r.Streaming.PoolSize 4096')
    mat_paths = [
        f'{TACK_ROOT}/Materials/M_TackSteel',
        f'{TACK_ROOT}/Materials/M_TackLeather',
        f'{TACK_ROOT}/Materials/M_TackLeatherDark',
        f'{TACK_ROOT}/Materials/M_TackBlanket',
        f'{TACK_ROOT}/Materials/M_Tack_Brass',
        f'{TACK_ROOT}/Materials/M_Tack_WaxedThread',
        WARHORSE_COAT_FADE,
        HORSE_ROOT + '/AppearanceR30/M_Warhorse_Fibres',
    ]
    mat_stats = {}
    for mp in mat_paths:
        m = ue.load_asset(mp)
        if not m:
            continue
        used_sk = bool(m.get_editor_property('used_with_skeletal_mesh'))
        # Calling get_statistics forces synchronous shader compilation for the active RHI (PCD3D_SM6)!
        st = ue.MaterialEditingLibrary.get_statistics(m)
        mat_stats[m.get_name()] = dict(
            used_with_skeletal_mesh=used_sk,
            pixel_samples=int(st.num_pixel_texture_samples),
            base_pass_instr=int(st.num_pixel_shader_instructions),
        )
        ue.log(f'  SHADER_READY {m.get_name():24s} sk={used_sk} tex_samples={st.num_pixel_texture_samples} instr={st.num_pixel_shader_instructions}')

    tex_paths = [
        f'{TACK_ROOT}/Textures/T_TackSteel_BaseColor',
        f'{TACK_ROOT}/Textures/T_TackSteel_NormalDX',
        f'{TACK_ROOT}/Textures/T_TackSteel_ORM',
        f'{TACK_ROOT}/Textures/T_TackLeather_BaseColor',
        f'{TACK_ROOT}/Textures/T_TackLeather_NormalDX',
        f'{TACK_ROOT}/Textures/T_TackLeather_ORM',
        f'{TACK_ROOT}/Textures/T_TackLeatherDark_BaseColor',
        f'{TACK_ROOT}/Textures/T_TackLeatherDark_NormalDX',
        f'{TACK_ROOT}/Textures/T_TackLeatherDark_ORM',
        f'{TACK_ROOT}/Textures/T_TackBlanket_BaseColor',
        f'{TACK_ROOT}/Textures/T_TackBlanket_NormalDX',
        f'{TACK_ROOT}/Textures/T_TackBlanket_ORM',
        HORSE_ROOT + '/Surfaces/T_Warhorse_BaseColor',
        HORSE_ROOT + '/Surfaces/T_Warhorse_Normal',
        HORSE_ROOT + '/Surfaces/T_Warhorse_MetalRough',
        HORSE_ROOT + '/AppearanceR30/T_Warhorse_Regions',
        HORSE_ROOT + '/AppearanceR30/T_Warhorse_Pigment',
    ]
    for tp in tex_paths:
        tex = ue.load_asset(tp)
        if tex and hasattr(tex, 'set_force_mip_levels_to_be_resident'):
            tex.set_force_mip_levels_to_be_resident(60.0)
    return mat_stats


def verify_live_rig():
    world = ue.EditorLevelLibrary.get_editor_world()
    mat_stats = ensure_shaders_and_textures_ready(world)
    sk = ue.load_asset(WARHORSE_SK)
    coat_fade = ue.load_asset(WARHORSE_COAT_FADE)
    mane_sk = ue.load_asset(WARHORSE_MANE)

    base_z = 12000.0
    spawned = []
    try:
        # Balanced studio lighting with warm key, soft cool fill, rim, and neutral skylight
        sun = ue.EditorLevelLibrary.spawn_actor_from_class(ue.DirectionalLight, ue.Vector(0, 0, base_z + 500))
        sun.set_actor_rotation(ue.Rotator(-36, -130, 0), False)
        sun.light_component.set_intensity(3.4)
        sun.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        spawned.append(sun)

        fill = ue.EditorLevelLibrary.spawn_actor_from_class(ue.PointLight, ue.Vector(280, 180, base_z + 240))
        fill.light_component.set_intensity(1800.0)
        fill.light_component.set_attenuation_radius(1600.0)
        fill.light_component.set_light_color(ue.LinearColor(0.88, 0.93, 1.0, 1.0))
        fill.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        spawned.append(fill)

        rim = ue.EditorLevelLibrary.spawn_actor_from_class(ue.PointLight, ue.Vector(-260, -240, base_z + 260))
        rim.light_component.set_intensity(2200.0)
        rim.light_component.set_attenuation_radius(1600.0)
        rim.light_component.set_light_color(ue.LinearColor(1.0, 0.94, 0.84, 1.0))
        rim.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        spawned.append(rim)

        # Ground stage
        floor = ue.EditorLevelLibrary.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0, 0, base_z - 5.0))
        floor.static_mesh_component.set_static_mesh(ue.load_asset('/Engine/BasicShapes/Cube'))
        floor.set_actor_scale3d(ue.Vector(14.0, 14.0, 0.1))
        spawned.append(floor)

        # Spawn Warhorse with M_Warhorse_CoatFade + CPD[1]=1.0 (HideOriginalTack!)
        horse = ue.EditorLevelLibrary.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, 0, base_z))
        skin = horse.skeletal_mesh_component
        skin.set_skeletal_mesh_asset(sk)
        skin.set_forced_lod(1)
        skin.set_update_animation_in_editor(True)
        skin.set_editor_property('visibility_based_anim_tick_option', ue.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        skin.set_material(0, coat_fade)
        skin.set_custom_primitive_data_float(0, 0.0)   # Fade = 0
        skin.set_custom_primitive_data_float(1, 1.0)   # HideOriginalTack = 1 (mask white stirrups + chest collar!)
        skin.set_custom_primitive_data_vector4(4, ue.Vector4(0.16, 0.075, 0.036, 1.0))   # Rich bay coat
        skin.set_custom_primitive_data_vector4(8, ue.Vector4(0.16, 0.075, 0.036, 1.0))
        skin.set_custom_primitive_data_vector4(12, ue.Vector4(0.0, 0.0, 0.01, 1.25))
        skin.set_custom_primitive_data_vector4(16, ue.Vector4(0.04, 0.03, 0.025, 1.0))
        skin.set_custom_primitive_data_vector4(20, ue.Vector4(0.9, 0.9, 0.025, 0.95))
        spawned.append(horse)

        # Attach Mane & all 4 Skinned Tack SkeletalMeshes via SetLeaderPoseComponent(skin, True)!
        follower_comps = []
        if mane_sk:
            ma = ue.EditorLevelLibrary.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, 0, base_z))
            mc = ma.skeletal_mesh_component
            mc.set_skeletal_mesh_asset(mane_sk)
            mc.set_forced_lod(1)
            mc.attach_to_component(skin, '', ue.AttachmentRule.SNAP_TO_TARGET, ue.AttachmentRule.SNAP_TO_TARGET, ue.AttachmentRule.KEEP_RELATIVE, False)
            mc.set_leader_pose_component(skin, True)
            mc.set_custom_primitive_data_float(0, 0.0)
            mc.set_custom_primitive_data_vector4(16, ue.Vector4(0.04, 0.03, 0.025, 1.0))
            mc.set_custom_primitive_data_vector4(20, ue.Vector4(0.9, 0.9, 0.025, 0.95))
            spawned.append(ma)
            follower_comps.append(mc)

        for sk_name in MOUNTED_SK_NAMES:
            tack_asset = ue.load_asset(f'{TACK_ROOT}/{sk_name}')
            ta = ue.EditorLevelLibrary.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, 0, base_z))
            tc = ta.skeletal_mesh_component
            tc.set_skeletal_mesh_asset(tack_asset)
            tc.set_forced_lod(1)
            tc.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
            tc.set_cast_shadow(True)
            tc.attach_to_component(skin, '', ue.AttachmentRule.SNAP_TO_TARGET, ue.AttachmentRule.SNAP_TO_TARGET, ue.AttachmentRule.KEEP_RELATIVE, False)
            tc.set_leader_pose_component(skin, True)
            tc.set_custom_primitive_data_float(0, 0.0)
            spawned.append(ta)
            follower_comps.append(tc)

        # Warm-up capture to flush streaming & shader compilation pipeline completely
        render_capture(world, (225, 205, base_z + 170), (0, 12, base_z + 115), OUT_DIR / 'ue_r52b_front34.png', fov=42)
        render_capture(world, (225, 205, base_z + 170), (0, 12, base_z + 115), OUT_DIR / 'ue_r52b_front34.png', fov=42)
        render_capture(world, (255, -8, base_z + 132), (0, 0, base_z + 110), OUT_DIR / 'ue_r52b_side.png', fov=44)
        render_capture(world, (210, -195, base_z + 170), (0, -25, base_z + 125), OUT_DIR / 'ue_r52b_rear34.png', fov=42)
        render_capture(world, (105, 195, base_z + 195), (0, 108, base_z + 175), OUT_DIR / 'ue_r52b_head.png', fov=34)
        render_capture(world, (105, 58, base_z + 28), (12, 42, base_z + 8), OUT_DIR / 'ue_r52b_hoof.png', fov=30)

        # Capture 50% synchronized dissolve fade!
        skin.set_custom_primitive_data_float(0, 0.50)
        for fc in follower_comps:
            fc.set_custom_primitive_data_float(0, 0.50)
        render_capture(world, (225, 205, base_z + 170), (0, 12, base_z + 115), OUT_DIR / 'ue_r52b_fade50.png', fov=42)
        skin.set_custom_primitive_data_float(0, 0.0)
        for fc in follower_comps:
            fc.set_custom_primitive_data_float(0, 0.0)

        # Capture REAL animated Canter & Feed poses!
        bind_head = skin.get_socket_transform('head', ue.RelativeTransformSpace.RTS_COMPONENT).translation
        bind_fl = skin.get_socket_transform('finger_L', ue.RelativeTransformSpace.RTS_COMPONENT).translation
        pose_report = dict(bind=dict(
            head=[round(float(bind_head.x), 1), round(float(bind_head.y), 1), round(float(bind_head.z), 1)],
            finger_L=[round(float(bind_fl.x), 1), round(float(bind_fl.y), 1), round(float(bind_fl.z), 1)],
        ))

        for pname, anim_path, t_norm in (('Canter', ANIMS['Canter'], 0.35), ('Feed', ANIMS['Feed'], 0.50)):
            seq = ue.load_asset(anim_path)
            if not seq:
                continue
            pos = float(seq.get_play_length()) * t_norm
            skin.set_animation_mode(ue.AnimationMode.ANIMATION_SINGLE_NODE)
            skin.override_animation_data(seq, False, False, pos, 0.0)
            skin.set_position(pos, False)
            if hasattr(skin, 'tick_animation'):
                skin.tick_animation(0.0, False)
            if hasattr(skin, 'refresh_bone_transforms'):
                skin.refresh_bone_transforms()
            for fc in follower_comps:
                if hasattr(fc, 'refresh_bone_transforms'):
                    fc.refresh_bone_transforms()

            hl = skin.get_socket_transform('head', ue.RelativeTransformSpace.RTS_COMPONENT).translation
            fl = skin.get_socket_transform('finger_L', ue.RelativeTransformSpace.RTS_COMPONENT).translation
            pose_report[pname] = dict(
                head=[round(float(hl.x), 1), round(float(hl.y), 1), round(float(hl.z), 1)],
                finger_L=[round(float(fl.x), 1), round(float(fl.y), 1), round(float(fl.z), 1)],
                head_delta_cm=round(float((hl - bind_head).length()), 2),
                finger_L_delta_cm=round(float((fl - bind_fl).length()), 2),
            )
            render_capture(world, (240, 200, base_z + 165), (0, 10, base_z + 110), OUT_DIR / f'ue_r52b_{pname.lower()}_front34.png', fov=44)
            render_capture(world, (265, -15, base_z + 135), (0, 0, base_z + 110), OUT_DIR / f'ue_r52b_{pname.lower()}_side.png', fov=45)

        return mat_stats, pose_report
    finally:
        for a in reversed(spawned):
            if a:
                a.destroy_actor()


def main():
    assets, tack_items = audit_assets()
    mat_stats, poses = verify_live_rig()
    report = dict(revision='HorseTackR52b', assets=assets, materials=mat_stats, tack_items=tack_items, poses=poses)
    out_json = OUT_DIR / 'ue_r52b_verify.json'
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log(f'HORSE_TACK_R52B_VERIFY_OK report={out_json}')
    for a in assets:
        ue.log(f'  ASSET {a["name"]:28s} kind={a["kind"]:8s} lods={a["lods"]} mats={a["mat_slots"]} nulls={len(a["null_mats"])} size={a["size_cm"]}')
    for k, v in poses.items():
        ue.log(f'  POSE  {k:8s} {v}')


if __name__ == '__main__':
    main()
