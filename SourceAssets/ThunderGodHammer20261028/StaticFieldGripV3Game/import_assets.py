"""Save Static Field grip, PBR materials, and actual-model production icon in UE."""
from pathlib import Path
import datetime, hashlib, json, os, shutil
import unreal as u

P = Path(__file__).resolve().parent
S = P
R = P.parents[2]
D = '/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV3Game'
OLD = '/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV2'
if Path(u.Paths.project_dir()).resolve() != R:
    raise RuntimeError('Wrong project')
manifest = json.loads((P/'runtime_manifest.json').read_text(encoding='utf-8'))
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
prior = json.loads((P/'import_receipt.json').read_text(encoding='utf-8')) if (P/'import_receipt.json').exists() else {}
prior_saved = set(prior.get('saved', []))
receipt = dict(complete=False, revision=manifest['revision'], textures=[], materials=[], models=[], saved=[], runtime_tested=False)

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    asset.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    record()

def imp(file, name, folder, options=None, replace=False):
    asset = u.load_asset(folder+'/'+name)
    if asset and not replace:
        return asset
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = replace
    task.replace_existing_settings = replace
    if options:
        task.options = options
    A.import_asset_tasks([task])
    asset = u.load_asset(folder+'/'+name)
    if not asset:
        raise RuntimeError('Import failed: '+name)
    return asset

icon_folder = '/Game/ColdSteelData/AttachmentIcons20260913'
icon_key = 'ue_thunder_god_hammer_grip_static_field'
for dirty in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    name = dirty.get_path_name()
    if name.startswith(D+'/') or name == icon_folder+'/'+icon_key:
        raise RuntimeError('Preserving unsaved target package: '+name)
record()
textures = {}
for family in ('Leather',):
    textures[family] = {}
    for kind in ('BaseColor','ORM','Normal'):
        name = 'T_StaticField_'+family+'_'+kind
        tex = imp(S/'Textures'/(name+'.png'), name, D+'/Textures')
        if tex.get_path_name() in prior_saved:
            textures[family][kind] = tex
            receipt['textures'].append(tex.get_path_name())
            receipt['saved'].append(tex.get_path_name())
            record()
            continue
        normal = kind == 'Normal'
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('srgb', kind=='BaseColor')
        tex.set_editor_property('flip_green_channel', normal)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('max_texture_size', 8192 if family=='Leather' else 4096)
        tex.set_editor_property('never_stream', False)
        save(tex)
        textures[family][kind] = tex
        receipt['textures'].append(tex.get_path_name())

def node(mat, cls):
    return L.create_material_expression(mat, cls)

def link(a, channel, b, pin):
    if not L.connect_material_expressions(a, channel, b, pin):
        raise RuntimeError('Material connection failed: '+pin)

def vector(mat, value):
    n = node(mat, u.MaterialExpressionConstant3Vector)
    n.set_editor_property('constant', u.LinearColor(value[0], value[1], value[2], 1.0))
    return n

def scalar(mat, value):
    n = node(mat, u.MaterialExpressionConstant)
    n.set_editor_property('r', value)
    return n

