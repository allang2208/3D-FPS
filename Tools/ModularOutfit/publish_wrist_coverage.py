"""Publish only fully saved wrist-coverage companions, preserving other edits."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/WristCoverage20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 plan=read(R/'plan.json');saved={j['source']:read(R/'Saved'/(j['key']+'.json')) for j in plan['jobs']}
 path=P/'Content/ColdSteelData/modular_outfits.json';original=path.read_bytes();c=read(path)
 for ref in plan['refs']:
  record=saved[ref['source']]
  target=c['profiles'][ref['key']] if ref['kind']=='profile' else c['items'][ref['key']]['skin_meshes']
  if target[ref['field']] not in [ref['source'],record['mesh']]:
   raise RuntimeError('Appearance source changed while authoring: '+ref['key'])
  if ref['kind']=='profile' and record['wrist_slot'] in c['profiles'][ref['key']].get('shirt_covers',[]):
   raise RuntimeError('Clothing coverage includes protected wrist section: '+ref['key'])
  package=record['mesh'].split('.')[0]
  asset=P/'Content'/(package.removeprefix('/Game/')+'.uasset')
  if not asset.is_file():raise RuntimeError('Saved asset missing: '+str(asset))
  target[ref['field']]=record['mesh']
 if path.read_bytes()!=original:raise RuntimeError('Configuration changed before publication')
 (R/'configuration-before-publication.json').write_bytes(original)
 write(path,c)
 write(R/'published.json',dict(assets=len(saved),references=len(plan['refs']),profiles=sorted({j['rig'] for j in plan['jobs']}),
  method='Existing distal forearm geometry assigned to WristUnderlapSkin, never hidden with shirt or gloves',
  native_positions_preserved=True,native_weights_preserved=True,shared_naked_assets_preserved=True,
  new_animations=0,lods=3,runtime_tested=False,refresh='next game session'))
 print('WRIST_COVERAGE_PUBLISHED',len(saved),'saved assets;',len(plan['refs']),'references')
if __name__=='__main__':main()
