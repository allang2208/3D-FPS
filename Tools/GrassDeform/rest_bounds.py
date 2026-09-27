"""Bake rest-mesh bounds into grass material instances, outside the frame path.

Renderer InstanceLocalBounds includes WPO padding. It must never determine the
lever arm used to clamp the same WPO. Union bounds for shared materials, so every
blade has one conservative rotation limit and its triangles stay rigid.
"""
import unreal as u

MESH_FOLDERS = ('/Game/PN_GrassLibrary/Meshes/grassMesh',
                '/Game/WorldGeneration/TemperateHills/Grass')
PARAM_MIN, PARAM_MAX = 'GrassRestBoundsMin', 'GrassRestBoundsMax'


def collect(masters, folders=MESH_FOLDERS):
    groups = {}
    for folder in folders:
        for path in u.EditorAssetLibrary.list_assets(folder, True, False):
            data = u.EditorAssetLibrary.find_asset_data(path)
            if str(data.asset_class_path.asset_name) != 'StaticMesh':
                continue
            mesh = u.load_asset(path)
            box = mesh.get_bounding_box()
            lo, hi = [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z]
            for slot in mesh.static_materials:
                material = slot.material_interface
                if not isinstance(material, u.MaterialInstanceConstant):
                    continue
                parent = material
                while isinstance(parent, u.MaterialInstance):
                    parent = parent.get_editor_property('parent')
                if not parent or parent.get_path_name().split('.')[0] not in masters:
                    continue
                key = material.get_path_name()
                group = groups.setdefault(key, {'material': material, 'min': list(lo), 'max': list(hi), 'meshes': []})
                group['min'] = [min(a,b) for a,b in zip(group['min'],lo)]
                group['max'] = [max(a,b) for a,b in zip(group['max'],hi)]
                group['meshes'].append(mesh.get_path_name())
    if not groups:
        raise RuntimeError('No grass mesh/material pairs for rest bounds authoring')
    return groups


def author(groups, save):
    report = {}
    for path, group in groups.items():
        material = group['material']
        for name, value in ((PARAM_MIN, group['min']), (PARAM_MAX, group['max'])):
            # UE 5.8's setter applies the value but always returns false (the
            # engine implementation never sets bResult). Read the authored value.
            u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                material, name, u.LinearColor(*value, 0))
            stored = u.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material, name)
            if any(abs(a-b) > 0.001 for a,b in zip((stored.r,stored.g,stored.b),value)):
                raise RuntimeError('Cannot author ' + name + ' on ' + path)
        save(material)
        report[path] = {k:v for k,v in group.items() if k != 'material'}
    return report
