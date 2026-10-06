"""Add only the saved chainmail trousers definition and Jason outfit recipe."""
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailPants20261004';D=P/'Content/ColdSteelData'
ITEM='ue_chainmail_pants'

def insert(raw,offset,key,value,indent):
    lines=json.dumps({key:value},ensure_ascii=False,indent=2)[1:-1].strip('\n').splitlines()
    text='\n'.join(' '*indent+line for line in lines)
    return raw[:offset]+('\n'+text+',').encode('utf-8')+raw[offset:]

def main():
    saved=json.loads((R/'saved_assets.json').read_text())
    outfit_path=D/'modular_outfits.json';item_path=D/'items.json'
    outfits_raw=outfit_path.read_bytes();items_raw=item_path.read_bytes()
    outfits=json.loads(outfits_raw.decode('utf-8-sig'));items=json.loads(items_raw.decode('utf-8-sig'))
    if ITEM in items or ITEM in outfits['items']:raise RuntimeError('Definition already exists; preserve the current published item')
    item=dict(id=ITEM,name='灰钢锁子甲裤',category='equipment',type='裤装',equipSlot='pants',
        rarity='common',stack_max=1,maxStack=1,price=65,grid_w=2,grid_h=3,defense={'base':40},
        desc='灰钢锁环织成的防护长裤，分片护腰覆盖胯部，金属护膝与上下叠片保护膝盖。裤腿渐收，裤口带内衬包边，可搭配休闲鞋或皮靴。',
        ue_icon='Icons/ue_chainmail_pants.png',icon_fallback='甲',world_mesh=saved['pickup'],world_material='',
        ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
    recipe=dict(slot=15,material='',appearance_family='ChainmailPants20261004',
        rig_meshes={'Jason':saved['standard']},
        rig_world_covers={'Jason':outfits['items']['ue_jeans']['rig_world_covers']['Jason'][:]},
        shoe_fit_meshes={'ue_boots':{'Jason':saved['boots']}})
    item_output=insert(items_raw,items_raw.index(b'{')+1,ITEM,item,0)
    anchor=outfits_raw.index(b'"items"');offset=outfits_raw.index(b'{',anchor)+1
    outfit_output=insert(outfits_raw,offset,ITEM,recipe,2)
    (R/'items-before.json').write_bytes(items_raw);(R/'outfits-before.json').write_bytes(outfits_raw)
    # Detect a concurrent edit before this short two-file publication window.
    if item_path.read_bytes()!=items_raw or outfit_path.read_bytes()!=outfits_raw:raise RuntimeError('Catalog changed during publication; no writes made')
    outfit_path.write_bytes(outfit_output);item_path.write_bytes(item_output)
    (R/'published.json').write_text(json.dumps(dict(item=item,recipe=recipe,saved=saved,
        refresh='next inventory/catalog load and outfit refresh',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
    print('CHAINMAIL_PANTS_PUBLISHED',ITEM,flush=True)

if __name__=='__main__':main()
