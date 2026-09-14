"""User-requested inspection of the currently referenced 715 rain materials."""
import json, re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1];L=u.MaterialEditingLibrary
source=(ROOT/'Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h').read_text()
path=re.search(r'MeshPath = TEXT\("([^"]+)"\)',source).group(1)
mesh=u.load_asset(path)
report={'mesh':path,'libraries':{},'scope':'Material asset bindings and wet shader parameters; no gameplay/render test'}
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'));rows=[]
    for slot in mesh.materials:
        dry=slot.material_interface
        if 'DW715' not in dry.get_name():continue
        wet=mapping.get(dry.get_path_name())
        rows.append(dict(slot=str(slot.material_slot_name),dry=dry.get_path_name(),wet=wet.get_path_name() if wet else None,
                         wet_parameter=bool(wet and 'WeaponWetness' in [str(n) for n in L.get_scalar_parameter_names(wet)])))
    report['libraries'][path]=rows
(O/'rain-before.json').write_text(json.dumps(report,indent=2))
u.log('DW715_RAIN_BINDINGS_READ '+json.dumps(report))
