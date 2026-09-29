"""Register the saved V7 original leather gloves without restoring old sleeves."""
import json
from pathlib import Path

ITEM_ID='ue_original_gloves'

def add_original_gloves(items,config):
    from original_leather_gloves import ROOT, read
    detail=ROOT.parents[1]/'GloveCompanionDetail20260928/Tactical/published.json'
    current=detail if detail.exists() else ROOT.parent/'OriginalLeatherV2/published.json'
    receipt=read(current if current.exists() else ROOT/'published.json')
    definition=dict(items.get(ITEM_ID,items['ue_field_gloves']))
    definition.update(id=ITEM_ID,name='原版战术手套',price=20)
    definition.update(receipt['appearance'])
    items[ITEM_ID]=definition
    config['items'][ITEM_ID]=receipt['recipe']

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
