"""Publish already-saved materials through the shirt's existing override path.

No Unreal process or mesh mutation is required. Current PIE reads the new recipe
on the next session; this does not end or restart the user's active game.
"""
import json
import shutil
from pathlib import Path

P=Path(__file__).resolve().parents[2]
R=P/'SourceAssets/ChainmailRelief20260929'
ITEM='ue_chainmail_shirt';ICON='Icons/ChainmailRelief20260929/ue_chainmail_shirt.png'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    production=read(R/'production.json');before=read(R/'before.json');mats=read(R/'materials-saved.json')
    cfgpath=P/'Content/ColdSteelData/modular_outfits.json';itempath=P/'Content/ColdSteelData/items.json'
    cfg=read(cfgpath);items=read(itempath);current=cfg['items'][ITEM];item=items[ITEM]
    if current!=before['recipe'] and current.get('appearance_family')!='ChainmailRelief20260929':
        raise RuntimeError('Chainmail recipe changed during authoring; publication stopped without overwriting it')
    if item.get('world_mesh')!=before['item']['world_mesh']:
        raise RuntimeError('Chainmail pickup changed during authoring; publication stopped')
    recipe=dict(current,material=mats['relief'],appearance_family='ChainmailRelief20260929')
    item.update(ue_icon=ICON,world_material=mats['standard'],
                desc='灰钢锁环交错覆盖双臂与躯干，交叠环面、暗色衬底和细微锻纹形成清晰层次，沿用长袖版型与收口袖缘，可与手套独立搭配。')
    icon=P/'Content/ColdSteelData'/ICON;icon.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(R/(ITEM+'.png'),icon)
    cfg['items'][ITEM]=recipe;items[ITEM]=item;write(cfgpath,cfg);write(itempath,items)
    write(R/'published.json',dict(item=ITEM,recipe=recipe,item_definition=item,materials=mats,
          profiles=recipe['rig_meshes'],pickup=item['world_mesh'],icon=str(icon),
          saved_material_assets=6,integration='existing shirt material override; no skeletal/static mesh reimport',
          geometry_changed=False,weights_changed=False,lods_preserved=True,high_poly_runtime=False,
          body_material='same outfit material, with distance/mip/grazing parallax fade',
          pickup_parallax=False,stats_changed=False,new_animations=0,runtime_tested=False,
          refresh='next game session; active PIE left running',production=production))
    print('CHAINMAIL_RELIEF_PUBLISHED',ITEM,len(recipe['rig_meshes']),'existing profiles; six saved material assets')


if __name__=='__main__':main()
