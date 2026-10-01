"""Capture live SVD material production inputs, without edits or runtime tests."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L = u.MaterialEditingLibrary
out = O / 'Input'
out.mkdir(parents=True, exist_ok=True)
if (out / 'current.json').exists():
    raise RuntimeError('Preserve the captured production baseline')
prior = json.loads((O.parent / 'Refine03/Input/materials.json').read_text())
result = {'meshes': {}, 'materials': {}, 'graphs': {}, 'tested': False}
for key, row in prior.items():
    mesh = u.load_asset(row['path'])
    if not mesh:
        raise RuntimeError('Missing production mesh ' + row['path'])
    skeletal = isinstance(mesh, u.SkeletalMesh)
    slots = mesh.get_editor_property('materials' if skeletal else 'static_materials')
    result['meshes'][key] = {'path': mesh.get_path_name(), 'skeletal': skeletal, 'slots': []}
    for slot in slots:
        mat = slot.material_interface
        mp = mat.get_path_name() if mat else None
        result['meshes'][key]['slots'].append({'slot': str(slot.material_slot_name), 'material': mp})
        if not mp or mp in result['materials'] or '/SVDDragunov20260922/' not in mp:
            continue
        base = mat.get_base_material()
        bp = base.get_path_name()
        if bp not in result['graphs']:
            nodes = []
            for n in L.get_material_expressions(base):
                props = {'type': type(n).__name__, 'name': n.get_name()}
                if isinstance(n, u.MaterialExpressionCustom):
                    props.update(description=str(n.get_editor_property('description')), code=str(n.get_editor_property('code')),
                        inputs=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')])
                if isinstance(n, u.MaterialExpressionConstant):
                    props['value'] = n.get_editor_property('r')
                if isinstance(n, u.MaterialExpressionConstant3Vector):
                    v = n.get_editor_property('constant')
                    props['value'] = [v.r, v.g, v.b, v.a]
                nodes.append(props)
            result['graphs'][bp] = {'nodes': nodes, 'blend': str(base.blend_mode)}
        parameters = {}
        for kind in ('scalar', 'vector', 'texture', 'static_switch'):
            parameters[kind] = {}
            for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
                fn = 'get_material_instance_' if isinstance(mat, u.MaterialInstanceConstant) else 'get_material_default_'
                value = getattr(L, fn + kind + '_parameter_value')(mat, name)
                parameters[kind][str(name)] = (value.get_path_name() if value else None) if kind == 'texture' else ([value.r, value.g, value.b, value.a] if kind == 'vector' else value)
        disk = P / 'Content' / (mp.split('.')[0].removeprefix('/Game/') + '.uasset')
        result['materials'][mp] = {'parent': mat.get_editor_property('parent').get_path_name() if isinstance(mat, u.MaterialInstanceConstant) else None,
            'base': bp, 'class': type(mat).__name__, 'sha256': hashlib.sha256(disk.read_bytes()).hexdigest(), 'parameters': parameters}
wet = u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials')
result['wet_materials'] = {str(k): v.get_path_name() if v else None for k, v in wet.get_editor_property('wet_materials').items()}
(out / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_SVD_R04_INPUTS', len(result['materials']), len(result['meshes']), flush=True)