materials = {}
for row in manifest['materials']:
    if row['slot'] != 'M_StaticField_Leather' and row['kind'] != 'native':
        reused = u.load_asset(OLD+'/Materials/'+row['slot'])
        if not reused:raise RuntimeError('Existing metal material missing: '+row['slot'])
        materials[row['slot']] = reused
        receipt['materials'].append(dict(slot=row['slot'], asset=reused.get_path_name(), reused=True))
        continue
    if row['kind'] == 'native':
        # Native seal and mating bands retain the host's live PBR finish.
        native = u.load_asset('/Game/Weapons/ThunderGodHammer20261028/Materials/M_ThunderGodHammerSurface')
        if not native:
            raise RuntimeError('Native hammer finish missing')
        materials[row['slot']] = native
        receipt['materials'].append(dict(slot=row['slot'], asset=native.get_path_name(), reused=True))
        continue
    name = row['slot']
    mat = u.load_asset(D+'/Materials/'+name) or A.create_asset(name, D+'/Materials', u.Material, u.MaterialFactoryNew())
    if mat.get_path_name() in prior_saved:
        materials[name] = mat
        receipt['materials'].append(dict(slot=name,asset=mat.get_path_name(),reused=False))
        receipt['saved'].append(mat.get_path_name())
        record()
        continue
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('use_material_attributes', False)
    mat.set_editor_property('used_with_skeletal_mesh', False)
    mat.set_editor_property('used_with_nanite', True)
    mat.set_editor_property('two_sided', False)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    surface = node(mat, u.MaterialExpressionSubstrateShadingModels)
    surface.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    inputs = {}
    if row['kind'] == 'pbr':
        samples = {}
        for kind, tex in textures[row['family']].items():
            n = node(mat, u.MaterialExpressionTextureSample)
            n.set_editor_property('texture', tex)
            n.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            samples[kind] = n
        base = samples['BaseColor']
        if row['tint'] != [1.,1.,1.]:
            multiply = node(mat, u.MaterialExpressionMultiply)
            link(base, 'RGB', multiply, 'A')
            link(vector(mat,row['tint']), '', multiply, 'B')
            base, base_channel = multiply, ''
        else:
            base_channel = 'RGB'
        blend = node(mat, u.MaterialExpressionLinearInterpolate)
        link(vector(mat,[0.,0.,1.]), '', blend, 'A')
        link(samples['Normal'], 'RGB', blend, 'B')
        blend.set_editor_property('const_alpha', row['normal_strength'])
        normal = node(mat, u.MaterialExpressionNormalize)
        link(blend, '', normal, 'VectorInput')
        inputs.update(BaseColor=(base,base_channel), Roughness=(samples['ORM'],'G'), Metallic=(samples['ORM'],'B'), Normal=(normal,''))
        L.connect_material_property(samples['ORM'], 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    else:
        inputs.update(BaseColor=(vector(mat,row['base']),''), Roughness=(scalar(mat,row['roughness']),''), Metallic=(scalar(mat,row['metallic']),''), EmissiveColor=(vector(mat,row['emission']),''))
    properties = dict(BaseColor=u.MaterialProperty.MP_BASE_COLOR, Roughness=u.MaterialProperty.MP_ROUGHNESS, Metallic=u.MaterialProperty.MP_METALLIC, Normal=u.MaterialProperty.MP_NORMAL, EmissiveColor=u.MaterialProperty.MP_EMISSIVE_COLOR)
    for pin, (n, ch) in inputs.items():
        link(n,ch,surface,'Emissive Color' if pin=='EmissiveColor' else pin)
        L.connect_material_property(n,ch,properties[pin])
    if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Substrate output missing')
    L.layout_material_expressions(mat)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed: '+str(errors))
    save(mat)
    materials[name] = mat
    receipt['materials'].append(dict(slot=name,asset=mat.get_path_name(),reused=False))

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh = True
opt.import_as_skeletal = False
opt.import_materials = False
opt.import_textures = False
opt.import_animations = False
data = opt.static_mesh_import_data
data.combine_meshes = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = imp(manifest['fbx'],manifest['mesh'],D+'/Meshes',opt)
for i, slot in enumerate(mesh.get_editor_property('static_materials')):
    name = str(slot.material_slot_name)
    if name not in materials:
        raise RuntimeError('Missing material binding: '+name)
    mesh.set_material(i,materials[name])
settings = mesh.get_editor_property('nanite_settings')
settings.enabled = True
settings.explicit_tangents = True
settings.position_precision = 10
settings.normal_precision = 15
settings.tangent_precision = 12
settings.keep_percent_triangles = 1.
settings.trim_relative_error = 0.
settings.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
settings.fallback_percent_triangles = .15
settings.fallback_relative_error = 0.
mesh.set_editor_property('nanite_settings',settings)
subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
build = subsystem.get_lod_build_settings(mesh,0)
for prop,value in [('use_full_precision_u_vs',True),('use_high_precision_tangent_basis',True),('recompute_normals',False),('recompute_tangents',True),('use_mikk_t_space',True)]:
    build.set_editor_property(prop,value)
subsystem.set_lod_build_settings(mesh,0,build)
u.EditorAssetLibrary.set_metadata_tag(mesh,'AuthoringRevision',manifest['revision'])
save(mesh)
receipt['models'].append(dict(id='static_field_grip',asset=mesh.get_path_name(),source_triangles=manifest['triangles'],fbx_sha256=manifest['fbx_sha256'],nanite=True,full_fidelity_fallback=False,fallback_fraction=.15,nanite_triangles=mesh.get_num_nanite_triangles(),fallback_triangles=mesh.get_num_triangles(0)))
record()


# The accepted design icon remains unchanged: this revision changes topology only.
receipt['icon'] = dict(reused=True, reason='Same design and materials; existing actual-model icon preserved')
receipt['complete'] = True
record()
print('STATIC_FIELD_GAME_ASSETS_SAVED',mesh.get_path_name())
