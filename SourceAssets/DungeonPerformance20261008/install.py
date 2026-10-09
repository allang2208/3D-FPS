"""Migrate only the production generator's cook references; no generation or play."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'


def main():
    report = dict(stage='preparing', map=TARGET, tests_run=False,
                  game_run=False, generated=False, rendered=False)
    receipt = ROOT / 'install-receipt.json'

    def record():
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')

    previous = None
    try:
        record()
        if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
            raise RuntimeError('Wrong project')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('Preserve active PIE; no assets written')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Preserve unsaved maps; no assets written')
        previous_world = editor.get_editor_world() if editor else None
        previous = previous_world.get_path_name().split('.')[0] if previous_world else None
        backup = ROOT / 'Backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
        files = [PROJECT / 'Content/GameMaps/L_Dungeon_Randomized.umap']
        for category in ('__ExternalActors__', '__ExternalObjects__'):
            folder = PROJECT / 'Content' / category / 'GameMaps/L_Dungeon_Randomized'
            if folder.exists():
                files.extend(p for p in folder.rglob('*') if p.is_file())
        for src in files:
            dest = backup / src.relative_to(PROJECT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        report['backup'] = str(backup)
        record()
        world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
        if len(generators) != 1:
            raise RuntimeError('Expected one production generator')
        generator = generators[0]
        report['legacy_hard_references_before'] = len(generator.get_editor_property('module_assets'))
        report['soft_references_before'] = len(generator.get_editor_property('module_asset_paths'))
        # Native PreSave converts legacy references and retains prior soft entries.
        # The catalog and its layout-bank signature are deliberately not rewritten.
        generator.modify()
        dirty = (list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) +
                 list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()))
        owned = [p for p in dirty if p.get_name() == TARGET or any(
            p.get_name().lower().startswith('/game/' + category + '/gamemaps/l_dungeon_randomized/')
            for category in ('__externalactors__', '__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned, False):
            raise RuntimeError('Generator external package save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
            raise RuntimeError('Production map save failed')
        report.update(stage='map_saved', saved_packages=[p.get_name() for p in owned],
                      legacy_hard_references_after=len(generator.get_editor_property('module_assets')),
                      soft_references_after=len(generator.get_editor_property('module_asset_paths')))
        record()
        print('DUNGEON_RESOURCE_REFERENCES_SAVED', TARGET,
              report['legacy_hard_references_before'], 'legacy references migrated;',
              report['soft_references_after'], 'soft references')
    except Exception:
        report['error'] = traceback.format_exc()
        record()
        raise
    finally:
        if (previous and previous != TARGET and previous.startswith('/Game/') and
                '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower()):
            u.EditorLoadingAndSavingUtils.load_map(previous)


if __name__ == '__main__':
    main()
