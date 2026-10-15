"""Scoped station placement update; preserve every unrelated module/prop field."""
import copy,json
from pathlib import Path

STATION='AbandonedTransitStation'
CHEST_ID='station_upper_platform'
CHEST_POSITION=[2960,-780,.5]
UPPER_WALK=dict(min=[2225,-1620,475],max=[2765,1620,760])
SOURCES=[
    'DungeonTransitStation20260928/Config/module.json',
    'DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'DungeonSplitLevels20261001/Config/catalog.json','WarehouseContainers20261002/Config/catalog.json',
    'DungeonStaffLiving20261002/Production20261002/Config/catalog.json','SceneLootExpansion20261003/Config/catalog.json',
    'StationWorkshop20261003/Config/catalog.json','StationWorkshop20261003/RefineV2/Config/catalog.json',
    'StationWorkshop20261003/RefineV3/Config/catalog.json','StationWorkshop20261003/RefineV4/Config/catalog.json',
    'StationWorkshop20261003/Config/workshop.json','StationWorkshop20261003/RefineV2/Config/workshop.json',
    'StationWorkshop20261003/RefineV3/Config/workshop.json','StationWorkshop20261003/RefineV4/Config/workshop.json']

def move_chest(value):
    if isinstance(value,dict):
        if value.get('identity')==CHEST_ID:
            value.update(position=list(CHEST_POSITION),yaw=180,role='station_ground_tunnel')
        for child in value.values():move_chest(child)
    elif isinstance(value,list):
        for child in value:move_chest(child)

def patch_module(module):
    result=copy.deepcopy(module)
    if result.get('id')!=STATION:return result
    move_chest(result)
    walks=result.setdefault('walk_mask',[])
    if not any(w.get('min')==UPPER_WALK['min'] and w.get('max')==UPPER_WALK['max'] for w in walks):
        walks.append(copy.deepcopy(UPPER_WALK))
    import runpy
    result=runpy.run_path(str(Path(__file__).with_name('service_doors.py')))['patch_module'](result)
    return result

def patch_document(data):
    if 'modules' in data:
        result=copy.deepcopy(data)
        result['modules']=[patch_module(m) for m in result['modules']]
        return result
    if data.get('id')==STATION:return patch_module(data)
    result=copy.deepcopy(data);move_chest(result);return result

def update_sources(project,root):
    receipt=root/'Receipts/sources.json';receipt.parent.mkdir(parents=True,exist_ok=True)
    saved=json.loads(receipt.read_text(encoding='utf8')) if receipt.exists() else []
    for relative in SOURCES:
        path=project/'SourceAssets'/relative
        if not path.exists():continue
        text=path.read_text(encoding='utf-8-sig');data=json.loads(text);result=patch_document(data)
        if result==data:continue
        backup=root/'Backups'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_text(text,encoding='utf8')
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        if relative not in saved:saved.append(relative)
        receipt.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf8')
    return saved

if __name__=='__main__':
    project=Path(__file__).resolve().parents[2]
    print('FREIGHT_SOURCES_SAVED '+str(len(update_sources(project,project/'SourceAssets/FreightEncounter20261014'))))
