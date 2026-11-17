"""Author the wave and sparks in the active V7 asset; caller holds the UE mutex."""
import json
import importlib
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorRadialImpact20261114'
DEST='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if hasattr(u,'DragonBreathAuthorLibrary'):
    u.RainAssetEditor=u.DragonBreathAuthorLibrary
import meteor_radial_impact_recipe as recipe
importlib.reload(recipe)
from build_fireball_assets import LIB

def run(expected_content_root=None):
    expected_content_root=expected_content_root or ROOT/'Content'
    assert Path(u.Paths.project_content_dir()).resolve()==Path(expected_content_root).resolve(), 'Wrong authoring project'
    names=['NS_MeteorPressureV7','M_GroundPressureV7','M_HotEjectaV7']
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts=dirty.intersection(DEST+n for n in names)
    if conflicts:raise RuntimeError('Preserve unsaved meteor edits: '+str(sorted(conflicts)))
    backup=OUT/'BeforeAssets';backup.mkdir(parents=True,exist_ok=True)
    for name in names:
        source=ROOT/'Content'/DEST.removeprefix('/Game/')/(name+'.uasset')
        target=backup/source.name
        if not target.exists():shutil.copy2(source,target)
    system=u.load_asset(DEST+names[0])
    materials=[]
    for name,kind in [(names[1],'pressure'),(names[2],'spark')]:
        material=u.load_asset(DEST+name)
        shape=next(node for node in LIB.get_material_expressions(material)
                   if isinstance(node,u.MaterialExpressionCustom) and node.get_editor_property('description')=='MeteorV7.Shape')
        shape.set_editor_property('code',(ROOT/f'Tools/Skills/meteor_reference_v7_{kind}.hlsl').read_text(encoding='utf8'))
        materials.append(material)
    recipe.apply(system)
    u.EditorAssetLibrary.set_metadata_tag(system,'Meteor.RadialImpact',f'20261114 revision {recipe.REVISION}: thin cooling 620ms wave, 36 velocity-scaled sparks, 24 persistent ember chips')
    compiler=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.PoisonMaggotMonster
    if not compiler.compile_material_assets(materials):raise RuntimeError('Meteor wave/spark material compile failed')
    if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Meteor Niagara compile failed')
    saved=[]
    for asset in materials+[system]:
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt=dict(saved_at=datetime.now().isoformat(),revision=recipe.REVISION,saved_assets=saved,content_root=u.Paths.project_content_dir(),
        impact_system=system.get_path_name(),wave_lifetime_seconds=.62,hot_sparks=36,cooling_embers=24,
        max_total_particles=81,smoke_budget=16,detail_reduction_respected=True,
        added_lights=0,added_components=0,added_collision_queries=0,
        preserved=['fire crown','contact flash and fan','rock and fragments','V6 flight','V4 low fire','gameplay values','sound','camera'],
        tested=False,rendered=False,editor_started_by_this_task=False)
    (OUT/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_RADIAL_IMPACT_SAVED '+json.dumps(receipt),flush=True)

if __name__=='__main__':run()
