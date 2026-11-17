"""Save a fireball-derived meteor body through the existing UE authoring bridge."""
import importlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorFireballImpact20261115'
IMPACT='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if hasattr(u,'DragonBreathAuthorLibrary'):u.RainAssetEditor=u.DragonBreathAuthorLibrary
import meteor_fireball_impact_recipe as recipe
importlib.reload(recipe)


def run():
    if Path(u.Paths.project_content_dir()).resolve()!=(ROOT/'Content').resolve():
        raise RuntimeError('Use the FPSGAME content author host')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE is running. End the current play session before saving meteor assets; leave the editor open.')
    paths=[IMPACT]+[recipe.DEST+name for name in recipe.MATERIAL_NAMES]
    dirty={package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict=dirty.intersection(paths)
    if conflict:raise RuntimeError('Preserve unsaved meteor target packages: '+str(sorted(conflict)))
    backup=OUT/'BeforeAssets'
    backup.mkdir(parents=True,exist_ok=True)
    for path in paths:
        source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        target=backup/source.name
        if source.exists() and not target.exists():shutil.copy2(source,target)
    materials=recipe.author_materials()
    system=u.load_asset(IMPACT)
    profile=recipe.apply(system,materials[-1])
    compiler=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.PoisonMaggotMonster
    if not compiler.compile_material_assets(materials):raise RuntimeError('Meteor combustion material compilation failed')
    if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Meteor Niagara compilation failed')
    saved=[]
    for asset in materials+[system]:
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt=dict(saved_at=datetime.now().isoformat(),saved_assets=saved,profile=profile,
        source_fireball_saved_or_modified=False,native_source_modified=False,
        new_textures=0,new_components=0,new_lights=0,compiled=True,rendered=False,tested=False,
        editor_started_by_this_task=False,
        preserved=['contact flash','radial pressure fan','current shockwave and sparks','impact dust and aftersmoke',
                   'falling flame','continuous trail','low ground fire','rock and fragments',
                   'gameplay values and timing','sound','camera','scorch'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_FIREBALL_IMPACT_SAVED '+json.dumps(receipt),flush=True)


if __name__=='__main__':run()
