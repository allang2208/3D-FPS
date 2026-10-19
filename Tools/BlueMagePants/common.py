"""Approved V2 mage suit-trouser production constants."""
import json,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMagePants20261019'
KEY='ue_blue_mage_pants';FAMILY='BlueMagePants20261019';DEST='/Game/Characters/ModularOutfit20260924/'+FAMILY
SLOTS=['BlackWorsted','CobaltPiping','SilverEmbroidery','DarkThread','BlackFacing','SilverClasp','Sapphire','NativeSkin']
VARIANTS=['Jason_BlueMagePants','Jason_BlueMagePants_ShortBootsFit','Jason_BlueMagePants_HighBootsFit','Jason_BlueMagePants_ST6BootsFit']
ITEM=dict(id=KEY,name='黑色法师长裤',category='equipment',type='裤装',equipSlot='pants',stack_max=1,maxStack=1,price=30,grid_w=2,grid_h=3,defense={'base':4},desc='哑黑精纺织物长裤，采用修身西裤剪裁、浅褶与平直裤脚，细蓝侧边和银色星藤纹呼应法师套装。',ue_icon='Icons/'+FAMILY+'/'+KEY+'.png',icon_fallback='裤',world_material='',ue_icon_pitch=0,ue_icon_yaw=0)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,data):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
