"""Approved mage-boot production constants."""
import json,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageBoots20261019'
KEY='ue_blue_mage_boots';FAMILY='BlueMageBoots20261019';DEST='/Game/Characters/ModularOutfit20260924/'+FAMILY
SLOTS=['BlackLeather','CobaltWoven','SilverEmbroidery','DarkThread','BlackLining','RubberSole','Sapphire']
VARIANTS=['Jason_BlueMageBoots']
ITEM=dict(id=KEY,name='蓝黑法师长靴',category='equipment',type='鞋靴',equipSlot='boots',stack_max=1,maxStack=1,price=45,grid_w=2,grid_h=3,defense={'base':8},desc='黑色皮革与深蓝织物拼接的膝下长靴，银色星藤纹和蓝宝石扣呼应法师套装。靴口留有裤脚余量，柔软踝部搭配圆头低跟。',ue_icon='Icons/'+FAMILY+'/'+KEY+'.png',icon_fallback='靴',world_material='',ue_icon_pitch=0,ue_icon_yaw=0)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,data):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
for folder in ('Authored','Textures','Exports'):(R/folder).mkdir(parents=True,exist_ok=True)
