"""Publish the current full-metal gauntlet icon without exporting any mesh.

Same glove icon contract as the field gloves: one empty native-shaped glove,
transparent vertical framing, 320 px per row, 91% fill, production materials.
"""
import json
import math
import shutil
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parents[2]
R = P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT = R/'InventoryIcon20260928'
ITEM = 'ue_steel_gauntlets'
FILL = .91


def read_png(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size[:]
    pixels = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(pixels)
    result = pixels.reshape(h, w, img.channels).copy()
    bpy.data.images.remove(img)
    return result


def linear(rgb):
    return np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)


def production_color(obj):
    """Area-weighted native UV samples, from the same textures UE imports."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    coords = np.asarray([tuple(obj.matrix_world@v.co) for v in mesh.vertices])
    faces = list(mesh.loop_triangles)
    triangles = np.asarray([f.vertices[:] for f in faces])
    normals = np.cross(coords[triangles[:, 1]]-coords[triangles[:, 0]],
                       coords[triangles[:, 2]]-coords[triangles[:, 0]])
    area = np.maximum(normals[:, 2], 0.)*.5
    uv = mesh.uv_layers.active
    centers = np.asarray([np.mean([uv.data[i].uv[:] for i in f.loops], axis=0) for f in faces])
    groups = np.asarray([f.material_index for f in faces])
    total, weight = np.zeros(3), 0.
    for index, mat in enumerate(mesh.materials):
        ids = np.where((groups == index) & (area > 1.e-10))[0]
        if not len(ids): continue
        tex = next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image
                   and 'BaseColor' in n.image.name)
        raw = read_png(Path(bpy.path.abspath(tex.image.filepath)))
        h, w = raw.shape[:2]
        repeat = np.ones(2)
        if mat.name.startswith('GreyMetalLiner_Baked'):
            # Read the actual material's production UV scale, not an icon tint.
            mapping = next(n for n in mat.node_tree.nodes if n.type=='VECT_MATH' and n.operation=='MULTIPLY')
            repeat = np.asarray(mapping.inputs[1].default_value[:2])
        sample = np.mod(centers[ids]*repeat, 1.)
        rgb = linear(raw[(sample[:, 1]*h).astype(int), (sample[:, 0]*w).astype(int), :3])
        total += (rgb*area[ids, None]).sum(0); weight += area[ids].sum()
    return total/weight


def measure(path):
    raw = read_png(path)
    opaque = raw[:, :, 3] > .95
    ys, xs = np.where(raw[:, :, 3] > .05)
    h, w = raw.shape[:2]
    return dict(size=[w, h], mean_linear=linear(raw[:, :, :3][opaque]).mean(0).tolist(),
                fill=max((xs.max()-xs.min()+1)/w, (ys.max()-ys.min()+1)/h),
                center=[float((xs.max()+xs.min()+1)/2/w), float((ys.max()+ys.min()+1)/2/h)])


def render_current_scene(obj):
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    catalog = json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
    item = catalog[ITEM]
    scene = bpy.context.scene
    for other in list(scene.objects):
        if other.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(other, do_unlink=True)
        elif other.type=='MESH':
            other.hide_render = other is not obj
    obj.hide_render = False
    coords = np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
    low, high = coords.min(0), coords.max(0)
    center = (low+high)*.5
    span = high-low
    width = max(256, round(320*item['grid_w']/max(1, item['grid_h'])))
    height = 320
    camera = bpy.data.cameras.new('EquipmentIconCamera')
    camera.type = 'ORTHO'; camera.clip_start = .01
    camera.ortho_scale = float(max(span[0], span[1]*width/height)/FILL)
    cam = bpy.data.objects.new(camera.name, camera); scene.collection.objects.link(cam)
    cam.location = Vector((center[0], center[1], high[2]+1.5))
    cam.rotation_euler = (0., 0., 0.); scene.camera = cam
    target = Vector(center)
    for name, offset, power, size in [('Key', (-.40, -.12, .70), 15., .55),
                                      ('Fill', (.40, .15, .60), 7., .65),
                                      ('Rim', (.08, .48, .45), 12., .45)]:
        light = bpy.data.lights.new('EquipmentIcon'+name, 'AREA')
        light.energy = power; light.size = size; light.color = (1., 1., 1.)
        lamp = bpy.data.objects.new(light.name, light); scene.collection.objects.link(lamp)
        lamp.location = target+Vector(offset)
        lamp.rotation_euler = (target-lamp.location).to_track_quat('-Z', 'Y').to_euler()
    world = bpy.data.worlds.new('EquipmentIconNeutralStudio'); world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
    background.inputs['Color'].default_value = (.35, .35, .35, 1.)
    background.inputs['Strength'].default_value = .12; scene.world = world
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = width*2; scene.render.resolution_y = height*2
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'; scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'; scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.; scene.view_settings.gamma = 1.
    target_color = production_color(obj)
    target_luma = float(target_color@np.asarray([.2126, .7152, .0722]))
    output = OUT/(ITEM+'.png'); scene.render.filepath = str(output)
    for attempt in range(3):
        bpy.ops.render.render(write_still=True)
        pixels = measure(output)
        actual = float(np.asarray(pixels['mean_linear'])@np.asarray([.2126, .7152, .0722]))
        adjustment = math.log2(target_luma/max(actual, 1.e-6))
        if abs(adjustment) < .08 or attempt==2: break
        scene.view_settings.exposure += float(np.clip(adjustment, -1., 1.))
    scene_path = OUT/'SteelGauntlet_InventoryIcon.blend'
    bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
    # Publish both copies so later asset imports cannot restore the old PNG.
    catalog_icon = P/'Content/ColdSteelData'/item['ue_icon']
    shutil.copy2(output, R/(ITEM+'.png')); shutil.copy2(output, catalog_icon)
    receipt = dict(item=ITEM, icon=str(catalog_icon), author_icon=str(R/(ITEM+'.png')),
                   scene=str(scene_path), source_scene=str(R/'SteelGauntlet_Icon.blend'),
                   materials=[m.name for m in obj.data.materials], target_color_linear=target_color.tolist(),
                   exposure=scene.view_settings.exposure, view_transform='Standard',
                   contract='Single empty glove; current full-metal materials; orthographic; transparent; 91% fill',
                   geometry_exported=False, runtime_tested=False, **pixels)
    (OUT/'delivery.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('STEEL_GAUNTLET_ICON_PUBLISHED '+json.dumps(receipt, ensure_ascii=False), flush=True)
    return receipt


def main():
    outfits=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    if outfits['items'][ITEM].get('appearance_family')=='SteelDetail20260928':
        import sys
        sys.path.insert(0,str(P/'Tools/ModularOutfit'))
        from build_glove_family_detail import icon
        icon('Steel',export_pickup=False)
        catalog=json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
        shutil.copy2(P/'SourceAssets/GloveCompanionDetail20260928/Steel/ue_steel_gauntlets.png',P/'Content/ColdSteelData'/catalog[ITEM]['ue_icon'])
        return
    bpy.ops.wm.open_mainfile(filepath=str(R/'SteelGauntlet_Icon.blend'))
    render_current_scene(bpy.data.objects['SM_SteelGauntlet_Pickup'])


if __name__=='__main__': main()
