"""树木板根剖面与断面材质只读探针（2026-09-28）。

背景：用户反馈砍树三问题——倒树底部未用年轮封死 / 树皮(板根)过于延展 / 整树倒伏不截断。
恢复"42cm 截断 + 封盖"前需要两组数值：
1. SM_CutUpper_*（=原树 42cm 以上的主干几何）的径向剖面：每个高度带的最大水平半径，
   找出板根收拢到树干半径的高度（FlareTop）——材质径向裁剪只在该高度带内生效；
2. SM_CutCap_* 的精确包围半径——裁剪半径必须 ≤ 封盖半径，断口才能被盖住。
另核对 M_FallingCutEnd / M_TreeCutSurface / M_PoplarEnd 采样的贴图（年轮贴图是否接线）
与 M_FallingPoplar 遮罩自定义节点的现行代码与输入脚名（为加径向裁剪做准备）。

只读：不修改、不保存任何资产。结果以 TREEPROBE 行打印（配 -abslog 收集）。
"""
import unreal as u

TAG = 'TREEPROBE'
BAND = 10.0  # cm/带


def log(message):
    u.log('%s %s' % (TAG, message))
    print('%s %s' % (TAG, message))


def dump_api():
    """5.8 python 绑定的 GeometryScript API 名单（本轮 get_all_vertex_ids 不存在，先自省再选路）。"""
    for owner in (u.GeometryScript_MeshQueries, u.DynamicMesh):
        names = [n for n in dir(owner) if 'vertex' in n.lower() or 'triangle' in n.lower()]
        log('API %s %s' % (owner.__name__, sorted(names)))


def band_profile(kind):
    """SM_CutUpper_<kind> SOURCE_MODEL 顶点 → 高度带最大水平半径表。"""
    path = '/Game/Items/HarvestTimber/SM_CutUpper_' + kind
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('CUTUPPER %s MISSING %s' % (kind, path))
        return
    read = u.GeometryScriptMeshReadLOD()
    read.lod_type = u.GeometryScriptLODType.SOURCE_MODEL
    dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        log('CUTUPPER %s COPY_FAIL %s' % (kind, outcome))
        return
    queries = u.GeometryScript_MeshQueries
    positions = []
    try:
        # 5.8 绑定返回 (DynamicMesh, GeometryScriptVectorList)，向量在 vectors 属性。
        raw = queries.get_all_vertex_positions(dynamic, False)
        for part in raw:
            if part.__class__.__name__ == 'GeometryScriptVectorList':
                length = part.get_vector_list_length()
                for index in range(length):
                    item = part.get_vector_list_item(index)
                    p = item[0] if isinstance(item, tuple) else item
                    positions.append((p.x, p.y, p.z))
                break
    except Exception as error:
        log('CUTUPPER %s TRI_API_FAIL %s' % (kind, error))
        return
    if not positions:
        log('CUTUPPER %s NO_POSITIONS' % kind)
        return
    bands = {}
    max_z = max(p[2] for p in positions)
    min_z = min(p[2] for p in positions)
    for x, y, z in positions:
        radius = (x * x + y * y) ** 0.5
        key = int(z // BAND)
        if radius > bands.get(key, -1.0):
            bands[key] = radius
    log('CUTUPPER %s verts=%d z=[%.1f,%.1f]' % (kind, len(positions), min_z, max_z))
    for key in sorted(bands):
        log('BAND %s z=%d..%d max_radius=%.1f' % (kind, key * int(BAND), (key + 1) * int(BAND), bands[key]))


def cap_bounds(kind):
    path = '/Game/Items/HarvestTimber/SM_CutCap_' + kind
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('CAP %s MISSING' % kind)
        return
    bounds = asset.get_bounds()
    log('CAP %s origin_z=%.2f half_extent_xy=%.2f,%.2f diameter_xy=%.2f,%.2f' % (
        kind, bounds.origin.z, bounds.box_extent.x, bounds.box_extent.y,
        bounds.box_extent.x * 2, bounds.box_extent.y * 2))


def rim_profile(kind):
    path = '/Game/Items/HarvestTimber/DA_TreeCut_' + kind
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('RIM %s MISSING' % kind)
        return
    rim = asset.get_editor_property('rim')
    if not rim:
        log('RIM %s EMPTY' % kind)
        return
    radii = [(p.x * p.x + p.y * p.y) ** 0.5 for p in rim]
    log('RIM %s points=%d max_radius=%.2f min_radius=%.2f' % (
        kind, len(radii), max(radii), min(radii)))


def describe_material(path):
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('MAT %s MISSING' % path)
        return
    log('MAT %s class=%s' % (path, asset.get_class().get_name()))
    try:
        expressions = asset.get_editor_property('expressions')
    except Exception as error:
        log('MAT %s EXPR_FAIL %s' % (path, error))
        return
    for expr in expressions:
        cls = expr.get_class().get_name()
        try:
            if cls == 'MaterialExpressionTextureSample':
                texture = expr.get_editor_property('texture')
                log('TEX %s -> %s' % (path, texture.get_path_name() if texture else '<none>'))
            elif cls == 'MaterialExpressionScalarParameter':
                log('SPARAM %s %s default=%.2f' % (
                    path, expr.get_editor_property('parameter_name'), expr.get_editor_property('default_value')))
            elif cls == 'MaterialExpressionVectorParameter':
                log('VPARAM %s %s' % (path, expr.get_editor_property('parameter_name')))
            elif cls == 'MaterialExpressionCustom':
                code = expr.get_editor_property('code').replace('\n', ' | ')
                inputs = [str(i.get_editor_property('input_name')) for i in expr.get_editor_property('inputs')]
                log('CUSTOM %s desc=%s inputs=%s' % (path, expr.get_editor_property('description'), inputs))
                log('CUSTOM_CODE %s %s' % (path, code))
            elif cls == 'MaterialExpressionMaterialFunctionCall':
                f = expr.get_editor_property('material_function')
                log('MFUNC %s -> %s' % (path, f.get_path_name() if f else '<none>'))
        except Exception as error:
            log('EXPR %s %s READ_FAIL %s' % (path, cls, error))


dump_api()
for kind in 'ABCD':
    for fn in (band_profile, cap_bounds, rim_profile):
        try:
            fn(kind)
        except Exception as error:
            log('STEP %s %s FAIL %s' % (fn.__name__, kind, error))

log('— 断面/切面材质接线 —')
for path in ('/Game/Items/HarvestTimber/M_FallingCutEnd',
             '/Game/Items/HarvestTimber/M_TreeCutSurface',
             '/Game/Items/HarvestTimber/M_PoplarEnd',
             '/Game/Items/HarvestTimber/M_FallingPoplar'):
    try:
        describe_material(path)
    except Exception as error:
        log('MATSTEP %s FAIL %s' % (path, error))

log('DONE')
