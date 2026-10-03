"""Install the refinement using the maintained parent production/preview installer."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
source=(PARENT/'Scripts/install_scenes.py').read_text('utf8')
source=source.replace("ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]",
    "ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]")
source=source.replace("ROOT/'Scripts/extend_catalog.py'","ROOT.parent/'Scripts/extend_catalog.py'")
exec(compile(source,'maintained_workshop_scene_installer','exec'))
(PARENT/'Config/workshop.json').write_text((ROOT/'Config/workshop.json').read_text('utf8'),encoding='utf8')
(PARENT/'Receipts/install.json').write_text((ROOT/'Receipts/install.json').read_text('utf8'),encoding='utf8')
(PARENT/'Config/catalog.json').write_text((ROOT/'Config/catalog.json').read_text('utf8'),encoding='utf8')
warehouse_config=PROJECT/'SourceAssets/WarehouseContainers20261002/Config/containers.json'
remap=rules.get('text_asset_remap',{})
def replace(value):
    if isinstance(value,str):return remap.get(value,value)
    if isinstance(value,list):return [replace(v) for v in value]
    if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
    return value
warehouse_config.write_text(json.dumps(replace(json.loads(warehouse_config.read_text('utf8'))),ensure_ascii=False,indent=2),encoding='utf8')
