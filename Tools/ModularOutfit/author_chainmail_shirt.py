"""Author an independent mail shirt from the currently equipped native sleeves.

Blender background production only: native topology/weights stay unchanged;
the item icon is a delivery asset, not a gameplay preview or acceptance render.
"""
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parents[2]
R = P/'SourceAssets/ChainmailShirt20260928'
sys.path.insert(0, str(P/'Tools/ModularOutfit'))
from steel_gauntlet_metal_liner import blender_material
from render_steel_gauntlet_icon import production_color, measure

ITEM = 'ue_chainmail_shirt'
CONTRACT = 'Current field sweater envelope and native weights; grey steel mail; UV density in centimetres; no new animations'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')


def mail_uv(positions, faces, uv):
    """Set 1 UV unit to 25 cm per existing chart, retaining all seams.

    The shared material repeats an eight-ring, 5.6 x 4.8 mm production tile
    over a 25 cm UV span. Do not weld the sleeve's separate shoulder caps.
    """
    positions = np.asarray(positions, dtype=float)
    faces = np.asarray(faces, dtype=int)
    uv = np.asarray(uv, dtype=float)
    parent = list(range(len(faces)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    edges = {}
    for fi, face in enumerate(faces):
        corners = [(int(vi), *np.round(uv[fi, ci], 5)) for ci, vi in enumerate(face)]
        for ci in range(3):
            edge = tuple(sorted((corners[ci], corners[(ci+1)%3])))
            previous = edges.get(edge)
            if previous is not None:
                parent[root(fi)] = root(previous)
            else:
                edges[edge] = fi
    groups = defaultdict(list)
    for fi in range(len(faces)):
        groups[root(fi)].append(fi)
    tri = positions[faces]
    area = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)*.5
    a, b = uv[:, 1]-uv[:, 0], uv[:, 2]-uv[:, 0]
    uv_area = np.abs(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0])*.5
    output = uv.copy()
    charts = []
    for ids in groups.values():
        real, tex = float(area[ids].sum()), float(uv_area[ids].sum())
        scale = math.sqrt(real/tex)/25. if tex > 1.e-10 and real > 1.e-8 else 1.
        origin = uv[ids].reshape(-1, 2).min(0)
        output[ids] = (uv[ids]-origin)*scale
        charts.append(dict(triangles=len(ids), area_cm2=real, uv_scale=scale))
    return output.tolist(), charts


def editable(data, material):
    name = data['profile']
    reflection = Matrix.Diagonal((1, -1, 1))
    arm = bpy.data.armatures.new(name+'_NativeReference')
    rig = bpy.data.objects.new(arm.name, arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    names = {b['index']: n for n, b in data['bones'].items()}
    for n, b in data['bones'].items():
        bone = arm.edit_bones.new(n)
        axes = Matrix(b['axes']).transposed()
        for col in range(3):
            axes.col[col] = axes.col[col].normalized()
        matrix = (reflection@axes@reflection).to_4x4()
        matrix.translation = reflection@Vector(b['position'])*.01
        bone.matrix = matrix
        bone.length = .025
    for n, b in data['bones'].items():
        if b['parent'] in names:
            arm.edit_bones[n].parent = arm.edit_bones[names[b['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = bpy.data.meshes.new('SK_'+name+'_ChainmailShirt')
    mesh.from_pydata([(p[0]*.01, -p[1]*.01, p[2]*.01) for p in data['positions']], [], data['triangles'])
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = rig
    obj.modifiers.new('NativeBinding', 'ARMATURE').object = rig
    for n in sorted({n for weights in data['weights'] for n in weights}):
        obj.vertex_groups.new(name=n)
    for vi, weights in enumerate(data['weights']):
        for n, weight in weights.items():
            obj.vertex_groups[n].add([vi], weight, 'REPLACE')
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name='GreySteelMail')
    normals = []
    for face, uv, ns in zip(mesh.polygons, data['uv'], data['normals']):
        face.use_smooth = True
        for loop, (u, v), n in zip(face.loop_indices, uv, ns):
            layer.data[loop].uv = (u, 1-v)
            normals.append((n[0], -n[1], n[2]))
    mesh.normals_split_custom_set(normals)
    obj['NativeSource'] = data['binding_source']
    obj['Contract'] = CONTRACT
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'Editable'/(name+'_ChainmailShirt.blend')))


def presentation():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = P/'SourceAssets/ModularOutfit20260924/ItemPresentation.blend'
    with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
        loaded.objects = ['SM_FieldSweater_Pickup']
    obj = loaded.objects[0]
    bpy.context.collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.name = 'SM_ChainmailShirt_Pickup'
    obj.data = obj.data.copy()
    obj.data.name = obj.name
    obj.data.materials.clear()
    obj.data.materials.append(blender_material())
    mesh = obj.data
    mesh.calc_loop_triangles()
    faces = [t.vertices[:] for t in mesh.loop_triangles]
    layer = mesh.uv_layers.active
    uv = [[layer.data[i].uv[:] for i in t.loops] for t in mesh.loop_triangles]
    coords = [tuple((obj.matrix_world@v.co)*100.) for v in mesh.vertices]
    adjusted, charts = mail_uv(coords, faces, uv)
    for face, values in zip(mesh.loop_triangles, adjusted):
        for loop, value in zip(face.loops, values):
            layer.data[loop].uv = value
    for poly in mesh.polygons:
        poly.material_index = 0
    obj['EquipmentDefinition'] = ITEM
    obj['Source'] = str(source)
    obj['Surface'] = 'Same baked grey mail BaseColor, ORM and Normal as the accepted steel gauntlet'
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(R/(obj.name+'.fbx')), use_selection=True,
        object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False,
        mesh_smooth_type='FACE', path_mode='STRIP')
    scene = bpy.context.scene
    coords = np.asarray([tuple(obj.matrix_world@v.co) for v in mesh.vertices])
    low, high = coords.min(0), coords.max(0)
    center = (low+high)*.5
    camdata = bpy.data.cameras.new('ChainmailInventoryCamera')
    camdata.type = 'ORTHO'
    camdata.ortho_scale = float(max((high-low)[:2])/.91)
    cam = bpy.data.objects.new(camdata.name, camdata)
    scene.collection.objects.link(cam)
    cam.location = (center[0], center[1], high[2]+2.)
    cam.rotation_euler = (0., 0., 0.)
    scene.camera = cam
    target = Vector(center)
    for name, offset, power, size in [('Key', (-1., -1., 2.), 55., 2.),
                                     ('Fill', (1., .2, 1.5), 30., 1.5),
                                     ('Rim', (0., 1., 1.2), 45., 1.)]:
        light = bpy.data.lights.new('ChainmailIcon'+name, 'AREA')
        light.energy = power
        light.size = size
        lamp = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(lamp)
        lamp.location = target+Vector(offset)
        lamp.rotation_euler = (target-lamp.location).to_track_quat('-Z', 'Y').to_euler()
    world = bpy.data.worlds.new('ChainmailIconStudio')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.35, .35, .35, 1.)
    bg.inputs['Strength'].default_value = .12
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.gamma = 1.
    scene.view_settings.exposure = 0.
    output = R/(ITEM+'.png')
    scene.render.filepath = str(output)
    target_color = production_color(obj)
    luma = np.asarray([.2126, .7152, .0722])
    for attempt in range(3):
        bpy.ops.render.render(write_still=True)
        pixels = measure(output)
        correction = math.log2(float(target_color@luma)/max(float(np.asarray(pixels['mean_linear'])@luma), 1.e-6))
        if abs(correction) < .08 or attempt == 2:
            break
        scene.view_settings.exposure += float(np.clip(correction, -1., 1.))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'ChainmailShirt_Presentation.blend'))
    return dict(icon=str(output), pickup=str(R/(obj.name+'.fbx')), uv_charts=charts,
                icon_exposure=scene.view_settings.exposure, icon_measurements=pixels)


