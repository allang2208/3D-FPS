"""M_CutUpperMotion 内壁舌头方位角掩码补丁 v2（活编辑器，2026-09-29）。

v1 教训：Custom 节点脚位名必须与代码引用一致（Z/Y/W），不能写成参数全名
（HarvestStubZMax→声明了却用 Z→undeclared identifier×24）。v2 负责把 v1 留下的
错名脚位就地改名（连线保留），或从干净状态完整重建。

掩码：S = step(60,P.z)*step(P.z,Z)*step(wrapDiffDeg(atan2(P.y,P.x),Y),W)*step(len(P.xy),31)
     O *= (1-S)     —— 60 以下不碰（年轮断面）；r<31 只切内壁舌头不伤外皮
默认 Z=W=0 ⇒ S≡0 全关。铁律：connect 查返回值、recompile 看错误数组、计数守卫、重载终验。
"""
import time

import unreal as u

EAL = u.EditorAssetLibrary
TAG = 'STUBPATCH'
MAT_PATH = '/Game/Items/HarvestTimber/M_CutUpperMotion'
EXPECT_BEFORE = 17   # 干净态（09-28 裁剪版）
EXPECT_AFTER = 20    # +3 个 ScalarParameter
BASE_PINS = ['O', 'P', 'H', 'F', 'R', 'T']
STUB_PINS = ['Z', 'Y', 'W']
NEW_PARAMS = [('HarvestStubZMax', 0.0), ('HarvestStubYaw', 0.0), ('HarvestStubYawTol', 0.0)]

ANCHOR = 'O*saturate(step(T,P.z)+step(length(P.xy),R))*step(frac('
MASK = ('O*saturate(step(T,P.z)+step(length(P.xy),R))*(1-step(60.0,P.z)*step(P.z,Z)'
        '*step(abs(frac((atan2(P.y,P.x)*57.29578-Y)/360.0+0.5)-0.5)*360.0,W)'
        '*step(length(P.xy),31.0))*step(frac(')


def log(m):
    u.log('%s %s' % (TAG, m))
    print('%s %s' % (TAG, m))


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


mat = None
for _try in range(6):
    mat = EAL.load_asset(MAT_PATH)
    if mat:
        break
    log('LOAD retry %d' % _try)
    time.sleep(8)
if not mat:
    log('FAIL load %s' % MAT_PATH)
    raise SystemExit(1)

exprs = u.MaterialEditingLibrary.get_material_expressions(mat)
log('EXPR_COUNT %d' % len(exprs))
if len(exprs) not in (EXPECT_BEFORE, EXPECT_AFTER):
    log('ABORT count %d not in (%d,%d)' % (len(exprs), EXPECT_BEFORE, EXPECT_AFTER))
    raise SystemExit(1)

mask_node = None
for e in exprs:
    if e.get_class().get_name() == 'MaterialExpressionCustom':
        code = str(prop(e, 'code', '') or '')
        if 'saturate(step(T,P.z)' in code:
            mask_node = e
            break
if mask_node is None:
    log('ABORT custom node not found')
    raise SystemExit(1)

code = str(prop(mask_node, 'code', '') or '')
inputs = list(prop(mask_node, 'inputs', []) or [])
names = [str(i.get_editor_property('input_name')) for i in inputs]
log('CUSTOM pins=%s masked_code=%s' % (names, '57.29578-Y' in code))

if '57.29578-Y' not in code:
    if ANCHOR not in code:
        log('ABORT anchor missing')
        raise SystemExit(1)
    mask_node.set_editor_property('code', code.replace(ANCHOR, MASK, 1))
    log('CODE patched')

# 脚位整形：前 6 个必须是 BASE_PINS；后缀必须是 Z/Y/W（把 v1 的 HarvestStub* 错名改过来）
if len(inputs) < 6 or names[:6] != BASE_PINS:
    log('ABORT base pins unexpected: %s' % names[:6])
    raise SystemExit(1)
changed = False
for idx, short in enumerate(STUB_PINS):
    want = short
    if len(inputs) < 7 + idx:
        entry = u.CustomInput()
        entry.set_editor_property('input_name', want)
        inputs.append(entry)
        changed = True
    else:
        cur = str(inputs[6 + idx].get_editor_property('input_name'))
        if cur != want:
            inputs[6 + idx].set_editor_property('input_name', want)
            changed = True
if len(inputs) > 9:
    log('ABORT too many pins %d' % len(inputs))
    raise SystemExit(1)
if changed:
    mask_node.set_editor_property('inputs', inputs)
log('PINS ok')

# 参数（幂等）
param_for = {}
for e in u.MaterialEditingLibrary.get_material_expressions(mat):
    if e.get_class().get_name() == 'MaterialExpressionScalarParameter':
        pn = str(prop(e, 'parameter_name', '') or '')
        if pn in dict(NEW_PARAMS):
            param_for[pn] = e
for name, default in NEW_PARAMS:
    if name in param_for:
        continue
    node = u.MaterialEditingLibrary.create_material_expression(
        mat, u.MaterialExpressionScalarParameter, -300, -800 + len(param_for) * 150)
    if not node:
        log('ABORT create param %s' % name)
        raise SystemExit(1)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', default)
    param_for[name] = node
log('PARAMS ok')

# 连线（重复连接幂等无害）
for (pname, _), pin in zip(NEW_PARAMS, STUB_PINS):
    res = u.MaterialEditingLibrary.connect_material_expressions(param_for[pname], '', mask_node, pin)
    log('CONNECT %s->%s=%s' % (pname, pin, bool(res)))
    if not res:
        log('ABORT connect')
        raise SystemExit(1)

errors = u.MaterialEditingLibrary.recompile_material(mat)
log('RECOMPILE errors=%d' % len(errors))
if len(errors) != 0:
    log('FIRST_ERR %s' % str(list(errors)[:1])[:400])
    raise SystemExit(1)
count2 = len(u.MaterialEditingLibrary.get_material_expressions(mat))
log('EXPR_COUNT_AFTER %d' % count2)
if count2 != EXPECT_AFTER:
    log('ABORT count after %d != %d' % (count2, EXPECT_AFTER))
    raise SystemExit(1)
if not EAL.save_loaded_asset(mat, False):
    log('ABORT save')
    raise SystemExit(1)

EAL.unload_loaded_asset(mat)
mat2 = EAL.load_asset(MAT_PATH)
ok = False
pins2 = []
for e in u.MaterialEditingLibrary.get_material_expressions(mat2):
    if e.get_class().get_name() == 'MaterialExpressionCustom':
        c = str(prop(e, 'code', '') or '')
        if '57.29578-Y' in c:
            pins2 = [str(i.get_editor_property('input_name')) for i in (prop(e, 'inputs', []) or [])]
            ok = 'Z' in pins2 and 'Y' in pins2 and 'W' in pins2
log('VERIFY reload code=%s pins=%s count=%d' % (ok, pins2, len(u.MaterialEditingLibrary.get_material_expressions(mat2))))
if not ok:
    log('ABORT verify')
    raise SystemExit(1)
log('DONE')
