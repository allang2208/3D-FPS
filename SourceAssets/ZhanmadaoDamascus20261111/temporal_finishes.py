"""Restore the normal steel finishes below the existing whirlwind Damascus and rune layers."""
import unreal as u

L = u.MaterialEditingLibrary
COMMON = 'SharedTwoHandFinish20261101V1 '
DAMASCUS = 'ZhanmadaoDamascus20261111V2 '
FIELDS = ('BASE_COLOR', 'ROUGHNESS', 'NORMAL', 'METALLIC', 'ANISOTROPY', 'TANGENT')


def inputs(material, node):
    return dict(zip(map(str, L.get_material_expression_input_names(node)),
                    L.get_inputs_for_material_expression(material, node)))


def channel(node, upstream):
    return str(L.get_input_node_output_name_for_material_expression(node, upstream) or '')


def restore(material):
    path = material.get_path_name().split('.')[0]
    if '/BeiweiRuneV1/' not in path or not path.endswith('_Whirlwind'):
        return False
    normal = u.load_asset(path.removesuffix('_Whirlwind'))
    if not normal:
        raise RuntimeError('Missing paired steel material: ' + path)
    def labelled(mat):
        return {str(n.get_editor_property('desc')): n for n in L.get_material_expressions(mat)
                if isinstance(n, u.MaterialExpressionCustom)}
    src, dest = labelled(normal), labelled(material)
    mask_node = dest[DAMASCUS+'steel response']
    mask = inputs(material, mask_node)['Mask']
    copied = {}

    def connect(upstream, output, target, pin):
        if not L.connect_material_expressions(upstream, output, target, pin):
            raise RuntimeError(f'{path}: cannot connect {target.get_name()}.{pin}')

    def copy_node(node):
        if node not in copied:
            copy = L.duplicate_material_expression(material, None, node)
            copied[node] = copy
            for pin, upstream in inputs(normal, node).items():
                if upstream:
                    connect(copy_node(upstream), channel(node, upstream), copy, pin)
        return copied[node]

    changed = False
    for field in FIELDS:
        name = COMMON+field
        outer = dest[DAMASCUS+field]
        old = inputs(material, outer)
        if old['Base'].get_editor_property('desc') == name:
            continue
        donor = src[name]
        restored = L.duplicate_material_expression(material, None, donor)
        # The temporal variant owns its native surface, metal channels and decorative mask.
        local = {'Base': (old['Base'], channel(outer, old['Base'])),
                 'Mode': (old['Mode'], ''), 'Mask': (mask, channel(mask_node, mask))}
        for pin, upstream in inputs(normal, donor).items():
            if upstream:
                if pin in local:
                    value, output = local[pin]
                else:
                    value, output = copy_node(upstream), channel(donor, upstream)
                connect(value, output, restored, pin)
        connect(restored, '', outer, 'Base')
        changed = True
    return changed
