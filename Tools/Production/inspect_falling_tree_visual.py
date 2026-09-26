"""树倒伏视觉只读体检（2026-09-25）。

排查"树倒了以后变成三角形碎片"：把倒树网格（Nanite 组合骨骼网格）、采集相关材质
（含淡出/切口/弯曲的实现节点）、落叶与破碎粒子用到的网格/材质、木材掉落网格全部读一遍，
只读不保存。用 UnrealEditor-Cmd -run=pythonscript 运行，结果以 FALLINGVIS 行打印。

配套：Tools/Production/run_falling_tree_visual_check.ps1
"""
import unreal as u

LIB = u.MaterialEditingLibrary
LINES = []


def emit(tag, **kw):
    parts = []
    for k in sorted(kw):
        parts.append('%s=%s' % (k, kw[k]))
    LINES.append('FALLINGVIS %s %s' % (tag, ' '.join(parts)))


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


def mat_info(m):
    d = {}
    if not m:
        return {'missing': True}
    d['class'] = m.get_class().get_name()
    # 使用标志决定材质能不能画在这种组件/网格上：站立树走 PCG 的实例化骨骼网格，
    # 倒树走普通骨骼网格 + Nanite 组合，缺任何一个标志都会退化成默认材质。
    for p in ('used_with_skeletal_mesh', 'used_with_instanced_skinned_mesh',
              'used_with_instanced_static_meshes', 'used_with_nanite',
              'used_with_mesh_deformer', 'used_with_niagara_mesh_particles',
              'two_sided', 'blend_mode', 'shading_model',
              'opacity_mask_clip_value', 'material_domain', 'dithered_lod_transition'):
        v = prop(m, p, '<n/a>')
        d[p] = str(v)
    parent = prop(m, 'parent', None)
    if parent:
        d['parent'] = path_of(parent)
        d['parent_class'] = parent.get_class().get_name()
        d['parent_skeletal'] = str(prop(parent, 'used_with_skeletal_mesh', '<n/a>'))
    for bucket, getter in (('scalars', 'scalar_parameter_values'),
                           ('vectors', 'vector_parameter_values'),
                           ('textures', 'texture_parameter_values')):
        try:
            items = m.get_editor_property(getter) or []
            out = {}
            for it in items:
                name = str(it.parameter_info.name)
                val = it.parameter_value
                if bucket == 'scalars':
                    out[name] = round(float(val), 3)
                elif bucket == 'vectors':
                    out[name] = str(val)
                else:
                    out[name] = path_of(val) if val else 'None'
            d[bucket] = out
        except Exception as e:
            d[bucket] = 'ERR %s' % e
        try:
            names = getattr(LIB, 'get_%s_names' % bucket[:-1])(m) or []
            d['declared_' + bucket] = sorted(str(x) for x in names)
        except Exception:
            pass
    # 静态开关是编译期决定的：叶片遮罩/双面/位移大多靠它，重挂父材质后最容易在这里错位。
    try:
        switches = LIB.get_static_switch_parameter_names(m) or []
        d['static_switches'] = {str(n): str(LIB.get_material_instance_static_switch_parameter_value(m, n))
                                for n in switches}
    except Exception:
        d['static_switches'] = 'ERR'
    # 实际生效值（父材质默认值 + 实例覆盖），用来和站立树的材质逐项对比。
    try:
        names = LIB.get_scalar_parameter_names(m) or []
        d['effective_scalars'] = {str(n): round(float(LIB.get_material_instance_scalar_parameter_value(m, n)), 4)
                                  for n in names}
    except Exception:
        d['effective_scalars'] = 'ERR'
    for p in ('MP_BASE_COLOR', 'MP_OPACITY_MASK', 'MP_OPACITY', 'MP_WORLD_POSITION_OFFSET',
              'MP_NORMAL', 'MP_EMISSIVE_COLOR'):
        try:
            node = LIB.get_material_property_input_node(m, getattr(u.MaterialProperty, p))
            d['in_' + p] = ('%s:%s' % (node.get_class().get_name(), node.get_name())) if node else None
        except Exception:
            pass
    try:
        used = LIB.get_material_used_textures(m) or []
        d['used_textures'] = sorted({path_of(t) for t in used if t})
    except Exception:
        pass
    return d


def dump_expressions(m, limit=90):
    try:
        nodes = LIB.get_material_expressions(m) or []
    except Exception as e:
        emit('EXPR_ERR', mat=path_of(m), err=str(e))
        return
    names = []
    for n in nodes[:limit]:
        cls = n.get_class().get_name()
        if cls == 'MaterialExpressionCustom':
            names.append('Custom:%s' % str(prop(n, 'code', ''))[:90].replace('\n', ' '))
        elif cls == 'MaterialExpressionMaterialFunctionCall':
            # 材质函数路径决定叶片遮罩/镂空来自哪里：站立树的叶片遮罩在被调用的函数里，
            # 倒树材质若调用了不同的函数，叶片就会退化成整块实心卡片。
            names.append('Function:%s' % (path_of(prop(n, 'material_function', None)) or '<none>'))
        else:
            names.append(cls)
    emit('EXPR', mat=path_of(m), count=len(nodes), nodes='|'.join(names))


