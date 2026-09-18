"""Install the per-rifle baked finish on the extended magazines.

weapon-finish.md: every accessory matches its own rifle's current coating, the
original structure normal/AO stay as they are, white markings survive, and the
metal areas take that rifle's coating. The BaseColor/ORM below are baked from
each rifle's receiver coating through the magazine's own coating UV (index 1,
MagazineCoatUV), so nothing assumes the M4 material on another rifle.

Also re-imports the meshes (they now carry UV0 + the coating UV, and the AKM
mesh has been re-expressed in its own WPN_SOCKET_Magazine frame).

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
MD = D + '/Materials'
TD = D + '/Textures'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary

JOBS = {
    'SM_ExtMag_M440': dict(fbx='SM_ExtMag_M440_finish.fbx', rifle='M4',
                           texture_dir=O / 'Textures' / 'M4',
                           base_material='/Game/Weapons/M4InfimaV3/Magazine_Light_001.Magazine_Light_001'),
    'SM_ExtMag_QBZ40': dict(fbx='SM_ExtMag_QBZ40_finish.fbx', rifle='QBZ191',
                            texture_dir=O / 'Textures' / 'QBZ',
                            base_material='/Game/Weapons/QBZ191/Attachments20260913/Materials/'
                                          'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer.'
                                          'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer'),
    'SM_ExtMag_AKM40': dict(fbx='SM_ExtMag_AKM40_finish.fbx', rifle='AKM',
                            texture_dir=O / 'Textures' / 'AKM',
                            base_material='/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR.M_AKM_Soviet_PBR'),
}


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


def node(mat, cls, **props):
    n = L.create_material_expression(mat, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def link(a, out, b, pin):
    pins = [str(x) for x in L.get_material_expression_input_names(b)]
    if pin == 'Input' and pin not in pins:
        pin = pins[0]
    if not L.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('Connection failed ' + pin)


def output(src, out, prop):
    if not L.connect_material_property(src, out, prop):
        raise RuntimeError('Output failed ' + str(prop))


def constant(mat, value):
    return node(mat, u.MaterialExpressionConstant, r=value)


report = {}
for name, cfg in JOBS.items():
    # The 2026-09-18 first pass had to save variants because the user's editor held
    # the canonical assets (weapon-finish.md's locked-editor rule). With the editor
    # released, install into the canonical names again and keep the earlier
    # *_Finish variants on disk as a registered fallback.
    mesh_name = name
    # 1. mesh (UV0 + MagazineCoatUV), replace existing asset
    task = u.AssetImportTask()
    task.filename = str(O / 'FBX' / cfg['fbx'])
    task.destination_path = D
    task.destination_name = mesh_name
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials = False
    opt.import_textures = False
    opt.import_animations = False
    opt.static_mesh_import_data.combine_meshes = True
    opt.static_mesh_import_data.convert_scene_unit = False
    opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = opt
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    mesh = u.load_asset(D + '/' + mesh_name)
    if not mesh:
        report[mesh_name] = 'MESH MISSING'
        continue
    name = mesh_name

    # 2. baked textures
    textures = {}
    for kind, srgb in (('BaseColor', True), ('ORM', False)):
        src = cfg['texture_dir'] / ('T_ExtMag_%s_%s.png' % (
            'M4' if cfg['rifle'] == 'M4' else ('QBZ' if cfg['rifle'] == 'QBZ191' else 'AKM'), kind))
        t = u.AssetImportTask()
        t.filename = str(src)
        t.destination_path = TD
        t.destination_name = 'T_ExtMag_%s_%s' % (cfg['rifle'], kind)
        t.automated = True
        t.replace_existing = True
        t.save = False
        A.import_asset_tasks([t])
        tex = u.load_asset(t.destination_path + '/' + t.destination_name)
        if not tex:
            report[name] = 'TEXTURE MISSING ' + str(src)
            break
        tex.srgb = srgb
        tex.compression_settings = (u.TextureCompressionSettings.TC_DEFAULT if srgb
                                   else u.TextureCompressionSettings.TC_MASKS)
        tex.lod_group = u.TextureGroup.TEXTUREGROUP_WEAPON
        save(tex)
        textures[kind] = tex
    if 'MESH MISSING' in str(report.get(name, '')) or len(textures) < 2:
        continue

    # 3. material: own rifle's coating on UV1, original normal/AO on UV0
    mat_name = 'M_ExtMag_Finish_' + cfg['rifle']
    mat_path = MD + '/' + mat_name
    original = u.load_asset(cfg['base_material'])
    if not original:
        report[name] = 'BASE MATERIAL MISSING ' + cfg['base_material']
        continue
    for stale in (mat_path, mat_path + '_Graph'):
        if E.does_asset_exist(stale):
            E.delete_asset(stale)
    # The host slot is often a MaterialInstanceConstant; expressions can only be
    # authored on a Material, so clone the graph and keep the instance on top with
    # its original parameter values (same route as WeaponAttachmentFinish
    # import_finish.py and QBZ191MetalCoat import_coating.py).
    if isinstance(original, u.MaterialInstanceConstant):
        graph = E.duplicate_asset(original.get_base_material().get_path_name(), mat_path + '_Graph')
        mat = E.duplicate_asset(original.get_path_name(), mat_path)
        values = {}
        L.set_material_instance_parent(mat, graph)
        for kind in ('scalar', 'vector', 'texture', 'static_switch'):
            names = getattr(L, 'get_%s_parameter_names' % kind)(graph)
            getter = getattr(L, 'get_material_instance_%s_parameter_value' % kind)
            setter = getattr(L, 'set_material_instance_%s_parameter_value' % kind)
            for n in names:
                v = getter(original, n)
                if v is not None:
                    setter(mat, n, v)
    else:
        graph = E.duplicate_asset(original.get_path_name(), mat_path)
        mat = graph
    authoring = graph
    uv = node(authoring, u.MaterialExpressionTextureCoordinate, coordinate_index=1)
    samples = {}
    for kind, tex in textures.items():
        sampler = (u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == 'BaseColor'
                   else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        s = node(authoring, u.MaterialExpressionTextureSample, texture=tex, sampler_type=sampler)
        link(uv, '', s, 'UVs')
        samples[kind] = s
    # keep white markings/lettering from the original material
    old_bc = L.get_material_property_input_node(authoring, u.MaterialProperty.MP_BASE_COLOR)
    old_out = L.get_material_property_input_node_output_name(authoring, u.MaterialProperty.MP_BASE_COLOR)
    mask = None
    if old_bc:
        lum = node(authoring, u.MaterialExpressionDesaturation)
        link(old_bc, old_out, lum, 'Input')
        link(constant(authoring, 1.0), '', lum, 'Fraction')
        white = node(authoring, u.MaterialExpressionSmoothStep, const_min=0.55, const_max=0.82)
        link(lum, '', white, 'Value')
        mask = node(authoring, u.MaterialExpressionOneMinus)
        link(white, '', mask, 'Input')
    for prop, sample, out in ((u.MaterialProperty.MP_BASE_COLOR, samples['BaseColor'], 'RGB'),
                              (u.MaterialProperty.MP_ROUGHNESS, samples['ORM'], 'G'),
                              (u.MaterialProperty.MP_METALLIC, samples['ORM'], 'B')):
        old = L.get_material_property_input_node(authoring, prop)
        oldout = L.get_material_property_input_node_output_name(authoring, prop)
        if mask and old:
            blend = node(authoring, u.MaterialExpressionLinearInterpolate)
            link(old, oldout, blend, 'A')
            link(sample, out, blend, 'B')
            link(mask, '', blend, 'Alpha')
            output(blend, '', prop)
        else:
            output(sample, out, prop)
    # original UV0 normal / cavity inputs stay connected
    E.set_metadata_tag(authoring, 'WeaponReceiverFinish', '20260918_extmag')
    E.set_metadata_tag(authoring, 'WeaponFinishCoatingUV', '1')
    E.set_metadata_tag(authoring, 'WeaponFinishReference', cfg['base_material'])
    L.recompile_material(authoring)
    save(authoring)
    if mat is not authoring:
        L.update_material_instance(mat)
    save(mat)

    # 4. bind every slot of this magazine to its own rifle's finish
    slots = mesh.get_editor_property('static_materials')
    for i, slot in enumerate(slots):
        slot.material_interface = mat
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    E.set_metadata_tag(mesh, 'WeaponFinishReference', cfg['base_material'])
    E.set_metadata_tag(mesh, 'WeaponFinishCoatingUV', '1')
    save(mesh)
    report[name] = {
        'material': mat.get_path_name(),
        'base': cfg['base_material'],
        'coating_uv': 1,
        'textures': {k: v.get_path_name() for k, v in textures.items()},
        'slots': [str(s.material_slot_name) for s in slots],
        'rifle': cfg['rifle'],
        'normal_note': 'original structure normal/AO kept (UV0)',
    }

(O / 'finish_install_receipt.json').write_text(json.dumps(report, indent=2, default=str))
u.log('EXTMAG_FINISH_INSTALLED ' + json.dumps(report, default=str))
