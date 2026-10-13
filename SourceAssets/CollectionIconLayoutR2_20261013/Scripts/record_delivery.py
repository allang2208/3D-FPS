from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text('utf-8-sig'))
icons=read('Receipts/installation.json');footprint=read('Receipts/footprint.json');builds=read('Receipts/native-build.json')
report=dict(stage='collection_icon_layout_and_gpu_footprint_saved',
    icon_count=icons['count'],horizontal_count=icons['horizontal_count'],vertical_count=icons['vertical_count'],standard_count=icons['standard_count'],
    gpu_footprint=[footprint['after']['grid_w'],footprint['after']['grid_h']],
    gpu_old_footprint=[footprint['before']['grid_w'],footprint['before']['grid_h']],
    prices_changed=False,rarities_changed=False,models_changed=False,weapon_and_equipment_icons_changed=False,
    old_icon_backups='PreviousIcons',legacy_neutral_hardware_icon_aliases_updated=3,
    native_build=builds,old_save_migration='Existing authored-footprint migration includes GPU, preserves rotation and inventory identity',
    reload_required=True,save_files_edited=False,tests_run=False,game_started=False,additional_previews_rendered=False)
if builds['stage']=='build_failed':
    report['stage']='icons_installed_editor_built_game_build_blocked'
    report['game_build_blocker']='Existing parallel woodworking changes: WoodworkingSystem.h type declarations and ColdSteelStationNetwork.cpp CreateNetworkSession argument mismatch'
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COLLECTION_LAYOUT_R2_DELIVERED',report['icon_count'],report['gpu_footprint'],builds['stage'])
