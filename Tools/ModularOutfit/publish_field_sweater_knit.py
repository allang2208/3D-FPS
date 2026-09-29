"""Publish saved garment families and matching icons, preserving item identity."""

if __name__ == "__main__":
    raise RuntimeError("Historical garment publication retired. Use garment_pipeline.py candidates and gate; do not overwrite current rig-specific repairs.")

import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterKnit20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 assets=read(R/'saved-assets.json');before=read(R/'before.json')
 for build in ['build-editor.txt','build-game.txt']:
  if 'Result: Succeeded' not in (R/build).read_text(encoding='utf-8-sig',errors='replace'):raise RuntimeError('Required native build not complete '+build)
 cp=P/'Content/ColdSteelData/modular_outfits.json';ip=P/'Content/ColdSteelData/items.json';cb=cp.read_bytes();ib=ip.read_bytes();c=read(cp);items=read(ip)
 for key,variant in [('ue_field_sweater','Olive'),('ue_field_sweater_charcoal','Charcoal')]:
  recipe=c['items'][key]
  if recipe!=before['recipes'][key]:raise RuntimeError('Clothing recipe changed during production '+key)
  group=assets[variant]
  for asset in list(group['profiles'].values())+[group['pickup']]:
   if not (P/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file():raise RuntimeError('Missing saved asset '+asset)
  recipe.update(appearance_family='FieldSweaterKnit20260929' if variant=='Olive' else 'CharcoalCottonTShirt20260929',rig_meshes=group['profiles'],material='')
  if variant=='Charcoal':recipe.update(covers=[],world_covers=[3])
  icon='Icons/FieldSweaterKnit20260929/'+key+'.png';dest=P/'Content/ColdSteelData'/icon;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(key+'.png'),dest)
  items[key].update(ue_icon=icon,world_mesh=group['pickup'],world_material='')
  if variant=='Charcoal':items[key].update(name='炭灰短袖 T恤',desc='炭灰色细密棉布短袖 T恤，上臂袖口向内卷边，露出下段上臂和前臂，可与手套独立搭配。')
 if cp.read_bytes()!=cb or ip.read_bytes()!=ib:raise RuntimeError('Equipment data changed before publication')
 (R/'config-before-publication.json').write_bytes(cb);(R/'items-before-publication.json').write_bytes(ib)
 write(cp,c);write(ip,items);write(R/'published.json',dict(assets=assets,short_sleeve_coverage=dict(first_person=[],body=[3]),native_editor_build=True,native_game_build=True,runtime_tested=False))
 print('GARMENTS_PUBLISHED',sum(len(v['profiles']) for v in assets.values()),'rig meshes; two pickups and icons')
if __name__=='__main__':main()