def main():
    config = json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    if config['items'].get(ITEM, {}).get('appearance_family') in ('ChainmailInterlace20260929','ChainmailCloth20260929','ChainmailSharedSway20260929','ChainmailInsetBinding20260929','ChainmailCameraClearance20260929'):
        if '--presentation-only' in sys.argv:
            import build_chainmail_interlace as current
            import shutil
            artwork = current.inventory()
            current.write(current.R/'icon.json', artwork)
            items = json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
            shutil.copy2(current.R/(ITEM+'.png'), P/'Content/ColdSteelData'/items[ITEM]['ue_icon'])
            print('CHAINMAIL_CURRENT_INTERLACE_ICON_SAVED', flush=True)
            return
        raise RuntimeError('The active shirt uses interlaced mail or cuff cloth; use its current authoring script.')
    if config['items'].get(ITEM, {}).get('appearance_family') == 'ChainmailRelief20260929':
        if '--presentation-only' in sys.argv:
            import build_chainmail_relief as current
            import shutil
            artwork = current.inventory()
            current.write(current.R/'icon.json', artwork)
            items = json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
            destination = P/'Content/ColdSteelData'/items[ITEM]['ue_icon']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current.R/(ITEM+'.png'), destination)
            print('CHAINMAIL_CURRENT_RELIEF_ICON_SAVED', flush=True)
            return
        raise RuntimeError('The active shirt is ChainmailRelief20260929; use build_chainmail_relief.py for its current surface. This legacy author would restore the earlier fine-mail recipe.')
    (R/'Authored').mkdir(parents=True, exist_ok=True)
    (R/'Editable').mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--presentation-only' in sys.argv:
        artwork = presentation()
        manifest = json.loads((R/'manifest.json').read_text(encoding='utf-8'))
        write(R/'artwork.json', dict(artwork, profiles=len(manifest), contract=CONTRACT,
            source_geometry='Existing field sweater; retained native binding, sleeve clearance and inward cuff wall',
            new_animations=0, runtime_tested=False))
        print('CHAINMAIL_AUTHORING_COMPLETE', len(manifest), flush=True)
        return
    sources = json.loads((R/'native-sources.json').read_text(encoding='utf-8'))
    manifest = []
    for name, source in sources.items():
        raw = (R/'Sources'/(name+'.json')).read_bytes()
        data = json.loads(raw)
        data['uv'], charts = mail_uv(data['positions'], data['triangles'], data['uv'])
        data['contract'] = CONTRACT
        data['source_sha256'] = hashlib.sha256(raw).hexdigest()
        path = R/'Authored'/(name+'.json')
        write(path, data)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        editable(data, blender_material())
        manifest.append(dict(profile=name, authored=str(path), source=source,
                             triangles=len(data['triangles']), uv_charts=charts))
        print('CHAINMAIL_AUTHORED', name, len(data['triangles']), flush=True)
    write(R/'manifest.json', manifest)
    artwork = presentation()
    write(R/'artwork.json', dict(artwork, profiles=len(manifest), contract=CONTRACT,
        source_geometry='Existing field sweater; retained native binding, sleeve clearance and inward cuff wall',
        new_animations=0, runtime_tested=False))
    print('CHAINMAIL_AUTHORING_COMPLETE', len(manifest), flush=True)


if __name__ == '__main__':
    main()
