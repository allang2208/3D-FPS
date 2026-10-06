"""Author reload lowering and detached cartridges from the installed RSH skin.

No render, animation playback, or acceptance pass. The donor clips stay shared.
"""
import bpy, json, math
from pathlib import Path

O = Path(__file__).resolve().parent
B = O.parent/'RSH12Speedloader20261003'
manifest = dict(meshes=[], profiles={}, runtime_tested=False)

def ease(x):
    x = max(0., min(1., x))
    return x*x*x*(10.+x*(-15.+6.*x))

for side in ('r', 'l'):
    src = B/'Dual'/side
    out = O/side
    out.mkdir(exist_ok=True)
    profile = json.loads((src/'profile.json').read_text(encoding='utf8'))
    samples = json.loads((O.parent/'RSH12Grip20261003'/('native_'+side+'.json')).read_text())['clips']
    samples.update(json.loads((B/('speed_'+side+'.json')).read_text())['clips'])
    for clip in profile['clips']:
        kind = clip['kind']
        if not (kind.startswith('single_') or kind == 'speed_0'):
            continue
        speed = kind == 'speed_0'
        empty = speed or kind.startswith('single_0_')
        # Work in the original 715 source seconds. The entire held hierarchy
        # lowers during the flick; the donor's existing deep reload then takes over.
        times = [row['time'] for row in samples[kind]['samples']]
        values = []
        for t in times:
            u = t*3.6/3.85 if speed else t
            catch_up = 1.5 if empty else .60
            weight = ease((u-.08)/.40)*(1.-ease((u-(catch_up-.35))/.35))
            values.extend([0., 0., -18.*weight, 0., 0., 0., 1., 0., 0., 0.])
        clip['tracks'].append(dict(bone='SK_DW715_Manny', times=times, values=values))
    (out/'profile.json').write_text(json.dumps(profile, separators=(',', ':')), encoding='utf8')
    manifest['profiles'][side] = str(out/'profile.json')

    bpy.ops.wm.open_mainfile(filepath=str(src/('RSH12_'+side+'_Editable.blend')))
    rig = next(ob for ob in bpy.data.objects if ob.type == 'ARMATURE')
    rig.data.pose_position = 'REST'
    source = bpy.data.objects['RSH12_NativeAssembly']
    material = bpy.data.materials.get('M_RSH12_SourcePBR')
    authored = []
    for chamber in range(5):
        bone = 'WPN_Case_'+str(chamber)
        # Export in THIS chamber's bind frame, retaining the source UVs. The
        # runtime bone frame then provides an exact position/rotation handoff.
        local = rig.data.bones[bone].matrix_local.inverted() @ rig.matrix_world.inverted() @ source.matrix_world
        for live in (False, True):
            groups = {source.vertex_groups[bone].index}
            if live:
                groups.add(source.vertex_groups['WPN_Round_'+str(chamber)].index)
            selected = {v.index for v in source.data.vertices if any(g.group in groups and g.weight > .99 for g in v.groups)}
            faces = [p for p in source.data.polygons if all(v in selected for v in p.vertices)]
            ids = sorted({v for p in faces for v in p.vertices})
            remap = {v:i for i,v in enumerate(ids)}
            name = 'SM_RSH12_'+('Live' if live else 'Case')+'_'+side+'_'+str(chamber)
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata([local @ source.data.vertices[v].co for v in ids], [], [[remap[v] for v in p.vertices] for p in faces])
            mesh.materials.append(material)
            mesh.update()
            uv = mesh.uv_layers.new(name='UVMap')
            source_uv = source.data.uv_layers.active.data
            normals = []
            normal_matrix = local.to_3x3().inverted().transposed()
            for p, old in zip(mesh.polygons, faces):
                for a, b in zip(p.loop_indices, old.loop_indices):
                    uv.data[a].uv = source_uv[b].uv
                    normals.append((normal_matrix @ source.data.corner_normals[b].vector).normalized())
            mesh.normals_split_custom_set(normals)
            ob = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(ob)
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            fbx = out/(name+'.fbx')
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE')
            authored.append(ob)
            manifest['meshes'].append(dict(fbx=str(fbx), name=name, side=side, chamber=chamber, live=live))
    # Keep a compact, editable source for the detached meshes only.
    for ob in list(bpy.data.objects):
        if ob not in authored:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'RSH12_DetachedCartridges.blend'))

(O/'authoring.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
print('RSH12_RELOAD_DROP_AUTHORED', flush=True)
