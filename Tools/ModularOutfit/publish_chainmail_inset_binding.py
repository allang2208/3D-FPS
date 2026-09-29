"""Publish the fully saved inset cuff family without changing other equipment."""

if __name__ == "__main__":
    raise RuntimeError("Historical garment publication retired. Use garment_pipeline.py candidates and gate; do not overwrite current rig-specific repairs.")

import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailInsetBinding20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 records=[read(R/'Saved'/(row['profile']+'.json')) for row in read(R/'manifest.json')]
 path=P/'Content/ColdSteelData/modular_outfits.json';before_bytes=path.read_bytes();c=read(path);recipe=c['items']['ue_chainmail_shirt']
 if recipe!=read(R/'before.json'):raise RuntimeError('Chainmail changed during authoring; preserve live recipe')
 for row in records:
  asset=P/'Content'/(row['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')
  if not asset.is_file():raise RuntimeError('Missing saved cuff '+row['profile'])
  recipe['rig_meshes'][row['profile']]=row['mesh']
 recipe['appearance_family']='ChainmailInsetBinding20260929'
 if path.read_bytes()!=before_bytes:raise RuntimeError('Configuration changed before publication')
 (R/'configuration-before.json').write_bytes(before_bytes)
 path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (R/'published.json').write_text(json.dumps(dict(recipe=recipe,assets=len(records),runtime_tested=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('INSET_BINDING_PUBLISHED',len(records),'assets')
if __name__=='__main__':main()
