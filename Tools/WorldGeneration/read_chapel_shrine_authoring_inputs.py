"""Read dimensions and stone materials required for the requested shrine pedestal."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ChapelShrineForecourt20261116'
OUT.mkdir(parents=True,exist_ok=True)
report={'shrines':[],'stone_sources':[]}
game=u.EditorLevelLibrary.get_game_world()
report['game_world']=game.get_path_name() if game else None
for row in json.loads((ROOT/'Content/ColdSteelData/shrines.json').read_text(encoding='utf-8'))['statues']:
    mesh=u.load_asset(row['mesh'])
    if not mesh:raise RuntimeError(row['mesh'])
    b=mesh.get_bounding_box()
    report['shrines'].append({'id':row['id'],'path':row['mesh'],'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]})
for name in ('YardPathStone','Foundation','YardWallA'):
    mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_Chapel'+name)
    if mesh:
        report['stone_sources'].append({'mesh':mesh.get_path_name(),'materials':[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.get_editor_property('static_materials')]})
(OUT/'authoring-inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
