"""Lengthen only the current meteor combustion motion/playback and save its system."""
import importlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorFireballImpact20261115/LongerRoll'
IMPACT='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if hasattr(u,'DragonBreathAuthorLibrary'):u.RainAssetEditor=u.DragonBreathAuthorLibrary
import meteor_fireball_impact_recipe as recipe
importlib.reload(recipe)


def run():
    if Path(u.Paths.project_content_dir()).resolve()!=(ROOT/'Content').resolve():
        raise RuntimeError('Use the FPSGAME content author host')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve the current PIE session; finish play before saving')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if IMPACT in dirty:raise RuntimeError('Preserve unsaved meteor impact edits')
    backup=OUT/'BeforeAssets';backup.mkdir(parents=True,exist_ok=True)
    source=ROOT/'Content'/(IMPACT.removeprefix('/Game/')+'.uasset')
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    system=u.load_asset(IMPACT)
    material=u.load_asset(recipe.DEST+'MI_MeteorFireballCombustion')
    if not material:raise RuntimeError('Missing the installed meteor fireball material')
    profile=recipe.apply(system,material)
    if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Meteor longer-roll Niagara compile failed')
    if not u.EditorAssetLibrary.save_loaded_asset(system,False):raise RuntimeError('Meteor longer-roll save failed')
    receipt=dict(saved_at=datetime.now().isoformat(),saved_assets=[system.get_path_name()],profile=profile,
        compiled=True,rendered=False,tested=False,materials_modified=False,native_source_modified=False,
        source_fireball_modified=False,additional_particles=0,additional_textures=0,additional_lights=0,
        preserved=['contact ignition and short flash','radial pressure fan','shockwave','sparks',
                   'dust and aftersmoke','falling flame','trail','low ground fire','rock and fragments',
                   'gameplay values and timing','sound','camera','scorch'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_LONGER_ROLL_SAVED '+json.dumps(receipt),flush=True)


if __name__=='__main__':run()
