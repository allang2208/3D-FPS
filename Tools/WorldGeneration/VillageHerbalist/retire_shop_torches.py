"""Retire only the authored torch pieces now supplied by the village shop lamp mounts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as u

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path[:0] = [str(here.parent / 'VillageBlacksmith'), str(here.parent / 'AbandonedVillage'), str(here)]
from author_shop import pose
from herbalist_lights import BODY, TORCHES, SCALE, offset
from shop_pendants import remove_components

level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
disk = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())) / (level[6:] + '.umap')
batch = Path(os.environ['VILLAGE_SHOP_LAMP_BATCH'])
before = disk.read_bytes()
layout = json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
house = next(row for row in layout['houses'] if row[0] == '03')
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Cannot load ' + level)

positions = {kind: [] for kind in ('body', 'socket', 'flame')}
for anchor, yaw in TORCHES:
    positions['body'].append(pose(house, *anchor).translation)
    positions['socket'].append(pose(house, *offset(anchor, yaw, 23., 0.)).translation)
    positions['flame'].append(pose(house, *offset(anchor, yaw, 50*SCALE, 62*SCALE)).translation)

def matches(position, kind):
    return any((position-expected).length() < 3. for expected in positions[kind])

counts = dict(body=0, socket=0, card=0, light=0)
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
    if actor.get_actor_label() not in {'Village_Herbalist_Common', 'Village_Herbalist_Ruined', 'Village_Herbalist_Repaired'}:
        continue
    remove = []
    for part in actor.get_components_by_class(u.SceneComponent):
        if isinstance(part, u.MaterialBillboardComponent):
            kind = 'card'
        elif isinstance(part, u.PointLightComponent):
            kind = 'light'
        elif isinstance(part, u.StaticMeshComponent) and part.static_mesh:
            name = part.static_mesh.get_name()
            if name == BODY.rsplit('/',1)[1]:
                kind = 'body'
            elif name == 'Cylinder':
                kind = 'socket'
            else:
                continue
        else:
            continue
        key = 'flame' if kind in ('card','light') else kind
        if isinstance(part, u.InstancedStaticMeshComponent):
            hits = [i for i in range(part.get_instance_count()) if matches(part.get_instance_transform(i,True).translation, key)]
            if not hits:
                continue
            if len(hits) == part.get_instance_count():
                remove.append(part)
            else:
                actor.modify()
                part.modify()
                for i in reversed(hits):
                    if not part.remove_instance(i):
                        raise RuntimeError(part.get_path_name())
            counts[kind] += len(hits)
        elif matches(part.get_world_location(), key):
            remove.append(part)
            counts[kind] += 1
    if remove:
        actor.modify()
        remove_components(actor, remove)

if any(counts.values()):
    if counts != dict(body=3, socket=2, card=2, light=2):
        raise RuntimeError('Incomplete set of existing apothecary fixtures: ' + str(counts))
    if disk.read_bytes() != before:
        raise RuntimeError('The village was saved while preparing the lamp migration; rerun on the latest level.')
    backup = batch/'Before'/('L_AbandonedVillage.'+hashlib.sha256(before).hexdigest()[:12]+'.umap')
    backup.parent.mkdir(parents=True,exist_ok=True)
    backup.write_bytes(before)
    if not u.EditorLoadingAndSavingUtils.save_packages([world.get_outermost()],False):
        raise RuntimeError('Cannot save ' + level)
    out = batch/'Published'/'Content'/(level[6:]+'.umap')
    out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(disk,out)
    (batch/'level-saved.json').write_text(json.dumps(dict(level=level, removed=counts,
        before=hashlib.sha256(before).hexdigest(), published=hashlib.sha256(out.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
u.log('SHOP_CHAIN_LAMP_MIGRATION ' + str(counts))
