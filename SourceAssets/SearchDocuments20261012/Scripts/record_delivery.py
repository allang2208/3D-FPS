"""Record produced assets in the existing design catalog; do not add runtime loot."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
project = root.parents[1]
models = json.loads((root / 'model_manifest.json').read_text('utf-8'))
ue = json.loads((root / 'Receipts/ue-import.json').read_text('utf-8'))
installation = json.loads((root / 'Receipts/installation.json').read_text('utf-8'))
catalog_path = project / 'Docs/Gameplay/search-item-catalog-v2-20261012.json'
catalog = json.loads(catalog_path.read_text('utf-8-sig'))
meshes = {m['item_id']: m for m in ue['meshes']}
assets = {m['id']: m for m in models['assets'].values()}
for item in catalog['items']:
    if item['id'] not in assets:
        continue
    authored = assets[item['id']]
    saved = meshes[item['id']]
    item['model'].update(
        status='ue_assets_saved_and_installed_not_loot_integrated',
        actual_dimensions_cm=saved['dimensions_cm'],
        source=str(Path(authored['source']).relative_to(project)).replace('\\', '/'),
        fbx=str(Path(authored['fbx']).relative_to(project)).replace('\\', '/'),
        glb=str(Path(authored['glb']).relative_to(project)).replace('\\', '/'),
        ue_mesh=saved['path'], ue_material=saved['material'],
        triangles_lod0=authored['triangles_lod0'], texture_size=authored['size'])
catalog['rules']['rarity'] = '沿用现有六档；本版22项均为非装备。杂物不可装备且不附加属性。'
catalog['delivery'].update(
    models_created=False, document_models_created=True,
    modeled_item_ids=list(assets), runtime_items_changed=True,
    runtime_item_changes=['soda_can rarity=uncommon', 'baguette_bread rarity=uncommon'],
    new_runtime_items_added=False, loot_pool_changed=False,
    model_delivery='Docs/Art/search-documents-models-20261012.md')
catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
delivery = dict(
    stage=installation['stage'], item_ids=list(assets),
    ue_meshes=[m['path'] for m in ue['meshes']],
    asset_counts=dict(meshes=len(ue['meshes']), materials=len(ue['materials']),
                      textures=len(ue['textures']), installed_packages=len(installation['packages'])),
    food_rarity=dict(soda_can='uncommon', baguette_bread='uncommon',
                    existing_instance_migration='on_next_profile_load'),
    builds={}, new_runtime_items_added=False, loot_pool_changed=False,
    icons_created=False, rendered=False, runtime_tested=False,
    import_route='UE 5.8 content-only host; identical package paths installed into main project',
    main_project_commandlet_startup_issue='Cast of Package /Script/FPSGAME to SkeletalMeshComponent failed; not changed by this task')
for target in ('FPSGAMEEditor', 'FPSGAME'):
    log = root / 'Receipts' / ('build-final-'+target+'.log')
    text = log.read_text(encoding='utf-8-sig', errors='replace') if log.exists() else ''
    # Build.bat emits Result only after UBT finishes; do not infer from asset status.
    result = next((line.strip() for line in reversed(text.splitlines()) if line.startswith('Result:')), None)
    delivery['builds'][target] = dict(result=result or 'pending', log=str(log))
if 'Failed' in delivery['builds']['FPSGAMEEditor']['result']:
    delivery['old_save_migration_binary_status'] = 'not_delivered_build_blocked'
    delivery['build_blocker'] = 'Unrelated ColdSteelPlayerState multiplayer compilation errors; preserved existing source'
    if delivery['builds']['FPSGAME']['result'] == 'pending':
        delivery['builds']['FPSGAME']['result'] = 'not_run_after_editor_compile_failure'
preview_path = root / 'Previews/preview_manifest.json'
if preview_path.exists():
    previews = json.loads(preview_path.read_text('utf-8'))
    delivery.update(rendered=True, preview_manifest='Previews/preview_manifest.json',
                    preview_renderer=previews['renderer'], preview_count=len(previews['previews']),
                    game_capture=False)
inventory_path = root / 'Receipts/inventory-integration.json'
if inventory_path.exists():
    inventory = json.loads(inventory_path.read_text('utf-8'))
    delivery.update(stage='inventory_catalog_icons_and_models_saved',
        new_runtime_items_added=True, icons_created=True,
        inventory_footprints={i['id']:[i['grid_w'],i['grid_h']] for i in inventory['items']},
        inventory_icons='inventory_icons.json', loot_pool_changed=False)
    catalog['delivery'].update(new_runtime_items_added=True, icons_created=True,
        runtime_added_item_ids=[i['id'] for i in inventory['items']])
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for target in ('FPSGAMEEditor','FPSGAME'):
        log = root / 'Receipts' / ('build-inventory-'+target+'.log')
        if not log.exists():
            delivery['builds'][target] = dict(result='pending',log=str(log))
            continue
        lines = log.read_text(encoding='utf-8-sig',errors='replace').splitlines()
        result = next((line.strip() for line in reversed(lines) if line.startswith('Result:')), 'pending')
        delivery['builds'][target] = dict(result=result,log=str(log))
    if all('Succeeded' in b['result'] for b in delivery['builds'].values()):
        delivery['old_save_migration_binary_status'] = 'compiled_next_profile_load'
        delivery.pop('build_blocker',None)
    elif 'Failed' in delivery['builds']['FPSGAMEEditor']['result']:
        if delivery['builds']['FPSGAME']['result'] == 'pending':
            delivery['builds']['FPSGAME']['result'] = 'not_run_after_editor_compile_failure'
(root / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('DOCUMENT_DELIVERY_RECORDED', delivery['stage'], delivery['builds'])
