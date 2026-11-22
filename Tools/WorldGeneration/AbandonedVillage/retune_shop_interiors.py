"""Update saved village fixtures in place after changing the interior lighting profile."""
import json
import os
import shutil
import sys
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here))
from author_staff_lamp_surfaces import FOLDER, retune_saved_surfaces
from shop_staff_light import configure

level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
content=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()
out=Path(os.environ['VILLAGE_INTERIOR_LIGHT_BATCH'])
saved=out/'Saved'
saved.mkdir(exist_ok=True)
def snapshot(file,base):
    target=base/'Content'/file.relative_to(content)
    target.parent.mkdir(exist_ok=True,parents=True)
    if base==saved or not target.exists():
        shutil.copy2(file,target)
    return target

surface_dir=content/FOLDER.removeprefix('/Game/')
for file in surface_dir.glob('M_*.uasset'):
    snapshot(file,out/'Before')
materials=retune_saved_surfaces()
if not materials:
    raise RuntimeError('No village emission materials were available.')
for path in materials:
    snapshot(content/(path.split('.')[0].removeprefix('/Game/')+'.uasset'),saved)
(out/'materials-saved.json').write_text(json.dumps(materials,indent=2),encoding='utf-8')

map_file=content/(level.removeprefix('/Game/')+'.umap')
stamp=map_file.stat().st_mtime_ns
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world: raise RuntimeError('Cannot open the current village')
sub=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
targets={'VillageBakery.Site':'VillageBakery.Restored','VillageGunshop.Site':'VillageGunshop.Restored',
         'VillageTavern.Site':'VillageTavern.CounterPendant','Village_Carpenter_Repaired':'VillageCarpenter.Repaired',
         'Village_Herbalist_Repaired':'VillageHerbalist.Repaired'}
lights=[]
for actor in sub.get_all_level_actors():
    ids=set(map(str,actor.tags))|{actor.get_actor_label()}
    for site in targets.keys() & ids:
        for light in actor.get_components_by_class(u.PointLightComponent):
            if targets[site] not in map(str,light.component_tags):continue
            actor.modify()
            light.modify()
            old=light.get_editor_property('intensity')
            configure(light)
            lights.append(dict(site=site,component=light.get_name(),old_lumens=old,
                               lumens=light.get_editor_property('intensity'),
                               radius_cm=light.get_editor_property('attenuation_radius')))
if set(row['site'] for row in lights)!=targets.keys():
    raise RuntimeError('Missing an authored interior assembly in the current village')
if map_file.stat().st_mtime_ns!=stamp:raise RuntimeError('Village changed during authoring')
backup=snapshot(map_file,out/'Before')
if map_file.stat().st_mtime_ns!=stamp or not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save the current village revision')
snapshot(map_file,saved)
tint=u.VillageInteriorLighting.glow_tint()
report=dict(level=level,backup=str(backup),lights=lights,materials=materials,
            linear_rgb=[tint.r,tint.g,tint.b],emission_strength=u.VillageInteriorLighting.get_emission_strength())
(out/'lighting-saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
