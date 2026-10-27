"""Background import of the kukri: mesh, Unreal-packed textures, Substrate material, seven clips.

Run (commandlet, editor closed or not holding these packages):
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file> -unattended -nosplash
Never runs PIE or tests.  Writes import_receipt.json next to this script.
"""
import json
from pathlib import Path
import unreal as u

# Also runs inside a live editor through Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript (no __file__ there).
P = Path(globals().get('__file__') or r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py").resolve().parent
ROOT = P.parents[1]
SRC = Path(r"D:\FPS3D\VaultCache\FabLibrary\Kukri-0a08e297\fbx\kukri_extracted\Textures\Unreal")
DEST = '/Game/Weapons/Kukri20261020'
ARMS = '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'
SKELETON = '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny_Skeleton'
REVISION = 'Kukri_V12_Stab_20261022'
# V8: three-hit chain -- first sweep ("Attack", right -> left), diagonal cut ("Attack2", upper-left -> lower-right)
# and the third hit ("Attack3") plus stance/locomotion/draw.
# V11: Attack2 re-fitted to reference melee #1 and Attack2/Attack3 start on the stance (combo recovers between hits).
# V12: Attack3 replaced by the one-handed crouch stab (reference melee #5 戳, 38/30 s; the V8-V11 two-handed thrust
# with the left palm on the pommel is archived under trash/kukri-20261022-v12/).
# The V1 Slash1/Slash2/Pommel assets stay unused.
# import_kukri_attacks.py sets KUKRI_CLIPS to re-import only the changed clips.
CLIPS = list(globals().get('KUKRI_CLIPS') or ('Idle', 'Walk', 'Run', 'Equip', 'Attack', 'Attack2', 'Attack3'))
A = u.AssetToolsHelpers.get_asset_tools()
L = u.EditorAssetLibrary
E = u.MaterialEditingLibrary
receipt = dict(revision=REVISION, assets=[], animations={}, runtime_tested=False, complete=False)


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Kukri save failed: ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return asset


def node(mat, cls, **props):
    n = E.create_material_expression(mat, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def link(a, out, b, pin):
    if not E.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('Kukri material input failed: ' + pin)


def output(a, pin, prop):
    if not E.connect_material_property(a, pin, prop):
        raise RuntimeError('Kukri material output failed: ' + str(prop))


def build_surface():
    """Textures, material and SM_Kukri (revision-gated).  Clip-only wrappers (KUKRI_CLIPS) skip this: re-saving the
    surface packages on every clip import changed nothing and raced other commandlets for SM_Kukri (2026-10-22)."""
    # ---------------------------------------------------------------- textures
    textures = {}
    # V2 surface (make_kukri_textures.py): steel blade re-authored over the Fab layout; reimported in place
    # whenever the texture revision tag differs.  Viewmodel close-up: weapon LOD groups, never streamed, so
    # the blade never shows a low mip.
    TEX_REVISION = 'KukriSteelV5_20261020'
    STEEL = P / 'Textures'
    for key, file, srgb, comp, group in [
            ('BaseColor', 'T_Kukri_BaseColor.png', True, u.TextureCompressionSettings.TC_BC7, u.TextureGroup.TEXTUREGROUP_WEAPON),
            ('Normal', 'T_Kukri_Normal.png', False, u.TextureCompressionSettings.TC_NORMALMAP, u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP),
            ('ORM', 'T_Kukri_ORM.png', False, u.TextureCompressionSettings.TC_MASKS, u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)]:
        name = 'T_Kukri_' + key
        tex = u.load_asset(DEST + '/Textures/' + name)
        if not tex or L.get_metadata_tag(tex, 'Kukri.TextureRevision') != TEX_REVISION:
            task = u.AssetImportTask()
            task.filename = str(STEEL / file)
            task.destination_path = DEST + '/Textures'
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            A.import_asset_tasks([task])
            tex = u.load_asset(DEST + '/Textures/' + name)
            if not tex:
                raise RuntimeError('Kukri texture import failed: ' + key)
        tex.set_editor_property('srgb', srgb)
        tex.set_editor_property('compression_settings', comp)
        tex.set_editor_property('lod_group', group)
        tex.set_editor_property('never_stream', True)
        tex.set_editor_property('max_texture_size', 2048)
        L.set_metadata_tag(tex, 'Kukri.TextureRevision', TEX_REVISION)
        textures[key] = save(tex)

    # ---------------------------------------------------------------- material (Substrate front material)
    MAT_REVISION = 'KukriSteelV2_20261020'
    mat = u.load_asset(DEST + '/Materials/M_Kukri')
    if not mat:
        mat = A.create_asset('M_Kukri', DEST + '/Materials', u.Material, u.MaterialFactoryNew())
    if L.get_metadata_tag(mat, 'Kukri.MaterialRevision') != MAT_REVISION:
        mat.modify()
        for old in list(E.get_material_expressions(mat)) if hasattr(E, 'get_material_expressions') else []:
            E.delete_material_expression(mat, old)
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
        mat.set_editor_property('two_sided', False)
        mat.set_editor_property('use_material_attributes', False)
        mat.set_editor_property('used_with_nanite', True)
        base = node(mat, u.MaterialExpressionTextureSample, texture=textures['BaseColor'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        orm = node(mat, u.MaterialExpressionTextureSample, texture=textures['ORM'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        nrm = node(mat, u.MaterialExpressionTextureSample, texture=textures['Normal'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        slab = node(mat, u.MaterialExpressionSubstrateShadingModels, shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for n, pin, prop, target in [(base, 'RGB', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                                     (nrm, 'RGB', u.MaterialProperty.MP_NORMAL, 'Normal'),
                                     (orm, 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION, 'AmbientOcclusion'),
                                     (orm, 'G', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                                     (orm, 'B', u.MaterialProperty.MP_METALLIC, 'Metallic')]:
            if target != 'AmbientOcclusion':
                link(n, pin, slab, target)
            output(n, pin, prop)
        output(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL)
        E.layout_material_expressions(mat)
        E.recompile_material(mat)
        L.set_metadata_tag(mat, 'Kukri.Revision', REVISION)
        L.set_metadata_tag(mat, 'Kukri.MaterialRevision', MAT_REVISION)
        u.log('KUKRI_MATERIAL_REBUILT expressions=%d' % E.get_num_material_expressions(mat))
    save(mat)

    # ---------------------------------------------------------------- static mesh (viewmodel attachment + world pickup)
    MESH_REVISION = 'KukriBladeNormalsV5_20261020'
    mesh = u.load_asset(DEST + '/SM_Kukri')
    if not mesh or L.get_metadata_tag(mesh, 'Kukri.MeshRevision') != MESH_REVISION:
        task = u.AssetImportTask()
        task.filename = str(P / 'Export' / 'SM_Kukri.fbx')
        task.destination_path = DEST
        task.destination_name = 'SM_Kukri'
        task.automated = True
        task.replace_existing = True
        task.save = False
        ui = u.FbxImportUI()
        ui.set_editor_property('import_mesh', True)
        ui.set_editor_property('import_as_skeletal', False)
        ui.set_editor_property('import_materials', False)
        ui.set_editor_property('import_textures', False)
        ui.set_editor_property('import_animations', False)
        sm = ui.get_editor_property('static_mesh_import_data')
        try:
            sm.set_editor_property('normal_import_method', u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        except Exception as exc:  # enum naming differs between versions; build settings below still apply
            u.log_warning('Kukri normal import method not set: %s' % exc)
        sm.set_editor_property('combine_meshes', True)
        sm.set_editor_property('auto_generate_collision', True)
        sm.set_editor_property('generate_lightmap_u_vs', True)
        task.options = ui
        A.import_asset_tasks([task])
        mesh = u.load_asset(DEST + '/SM_Kukri')
        if not mesh:
            raise RuntimeError('Kukri mesh import failed')
    # V5 build: keep the authored corner normals (blade flats rebuilt in Blender), MikkTSpace tangents in high
    # precision (8-bit tangents band on a smooth reflective blade), full-precision UVs, no Nanite (a 3.4k-triangle
    # viewmodel attachment gains nothing and Nanite's default normal precision facets polished metal).
    try:
        ses = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
        bs = ses.get_lod_build_settings(mesh, 0)
        bs.set_editor_property('recompute_normals', False)
        bs.set_editor_property('recompute_tangents', True)
        bs.set_editor_property('use_mikk_t_space', True)
        bs.set_editor_property('use_high_precision_tangent_basis', True)
        bs.set_editor_property('use_full_precision_u_vs', True)
        ses.set_lod_build_settings(mesh, 0, bs)
        u.log('KUKRI_MESH_BUILD normals=imported tangents=mikk/high uv=full')
    except Exception as exc:
        u.log_warning('Kukri build settings not applied: %s' % exc)
    try:
        ns = mesh.get_editor_property('nanite_settings')
        u.log('KUKRI_MESH_NANITE was %s' % ns.get_editor_property('enabled'))
        ns.set_editor_property('enabled', False)
        mesh.set_editor_property('nanite_settings', ns)
    except Exception as exc:
        u.log_warning('Kukri nanite settings not applied: %s' % exc)
    L.set_metadata_tag(mesh, 'Kukri.MeshRevision', MESH_REVISION)
    # 2026-10-22: editing the elements of get_editor_property('static_materials') in Python edits copies, so the old loop
    # here never assigned anything and the slot stayed on WorldGridMaterial (the "white mosaic" blade).  Assign through
    # UStaticMesh::SetMaterial and read it back.
    for i in range(len(mesh.get_editor_property('static_materials'))):
        mesh.set_material(i, mat)
        if mesh.get_material(i) != mat:
            raise RuntimeError('Kukri material slot %d not assigned' % i)
    L.set_metadata_tag(mesh, 'Kukri.Frame', 'grip centre origin; +Z blade; +X edge; attaches to WPN_root at identity (scale 0.01 vs bone 100)')
    L.set_metadata_tag(mesh, 'Kukri.Source', 'Fab: Kukri by powers28 (0a08e297-e2d0-472b-b572-53077a548196)')
    save(mesh)
    bounds = mesh.get_bounding_box()
    receipt['mesh_bounds_cm'] = dict(min=[bounds.min.x, bounds.min.y, bounds.min.z], max=[bounds.max.x, bounds.max.y, bounds.max.z])


if not globals().get('KUKRI_CLIPS') or globals().get('KUKRI_SURFACE'):
    build_surface()


# ---------------------------------------------------------------- animations
arms = u.load_asset(ARMS)
skeleton = u.load_asset(SKELETON)
if not arms or not skeleton:
    raise RuntimeError('Shared sword arms or skeleton missing')
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for clip in CLIPS:
    data = json.loads((P / 'Clips' / (clip + '.json')).read_text('utf-8'))
    name = 'A_Kukri_' + clip
    path = DEST + '/Animations/' + name
    if path in dirty:
        raise RuntimeError('Preserving unsaved edits: ' + path)
    seq = u.load_asset(path)
    if not seq:
        factory = u.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton', skeleton)
        factory.set_editor_property('preview_skeletal_mesh', arms)
        seq = A.create_asset(name, DEST + '/Animations', u.AnimSequence, factory)
        if not seq:
            raise RuntimeError('Cannot create ' + path)
    # SetFrameRate updates the source model only. Keep compression at the authored
    # rate before closing the edit bracket: 222 intervals at 120 Hz cannot be
    # resampled to the default 30 Hz (55.5 frames; UE asserts during compression).
    authored_rate = u.FrameRate(numerator=data['fps'], denominator=1)
    seq.get_editor_property('platform_target_frame_rate').set_editor_property('default', authored_rate)
    controller = seq.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(seq.get_editor_property('data_model_interface'))
    frames = data['frames']
    controller.open_bracket('Kukri ' + clip, False)
    try:
        controller.remove_all_bone_tracks(False)
        controller.set_frame_rate(authored_rate, False)
        controller.set_number_of_frames(u.FrameNumber(value=len(frames) - 1), False)
        for bone in data['bones']:
            if not controller.add_bone_curve(bone, False):
                raise RuntimeError('Cannot add bone ' + bone)
            keys = [f[bone] for f in frames]
            ok = controller.set_bone_track_keys(bone, [u.Vector(*k[0]) for k in keys],
                                                [u.Quat(k[1][1], k[1][2], k[1][3], k[1][0]) for k in keys],
                                                [u.Vector(*k[2]) for k in keys], False)
            if not ok:
                raise RuntimeError('Cannot key ' + bone)
    finally:
        controller.close_bracket(False)
    seq.set_preview_skeletal_mesh(arms)
    seq.set_editor_property('enable_root_motion', False)
    seq.set_editor_property('force_root_lock', False)
    L.set_metadata_tag(seq, 'Kukri.AuthorSource', str(P / 'Clips' / (clip + '.json')))
    L.set_metadata_tag(seq, 'Kukri.Revision', REVISION)
    # Complete this asset's compression before saving or reporting import success.
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):
        raise RuntimeError('Cannot finalize ' + path)
    save(seq)
    receipt['animations'][path] = dict(frames=len(frames), fps=data['fps'], seconds=(len(frames) - 1) / data['fps'],
                                       play_length=seq.get_play_length(), contact=data.get('contact'), loop=data['loop'])
    u.log('KUKRI_ANIM_SAVED %s %.3f s' % (path, seq.get_play_length()))

receipt['complete'] = True
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('KUKRI_IMPORT_COMPLETE assets=%d' % len(receipt['assets']))
