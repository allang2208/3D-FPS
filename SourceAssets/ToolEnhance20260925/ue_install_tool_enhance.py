"""阶段 2 编辑器批次：采集工具强化材质与拆槽网格接入。

做四件事（视模留到第二批，DO_VIEWMODEL=False）：
  1. 在 /Game/Items/ProductionTools/Enhance20260925/ 下新建两个母材质
     M_ToolHead_Master_Axe / M_ToolHead_Master_Pick：贴图参数沿用各工具现有贴图集，
     另加等级参数 Desaturate/Tint/MetallicUseConst/MetallicConst/RoughScale/ClearCoat/
     EmissiveColor/EmissiveStrength。不改动 M_BattleAxe / M_RusticPickaxe 的既有图
     （install_battle_axe.py 明确警告：改已保存网格引用的材质图会触发 !IsRooted 断言）。
  2. 建 8 个材质实例（每工具 1/3/4/5 级）。2 级不建实例，直接指向原材质，
     因此"2 级＝当前外观"是结构性等价，不需要渲染对比。
  3. 重导入 SM_BattleAxe / SM_RusticPickaxe（源 FBX 已被拆槽版覆盖），随后按
     install 脚本的原样补回 LOD1/LOD2、屏幕尺寸、Nanite 关闭，并按槽名赋材质：
     Metal <- 出厂 1 级石头实例，Wood <- 原材质。
  4. 保存全部 touched 资产并写回执（含重导入前后包围盒/LOD 数对照）。

安全约束：不在 PIE 中运行；目标包有未保存修改时直接拒绝；不启动/关闭编辑器。
运行方式（批次互斥）：
  powershell -File Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript SourceAssets/ToolEnhance20260925/ue_install_tool_enhance.py -QueueWaitSeconds 600
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
DEST = '/Game/Items/ProductionTools/Enhance20260925'
SPLIT = ROOT / 'SourceAssets' / 'ToolEnhance20260925'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary

DO_WORLD_MESH = True
DO_VIEWMODEL = False

# 阶段开关：远程执行是同步阻塞的，单批次不宜过长。默认读 ue-install-stage.json，
# 文件不存在时两阶段全做。第一批 {"materials": true, "world_mesh": false}，
# 第二批 {"materials": false, "world_mesh": true}。
STAGE_FILE = SPLIT / 'ue-install-stage.json'
if STAGE_FILE.exists():
    _stage = json.loads(STAGE_FILE.read_text(encoding='utf-8'))
    DO_MATERIALS = bool(_stage.get('materials', True))
    DO_WORLD_MESH = bool(_stage.get('world_mesh', True))
    DO_VIEWMODEL = bool(_stage.get('viewmodel', False))
else:
    DO_MATERIALS = True

GUARD_DIRS = ('/Game/Items/ProductionTools/BattleAxe20260919',
              '/Game/Items/ProductionTools/RusticPickaxe20260919',
              '/Game/Items/ProductionTools/GripMotion20260913')
# DEST 是本阶段专属目录，不进保护名单：失败重跑时先丢弃自己的残留资产。
OWN_ASSETS = ['M_ToolHead_Master_Axe', 'M_ToolHead_Master_Pick'] + [
    'MI_ToolHead_%s_%s' % (tag, level)
    for tag in ('Axe', 'Pick')
    for level in ('Stone', 'Steel', 'Stainless', 'PurpleStone')]

LEVEL_PARAMS = {
    'Stone': dict(scalars={'Desaturate': 0.85, 'MetallicUseConst': 1.0, 'MetallicConst': 0.0,
                           'RoughScale': 1.7, 'ClearCoat': 0.0, 'EmissiveStrength': 0.0},
                  vectors={'Tint': (0.42, 0.40, 0.37, 1.0), 'EmissiveColor': (0.0, 0.0, 0.0, 1.0)}),
    'Steel': dict(scalars={'Desaturate': 0.90, 'MetallicUseConst': 1.0, 'MetallicConst': 1.0,
                           'RoughScale': 0.55, 'ClearCoat': 0.0, 'EmissiveStrength': 0.0},
                  vectors={'Tint': (0.55, 0.57, 0.60, 1.0), 'EmissiveColor': (0.0, 0.0, 0.0, 1.0)}),
    'Stainless': dict(scalars={'Desaturate': 0.95, 'MetallicUseConst': 1.0, 'MetallicConst': 1.0,
                               'RoughScale': 0.28, 'ClearCoat': 0.6, 'EmissiveStrength': 0.0},
                      vectors={'Tint': (0.75, 0.78, 0.82, 1.0), 'EmissiveColor': (0.0, 0.0, 0.0, 1.0)}),
    'PurpleStone': dict(scalars={'Desaturate': 0.90, 'MetallicUseConst': 1.0, 'MetallicConst': 0.0,
                                 'RoughScale': 1.1, 'ClearCoat': 0.0, 'EmissiveStrength': 0.35},
                        vectors={'Tint': (0.45, 0.20, 0.75, 1.0), 'EmissiveColor': (0.35, 0.10, 0.80, 1.0)}),
}

TOOLS_DEF = {
    'Axe': dict(
        mesh=ROOT / 'SourceAssets/BattleAxeReplace20260919/Fitted/BattleAxe_16000.fbx',
        lods=[ROOT / 'SourceAssets/BattleAxeReplace20260919/Fitted/BattleAxe_LOD1.fbx',
              ROOT / 'SourceAssets/BattleAxeReplace20260919/Fitted/BattleAxe_LOD2.fbx'],
        mesh_asset='/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe',
        wood_material='/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe',
        textures=dict(base='/Game/Items/ProductionTools/BattleAxe20260919/T_BattleAxe_BaseColor',
                      normal='/Game/Items/ProductionTools/BattleAxe20260919/T_BattleAxe_Normal',
                      rough='/Game/Items/ProductionTools/BattleAxe20260919/T_BattleAxe_Roughness',
                      metal='/Game/Items/ProductionTools/BattleAxe20260919/T_BattleAxe_Metallic'),
        rough_channel='R', metal_channel='R'),
    'Pick': dict(
        mesh=ROOT / 'SourceAssets/RusticPickaxe20260919/Export/RusticPickaxe_World.fbx',
        lods=[ROOT / 'SourceAssets/RusticPickaxe20260919/Export/RusticPickaxe_LOD1.fbx',
              ROOT / 'SourceAssets/RusticPickaxe20260919/Export/RusticPickaxe_LOD2.fbx'],
        mesh_asset='/Game/Items/ProductionTools/RusticPickaxe20260919/SM_RusticPickaxe',
        wood_material='/Game/Items/ProductionTools/RusticPickaxe20260919/M_RusticPickaxe',
        textures=dict(base='/Game/Items/ProductionTools/RusticPickaxe20260919/T_RusticPickaxe_BaseColor',
                      normal='/Game/Items/ProductionTools/RusticPickaxe20260919/T_RusticPickaxe_Normal',
                      rough='/Game/Items/ProductionTools/RusticPickaxe20260919/T_RusticPickaxe_MetallicRoughness',
                      metal='/Game/Items/ProductionTools/RusticPickaxe20260919/T_RusticPickaxe_MetallicRoughness'),
        rough_channel='G', metal_channel='B'),
}

report = {'saved': [], 'runtime_tested': False, 'masters': {}, 'instances': {}, 'meshes': {}}


def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save: ' + str(asset))
    report['saved'].append(asset.get_path_name())
    return asset


def node(material, cls, **props):
    expr = LIB.create_material_expression(material, cls)
    for key, value in props.items():
        expr.set_editor_property(key, value)
    return expr


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + pin + ' on ' + target.get_class().get_name())


def link_input(source, output, target, candidates):
    for name in candidates:
        if LIB.connect_material_expressions(source, output, target, name):
            return name
    raise RuntimeError('No usable input pin on ' + target.get_class().get_name())


# ---------------------------------------------------------------- guards
if not ('-run=pythonscript' in u.SystemLibrary.get_command_line().lower()):
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level_editor and level_editor.is_in_play_in_editor():
        raise RuntimeError('Stop PIE before installing tool enhancement. No assets changed.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    name = package.get_name()
    if any(name.startswith(prefix) for prefix in GUARD_DIRS):
        raise RuntimeError('Save these packages first: ' + name)
# 只在建材质的阶段清理自己的残留：阶段 B 依赖阶段 A 的落盘资产，绝不能删。
if DO_MATERIALS:
    for name in OWN_ASSETS:
        path = DEST + '/' + name
        try:
            if EAL.does_asset_exist(path):
                EAL.delete_asset(path)
                report.setdefault('discarded_leftovers', []).append(name)
        except Exception as exc:
            report.setdefault('discard_warnings', []).append(name + ': ' + str(exc))
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
EAL.make_directory(DEST)


# ---------------------------------------------------------------- masters + instances
def build_master(tag, cfg):
    name = 'M_ToolHead_Master_' + tag
    path = DEST + '/' + name
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    material = TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    for expr in list(LIB.get_material_expressions(material)):
        LIB.delete_material_expression(material, expr)
    material.set_editor_property('two_sided', False)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('used_with_skeletal_mesh', True)

    textures = {key: u.load_asset(value) for key, value in cfg['textures'].items()}
    missing = [key for key, tex in textures.items() if tex is None]
    if missing:
        raise RuntimeError('Missing textures for ' + tag + ': ' + ','.join(missing))

    base = node(material, u.MaterialExpressionTextureSampleParameter2D,
                parameter_name='BaseColorTex', texture=textures['base'],
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    desat = node(material, u.MaterialExpressionDesaturation)
    desat_param = node(material, u.MaterialExpressionScalarParameter,
                       parameter_name='Desaturate', default_value=0.0)
    link_input(desat_param, '', desat, ('Fraction', 'fraction'))
    link_input(base, '', desat, ('', 'Input', 'Coordinates'))
    tint = node(material, u.MaterialExpressionVectorParameter,
                parameter_name='Tint', default_value=u.LinearColor(1., 1., 1., 1.))
    tinted = node(material, u.MaterialExpressionMultiply)
    wire(desat, tinted, 'A')
    wire(tint, tinted, 'B')
    if not LIB.connect_material_property(tinted, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Could not bind BaseColor for ' + tag)

    normal = node(material, u.MaterialExpressionTextureSampleParameter2D,
                  parameter_name='NormalTex', texture=textures['normal'],
                  sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    if not LIB.connect_material_property(normal, '', u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Could not bind Normal for ' + tag)

    rough = node(material, u.MaterialExpressionTextureSampleParameter2D,
                 parameter_name='RoughTex', texture=textures['rough'],
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    rough_scale = node(material, u.MaterialExpressionScalarParameter,
                       parameter_name='RoughScale', default_value=1.0)
    rough_mul = node(material, u.MaterialExpressionMultiply)
    wire(rough, rough_mul, 'A', cfg['rough_channel'])
    wire(rough_scale, rough_mul, 'B')
    rough_clamp = node(material, u.MaterialExpressionClamp)
    link_input(rough_mul, '', rough_clamp, ('Input', '', 'Value', 'A'))
    for pin, value in (('Min', 0.0), ('Max', 1.0)):
        try:
            rough_clamp.set_editor_property('min_default' if pin == 'Min' else 'max_default', value)
        except Exception:
            const = node(material, u.MaterialExpressionConstant, r=value)
            wire(const, rough_clamp, pin)
    if not LIB.connect_material_property(rough_clamp, '', u.MaterialProperty.MP_ROUGHNESS):
        raise RuntimeError('Could not bind Roughness for ' + tag)

    metal = node(material, u.MaterialExpressionTextureSampleParameter2D,
                 parameter_name='MetalTex', texture=textures['metal'],
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    metal_const = node(material, u.MaterialExpressionScalarParameter,
                       parameter_name='MetallicConst', default_value=1.0)
    metal_use = node(material, u.MaterialExpressionScalarParameter,
                     parameter_name='MetallicUseConst', default_value=0.0)
    metal_lerp = node(material, u.MaterialExpressionLinearInterpolate)
    wire(metal, metal_lerp, 'A', cfg['metal_channel'])
    wire(metal_const, metal_lerp, 'B')
    wire(metal_use, metal_lerp, 'Alpha')
    if not LIB.connect_material_property(metal_lerp, '', u.MaterialProperty.MP_METALLIC):
        raise RuntimeError('Could not bind Metallic for ' + tag)

    coat = node(material, u.MaterialExpressionScalarParameter,
                parameter_name='ClearCoat', default_value=0.0)
    try:
        LIB.connect_material_property(coat, '', u.MaterialProperty.MP_CLEAR_COAT)
        report.setdefault('clear_coat', {})[tag] = 'bound'
    except Exception:
        LIB.delete_material_expression(material, coat)
        report.setdefault('clear_coat', {})[tag] = 'unavailable'

    emissive_color = node(material, u.MaterialExpressionVectorParameter,
                          parameter_name='EmissiveColor', default_value=u.LinearColor(0., 0., 0., 1.))
    emissive_strength = node(material, u.MaterialExpressionScalarParameter,
                             parameter_name='EmissiveStrength', default_value=0.0)
    emissive = node(material, u.MaterialExpressionMultiply)
    wire(emissive_color, emissive, 'A')
    wire(emissive_strength, emissive, 'B')
    if not LIB.connect_material_property(emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Could not bind Emissive for ' + tag)

    LIB.layout_material_expressions(material)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Master compile errors ' + tag + ': ' + str(errors))
    save(material)
    report['masters'][tag] = material.get_path_name()
    return material


def build_instance(tag, level_id, master):
    name = 'MI_ToolHead_%s_%s' % (tag, level_id)
    path = DEST + '/' + name
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    instance = TOOLS.create_asset(name, DEST, u.MaterialInstanceConstant,
                                  u.MaterialInstanceConstantFactoryNew())
    instance.set_editor_property('parent', master)
    #  skeletal 使用标记只存在于 UMaterial；实例继承父材质的使用标志，不设此属性。
    params = LEVEL_PARAMS[level_id]
    # UE 5.8 的实例参数设置挂在 MaterialEditingLibrary 上，对象方法已不存在（探针确认）。
    for key, value in params['scalars'].items():
        LIB.set_material_instance_scalar_parameter_value(instance, key, value)
    for key, value in params['vectors'].items():
        LIB.set_material_instance_vector_parameter_value(instance, key, u.LinearColor(*value))
    LIB.update_material_instance(instance)
    save(instance)
    report['instances'][name] = instance.get_path_name()
    return instance


masters = {}
instances = {}
for tag, cfg in TOOLS_DEF.items():
    if DO_MATERIALS:
        masters[tag] = build_master(tag, cfg)
        instances[tag] = {level: build_instance(tag, level, masters[tag])
                          for level in ('Stone', 'Steel', 'Stainless', 'PurpleStone')}
    else:
        masters[tag] = u.load_asset(DEST + '/M_ToolHead_Master_' + tag)
        instances[tag] = {level: u.load_asset(DEST + '/MI_ToolHead_%s_%s' % (tag, level))
                          for level in ('Stone', 'Steel', 'Stainless', 'PurpleStone')}
        if masters[tag] is None or any(value is None for value in instances[tag].values()):
            raise RuntimeError('Stage B needs stage A assets; run the materials stage first')


# ---------------------------------------------------------------- world meshes
def snapshot(mesh):
    info = {'bounds': str(mesh.get_bounds()), 'lods': mesh.get_num_lods(),
            'slots': [str(slot.material_slot_name) for slot in mesh.static_materials]}
    try:
        info['nanite'] = mesh.get_editor_property('nanite_settings').enabled
    except Exception:
        info['nanite'] = None
    return info


if DO_WORLD_MESH:
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for tag, cfg in TOOLS_DEF.items():
        mesh = u.load_asset(cfg['mesh_asset'])
        if mesh is None:
            raise RuntimeError('Missing mesh asset: ' + cfg['mesh_asset'])
        before = snapshot(mesh)
        options = u.FbxImportUI()
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.import_as_skeletal = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.automated_import_should_detect_type = False
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.auto_generate_collision = True
        options.static_mesh_import_data.generate_lightmap_u_vs = True
        options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        # 重导入会保留旧槽（镐出现 3 槽：旧 M_RusticPickaxe + 新 Metal/Wood），
        # 旧槽索引与重导入面索引的对应关系不可靠，改名也无法保证面映射正确。
        # 改为删除后全新导入，与 install_battle_axe.py 的原流程一致：全新导入恰好得到
        # [Metal, Wood] 两槽且面索引对齐，LOD 随后用 import_lod 补回，碰撞自动生成。
        if EAL.does_asset_exist(cfg['mesh_asset']):
            EAL.delete_asset(cfg['mesh_asset'])
            report.setdefault('deleted_before_import', []).append(cfg['mesh_asset'])
        task = u.AssetImportTask()
        task.filename = str(cfg['mesh'])
        task.destination_path = cfg['mesh_asset'].rsplit('/', 1)[0]
        task.destination_name = cfg['mesh_asset'].rsplit('/', 1)[1]
        task.automated = True
        task.replace_existing = True
        # 必须 save=True：commandlet 退出时会丢弃未保存包，阶段 B 首跑因此丢掉了整次导入。
        task.save = True
        task.options = options
        TOOLS.import_asset_tasks([task])
        mesh = u.load_asset(cfg['mesh_asset'])
        if mesh is None:
            raise RuntimeError('Import did not produce ' + cfg['mesh_asset'])
        got = [str(s.material_slot_name) for s in mesh.static_materials]
        if got != ['Metal', 'Wood']:
            raise RuntimeError('%s: 全新导入后槽名应为 [Metal, Wood]，实际 %s' % (tag, got))
        for index, lod_file in enumerate(cfg['lods'], start=1):
            if editor.import_lod(mesh, index, str(lod_file)) != index:
                raise RuntimeError('Could not import %s LOD%d' % (tag, index))
        if not editor.set_lod_screen_sizes(mesh, [1.0, 0.35, 0.1]):
            raise RuntimeError('Could not set %s LOD screen sizes' % tag)
        nanite = mesh.get_editor_property('nanite_settings')
        nanite.enabled = False
        mesh.set_editor_property('nanite_settings', nanite)

        wood = u.load_asset(cfg['wood_material'])
        stone = instances[tag]['Stone']
        assigned = {}
        for index, name in enumerate(('Metal', 'Wood')):
            mat = stone if name == 'Metal' else wood
            mesh.set_material(index, mat)
            assigned[name] = mat.get_path_name()
        save(mesh)
        report['meshes'][tag] = {'asset': mesh.get_path_name(), 'before': before,
                                 'after': snapshot(mesh), 'assigned': assigned}

(SPLIT / 'ue-install-receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('TOOL_ENHANCE_PHASE2_PASS')
