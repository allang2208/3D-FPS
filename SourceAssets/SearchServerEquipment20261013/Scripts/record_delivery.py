"""Record model and inventory delivery without changing drop pools."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
models=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
imported=json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))
installed=json.loads((ROOT/'Receipts/installation.json').read_text('utf-8'))
inventory_path=ROOT/'Receipts/inventory-integration.json'
inventory=json.loads(inventory_path.read_text('utf-8')) if inventory_path.exists() else None
catalog_path=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
catalog=json.loads(catalog_path.read_text('utf-8'))
assets={a['id']:a for a in models['assets'].values()}
meshes={m['item_id']:m for m in imported['meshes']}
for item in catalog['items']:
    if item['id'] not in assets:continue
    # Preserve a later user-directed model revision when recording this original batch.
    if item['model'].get('status') in ('reference_remodel_assets_installed','original_marks_assets_installed','neutral_pcb_assets_installed'):continue
    asset=assets[item['id']];mesh=meshes[item['id']]
    item['status']='runtime_catalog_and_art_integrated_loot_pending' if inventory else 'model_assets_saved_runtime_item_pending'
    item['model'].update(status='ue_assets_saved_and_installed',
        actual_dimensions_cm=mesh['dimensions_cm'],triangles_lod0=asset['triangles_lod0'],texture_size=asset['size'],
        source=str(Path(asset['source']).relative_to(PROJECT)).replace('\\','/'),
        fbx=str(Path(asset['fbx']).relative_to(PROJECT)).replace('\\','/'),
        glb=str(Path(asset['glb']).relative_to(PROJECT)).replace('\\','/'),
        ue_mesh=mesh['path'],ue_material=mesh['material'])
catalog['delivery']['modeled_item_ids']=list(dict.fromkeys(catalog['delivery'].get('modeled_item_ids',[])+list(assets)))
catalog['delivery'].update(server_models_created=True,server_model_delivery='Docs/Art/search-server-equipment-models-20261013.md')
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=dict(stage=installed['stage'],item_ids=list(assets),
    meshes=len(imported['meshes']),materials=len(imported['materials']),textures=len(imported['textures']),
    installed_packages=len(installed['packages']),
    source_formats=['Blender','FBX','GLB','PNG PBR'],
    import_route='Same-version UE 5.8 content-only host; identical package paths installed into main project',
    material_compile_errors=imported['material_compile_errors'],
    runtime_items_changed=False,loot_pool_changed=False,icons_created=False,
    preview_rendered=False,tests_run=False,native_build_required=bool(inventory))
if inventory:
    icons=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
    report.update(stage='models_icons_and_catalog_saved',runtime_items_changed=True,icons_created=True,
        icon_count=len(icons['icons']),inventory_icons='inventory_icons.json',
        inventory_footprints={i['id']:[i['grid_w'],i['grid_h']] for i in inventory['items']},builds={})
    for target in ('FPSGAMEEditor','FPSGAME'):
        log=ROOT/'Receipts'/('build-inventory-'+target+'.log')
        contents=log.read_text('utf-8-sig',errors='replace') if log.exists() else ''
        result=next((s.strip() for s in reversed(contents.splitlines()) if s.startswith('Result:')),'pending')
        report['builds'][target]=dict(result=result,log=str(log))
    if 'Failed' in report['builds']['FPSGAMEEditor']['result'] and report['builds']['FPSGAME']['result']=='pending':
        report['builds']['FPSGAME']['result']='not_run_after_editor_compile_failure'
    if 'Failed' in report['builds']['FPSGAMEEditor']['result']:
        report['native_integration_status']='source_saved_build_blocked'
        report['build_blocker']='Existing ColdSteelSharedInventorySubsystem.cpp: undeclared ColdSteelCompartment and private StampProductionDrop access'
    elif all('Succeeded' in entry['result'] for entry in report['builds'].values()):
        report['native_integration_status']='editor_and_game_built'
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SERVER_DELIVERY_SAVED',report['stage'],report.get('builds',{}))
