"""Render the delivered chainmail icon from its current Body clothing source.

Blender background authoring only. No game mesh, animation or UE package writes.
"""
import hashlib
import json
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parents[2]
R = P / 'SourceAssets/ChainmailInventoryIcon20260930'
FAMILY = P / 'SourceAssets/ChainmailInterlace20260929'
SOURCE = FAMILY / 'Editable/Body_ChainmailShirt.blend'
ITEM = 'ue_chainmail_shirt'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material():
    # Build fresh nodes: never reuse a similarly named material from an old
    # presentation file. These are the current production ring textures/scale.
    mat = bpy.data.materials.new('ChainmailInventory_CurrentProductionPBR')
    mat.use_nodes = True
    n, links = mat.node_tree.nodes, mat.node_tree.links
    n.clear()
    bs = n.new('ShaderNodeBsdfPrincipled')
    result = n.new('ShaderNodeOutputMaterial')
    links.new(bs.outputs['BSDF'], result.inputs['Surface'])
    uv = n.new('ShaderNodeTexCoord')
    scale = n.new('ShaderNodeVectorMath')
    scale.operation = 'MULTIPLY'
    tile = read(FAMILY / 'tile.json')['tile_meters']
    scale.inputs[1].default_value = (.25 / tile[0], .25 / tile[1], 1.)
    links.new(uv.outputs['UV'], scale.inputs[0])
    maps = {}
    for channel in ('BaseColor', 'ORM', 'Normal'):
        image = bpy.data.images.load(str(FAMILY / 'Textures' / ('T_ChainmailRelief_' + channel + '.png')), check_existing=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'BaseColor' else 'Non-Color'
        image.pack()
        tex = n.new('ShaderNodeTexImage')
        tex.image = image
        tex.extension = 'REPEAT'
        links.new(scale.outputs[0], tex.inputs['Vector'])
        maps[channel] = tex
    orm = n.new('ShaderNodeSeparateColor')
    links.new(maps['ORM'].outputs['Color'], orm.inputs['Color'])
    links.new(orm.outputs['Green'], bs.inputs['Roughness'])
    links.new(orm.outputs['Blue'], bs.inputs['Metallic'])
    # Principled has no baked AO socket. Retain the production cavity contrast
    # in this offline studio instead of dropping ORM.R as the old icon did.
    cavity = n.new('ShaderNodeMixRGB')
    cavity.blend_type = 'MULTIPLY'
    cavity.inputs[0].default_value = 1.
    links.new(maps['BaseColor'].outputs['Color'], cavity.inputs[1])
    links.new(orm.outputs['Red'], cavity.inputs[2])
    links.new(cavity.outputs[0], bs.inputs['Base Color'])
    normal = n.new('ShaderNodeNormalMap')
    links.new(maps['Normal'].outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], bs.inputs['Normal'])
    mat['SourceFamily'] = 'ChainmailInterlace20260929'
    mat['TileMeters'] = tile
    return mat


