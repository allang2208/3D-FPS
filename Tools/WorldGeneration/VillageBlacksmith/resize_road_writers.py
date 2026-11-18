"""Update only the authored road coordinate spans in the two existing RVT writers."""
import json,shutil
from pathlib import Path
import unreal as u
root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out=root/'SourceAssets/HillsVillageBlacksmith20261117'
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
saved=[]
for rel in ('M_TemperateGround','PebbleShore/M_PebbleShoreGround'):
    file=Path('Content/WorldGeneration/TemperateHills')/(rel+'.uasset')
    backup=out/'Before'/file
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/file,backup)
    mat=u.load_asset('/Game/WorldGeneration/TemperateHills/'+rel);mat.modify()
    for node in L.get_material_expressions(mat):
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property('code')
            if code.startswith('return .5+XY/float2('):
                node.set_editor_property('code','return .5+XY/float2(13000.000000,10000.000000);')
            elif code.startswith('return (XY+float2('):
                node.set_editor_property('code',code.replace('4600.000000','6500.000000').replace('3200.000000','5000.000000'))
        elif isinstance(node,u.MaterialExpressionConstant2Vector) and node.get_editor_property('desc')=='VillageRoadEdge20261115':
            node.set_editor_property('r',13000.);node.set_editor_property('g',10000.)
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Save road writer '+rel)
    saved.append(mat.get_path_name())
(out/'road-writers-saved.json').write_text(json.dumps(dict(saved=saved),indent=2),encoding='utf-8')