def dump_parameters(m, limit=60):
    """材质参数名与当前值。基础材质要用 MaterialEditingLibrary 的按名读取（实例属性读不到，
    之前那版把 scalar_parameter_values 当通用属性读，报 'Failed to find property'）。"""
    for kind, list_name, read_name in (
            ('scalar', 'get_scalar_parameter_names', 'get_scalar_parameter_value'),
            ('vector', 'get_vector_parameter_names', 'get_vector_parameter_value'),
            ('texture', 'get_texture_parameter_names', None)):
        try:
            names = getattr(LIB, list_name)(m) or []
        except Exception as e:
            emit('PARAM_ERR', mat=path_of(m), kind=kind, err=str(e))
            continue
        values = []
        for name in list(names)[:limit]:
            if read_name:
                try:
                    values.append('%s=%s' % (name, getattr(LIB, read_name)(m, name)))
                except Exception:
                    values.append('%s=<err>' % name)
            else:
                values.append(str(name))
        emit('PARAM', mat=path_of(m), kind=kind, values='|'.join(values))


def mesh_info(path, dump_materials=True):
    a = u.load_asset(path)
    if not a:
        emit('MESH', path=path, exists=False)
        return None
    emit('MESH', path=path, exists=True, cls=a.get_class().get_name())
    skel = prop(a, 'skeleton', None)
    emit('MESH_SKEL', path=path, skeleton=path_of(skel))
    try:
        mats = a.get_editor_property('materials') or []
        for s in mats:
            slot = str(s.material_slot_name)
            mi = s.material_interface
            emit('MESH_SLOT', path=path, slot=slot, mat=path_of(mi))
            if dump_materials:
                info = mat_info(mi)
                emit('MESH_SLOT_INFO', path=path, slot=slot, info=info)
    except Exception as e:
        emit('MESH_SLOT_ERR', path=path, err=str(e))
    ns = prop(a, 'nanite_settings', None)
    if ns is None:
        emit('NANITE', path=path, settings='<none>')
    else:
        emit('NANITE', path=path, enabled=str(prop(ns, 'enabled', '<n/a>')),
             fallback_percent=str(prop(ns, 'fallback_percent_triangles', '<n/a>')),
             fallback_error=str(prop(ns, 'fallback_relative_error', '<n/a>')),
             position_precision=str(prop(ns, 'position_precision', '<n/a>')))
        ad = prop(ns, 'nanite_assembly_data', None)
        if ad is not None:
            try:
                parts = ad.get_editor_property('parts') or []
            except Exception as e:
                emit('ASSEMBLY_ERR', path=path, err=str(e))
                parts = None
            if parts is not None:
                emit('ASSEMBLY', path=path, parts=len(parts))
                for i, part in enumerate(parts):
                    # 子部件是受保护的组合节点：属性名逐个试，读到什么就报什么。
                    # 关键是每个部件的 material_index —— 它决定叶片部件用宿主网格的哪个槽。
                    try:
                        fields = {}
                        for name in ('mesh', 'material_index', 'material_slot', 'material',
                                     'bone_index', 'bone', 'node_index', 'transform',
                                     'weight', 'enabled', 'mesh_index'):
                            value = prop(part, name, None)
                            if value is None:
                                continue
                            fields[name] = path_of(value) if hasattr(value, 'get_path_name') else str(value)
                        emit('ASSEMBLY_PART', path=path, index=i, fields=fields or '<no readable fields>')
                    except Exception as e:
                        emit('ASSEMBLY_PART_ERR', path=path, index=i, err=str(e))
        else:
            emit('ASSEMBLY', path=path, parts='<no assembly data>')
    nv = '<n/a>'
    lod_count = '<n/a>'
    # 5.8 里骨骼网格的编辑器 API 挂在 SkeletalMeshEditorSubsystem 的**实例**上
    # （u.get_editor_subsystem(...)）；直接当静态类用会 AttributeError，本次踩过。
    try:
        sub = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        nv = sub.get_num_verts(a, 0)
        lod_count = sub.get_lod_count(a)
    except Exception:
        try:
            nv = u.EditorStaticMeshLibrary.get_num_vertices(a, 0)
            lod_count = u.EditorStaticMeshLibrary.get_lod_count(a)
        except Exception:
            pass
    b = prop(a, 'bounds', None)
    try:
        bounds = '%s / %s' % (b.origin, b.box_extent)
    except Exception:
        bounds = '<n/a>'
    # lod_count 是判据之一：倒树若还留着原树的经典 LOD，非 Nanite 路径就会画出未切的原树代理。
    emit('MESH_STATS', path=path, lod0_verts=nv, lod_count=lod_count, bounds=bounds)
    return a


