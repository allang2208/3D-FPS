"""倒树/断面/切面材质只读探针 II（2026-09-28）。

Material.expressions 在 python 里受保护，改走 MaterialEditingLibrary。
目的：
1. M_FallingPoplar 遮罩自定义节点的现行代码与输入脚名（为加径向裁剪做准备）；
2. M_FallingCutEnd / M_TreeCutSurface / M_PoplarEnd 使用的贴图（年轮贴图是否接线）与参数表。
只读：不修改、不保存任何资产。结果以 TREEPMAT 行打印（配 -abslog 收集）。
"""
import unreal as u

LIB = u.MaterialEditingLibrary
TAG = 'TREEPMAT'


def log(message):
    u.log('%s %s' % (TAG, message))
    print('%s %s' % (TAG, message))


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def describe(path):
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('MISSING %s' % path)
        return
    log('MAT %s class=%s' % (path, asset.get_class().get_name()))
    try:
        for texture in (LIB.get_material_used_textures(asset) or []):
            log('TEX %s %s' % (path, texture.get_path_name() if texture else '<none>'))
    except Exception as error:
        log('TEX_FAIL %s %s' % (path, error))
    try:
        nodes = LIB.get_material_expressions(asset) or []
    except Exception as error:
        log('EXPR_FAIL %s %s' % (path, error))
        return
    for node in nodes:
        cls = node.get_class().get_name()
        if cls == 'MaterialExpressionCustom':
            inputs = [str(prop(i, 'input_name', '?')) for i in (prop(node, 'inputs', None) or [])]
            log('CUSTOM %s desc=%s inputs=%s' % (path, prop(node, 'description', ''), inputs))
            log('CUSTOM_CODE %s %s' % (path, str(prop(node, 'code', '')).replace('\n', ' | ')))
        elif cls == 'MaterialExpressionScalarParameter':
            log('SPARAM %s %s default=%.2f' % (path, prop(node, 'parameter_name', '?'),
                                               float(prop(node, 'default_value', 0) or 0)))
        elif cls == 'MaterialExpressionVectorParameter':
            log('VPARAM %s %s' % (path, prop(node, 'parameter_name', '?')))
        elif cls == 'MaterialExpressionTextureSample':
            texture = prop(node, 'texture', None)
            log('TSAMPLE %s %s' % (path, texture.get_path_name() if texture else '<none>'))
        elif cls == 'MaterialExpressionMaterialFunctionCall':
            f = prop(node, 'material_function', None)
            log('MFUNC %s %s' % (path, f.get_path_name() if f else '<none>'))


for path in ('/Game/Items/HarvestTimber/M_FallingCutEnd',
             '/Game/Items/HarvestTimber/M_TreeCutSurface',
             '/Game/Items/HarvestTimber/M_PoplarEnd',
             '/Game/Items/HarvestTimber/M_FallingPoplar',
             '/Game/Items/HarvestTimber/MI_FallingPoplar_Bark',
             '/Game/Items/HarvestTimber/MI_FallingPoplar_Foliage'):
    try:
        describe(path)
    except Exception as error:
        log('STEP %s FAIL %s' % (path, error))

log('DONE')
