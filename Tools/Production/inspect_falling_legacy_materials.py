"""上一代倒树（原树网格 + 材质裁切）材质只读体检（2026-09-26）。

背景：2026-09-25 用户报告"树倒了以后变成三角形碎片"。体检已排除材质与组合部件数量问题
（SourceAssets/HarvestTimber20260913 重制的 SK_CutUpper_* 组合部件 13/13 与源树一致、
材质函数与实例参数与站立树相同），剩下的嫌疑是重制网格的 Nanite 组合节点/骨骼数据。
保底方案是回到上一代做法：**用原树网格做倒下的上半段**（站立树已验证渲染正常），
切口靠材质遮罩裁掉切口以下——本脚本就是确认那套材质还在、遮罩与参数是否可用。

只读：不保存任何资产。用 UnrealEditor-Cmd -run=pythonscript 运行，结果以 FALLVIS2 行打印。
注意：python 的 u.log()/print() 只写引擎日志文件，要配 -abslog 才能收集（2026-09-26 实测）。
"""
import unreal as u

LIB = u.MaterialEditingLibrary
LINES = []

FLAGS = ('used_with_skeletal_mesh', 'used_with_instanced_skinned_mesh',
         'used_with_instanced_static_meshes', 'used_with_nanite', 'two_sided',
         'blend_mode', 'dithered_lod_transition', 'opacity_mask_clip_value')


def emit(tag, **kw):
    LINES.append('FALLVIS2 %s %s' % (tag, ' '.join('%s=%s' % (k, kw[k]) for k in sorted(kw))))


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def path_of(obj):
    try:
        return obj.get_path_name() if obj else None
    except Exception:
        return '<unreadable>'


TARGETS = ('/Game/Items/HarvestTimber/M_FallingPoplar',
           '/Game/Items/HarvestTimber/MI_FallingPoplar_Bark',
           '/Game/Items/HarvestTimber/MI_FallingPoplar_Foliage',
           '/Game/Items/HarvestTimber/M_PoplarEnd')

for path in TARGETS:
    asset = u.load_asset(path)
    if not asset:
        emit('MISSING', path=path)
        continue
    emit('ASSET', path=path, cls=asset.get_class().get_name())
    flags = {name: str(prop(asset, name, '<n/a>')) for name in FLAGS}
    parent = prop(asset, 'parent', None)
    emit('FLAGS', path=path, parent=path_of(parent), **flags)
    # 参数：实例上 scalar/vector/texture_parameter_values 可能是 dict，也可能是 struct 数组
    # （2026-09-26 实测：基础材质上取到的是 Array，直接 .items() 会 AttributeError 中断整轮）。
    for getter in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values'):
        try:
            values = asset.get_editor_property(getter)
        except Exception:
            continue
        if not values:
            continue
        pairs = {}
        if hasattr(values, 'items'):
            pairs = {str(k): str(v)[:80] for k, v in values.items()}
        else:
            for item in values:
                name = prop(item, 'parameter_info', None)
                if name is None:
                    name = prop(item, 'name', None)
                value = prop(item, 'parameter_value', item)
                pairs[str(name)] = str(value)[:80]
        if pairs:
            emit('VALUES', path=path, kind=getter.replace('_parameter_values', ''), values=pairs)
    try:
        switches = LIB.get_static_switch_parameter_names(asset) or []
        names = []
        for name in switches:
            try:
                names.append('%s=%s' % (name, LIB.get_static_switch_parameter_value(asset, name)))
            except Exception:
                names.append(str(name))
        if names:
            emit('SWITCHES', path=path, values='|'.join(names))
    except Exception as exc:
        emit('SWITCHES_ERR', path=path, err=str(exc))
    # 表达式图：确认是否带"切口以下隐藏"的遮罩（上一代做法）与弯曲/淡出自定义节点。
    try:
        nodes = LIB.get_material_expressions(asset) or []
    except Exception as exc:
        emit('EXPR_ERR', path=path, err=str(exc))
        nodes = []
    names = []
    for node in nodes:
        cls = node.get_class().get_name()
        if cls == 'MaterialExpressionCustom':
            names.append('Custom:%s' % str(prop(node, 'code', ''))[:110].replace('\n', ' '))
        elif cls == 'MaterialExpressionMaterialFunctionCall':
            names.append('Function:%s' % (path_of(prop(node, 'material_function', None)) or '<none>'))
        elif cls == 'MaterialExpressionScalarParameter':
            names.append('Scalar:%s' % prop(node, 'parameter_name', '?'))
        elif cls == 'MaterialExpressionVectorParameter':
            names.append('Vector:%s' % prop(node, 'parameter_name', '?'))
        elif cls == 'MaterialExpressionStaticSwitchParameter':
            names.append('Switch:%s' % prop(node, 'parameter_name', '?'))
        else:
            names.append(cls)
    emit('EXPR', path=path, count=len(nodes), nodes='|'.join(names))
    try:
        used = LIB.get_material_used_textures(asset) or []
        emit('TEXTURES', path=path, values='|'.join(sorted({path_of(t) for t in used if t})))
    except Exception:
        pass

emit('DONE', lines=len(LINES))
for line in LINES:
    u.log(line)
print('FALLVIS2_TOTAL %d' % len(LINES))