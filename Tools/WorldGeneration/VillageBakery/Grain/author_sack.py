"""Adapt the village's existing single Quixel canvas bag to unbleached flour cloth."""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[4]
DEST = '/Game/WorldGeneration/TemperateHills/VillageBakery/Grain'
SOURCE_NAME = 'Mil_Trench_Equipment_Sandbag_Canvas_Single'
SOURCE = '/Game/MilitaryTrench/Assets/3D/' + SOURCE_NAME
E, M = u.EditorAssetLibrary, u.MaterialEditingLibrary
E.make_directory(DEST)


def require(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing asset ' + path)
    return obj


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save ' + obj.get_path_name())


def link(source, output, dest, pin):
    if not M.connect_material_expressions(source, output, dest, pin):
        raise RuntimeError(f'Could not connect {source} to {dest} {pin}')


def expression(node_type, **values):
    node = M.create_material_expression(mat, node_type)
    for key, value in values.items():
        node.set_editor_property(key, value)
    return node


def texture(suffix):
    tex = require(f'{SOURCE}/Textures/T_{SOURCE_NAME}_{suffix}')
    # Setting Texture through the editor property API chooses its actual sample type,
    # including virtual or linear packed channels, from the scan's import settings.
    return expression(u.MaterialExpressionTextureSample, texture=tex)


def feed(source, output, prop):
    if not M.connect_material_property(source, output, prop):
        raise RuntimeError('Could not bind cloth channel ' + str(prop))


mat_path = DEST + '/M_BakeryFlourCanvas'
mat = (require(mat_path) if E.does_asset_exist(mat_path) else
       u.AssetToolsHelpers.get_asset_tools().create_asset('M_BakeryFlourCanvas', DEST,
                                                         u.Material, u.MaterialFactoryNew()))
M.delete_all_material_expressions(mat)
mat.set_editor_property('used_with_instanced_static_meshes', True)
base, normal, packed = texture('B'), texture('N'), texture('ORM')
# Lift the olive-brown donor's luminance to raw undyed flax. The original weave,
# wrinkles, seam shading and locally uneven roughness remain in the scanned maps.
mono = expression(u.MaterialExpressionDesaturation)
link(base, 'RGB', mono, '')
link(expression(u.MaterialExpressionConstant, r=1.0), '', mono, 'Fraction')
lift = expression(u.MaterialExpressionPower, const_exponent=0.70)
link(mono, '', lift, 'Base')
unbleached = expression(u.MaterialExpressionMultiply)
link(lift, '', unbleached, 'A')
link(expression(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(1.14, .99, .74, 1)),
     '', unbleached, 'B')
feed(unbleached, '', u.MaterialProperty.MP_BASE_COLOR)
feed(normal, 'RGB', u.MaterialProperty.MP_NORMAL)
feed(packed, 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
feed(packed, 'G', u.MaterialProperty.MP_ROUGHNESS)
feed(expression(u.MaterialExpressionConstant, r=.27), '', u.MaterialProperty.MP_SPECULAR)
M.layout_material_expressions(mat)
M.recompile_material(mat)
save(mat)

source_path = f'{SOURCE}/StaticMeshes/SM_{SOURCE_NAME}'
mesh_path = DEST + '/SM_BakeryGrainSack'
mesh = require(mesh_path) if E.does_asset_exist(mesh_path) else E.duplicate_asset(source_path, mesh_path)
if not mesh:
    raise RuntimeError('Could not adapt the existing canvas scan')
for slot_index in range(len(mesh.static_materials)):
    mesh.set_material(slot_index, mat)
save(mesh)
box = mesh.get_bounding_box()
record = {
    'mesh': mesh_path, 'material': mat_path, 'source': source_path,
    'size_cm': [round(x, 2) for x in (box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z)],
    'bounds_min_cm': [round(x, 2) for x in (box.min.x, box.min.y, box.min.z)]
}
receipt = ROOT / 'SourceAssets/HillsVillageBakery/Grain/saved.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps(record, indent=2), encoding='utf-8')
u.log('BAKERY_GRAIN_SACK_SAVED')
