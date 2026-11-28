"""Import SM_LightningSpire textures, Substrate PBR/emissive materials, and 5 modular static meshes into UE 5.8."""
from pathlib import Path
from struct import iter_unpack
from zipfile import ZipFile
import gc
import hashlib
import json
import os
import sys
import unreal as ue

src = Path(__file__).resolve().parent
root = src.parents[2]
os.environ['HIGH_VILLAGE_PROJECT'] = str(root)
sys.path.insert(0, str(root / 'Tools/WorldGeneration/HighVillageDefense'))
sys.path.insert(0, str(root / 'Tools/Fluids'))
import import_kit as kit
from furnace_material_graph import custom, node, prop, scalar, wire

E = ue.EditorAssetLibrary
A = ue.AssetToolsHelpers.get_asset_tools()
L = ue.MaterialEditingLibrary

DEST = '/Game/WorldGeneration/TemperateHills/HighVillageDefense/LightningSpire'
MAT_DEST = DEST + '/Materials'
TEX_DEST = DEST + '/Textures'
TEX_SRC = src / 'PropTextures'


def import_spire_texture(slot, channel):
    fname = TEX_SRC / f'{slot}_{channel}.png'
    name = f'T_{slot}_{channel}'
    path = TEX_DEST + '/' + name
    digest = hashlib.sha256(fname.read_bytes()).hexdigest()
    old = E.load_asset(path) if E.does_asset_exist(path) else None
    if old and str(E.get_metadata_tag(old, 'VillageSourceSHA')) == digest:
        return old
    task = ue.AssetImportTask()
    task.filename = str(fname)
    task.destination_name = name
    task.destination_path = TEX_DEST
    task.automated = True
    task.save = False
    task.replace_existing = bool(old)
    A.import_asset_tasks([task])
    tex = kit.require(path)
    tex.set_editor_property('srgb', channel == 'base_color')
    if channel == 'normal':
        tex.set_editor_property('compression_settings', ue.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)
    elif channel != 'base_color':
        tex.set_editor_property('compression_settings', ue.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('max_texture_size', 1024)
    E.set_metadata_tag(tex, 'VillageSourceSHA', digest)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError('Failed saving texture ' + path)
    return tex


def tex_sampler(mat, tex, sampler_type, uv_node, param_name):
    s = node(mat, ue.MaterialExpressionTextureSampleParameter2D)
    s.set_editor_property('parameter_name', param_name)
    s.set_editor_property('texture', tex)
    s.set_editor_property('sampler_type', sampler_type)
    wire((uv_node, ''), s, 'UVs')
    return s


def build_pbr_material(slot, emissive_mode=None):
    name = f'M_{slot}'
    path = MAT_DEST + '/' + name
    mat = E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name, MAT_DEST, ue.Material, ue.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', ue.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided', False)

    slab = node(mat, ue.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', ue.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv0 = node(mat, ue.MaterialExpressionTextureCoordinate)
    uv0.set_editor_property('coordinate_index', 0)

    def surface(key, pin, expr, out_pin=''):
        src_val = (expr, out_pin) if out_pin else expr
        if not L.connect_material_property(expr, out_pin, getattr(ue.MaterialProperty, 'MP_' + key)):
            raise RuntimeError('Spire link failed: ' + key)
        wire(src_val, slab, pin)

    base_tex = import_spire_texture(slot, 'base_color')
    norm_tex = import_spire_texture(slot, 'normal')
    rough_tex = import_spire_texture(slot, 'roughness')
    metal_tex = import_spire_texture(slot, 'metallic')

    sb = tex_sampler(mat, base_tex, ue.MaterialSamplerType.SAMPLERTYPE_COLOR, uv0, 'BaseColorMap')
    sn = tex_sampler(mat, norm_tex, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv0, 'NormalMap')
    sr = tex_sampler(mat, rough_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'RoughnessMap')
    sm = tex_sampler(mat, metal_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'MetallicMap')

    surface('BASE_COLOR', 'BaseColor', sb, 'RGB')
    surface('ROUGHNESS', 'Roughness', sr, 'R')
    surface('METALLIC', 'Metallic', sm, 'R')
    surface('SPECULAR', 'Specular', scalar(mat, 'Specular', 0.56 if emissive_mode == 'crystal' else 0.52))
    surface('NORMAL', 'Normal', sn, 'RGB')

    if emissive_mode:
        em_tex = import_spire_texture(slot, 'emissive')
        se = tex_sampler(mat, em_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'EmissiveMask')
        t = node(mat, ue.MaterialExpressionTime)
        cpd0 = scalar(mat, 'ChargePower', 0.0)
        cpd0.set_editor_property('use_custom_primitive_data', True)
        cpd0.set_editor_property('primitive_data_index', 0)
        if emissive_mode == 'rune':
            glow = scalar(mat, 'RuneIntensity', 4.6)
            hlsl = (
                'float pwr = (CPD > 0.01) ? CPD : 1.0;'
                'float pulse = 0.78 + 0.22 * sin(T * 3.2 + UV.x * 6.283 + UV.y * 6.283);'
                'float3 c = lerp(float3(0.10, 0.52, 0.96), float3(0.32, 0.88, 1.0), saturate(Mask * 1.15));'
                'return c * pow(saturate(Mask), 1.1) * pulse * Power * pwr;'
            )
        else:
            glow = scalar(mat, 'CrystalIntensity', 5.2)
            hlsl = (
                'float pwr = (CPD > 0.01) ? CPD : 1.0;'
                'float pulse = 0.82 + 0.18 * sin(T * 4.1 + UV.y * 9.0);'
                'float3 c = lerp(float3(0.14, 0.45, 0.95), float3(0.45, 0.90, 1.0), saturate(Mask));'
                'return c * (0.28 + 0.72 * pow(saturate(Mask), 1.2)) * pulse * Power * pwr;'
            )
        em = custom(mat, hlsl, {'Mask': (se, 'R'), 'T': t, 'UV': uv0, 'Power': glow, 'CPD': cpd0}, 3)
        surface('EMISSIVE_COLOR', 'Emissive Color', em)

    prop(mat, slab, 'FRONT_MATERIAL')
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError(f'{name} compile failed: {errors}')
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Failed saving material ' + path)
    return mat


def create_spire_mesh(role, materials, receipt, receipt_file):
    path = DEST + '/' + role
    meshzip = src / f'{role}.meshzip'
    digest = hashlib.sha256(meshzip.read_bytes()).hexdigest()
    obj = kit.existing(path)
    if obj and str(E.get_metadata_tag(obj, 'VillageSourceSHA')) == digest and role in receipt['saved']:
        return
    dynamic = ue.DynamicMesh()
    with ZipFile(meshzip) as archive:
        spec = json.loads(archive.read('mesh.json'))
        for i, slot in enumerate(spec['materials']):
            if slot not in materials:
                raise RuntimeError('Unbound material ' + slot)
            def entries(name, fmt):
                return iter_unpack('<' + fmt, archive.read(f'{i}/{name}'))
            buf = ue.GeometryScriptSimpleMeshBuffers()
            buf.vertices = [ue.Vector(*p) for p in entries('vertices', '3f')]
            buf.uv1 = [ue.Vector2D(max(p[2], 0.) / 170., 0.) for p in entries('vertices', '3f')]
            buf.uv0 = [ue.Vector2D(*p) for p in entries('uv', '2f')]
            buf.normals = [ue.Vector(*p) for p in entries('normals', '3f')]
            buf.triangles = [ue.IntVector(*p) for p in entries('indices', '3i')]
            ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic, buf, material_id=i)
            del buf

    if not obj:
        obj, result = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
            dynamic, path,
            ue.GeometryScriptCreateNewStaticMeshAssetOptions(
                enable_recompute_normals=False,
                enable_recompute_tangents=True,
                enable_collision=True,
                enable_nanite=False,
            ),
        )
        if not obj or result != ue.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot create ' + path)

    # Always disable Nanite so curved copper coils & faceted stone never hit 1% fallback proxy decimation.
    ns = obj.get_editor_property('nanite_settings')
    ns.enabled = False
    slots = spec['materials']
    options = ue.GeometryScriptCopyMeshToAssetOptions(
        enable_recompute_normals=False,
        enable_recompute_tangents=True,
        replace_materials=True,
        new_materials=[materials[s] for s in slots],
        new_material_slot_names=slots,
        apply_nanite_settings=True,
        new_nanite_settings=ns,
    )
    _, result = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic, obj, options, ue.GeometryScriptMeshWriteLOD())
    if result != ue.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Mesh build failed: ' + role)

    body = obj.get_editor_property('body_setup')
    aggregate = body.get_editor_property('agg_geom')
    boxes = []
    for data in spec['boxes']:
        box = ue.KBoxElem()
        box.set_editor_property('center', ue.Vector(*data['center']))
        for field, length in zip(('x', 'y', 'z'), data['size']):
            box.set_editor_property(field, length)
        if 'pitch' in data:
            box.set_editor_property('rotation', ue.Rotator(pitch=data['pitch'], yaw=data.get('yaw', 0.)))
        boxes.append(box)
    for key in ('convex_elems', 'sphere_elems', 'sphyl_elems'):
        aggregate.set_editor_property(key, [])
    aggregate.set_editor_property('box_elems', boxes)
    body.set_editor_property('agg_geom', aggregate)
    body.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    E.set_metadata_tag(obj, 'VillageSourceSHA', digest)
    kit.save(obj)
    receipt['saved'][role] = {
        'path': obj.get_path_name(),
        'materials': slots,
        'triangles': spec['faces'],
        'collision_boxes': len(boxes),
        'source_sha256': digest,
    }
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    del dynamic
    gc.collect()


def main():
    for d in (DEST, MAT_DEST, TEX_DEST):
        E.make_directory(d)

    materials = {
        'SpireStone': build_pbr_material('SpireStone'),
        'SpireCastIron': build_pbr_material('SpireCastIron'),
        'SpireCopperBrass': build_pbr_material('SpireCopperBrass'),
        'SpireInsulator': build_pbr_material('SpireInsulator'),
        'SpireRuneGlow': build_pbr_material('SpireRuneGlow', emissive_mode='rune'),
        'SpireCrystal': build_pbr_material('SpireCrystal', emissive_mode='crystal'),
    }

    roles = (
        'SM_LightningSpireBase',
        'SM_LightningSpireMast',
        'SM_LightningSpireCrystal',
        'SM_LightningSpireRings',
        'SM_LightningSpirePreview',
    )
    out = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())) / 'spire-saved.json'
    receipt = {'saved': {}, 'materials': {k: v.get_path_name() for k, v in materials.items()}}
    for role in roles:
        create_spire_mesh(role, materials, receipt, out)
    out.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    ue.log('SPIRE_IMPORT_COMPLETE')


if __name__ == '__main__':
    main()
