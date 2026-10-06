"""Save the modeled tactical stock and its PBR assets, without gameplay changes."""
import json
import re
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parents[3]
O = P / 'SourceAssets/LegendaryStock20261006'
D = '/Game/Weapons/LegendaryStock20261006'
auth = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
receipt = O / 'import-receipt.json'
report = {'display_name': auth['display_name'], 'stage': 'model_only', 'saved': [],
          'models': {}, 'materials': {}, 'textures': {}, 'runtime_integrated': False,
          'host_fitted': False, 'game_tested': False, 'status': 'importing'}
report['visual_revision'] = auth.get('visual_revision', 'V1')

targets = ({D+'/Models/'+name for name in auth['models']}
           | {D+'/Textures/'+name for name in auth['textures']}
           | {D+'/Materials/M_'+spec['name'] for spec in auth['materials']})
dirty = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):
    raise RuntimeError('Unsaved content exists at this stock destination; preserve current edits.')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stock asset import requires the current play session to finish.')


def record():
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()


def node(mat, kind, **values):
    obj = L.create_material_expression(mat, kind)
    for key, value in values.items():
        obj.set_editor_property(key, value)
    return obj


def wire(source, destination, pin, output=''):
    if not L.connect_material_expressions(source, output, destination, pin):
        raise RuntimeError('Material input connection failed: ' + pin)


def prop(source, output_property, output=''):
    if not L.connect_material_property(source, output, output_property):
        raise RuntimeError('Material output connection failed')


textures = {}
for name, spec in auth['textures'].items():
    task = u.AssetImportTask()
    task.filename = spec['file']
    task.destination_path = D + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    tex = u.load_asset(D+'/Textures/'+name)
    if tex is None or not task.imported_object_paths:
        raise RuntimeError('Texture was not imported: '+name)
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP
                            if spec['kind'] == 'N' else u.TextureCompressionSettings.TC_MASKS)
    if spec['kind'] == 'N':
        tex.set_editor_property('flip_green_channel', True)
    E.set_metadata_tag(tex, 'Source', 'Original procedural tactical-stock surface map')
    save(tex)
    textures[name] = tex
    report['textures'][name] = tex.get_path_name()

materials = {}
for spec in auth['materials']:
    name = 'M_' + spec['name']
    path = D + '/Materials/' + name
    mat = (u.load_asset(path) if E.does_asset_exist(path)
           else A.create_asset(name, D+'/Materials', u.Material, u.MaterialFactoryNew()))
    for expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, expression)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided', False)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    tint = node(mat, u.MaterialExpressionVectorParameter, parameter_name='SurfaceTint',
                default_value=u.LinearColor(*spec['color']))
    prop(tint, u.MaterialProperty.MP_BASE_COLOR)
    metallic = node(mat, u.MaterialExpressionScalarParameter, parameter_name='Metallic',
                    default_value=spec['metallic'])
    prop(metallic, u.MaterialProperty.MP_METALLIC)
    specular = node(mat, u.MaterialExpressionScalarParameter, parameter_name='Specular',
                    default_value=.28 if spec['family'] == 'Rubber' else .5)
    prop(specular, u.MaterialProperty.MP_SPECULAR)
    normal = node(mat, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceNormal',
                  texture=textures['T_TacticalStock_'+spec['family']+'_N'],
                  sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    prop(normal, u.MaterialProperty.MP_NORMAL, 'RGB')
    orm = node(mat, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceORM',
               texture=textures['T_TacticalStock_'+spec['family']+'_ORM'],
               sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if spec['family'] == 'Rubber':
        rubber_color = node(mat, u.MaterialExpressionMultiply)
        wire(tint, rubber_color, 'A')
        wire(orm, rubber_color, 'B', 'B')
        prop(rubber_color, u.MaterialProperty.MP_BASE_COLOR)
    base_roughness = node(mat, u.MaterialExpressionScalarParameter, parameter_name='RoughnessScale',
                          default_value=spec['roughness']/.9)
    dry = node(mat, u.MaterialExpressionMultiply)
    wire(orm, dry, 'A', 'G')
    wire(base_roughness, dry, 'B')
    wet = node(mat, u.MaterialExpressionScalarParameter, parameter_name='WeaponWetness', default_value=0.)
    wet_roughness = node(mat, u.MaterialExpressionConstant, r=max(.12, spec['roughness']*.6))
    blend = node(mat, u.MaterialExpressionLinearInterpolate)
    wire(dry, blend, 'A')
    wire(wet_roughness, blend, 'B')
    wire(wet, blend, 'Alpha')
    prop(blend, u.MaterialProperty.MP_ROUGHNESS)
    prop(orm, u.MaterialProperty.MP_AMBIENT_OCCLUSION, 'R')
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    E.set_metadata_tag(mat, 'Source', auth['source'])
    save(mat)
    materials[spec['name']] = mat
    report['materials'][spec['name']] = mat.get_path_name()

old = u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
try:
    for name, entry in auth['models'].items():
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.import_animations = False
        options.override_full_name = True
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task = u.AssetImportTask()
        task.filename = entry['fbx']
        task.destination_name = name
        task.destination_path = D+'/Models'
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.options = options
        task.factory = u.FbxFactory()
        task.save = False
        A.import_asset_tasks([task])
        mesh = u.load_asset(D+'/Models/'+name)
        if mesh is None or not task.imported_object_paths:
            raise RuntimeError('Mesh was not imported: '+name)
        slots = list(mesh.static_materials)
        for i, slot in enumerate(slots):
            key = re.sub(r'[._]\d{3}$', '', str(slot.material_slot_name))
            slot.material_interface = materials[key]
            slots[i] = slot
        mesh.set_editor_property('static_materials', slots)
        for key, position in entry['sockets_ue_cm'].items():
            socket = mesh.find_socket(key)
            if socket is None:
                socket = u.StaticMeshSocket(outer=mesh)
                socket.set_editor_property('socket_name', key)
                mesh.add_socket(socket)
            socket.set_editor_property('relative_location', u.Vector(*position))
        E.set_metadata_tag(mesh, 'DisplayName', auth['display_name'])
        E.set_metadata_tag(mesh, 'Rarity', 'legendary')
        E.set_metadata_tag(mesh, 'ProductionStage', 'Master model; per-weapon runtime assets are in Fitted')
        E.set_metadata_tag(mesh, 'VisualRevision', report['visual_revision'])
        E.set_metadata_tag(mesh, 'Source', auth['source'])
        save(mesh)
        report['models'][name] = {'asset': mesh.get_path_name(), 'triangles_authored': entry['triangles'],
                                 'sockets_ue_cm': entry['sockets_ue_cm']}
finally:
    u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status'] = 'six_meshes_six_materials_six_textures_saved'
record()
print('TACTICAL_STOCK_ASSETS_SAVED '+json.dumps({'models':len(report['models']),
      'materials':len(report['materials']), 'textures':len(report['textures']),
      'receipt':str(receipt)}, ensure_ascii=False))
