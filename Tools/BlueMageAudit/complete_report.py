"""Collect final receipts, preserving the distinction between wire and visual coverage."""
import json,hashlib,re
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageSetAudit20261019'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sources=read(R/'source-audit-all-profiles-fixed.json');saved=read(R/'saved-render-audit.json');sections=read(R/'sections-resaved.json');wire=read(R/'wire-receipt.json');cases=read(Path(wire['directory'])/'host.json');lower=read(R/'lower-fit-and-motion.json');publish=read(R/'publish-regression.json')
owned={p for p in saved['meshes'] if p.startswith('/Game/Characters/ModularOutfit20260924/BlueMage')}
assert saved.get('completed') and saved['passed'] and not sources['failures']
assert sections['completed'] and owned<=set(sections['assets'])
assert wire['passed'] and len(cases['cases'])==14 and all(c['passed'] for c in cases['cases'])
asymmetric=sum(len(m:=re.findall(r'\bmask=(\d+)',row['client']))==2 and m[0]!=m[1] for row in cases['cases'])
assert asymmetric==10,'Final wire run must include divergent host/client outfits'
exits=read(Path(wire['directory'])/'peer-exits.json');assert len(exits)==3 and all(row['exit_code']==0 for row in exits),exits
assert lower['passed'] and all(v for k,v in publish.items() if k.endswith('preserved'))
log=(R/'final-readback-01.log').read_text(encoding='utf-8',errors='replace')
owned_warnings=[line for line in log.splitlines() if 'Fix some section data' in line and 'BlueMage' in line]
assert not owned_warnings,owned_warnings
report=dict(completed=True,source_meshes=len(sources['geometry']),rig_profiles=len(sources['profiles']),saved_meshes=len(saved['meshes']),render_lods=sum(len(v['render_lods']) for v in saved['meshes'].values()),mage_assets_resaved=len(owned),wire_cases=len(cases['cases']),asymmetric_outfit_cases=asymmetric,peer_exits=exits,wire=wire,trouser_combinations=len(lower['trouser_fits']),movement_clips=len(lower['clips']),movement_poses=sum(v['samples'] for v in lower['clips'].values()),minimum_shaft_clearance_cm=-max(v['max_gap_cm'] for v in lower['trouser_fits'].values()),minimum_sampled_collider_margin_cm=-max(v['max_gap_cm'] for v in lower['clips'].values()),underlayers_preserved=publish['underlayer_count'],rendered_runtime_tested=False,limitations=['No rendered stair or long-duration Chaos cloth acceptance','Listen host plus one client and reconnect; not a dedicated-server or 3+ player test','Gait evaluation samples source poses and collider envelopes, not runtime stair IK/cloth solve'])
(R/'completed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
doc=P/'Docs/Characters/blue-mage-set-audit-20261019.md';doc.write_text(doc.read_text(encoding='utf-8').replace('Wire/20261019-174302/', 'Wire/'+Path(wire['directory']).name+'/'),encoding='utf-8')
for filename,before,after in [('blue-mage-boots-20261019.md','109,334','106,712'),('blue-mage-pants-20261019.md','63,028','63,012')]:
    path=P/'Docs/Characters'/filename;text=path.read_text(encoding='utf-8').replace(before,after)
    if 'blue-mage-set-audit-20261019.md' not in text:text+='\n\n2026-10-19 用户要求的衣物与联机复核、已修复项和实测边界见 [法师套装复核](blue-mage-set-audit-20261019.md)。\n'
    path.write_text(text,encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
