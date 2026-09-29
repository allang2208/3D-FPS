"""活编辑器内：M_CutUpperMotion 板根径向裁剪补丁（2026-09-29，几何截断路径配套）。

背景：默认倒树改走 SK_CutUpper_*（几何真切断）后，42–85cm 板根裙边仍在（同源几何）；
给几何路径的材质 M_CutUpperMotion 的淡出遮罩节点加与 M_FallingPoplar 同式的径向裁剪。
程序（每一步都硬校验，任何异常立即中止且不保存）：
  1. 定位遮罩节点（inputs=[O,P,H,F]、代码含淡出噪声，非 Bend 节点）；
  2. 幂等检查（已打补丁则只核对）；
  3. 改代码 + 增 R/T 输入脚 + 建两个标量参数（默认 1e5/0＝不裁）；
  4. connect 必须返回 True，recompile 返回的错误数组必须为空；
  5. 表达式计数守卫（原 15 → 17；空图损坏会在计数上暴露）；
  6. 全部通过才保存，保存后重载终验。
备份：trash/treefall-restore-20260928/M_CutUpperMotion.uasset.bak（SHA c2f06285…）。
"""
import unreal as u

LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TAG = 'CUTPATCH'
PATH = '/Game/Items/HarvestTimber/M_CutUpperMotion'
OLD = 'O*step(frac('
NEW = 'O*saturate(step(T,P.z)+step(length(P.xy),R))*step(frac('


def log(m):
    u.log('%s %s' % (TAG, m))
    print('%s %s' % (TAG, m))


def prop(o, n, d=None):
    try:
        return o.get_editor_property(n)
    except Exception:
        return d


def abort(reason):
    log('ABORT %s — 未保存，原资产未动' % reason)
    raise SystemExit(1)


mat = EAL.load_asset(PATH)
if not mat:
    abort('load failed')
nodes = LIB.get_material_expressions(mat) or []
count_before = len(nodes)
mask_node = None
for node in nodes:
    if node.get_class().get_name() != 'MaterialExpressionCustom':
        continue
    inputs = [str(prop(i, 'input_name', '?')) for i in (prop(node, 'inputs', None) or [])]
    code = str(prop(node, 'code', '') or '')
    if 'R' in inputs and 'T' in inputs:
        log('ALREADY inputs=%s' % inputs)
        log('ALREADY_CODE %s' % code.replace('\n', ' '))
        raise SystemExit(0)
    if inputs == ['O', 'P', 'H', 'F'] and OLD in code:
        mask_node = node
if mask_node is None:
    abort('mask node not found')

code = str(prop(mask_node, 'code', '') or '')
new_code = code.replace(OLD, NEW, 1)
mask_node.set_editor_property('code', new_code)

inputs = list(prop(mask_node, 'inputs', None) or [])
for name in ('R', 'T'):
    entry = u.CustomInput()
    entry.set_editor_property('input_name', name)
    inputs.append(entry)
mask_node.set_editor_property('inputs', inputs)

x = int(prop(mask_node, 'editor_x', 0) or 0)
y = int(prop(mask_node, 'editor_y', 0) or 0)
existing = {}
for node in nodes:
    if node.get_class().get_name() == 'MaterialExpressionScalarParameter':
        existing[str(prop(node, 'parameter_name', ''))] = node
created = {}
for name, default in (('HarvestCutRadius', 100000.0), ('HarvestFlareTop', 0.0)):
    if name in existing:
        created[name] = existing[name]
        continue
    node = LIB.create_material_expression(mat, u.MaterialExpressionScalarParameter, x - 300, y + 220 + len(created) * 150)
    if not node:
        abort('create param %s failed' % name)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', default)
    created[name] = node

for pin, param_name in (('R', 'HarvestCutRadius'), ('T', 'HarvestFlareTop')):
    ok = bool(LIB.connect_material_expressions(created[param_name], '', mask_node, pin))
    log('CONNECT %s returns=%s' % (pin, ok))
    if not ok:
        abort('connect %s failed' % pin)

errors = LIB.recompile_material(mat)
log('RECOMPILE errors=%d %s' % (len(errors), list(errors)[:3]))
if errors:
    abort('compile errors')

check = LIB.get_material_expressions(mat) or []
if not (count_before + 1 <= len(check) <= count_before + 3):
    abort('expression count guard: before=%d after=%d' % (count_before, len(check)))
mask2 = None
for node in check:
    if node.get_class().get_name() == 'MaterialExpressionCustom':
        c2 = str(prop(node, 'code', '') or '')
        i2 = [str(prop(i, 'input_name', '?')) for i in (prop(node, 'inputs', None) or [])]
        if 'saturate(step(T,P.z)' in c2 and 'R' in i2 and 'T' in i2:
            mask2 = node
if mask2 is None:
    abort('post-edit verify: patched node not found')

saved = EAL.save_loaded_asset(mat, False)
log('SAVED %s' % bool(saved))
if not saved:
    abort('save returned false')

# 保存后重载终验（防“空图保存”类损坏落盘）。
reloaded = EAL.load_asset(PATH)
final = LIB.get_material_expressions(reloaded) or []
ok_final = any(
    n.get_class().get_name() == 'MaterialExpressionCustom' and 'saturate(step(T,P.z)' in str(prop(n, 'code', '') or '')
    for n in final)
log('FINAL expr=%d patched=%s' % (len(final), ok_final))
if not ok_final or len(final) < count_before:
    abort('final reload verify failed')
log('DONE')
