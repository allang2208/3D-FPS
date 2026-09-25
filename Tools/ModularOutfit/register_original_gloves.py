"""Register an equippable restoration of the original first-person arm mesh."""
import json
from pathlib import Path

ITEM_ID='ue_original_gloves'

def add_original_gloves(items,config):
    # Reuse the existing leather-glove inventory icon and dropped-item prop.
    # Equipped appearance comes from the original weapon, not this prop mesh.
    definition=dict(items['ue_field_gloves'])
    definition.update(id=ITEM_ID,name='原版战术手套',price=20,
        desc='穿戴后恢复原版手套与整套手臂、衣袖外观；卸下后回到当前默认手部外观。')
    items[ITEM_ID]=definition
    config['items'][ITEM_ID]={'slot':3,'part':'gloves','first_person_mode':'source_arms'}

if __name__=='__main__':
    root=Path('D:/FPS3D/FPSGAME')
    item_path=root/'Content/ColdSteelData/items.json'
    outfit_path=root/'Content/ColdSteelData/modular_outfits.json'
    items=json.loads(item_path.read_text(encoding='utf-8-sig'))
    config=json.loads(outfit_path.read_text(encoding='utf-8-sig'))
    add_original_gloves(items,config)
    item_path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    outfit_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ORIGINAL_GLOVES_REGISTERED',ITEM_ID)
