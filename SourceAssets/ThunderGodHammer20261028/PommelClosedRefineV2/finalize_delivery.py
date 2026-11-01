from pathlib import Path
import json,datetime
P=Path(__file__).resolve().parent
build_path=max(P.glob('build-*-receipt.json'),key=lambda p:p.stat().st_mtime)
build=json.loads(build_path.read_text(encoding='utf-8-sig'))
publication=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
parts={}
for kind in ['LeiXi','ZhenTing']:
 model=json.loads((P/kind/'model_manifest.json').read_text(encoding='utf-8'))
 receipt=json.loads((P/kind/'import_receipt.json').read_text(encoding='utf-8'))
 parts[kind]={'model':model,'saved_assets':receipt['saved_assets'],'assets_saved':receipt['complete'],'mesh':receipt['mesh'],'icon':receipt['icon']}
delivery={'complete':build['exit_code']==0 and publication['complete'] and all(x['assets_saved'] for x in parts.values()),'finished':datetime.datetime.now().astimezone().isoformat(),'models':parts,'publication':publication,'build':build,'build_receipt':build_path.name,'additional_strikes_seconds':[.25,.50,.75],'gameplay_tested':False,'multiplayer_tested':False,'editor_started_by_task':False,'geometry_scope':'User-reported open/back-facing surfaces: diagnosed old sources; closed construction exported with zero boundary and multi-face edges. No gameplay acceptance.'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'complete':delivery['complete'],'saved_assets':sum(len(x['saved_assets']) for x in parts.values()),'build_exit_code':build['exit_code']},ensure_ascii=False))
