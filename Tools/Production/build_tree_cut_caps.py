"""从重制网格 SM_CutUpper_<A..D> 里按材质提取切口封盖面，生成 SM_CutCap_<A..D>。

背景：倒树保底路径改用站立树原网格 + 材质 `step(H,P.z)` 遮罩切掉切口以下；原树干是空心筒，
断口会看到中空。重制网格 `SM_CutUpper_*` 的几何里本来带真实封盖（材质槽 `CutEndGrain`，
材质 `M_FallingCutEnd`，带切面烘焙 UV 与 `HarvestFade` 抖动淡出），这里把这部分三角形单独
提出来做成独立小网格，倒树时贴在切口平面上补上封盖。

只读源网格、只新建 `SM_CutCap_*`（已存在则覆盖），不修改其它资产。
"""
import unreal as u

TAG = 'CUTCAP'
DEST = '/Game/Items/HarvestTimber'
CUT_MATERIAL = '/Game/Items/HarvestTimber/M_FallingCutEnd'


def log(message):
    u.log('%s %s' % (TAG, message))
    print('%s %s' % (TAG, message))


def first_line(value):
    text = (getattr(value, '__doc__', '') or '').strip().split('\n')
    return text[0][:170] if text else ''


# 1) 先探明本版本真实可用的 API 与参数表（避免凭记忆写错签名）。
for module, names in ((u.GeometryScript_AssetUtils, ('copy_mesh_from_static_mesh',)),
                      (u.GeometryScript_Materials, ('get_triangle_material_id', 'delete_triangles_by_material_id',
                                                    'remap_material_i_ds')),
                      (u.GeometryScript_NewAssetUtils, ('create_new_static_mesh_asset_from_mesh',)),
                      (u.DynamicMesh, ('get_triangle_count',)),
                      (u.StaticMeshEditorSubsystem, ('set_material',))):
    for name in names:
        function = getattr(module, name, None)
        log('API %s.%s %s | %s' % (module.__name__, name, 'OK' if function else 'MISSING', first_line(function)))

cut_material = u.EditorAssetLibrary.load_asset(CUT_MATERIAL)
if not cut_material:
    raise RuntimeError('缺少切口材质 ' + CUT_MATERIAL)

results = {}
for kind in 'ABCD':
    source_path = '/Game/Items/HarvestTimber/SM_CutUpper_' + kind
    source = u.EditorAssetLibrary.load_asset(source_path)
    if not source:
        log('FAIL %s 源网格缺失' % kind)
        continue

    # 2) 找出切口材质所在槽号（模板网格槽名是 Bark / CutEndGrain）。
    slots = []
    try:
        for entry in source.get_editor_property('static_materials'):
            slots.append((str(entry.get_editor_property('material_slot_name')),
                          entry.get_editor_property('material_interface')))
    except Exception as error:
        log('WARN %s 读材质槽失败 %s' % (kind, error))
    log('%s slots=%s' % (kind, [(name, material.get_name() if material else None) for name, material in slots]))

    cut_id = -1
    for index, (name, material) in enumerate(slots):
        if (material and 'FallingCutEnd' in material.get_name()) or 'CutEnd' in name:
            cut_id = index
    if cut_id < 0 and len(slots) == 2:
        cut_id = 1
        log('WARN %s 未按名字识别出切口槽，按约定取槽 1' % kind)
    if cut_id < 0:
        log('FAIL %s 无法确定切口槽' % kind)
        continue

    # 3) 静态网格 → DynamicMesh（源模型 LOD）。
    read = u.GeometryScriptMeshReadLOD()
    read.lod_type = u.GeometryScriptLODType.SOURCE_MODEL
    dynamic = u.DynamicMesh()
    try:
        dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
            source, dynamic, u.GeometryScriptCopyMeshFromAssetOptions(), read)
    except Exception as error:
        log('FAIL %s 复制网格异常 %s' % (kind, error))
        continue
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        log('FAIL %s 复制网格结果 %s' % (kind, outcome))
        continue

    total = dynamic.get_triangle_count()
    counts = {}
    for triangle in range(total):
        material_id, valid = u.GeometryScript_Materials.get_triangle_material_id(dynamic, triangle)
        if valid:
            counts[material_id] = counts.get(material_id, 0) + 1
    log('%s tris=%d material_counts=%s cut_id=%d' % (kind, total, counts, cut_id))
    if not counts.get(cut_id, 0):
        log('FAIL %s 切口材质上没有三角形' % kind)
        continue

    # 4) 删掉切口以外的所有三角形，只留封盖。
    for material_id in sorted(counts):
        if material_id == cut_id:
            continue
        try:
            _, deleted = u.GeometryScript_Materials.delete_triangles_by_material_id(dynamic, material_id, True)
            log('%s 删除材质 %d 三角形 %s' % (kind, material_id, deleted))
        except Exception as error:
            log('WARN %s 删除材质 %d 异常 %s' % (kind, material_id, error))

    # 剩下的切口面统一归到槽 0，新资产就是单槽。
    if cut_id != 0:
        try:
            u.GeometryScript_Materials.remap_material_i_ds(dynamic, cut_id, 0)
        except Exception as error:
            log('WARN %s 材质号归一异常 %s' % (kind, error))

    cap_triangles = dynamic.get_triangle_count()
    if cap_triangles <= 0:
        log('FAIL %s 提取后没有三角形' % kind)
        continue

    # 5) 建成新静态网格资产（不要碰撞：纯装饰封盖）。
    create = u.GeometryScriptCreateNewStaticMeshAssetOptions()
    create.enable_collision = False
    asset, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        dynamic, DEST + '/SM_CutCap_' + kind, create)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS or not asset:
        log('FAIL %s 建资产失败 %s' % (kind, outcome))
        continue

    # 6) 槽位都指向切口材质（提取后三角形可能仍引用原槽号，两个槽都填最稳）。
    subsystem = None
    try:
        subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    except Exception as error:
        log('WARN %s 取 StaticMeshEditorSubsystem 异常 %s' % (kind, error))
    for slot_index in (0, 1):
        assigned = False
        if subsystem:
            try:
                subsystem.set_material(asset, slot_index, cut_material)
                assigned = True
            except Exception as error:
                log('WARN %s 子系统设置槽 %d 异常 %s' % (kind, slot_index, error))
        if not assigned:
            try:
                asset.set_material(slot_index, cut_material)
            except Exception as error:
                log('WARN %s 设置槽 %d 材质异常 %s' % (kind, slot_index, error))
    u.EditorAssetLibrary.save_loaded_asset(asset)

    bounds = asset.get_bounds()
    results[kind] = {'triangles': cap_triangles, 'asset': asset.get_path_name(),
                     'origin': [round(bounds.origin.x, 1), round(bounds.origin.y, 1), round(bounds.origin.z, 1)],
                     'extent': [round(bounds.box_extent.x, 1), round(bounds.box_extent.y, 1), round(bounds.box_extent.z, 1)]}
    log('%s DONE cap_tris=%d origin=%s extent=%s' % (kind, cap_triangles, results[kind]['origin'], results[kind]['extent']))

log('SUMMARY %s' % results)
log('CUTCAP_DONE %d/4' % len(results))