def inventory():
    config = read(P / 'Content/ColdSteelData/modular_outfits.json')
    item = read(P / 'Content/ColdSteelData/items.json')[ITEM]
    body_asset = config['items'][ITEM]['rig_meshes']['Body']
    if '/ChainmailInterlace20260929/Body/' not in body_asset:
        raise RuntimeError('Current Body source changed; update the icon source before rendering.')
    R.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    obj = bpy.data.objects['SK_Body_ChainmailShirt']
    rig = obj.parent
    # The display pose only lowers the existing arm chains. It keeps native
    # bone lengths and garment proportions and is saved to a separate blend.
    for side, angle in (('l', 12.), ('r', -12.)):
        bone = rig.pose.bones['upperarm_' + side]
        head = bone.matrix.translation.copy()
        bone.matrix = (Matrix.Translation(head) @ Matrix.Rotation(math.radians(angle), 4, 'Y')
                       @ Matrix.Translation(-head) @ bone.matrix)
    bpy.context.view_layer.update()
    obj.data.materials[0] = material()
    obj['IconOnlyPose'] = 'Native Body shell; shoulders lowered 12 degrees; upright, no skin/mannequin'
    for other in scene.objects:
        other.hide_render = other.type == 'MESH' and other != obj

    # Front camera, slightly above the collar; no roll or nonorthogonal warp.
    coords = np.array([tuple(obj.matrix_world @ v.co) for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices])
    center = Vector((coords.min(0) + coords.max(0)) * .5)
    camera_data = bpy.data.cameras.new('ChainmailInventoryCamera')
    camera_data.type = 'ORTHO'
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((0., -3., .38))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    bpy.context.view_layer.update()
    inverse = camera.matrix_world.inverted()
    projected = np.array([tuple(inverse @ Vector(p)) for p in coords])
    low, high = projected.min(0), projected.max(0)
    width = max(256, round(320 * item['grid_w'] / max(1, item['grid_h'])))
    height = 320
    aspect = width / height
    camera_data.ortho_scale = float(max(high[0] - low[0], (high[1] - low[1]) * aspect) / .91)
    camera.location += camera.rotation_euler.to_matrix() @ Vector(((low[0]+high[0])*.5, (low[1]+high[1])*.5, 0.))
    for name, offset, power, size in (
            ('Key', (-1.1, -1.8, 1.6), 75., 1.3),
            ('Fill', (1.2, -1., .3), 25., 1.6),
            ('Rim', (.8, .7, 1.2), 60., .85)):
        light = bpy.data.lights.new('ChainmailInventory' + name, 'AREA')
        light.energy, light.size = power, size
        lamp = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(lamp)
        lamp.location = center + Vector(offset)
        lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    world = bpy.data.worlds.new('ChainmailInventoryNeutralStudio')
    world.use_nodes = True
    world.node_tree.nodes.clear()
    background = world.node_tree.nodes.new('ShaderNodeBackground')
    world_output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
    world.node_tree.links.new(background.outputs[0], world_output.inputs['Surface'])
    background.inputs['Color'].default_value = (.35, .35, .35, 1.)
    background.inputs['Strength'].default_value = .12
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1024
    scene.cycles.adaptive_threshold = .002
    scene.cycles.use_denoising = False  # Preserve fine rings at the delivered size.
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.
    scene.view_settings.gamma = 1.
    output = R / (ITEM + '.png')
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    blend = R / 'ChainmailInventoryIcon.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    # The UI imports directory PNGs directly, so no Texture2D package or UE
    # session is needed. Preserve the active path and old saved-item aliases.
    destinations = [P / 'Content/ColdSteelData' / item['ue_icon'], FAMILY / (ITEM + '.png')]
    for family in ('ChainmailShirt20260928', 'ChainmailRelief20260929'):
        alias = P / 'Content/ColdSteelData/Icons' / family / (ITEM + '.png')
        if alias.exists():
            destinations.append(alias)
    before = R / 'Before'
    before.mkdir(exist_ok=True)
    changed = []
    for destination in destinations:
        backup = before / ('_'.join(destination.relative_to(P).parts))
        if destination.exists() and not backup.exists():
            shutil.copy2(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output, destination)
        changed.append(str(destination))
    receipt = dict(item=ITEM, icon=str(output), size=[width, height], blend=str(blend),
                   source=str(SOURCE), source_sha256=digest(SOURCE), source_asset=body_asset,
                   material_family='ChainmailInterlace20260929', fill=.91, transparent=True,
                   icon_sha256=digest(output), installed=changed, gameplay_assets_changed=False,
                   runtime_tested=False, preview=False)
    (R / 'production.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('CHAINMAIL_INVENTORY_ICON_SAVED ' + str(output), flush=True)
    return receipt


if __name__ == '__main__':
    inventory()
