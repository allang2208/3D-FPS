"""Collect completed real-map seed runs and prepare contact sheets for manual review."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw

root=Path(__file__).resolve().parents[3]
batch=root/'Saved/VillageRuntimeReview/20261114'
config=json.loads((batch/'batch.json').read_text(encoding='utf-8'))
rows=[]
for seed in config['seeds']:
    run=batch/config.get('case_runs',{}).get(str(seed),str(seed)+'-repaired')
    data=json.loads((run/'Evidence/result.json').read_text(encoding='utf-8'))
    launch=json.loads((run/'launch.json').read_text(encoding='utf-8-sig'))
    if data['seed']!=seed or not data['pass'] or len(data['walls'])!=154 or len(data['routes'])!=19:
        raise RuntimeError('Incomplete or failed seed: '+str(seed))
    if any(not x['pass'] for x in data['walls']+data['routes']):
        raise RuntimeError('Failed individual check: '+str(seed))
    captures=sorted((run/'Evidence').glob('wall_*.png'))
    if len(captures)!=12:raise RuntimeError('Missing wall captures: '+str(seed))
    sheet=Image.new('RGB',(1440,1304),(225,225,225));draw=ImageDraw.Draw(sheet)
    for i,p in enumerate(captures):
        im=Image.open(p).convert('RGB');im.thumbnail((480,300));x=i%3*480;y=i//3*326
        sheet.paste(im,(x,y+26));draw.text((x+5,y+5),str(seed)+' / '+p.stem,fill='black')
    sheet.save(run/'Evidence/wall-sheet.jpg')
    exit_path=run/'exit.json'
    exit_state=json.loads(exit_path.read_text(encoding='utf-8-sig')) if exit_path.exists() else None
    rows.append(dict(seed=seed,run=str(run),exit_state=exit_state,wall_count=len(data['walls']),terrain_contact_points=data['terrain_collision_samples'],
                     road_direction_runs=12,house_round_trips=7,walked_m=round(sum(r['walked_cm'] for r in data['routes'])/100,2),
                     max_gap_cm=max(w['max_ground_gap_cm'] for w in data['walls']),
                     max_extra_burial_cm=max(w['max_extra_burial_cm'] for w in data['walls']),
                     crouched=any(r['crouched'] for r in data['routes']),airborne=any(r['airborne'] for r in data['routes']),
                     village_origin=data['village_origin'],village_yaw=data['village_yaw'],side_lane=data['side_lane'],
                     module_sha256=launch['module_sha256'],wall_screenshots=len(captures),pass_result=True))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
changed_saves=[p for p,h in config['production_save_hashes_before'].items() if not (root/p).exists() or sha(root/p)!=h]
report=dict(seeds=rows,wall_instances_checked=sum(r['wall_count'] for r in rows),
            terrain_contact_points=sum(r['terrain_contact_points'] for r in rows),
            standing_routes=95,walked_m=round(sum(r['walked_m'] for r in rows),2),
            original_production_saves_changed=changed_saves,
            village_map_sha256_after=sha(root/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'),
            visual_contact_sheet_review='pending manual viewing',
            fix='Eastern courtyard road dogleg avoids House 06 northwest masonry; road texture and native PCG exclusions saved.')
(batch/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
