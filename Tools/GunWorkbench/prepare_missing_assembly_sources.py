"""Import native exports into Blender and inventory rigid mechanical groups."""
import bpy, json, collections
from pathlib import Path

ROOT = Path(globals().get('ASSEMBLY_ROOT', 'D:/FPS3D/FPSGAME/SourceAssets/GunAssemblyCompletion20261015'))
result = []
for source in json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))['weapons']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source['fbx'], use_anim=False)
    row = {'key': source['key'], 'objects': []}
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            row['bones'] = [{'name': b.name, 'parent': b.parent.name if b.parent else None}
                            for b in obj.data.bones if 'wpn' in b.name.lower() or 's90' in b.name.lower()]
        if obj.type != 'MESH':
            continue
        labels = {g.index: g.name for g in obj.vertex_groups}
        dominant = {v.index: labels[max(v.groups, key=lambda x: x.weight).group] if v.groups else ''
                    for v in obj.data.vertices}
        groups = collections.Counter()
        for face in obj.data.polygons:
            bone = collections.Counter(dominant[v] for v in face.vertices).most_common(1)[0][0]
            groups[(bone, face.material_index)] += 1
        row['objects'].append({'name': obj.name, 'faces': len(obj.data.polygons),
                               'materials': [m.name if m else None for m in obj.data.materials],
                               'groups': [{'bone': b, 'slot': source['materials'][m]['slot'], 'faces': n}
                                          for (b, m), n in groups.items()]})
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Sources' / (source['key'] + '.blend')))
    result.append(row)
    (ROOT / 'source-groups.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ASSEMBLY_SOURCE_PREPARED', source['key'], flush=True)
