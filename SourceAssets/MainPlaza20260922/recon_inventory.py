"""Full compact inventory of the main hub scene (read-only) for the 100x100 m plaza layout.

Prints every actor as `label | class | x,y,z | mesh`, plus a class histogram. Writes
inventory.txt next to this file. No edits, no save, no PIE.
"""
from collections import Counter
from pathlib import Path

import unreal

HERE = Path(__file__).parent

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_editor_world()
if world is None:
    raise RuntimeError('No editor world.')

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def short(p):
    if not p:
        return ''
    name = p.split('.')[-1]
    if p.startswith('/Engine/'):
        return 'ENGINE:' + name
    if '/Props/' in p:
        return p.split('/Props/')[-1].split('.')[0]
    return name


rows = []
hist = Counter()
for a in actors:
    cls = a.get_class().get_name()
    hist[cls] += 1
    mesh = ''
    if isinstance(a, unreal.StaticMeshActor):
        comp = a.static_mesh_component
        if comp and comp.static_mesh:
            mesh = comp.static_mesh.get_path_name()
    loc = a.get_actor_location()
    rows.append('%s | %s | %.0f,%.0f,%.0f | %s'
                % (a.get_actor_label(), cls, loc.x, loc.y, loc.z, short(mesh)))

rows.sort()
lines = ['# class histogram'] + ['%4d  %s' % (n, c) for c, n in hist.most_common()] + ['', '# actors'] + rows
text = '\n'.join(lines)
(HERE / 'inventory.txt').write_text(text, encoding='utf-8')

fountains = [r for r in rows if 'fountain' in r.lower()]
print('INVENTORY_OK total=%d classes=%d fountains=%d' % (len(rows), len(hist), len(fountains)))
for f in fountains:
    print('FOUNTAIN: ' + f)
