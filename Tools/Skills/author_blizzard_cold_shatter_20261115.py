"""Save Blizzard-only cold mist assets; original IceSpike supplies runtime shatter."""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/BlizzardColdShatter20261115'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import save
import blizzard_cold_mist_recipe as recipe


def run():
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT/'Content').resolve():
        raise RuntimeError('Use the FPSGAME content author host')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve active PIE; finish play before saving')
    targets = (recipe.SYSTEM, recipe.MATERIAL)
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(targets):
        raise RuntimeError('Preserve unsaved Blizzard assets')
    backup = OUT/'BeforeAssets'
    backup.mkdir(parents=True, exist_ok=True)
    for target in targets:
        source = ROOT/'Content'/(target.removeprefix('/Game/')+'.uasset')
        if source.exists() and not (backup/source.name).exists():
            shutil.copy2(source, backup/source.name)
    system = u.load_asset(recipe.SYSTEM)
    if not system:
        raise RuntimeError('Missing installed Blizzard boundary mist')
    material = recipe.author_material()
    profile = recipe.apply(system, material)
    save(material)
    save(system)
    receipt = dict(saved_at=datetime.now().isoformat(), saved_assets=[material.get_path_name(), system.get_path_name()],
                   profile=profile, compiled=True, rendered=False, tested=False,
                   shatter_source='/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact',
                   preserved=['clouds', 'precipitation', 'falling spike meshes', 'ground frost',
                              'audio', 'gameplay values', 'damage timing', 'network authority'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('BLIZZARD_COLD_SHATTER_SAVED '+json.dumps(receipt), flush=True)


if __name__ == '__main__':
    run()
