"""Read-only diagnosis of the reported G18 shell speckles and laser colour."""
import json
from pathlib import Path
import unreal as u

L = u.MaterialEditingLibrary
mesh = u.load_asset('/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_laser')
report = {'mesh': mesh.get_path_name(), 'sockets': {}, 'materials': [], 'live_effects': []}
for name in ['Emitter', 'AimGuide']:
    socket = mesh.find_socket(name)
    report['sockets'][name] = str(socket.relative_location) if socket else None
paths = []
for slot in mesh.static_materials:
    mat = slot.material_interface
    report['materials'].append({'slot': str(slot.material_slot_name), 'path': mat.get_path_name()})
    paths.append(mat.get_path_name())
paths += ['/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserBeam',
          '/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserDot']
report['graphs'] = {}
for path in paths:
    mat = u.load_asset(path)
    if not isinstance(mat, u.Material):
        report['graphs'][path] = {'class': mat.get_class().get_name(), 'parent': str(mat.get_editor_property('parent'))}
        continue
    nodes = []
    for node in L.get_material_expressions(mat):
        item = {'class': node.get_class().get_name(), 'name': node.get_name(), 'desc': str(node.get_editor_property('desc'))}
        for prop in ['code', 'parameter_name', 'default_value', 'constant', 'texture', 'coordinate_index', 'const_a', 'const_b']:
            try:
                item[prop] = str(node.get_editor_property(prop))
            except Exception:
                pass
        nodes.append(item)
    outputs = {}
    for name, prop in [('emissive', u.MaterialProperty.MP_EMISSIVE_COLOR), ('opacity', u.MaterialProperty.MP_OPACITY), ('base', u.MaterialProperty.MP_BASE_COLOR)]:
        node = L.get_material_property_input_node(mat, prop)
        outputs[name] = node.get_name() if node else None
    report['graphs'][path] = {'outputs': outputs, 'nodes': nodes}

for world in u.EditorLevelLibrary.get_pie_worlds(False):
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mats = [comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]
            if any(m and ('Laser' in m or 'laser' in m) for m in mats):
                report['live_effects'].append({'component': comp.get_path_name(), 'mesh': str(comp.static_mesh), 'visible': comp.is_visible(), 'materials': mats, 'scale': str(comp.get_world_scale())})
out = Path('D:/FPS3D/FPSGAME/Saved/BlessedLaser20261006/visual-diagnosis.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'report': str(out), 'materials': report['materials'], 'sockets': report['sockets'], 'live_effects': report['live_effects']}, ensure_ascii=False))
