"""Bounded container bays and a restroom chest using accepted interaction assets."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
for name in ('Config','Receipts','Backup'):(ROOT/name).mkdir(parents=True,exist_ok=True)
prototypes=read(PROJECT/'SourceAssets/WarehouseContainers20261002/Authored/manifest.json')['prototypes']
oldrules=read(PROJECT/'SourceAssets/WarehouseContainers20261002/Config/containers.json')
remap=read(PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Config/text-asset-remap.json')
BASE='/Game/Dungeons/WarehouseContainers20261002/Meshes/'
captions=dict(WoodCrate='加固运输木箱',MetalCase='金属设备箱',Tote='物资周转箱',ToolCabinet='维护工具柜',ToolDrawer='工具柜抽屉')
def spec(key,p,yaw,identity):
    c=copy.deepcopy(prototypes[key]);c.pop('dimensions_m',None)
    c.update(type='scene_container',position=p,yaw=yaw,container_id=identity,caption=captions[key],initial_open_fraction=0)
    for part in ('body','door'):
        path=BASE+c[part];c[part]=remap.get(path,path)
    return c
def cargo_slot(identity,p,yaw,axis=0):
    variants=[]
    for i,key in enumerate(('WoodCrate','MetalCase','Tote')):
        q=list(p);q[axis]+=(-6,5,1)[i]
        variants.append(dict(containers=[spec(key,q,yaw+(-4,5,-2)[i],identity+'.'+key)]))
    return dict(id=identity,variants=variants)

# Lower floor and 60 cm dock are distinct support surfaces. Keep both stair
# approaches, the entry centre line, original pallets, east rack and gate clear.
freight_groups=[dict(id='LootExpansion.TransferCargo',pick_count=[2,3],slots=[
    cargo_slot('FreightTransfer.EntryWest',[490,-460,0],90,1),
    cargo_slot('FreightTransfer.EntryEast',[1310,-650,0],-90,1),
    cargo_slot('FreightTransfer.DockWest',[130,-1710,60],90,1),
    cargo_slot('FreightTransfer.DockEast',[1680,-1710,60],-90,1)]),
    dict(id='LootExpansion.TransferMaintenance',pick_count=[1,1],slots=[
        dict(id='FreightTransfer.Maintenance.West',variants=[dict(containers=[
            spec('ToolCabinet',[55,-1300,0],90,'FreightTransfer.Tools.West'),
            spec('ToolDrawer',[55,-1300,0],90,'FreightTransfer.Tools.West.Drawer')])]),
        dict(id='FreightTransfer.Maintenance.East',variants=[dict(containers=[
            spec('ToolCabinet',[1745,-1030,0],-90,'FreightTransfer.Tools.East'),
            spec('ToolDrawer',[1745,-1030,0],-90,'FreightTransfer.Tools.East.Drawer')])])])]

# New independent bays supplement the existing pallet/rack replacements.
# Ground south wall and west corner; dock top is exactly 120 cm. Avoid stairs,
# the roller bed, the power cabinet and the three existing maintenance bays.
warehouse_groups=[dict(id='LootExpansion.WarehouseReserve',pick_count=[3,4],slots=[
    cargo_slot('CargoWarehouse.Reserve.SouthWest',[-1230,1260,0],0),
    cargo_slot('CargoWarehouse.Reserve.SouthMiddle',[-650,1270,0],0),
    cargo_slot('CargoWarehouse.Reserve.SouthEast',[1290,1260,0],0),
    cargo_slot('CargoWarehouse.Reserve.DockMiddle',[-200,-1240,120],180),
    cargo_slot('CargoWarehouse.Reserve.DockEast',[1180,-1250,120],180),
    cargo_slot('CargoWarehouse.Reserve.WestCorner',[-1370,-710,0],90,1)])]

catalog=read(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json')
chest=copy.deepcopy(next(m for m in catalog['modules'] if m['id']=='Treasure')['props'][0])
chest.update(position=[1035,-915,.4],yaw=90,role='staff_restroom_cache',identity='staff_activity_restroom',scene_loot_expansion=True)
rules=dict(revision=1,owner='SceneLootExpansion20261003',freight_groups=freight_groups,
    warehouse_groups=warehouse_groups,restroom_chest=chest,outline=oldrules['outline'],
    preview_seed=20261003,freight_count=[4,5],warehouse_additional_count=[3,4],warehouse_total_count=[12,17],
    restroom_location='Original northeast wall inset, southwest interior corner; door, floor drain, sink and stall kept clear',
    rewards_deferred=True,tests_run=False,rendered=False)
(ROOT/'Config/layout.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf8')
print('SCENE_LOOT_LAYOUT_AUTHORED: transfer 4-5, warehouse +3-4, staff restroom +1 chest')
