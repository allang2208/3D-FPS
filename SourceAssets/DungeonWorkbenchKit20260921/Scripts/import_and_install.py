from pathlib import Path
import runpy,unreal as u
ROOT=Path(__file__).resolve().parents[1]
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps before kit changes: '+', '.join(p.get_name() for p in dirty))
for name in ('import_kit.py','build_blueprints.py','install_kit.py'):
    print('WORKBENCH_KIT_STAGE '+name)
    # Blueprint reinstancing dirties the owning OFPA package even with unchanged placement.
    generated_external=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages() if p.get_name().startswith('/Game/__ExternalActors__/GameMaps/L_Dungeon_Prototype/')] if name=='install_kit.py' else []
    runpy.run_path(str(ROOT/'Scripts'/name),run_name='__main__',init_globals={'WORKBENCH_FULL_REBUILD':globals().get('WORKBENCH_FULL_REBUILD',False),'WORKBENCH_MAP_WAS_CLEAN':True,'WORKBENCH_DIRTY_EXTERNAL_PACKAGES':generated_external})
