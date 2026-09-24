"""Probe the wood voxel material graph (walks inputs from each material output)."""
import unreal as u

PAL = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
wood = next((e for e in PAL.get_editor_property('materials')
             if str(e.get_editor_property('id')) == 'wood'), None)
surf = wood.get_editor_property('surface')
mat = u.load_asset(str(surf.get_path_name()).split('.')[0])
print('CLASS', mat.get_class().get_name(), 'TWO_SIDED', mat.get_editor_property('two_sided'), flush=True)

def texline(tex):
    if tex is None:
        return 'None'
    size = ''
    for getter in ('get_imported_size_x', 'get_editor_property'):
        try:
            if getter == 'get_imported_size_x':
                size = ' %dx%d' % (tex.get_imported_size_x(), tex.get_imported_size_y())
            break
        except Exception:
            continue
    return '%s [%s srgb=%s%s]' % (tex.get_path_name(), tex.get_class().get_name(),
                                  tex.get_editor_property('srgb'), size)

try:
    used = u.MaterialEditingLibrary.get_material_used_textures(mat, True)
except TypeError:
    used = u.MaterialEditingLibrary.get_material_used_textures(mat)
for tex in used or []:
    print('USED_TEX', texline(tex), flush=True)

def describe(node):
    cls = node.get_class().get_name()
    bits = [cls]
    try:
        if isinstance(node, u.MaterialExpressionTextureSample):
            bits.append(texline(node.get_editor_property('texture')))
            bits.append(str(node.get_editor_property('sampler_type')))
    except Exception:
        pass
    try:
        if isinstance(node, u.MaterialExpressionTextureCoordinate):
            bits.append('tiling=%s,%s' % (node.get_editor_property('u_tiling'), node.get_editor_property('v_tiling')))
    except Exception:
        pass
    try:
        if isinstance(node, u.MaterialExpressionConstant):
            bits.append('r=%s' % node.get_editor_property('r'))
    except Exception:
        pass
    try:
        if isinstance(node, u.MaterialExpressionConstant3Vector):
            bits.append('color=%s' % node.get_editor_property('constant'))
    except Exception:
        pass
    try:
        if 'Parameter' in cls:
            bits.append('name=%s' % node.get_editor_property('name'))
            bits.append('default=%s' % node.get_editor_property('default_value'))
    except Exception:
        pass
    return ' '.join(str(b) for b in bits)

def walk(node, depth, seen):
    if node is None or depth > 4 or id(node) in seen:
        return
    seen.add(id(node))
    print('  ' * depth + describe(node), flush=True)
    try:
        ins = node.get_editor_property('inputs')
    except Exception:
        return
    for link in ins or []:
        try:
            src = link.get_editor_property('expression')
        except Exception:
            src = None
        if src is not None:
            walk(src, depth + 1, seen)

for p in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_EMISSIVE_COLOR', 'MP_OPACITY'):
    prop = getattr(u.MaterialProperty, p)
    node = u.MaterialEditingLibrary.get_material_property_input_node(mat, prop)
    print('OUTPUT', p, flush=True)
    walk(node, 1, set())
print('DUMP_DONE', flush=True)