# 'fast'：只查 A 变体 + 站立树基线 + 材质，编辑器内 120 秒超时内跑得完。
# 'full'：再查四个变体、落叶网格与粒子渲染器、木材掉落网格。
SCOPE = 'fast'

emit('BEGIN', project='FPSGAME', scope=SCOPE, note='read-only falling-tree visual inspection')

# 1) 倒树骨骼网格 vs 原树骨骼网格
if SCOPE == 'full':
    for kind in 'ABCD':
        mesh_info('/Game/Items/HarvestTimber/SK_CutUpper_%s' % kind)
        mesh_info('/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_%s' % kind, dump_materials=False)
else:
    mesh_info('/Game/Items/HarvestTimber/SK_CutUpper_A')
    mesh_info('/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_A', dump_materials=False)

# 2) 采集材质：切口/弯曲/淡出实现；站立树的基材与实例作为对照组。
EXPR_TARGETS = ('/Game/Items/HarvestTimber/M_CutUpperMotion',
                '/Game/WorldGeneration/TemperateHills/M_BlackPoplarPCG',
                '/Game/Items/HarvestTimber/M_FallingCutEnd')
for path in ('/Game/Items/HarvestTimber/M_CutUpperMotion',
             '/Game/Items/HarvestTimber/MI_CutUpper_Bark',
             '/Game/Items/HarvestTimber/MI_CutUpper_Foliage',
             '/Game/Items/HarvestTimber/M_FallingCutEnd',
             '/Game/Items/HarvestTimber/M_TreeCutSurface',
             '/Game/WorldGeneration/TemperateHills/M_BlackPoplarPCG',
             '/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_Bark',
             '/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_Foliage'):
    a = u.load_asset(path)
    emit('MAT', path=path, exists=bool(a), info=(mat_info(a) if a else None))
    if a and (SCOPE == 'full' or path in EXPR_TARGETS):
        dump_expressions(a)
        dump_parameters(a)

if SCOPE != 'full':
    emit('DONE', lines=len(LINES), skipped='leaf/fx/cascade/log sections')

if SCOPE == 'full':
    # 3) 落叶：网格与材质
    for leaf in ('SM_Leaf_01', 'SM_Leaf_02', 'SM_Leaf_03', 'SM_Twig_01', 'SM_Twig_02'):
        p = '/Game/RuralAustralia/Effects/FallingLeaves/Meshes/%s' % leaf
        mesh_info(p)

    # 4) 落叶 Niagara 的渲染器
    sys = u.load_asset('/Game/RuralAustralia/Effects/FallingLeaves/FX_FallingLeaves')
    emit('FX', path='FX_FallingLeaves', exists=bool(sys), cls=(sys.get_class().get_name() if sys else None))
    if sys:
        for hname in ('emitter_handles', 'emitters'):
            handles = prop(sys, hname, None)
            if handles is None:
                continue
            emit('FX_HANDLES', path='FX_FallingLeaves', prop=hname, count=len(handles))
            for i, h in enumerate(handles):
                em = prop(h, 'emitter', h)
                name = str(prop(h, 'name', ''))
                rends = prop(em, 'renderer_properties', None)
                emit('FX_EMITTER', index=i, name=name, cls=em.get_class().get_name(),
                     renderers=(len(rends) if rends is not None else '<n/a>'))
                for r in (rends or []):
                    info = {'cls': r.get_class().get_name()}
                    mats = prop(r, 'materials', None)
                    if mats is not None:
                        info['materials'] = [path_of(m) for m in mats]
                    meshes = prop(r, 'meshes', None)
                    if meshes is not None:
                        info['meshes'] = [path_of(prop(m, 'mesh', None)) for m in meshes]
                    info['mat'] = path_of(prop(r, 'material', None))
                    emit('FX_RENDERER', index=i, info=info)

    # 5) 木质破碎粒子与木材掉落
    ps = u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Wood')
    emit('CASCADE', path='P_Destruction_Wood', exists=bool(ps))
    if ps:
        for i, em in enumerate(prop(ps, 'emitters', None) or []):
            lods = prop(em, 'lod_levels', None) or []
            for j, lod in enumerate(lods):
                req = prop(lod, 'required_module', None)
                td = prop(lod, 'type_data', None)
                emit('CASCADE_LOD', index=i, lod=j,
                     material=path_of(prop(req, 'material', None)) if req else None,
                     type_data=(td.get_class().get_name() if td else None),
                     mesh=path_of(prop(td, 'mesh', None)) if td else None,
                     td_material=path_of(prop(td, 'material', None)) if td else None)
    mesh_info('/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A')
    emit('DONE', lines=len(LINES))

for line in LINES:
    u.log(line)
print('FALLINGVIS_TOTAL %d' % len(LINES))