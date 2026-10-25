"""Record producer fingerprints only after actual saved-asset publication."""
import json,os,runpy
from pathlib import Path
from pending import signatures,REG
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
publication=json.loads((R/'published.json').read_text())
if publication['status']!='saved_and_integrated':raise RuntimeError('Publish saved assets first')
original=R/'plan.json';text=original.read_bytes();produced=json.loads(text)
try:
    runpy.run_path(str(P/'Tools/BackpackFit/prepare.py'),run_name='__main__')
    current=json.loads(original.read_text(encoding='utf-8'))
    routes=json.loads(REG.read_text(encoding='utf-8')).get('routes',{}) if REG.exists() else {}
    updated=signatures(current)
    for row in produced['rows']:
        key='/'.join([row['rig'],row['item'],row['shirt'] or 'bare']);routes[key]=updated[key]
finally:original.write_bytes(text)
REG.write_text(json.dumps({'revision':R.name,'routes':routes,'meaning':'Production dependency fingerprints, not gameplay acceptance'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BACKPACK_FIT_REGISTERED',len(routes))
