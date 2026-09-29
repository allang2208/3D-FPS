"""Publish only the completed chainmail family, retaining current gameplay data."""

if __name__ == "__main__":
    raise RuntimeError("Historical garment publication retired. Use garment_pipeline.py candidates and gate; do not overwrite current rig-specific repairs.")

import json
import shutil
from pathlib import Path
P=Path(__file__).resolve().parents[2]
R=P/'SourceAssets/ChainmailInterlace20260929'
ITEM='ue_chainmail_shirt';FAMILY='ChainmailInterlace20260929'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    production=read(R/'production.json');before=read(R/'before.json');mats=read(R/'materials-saved.json')
    records={r['profile']:read(R/'Saved'/(r['profile']+'.json')) for r in read(R/'manifest.json')}
    config_path=P/'Content/ColdSteelData/modular_outfits.json';items_path=P/'Content/ColdSteelData/items.json'
    config=read(config_path);items=read(items_path);recipe=config['items'][ITEM];item=items[ITEM]
    if recipe!=before['recipe'] and recipe.get('appearance_family')!=FAMILY:
        raise RuntimeError('Chainmail recipe changed while authoring; keep the current data')
    if item['world_mesh']!=before['item']['world_mesh']:raise RuntimeError('Chainmail pickup changed while authoring')
    icon='Icons/'+FAMILY+'/'+ITEM+'.png';destination=P/'Content/ColdSteelData'/icon;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(R/(ITEM+'.png'),destination)
    recipe.update(appearance_family=FAMILY,material='',rig_meshes={k:v['mesh'] for k,v in records.items()})
    item.update(ue_icon=icon,world_material=mats['standard'],
        desc='灰钢锁环交错覆盖衣身与双臂，磨亮环面与暗色衬底形成层次，袖口采用实体金属环和暗色包边，可与手套独立搭配。')
    write(config_path,config);write(items_path,items)
    write(R/'published.json',dict(recipe=recipe,item_definition=item,materials=mats,profiles=records,
        production=production,icon=str(destination),body_parallax=False,pickup_parallax=False,
        first_person_cuff_geometry=True,body_and_pickup_geometry_preserved=True,
        new_animations=0,stats_changed=False,runtime_tested=False,refresh='next game session'))
    print('CHAINMAIL_INTERLACE_PUBLISHED',ITEM,len(records),'profiles',flush=True)


if __name__=='__main__':main()
