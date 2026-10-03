"""Author bounded warehouse slots using the existing cargo supports and blank wall bays."""
import json,math,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];BASE='/Game/Dungeons/WarehouseContainers20261002'
for key in ('Config','Receipts','Backup'): (ROOT/key).mkdir(parents=True,exist_ok=True)
prototypes=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))['prototypes']
source=json.loads((PROJECT/'SourceAssets/DungeonCargoWarehouse20261001/Config/room.json').read_text('utf8'))

def spec(key,position,yaw,identity,color=None):
    p=copy.deepcopy(prototypes[key]);p.pop('dimensions_m',None)
    p.update(type='scene_container',container_id='CargoWarehouse.'+identity,position=position,yaw=yaw,
        body=BASE+'/Meshes/'+p['body'],door=BASE+'/Meshes/'+p['door'])
    if color:
        p['body_materials']=[BASE+'/Materials/M_Warehouse_Polymer'+color]
        p['door_materials']=[BASE+'/Materials/M_Warehouse_Polymer'+color]
    return p

groups=[];floor=[];racks=[]
for cargo in source['reused_parts']:
    if cargo['id'].startswith('FloorCargo'):
        pos=[cargo['position'][0]*100,-cargo['position'][1]*100,cargo['position'][2]*100]
        variants=[]
        for key,angle in [('WoodCrate',-6),('MetalCase',5)]:
            variants.append(dict(containers=[spec(key,pos,-cargo['yaw']+angle,cargo['id']+'.'+key)]))
        floor.append(dict(id=cargo['id'],variants=variants))
    if cargo['id'].startswith('RackCargo') and cargo['position'][2]<.5:
        yaw=-cargo['yaw'];a=math.radians(yaw)
        # Front edge of a 44cm tote stays 9cm inside the accepted rack deck.
        p=[cargo['position'][0]*100+math.sin(a)*56,-cargo['position'][1]*100-math.cos(a)*56,20]
        variants=[dict(containers=[spec('Tote',p,yaw,cargo['id']+'.Tote',color)]) for color in ('Green','Blue','Gray')]
        racks.append(dict(id=cargo['id'],variants=variants))
groups.append(dict(id='PalletCargo',pick_count=[4,5],slots=floor))
groups.append(dict(id='ReachableRackCargo',pick_count=[3,4],slots=racks))
tools=[]
for identity,p,yaw in [('DockWest',[-1100,-1325,120],180),('DockCenter',[100,-1325,120],180),('SouthWall',[-300,1335,0],0)]:
    tools.append(dict(id='ToolBay.'+identity,variants=[dict(containers=[spec('ToolCabinet',p,yaw,'Tools.'+identity),
        spec('ToolDrawer',p,yaw,'Tools.'+identity+'.Drawer')])]))
groups.append(dict(id='MaintenanceBays',pick_count=[1,2],slots=tools))
staff=json.loads((PROJECT/'SourceAssets/DungeonStaffLiving20261002/Production20261002/Config/modules.json').read_text('utf8'))
data=dict(revision=1,groups=groups,outline=staff['container_outline'],
    preview_seed=20261002,rewards_deferred=True,placement='existing lower cargo and pallet footprints; blank maintenance wall bays',
    minimum_main_aisle_m=1.5,tests_run=False,rendered=False)
expansion=ROOT.parent/'SceneLootExpansion20261003';saved=expansion/'Receipts/install.json'
if saved.exists() and json.loads(saved.read_text('utf8')).get('stage')=='maps_saved':
    import runpy
    data=runpy.run_path(str(expansion/'Scripts/extend_catalog.py'))['expand_warehouse'](data)
(ROOT/'Config/containers.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

im=Image.new('RGB',(800,2400),(214,211,186));draw=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',58);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',29)
panels=[('货运物资 / 木箱','WH-04 | KEEP DRY | THIS SIDE UP'),('周转物资 / 配件','RETURNABLE BIN | A-12'),
 ('精密设备 / 小心搬运','FRAGILE | SEALED TRANSPORT CASE'),('设备维护 / 工具','MAINTENANCE | RETURN AFTER USE'),
 ('手工具 / 紧固件','HAND TOOLS | M6 / M8 / M10'),('装卸登记 / 批次','RECEIVING LOG | DOCK 02')]
for i,(cn,en) in enumerate(panels):
    y=i*400;draw.rectangle((12,y+12,788,y+388),outline=(31,44,42),width=6)
    draw.rectangle((18,y+18,782,y+67),fill=(31,44,42));draw.text((42,y+97),cn,font=font,fill=(24,28,26))
    draw.text((42,y+182),en,font=small,fill=(32,38,34))
    draw.text((42,y+235),'LOT 26-1002   /   BAY 03',font=small,fill=(32,38,34))
    for j in range(95):
        if (j*73+i*11)%7<4:draw.rectangle((45+j*4,y+292,47+j*4,y+349),fill=(24,28,26))
    draw.text((473,y+296),'HANDLE',font=small,fill=(32,38,34));draw.text((473,y+334),'WITH CARE',font=small,fill=(32,38,34))
im.save(ROOT/'Authored/T_Warehouse_Labels.png')
print('WAREHOUSE_CONTAINER_SLOTS_AUTHORED',len(floor),len(racks),len(tools),flush=True)
