from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
models=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
icons=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
installed=json.loads((ROOT/'Receipts/installation.json').read_text('utf-8'))
integration=json.loads((ROOT/'Receipts/inventory-integration.json').read_text('utf-8'))
report=dict(stage='models_icons_and_catalog_saved',items=[i['id'] for i in integration['items']],
    meshes=len(models['assets']),materials=5,pbr_textures=15,icons=len(icons['icons']),
    installed_packages=len(installed['packages']),
    inventory_footprints={i['id']:[i['grid_w'],i['grid_h']] for i in integration['items']},
    runtime_recipes_changed=False,loot_pool_changed=False,player_inventory_changed=False,
    icon_rendered=True,extra_preview_rendered=False,tests_run=False,builds={})
for target in ('FPSGAMEEditor','FPSGAME'):
    log=ROOT/'Receipts'/('build-'+target+'.log')
    text=log.read_text('utf-8-sig',errors='replace') if log.exists() else ''
    status=next((s.strip() for s in reversed(text.splitlines()) if s.startswith('Result:')),'pending')
    report['builds'][target]=dict(result=status,log=str(log))
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MAINTENANCE_DELIVERY_SAVED',report['builds'])
