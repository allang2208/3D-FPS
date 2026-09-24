import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog):
    catalog=copy.deepcopy(catalog)
    mapping=json.loads((ROOT/'Config/mesh-variants.json').read_text())
    materials=json.loads((ROOT/'Config/material-remap.json').read_text())
    reverse={v:k for k,values in mapping.items() for v in values}
    for module in catalog['modules']:
        for owner in [module]+module.get('side_sockets',[]):
            for part in owner.get('parts',[]):
                path=part.get('mesh','').split('.')[0];source=reverse.get(path,path)
                if source in mapping:
                    part['mesh']=mapping[source][0];part['surface_mesh_variants']=mapping[source]
                part['materials']=[materials.get(p.split('.')[0],p) for p in part.get('materials',[])]
    catalog['wall_damage_version']=2
    return catalog
