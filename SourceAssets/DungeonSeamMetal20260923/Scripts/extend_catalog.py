"""Keep the seam reservation and material overrides through future catalog rebuilds."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog):
    mapping=json.loads((ROOT/'Config/material-remap.json').read_text(encoding='utf-8'))
    def replace(value):
        if isinstance(value,str):return mapping.get(value.split('.')[0],value)
        if isinstance(value,list):return [replace(v) for v in value]
        if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
        return value
    catalog=replace(catalog)
    for module in catalog['modules']:
        if module['id']=='TreasureLink':
            module['min']=[-180,-200,-22];module['max']=[180,0,302]
            module['cells']=[dict(min=module['min'],max=module['max'])]
            module['portal_geometry']=dict(owner='adjoining_room',frame_depth_cm=29,skin_setback_cm=15,reveal_recess_cm=4)
    return catalog
