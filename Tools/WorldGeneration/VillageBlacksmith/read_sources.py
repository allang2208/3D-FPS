"""Read production inputs for furnishing; no map changes or gameplay."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/HillsVillageBlacksmith20261117')
out.mkdir(parents=True,exist_ok=True)
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entries=[]
for entry in palette.get_editor_property('components'):
    identity=str(entry.get_editor_property('id'))
    obj=entry.get_editor_property('mesh')
    path=obj.get_path_name() if obj else ''
    row={'id':identity,'label':str(entry.get_editor_property('display_name')),'mesh':path}
    if any(word in identity.lower() for word in ('bed','chair','table','bench','shelf','cabinet','chest','casting','torch','barrel')):
        mesh=obj
        if mesh:
            b=mesh.get_bounding_box()
            row['min']=[b.min.x,b.min.y,b.min.z];row['max']=[b.max.x,b.max.y,b.max.z]
            row['materials']=[str(s.material_interface.get_path_name()) for s in mesh.get_editor_property('static_materials') if s.material_interface]
    entries.append(row)
for path in ('/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelPew',
             '/Game/MilitaryTrench/Assets/3D/Mil_Trench_Bench_Wood_01/StaticMeshes/SM_Mil_Trench_Bench_Wood_01',
             '/Game/UndergroundTunnel/Meshes/Props/SM_WoodCrate01a',
             '/Game/Props/CastingStation20260926/SM_CoolingBarrel'):
    mesh=u.load_asset(path)
    if mesh:
        b=mesh.get_bounding_box()
        entries.append(dict(id=path.rsplit('/',1)[-1],mesh=mesh.get_path_name(),min=[b.min.x,b.min.y,b.min.z],
                            max=[b.max.x,b.max.y,b.max.z],materials=[s.material_interface.get_path_name() if s.material_interface else '' for s in mesh.static_materials]))
(out/'source-assets.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VILLAGE_BLACKSMITH_SOURCE_INPUTS_SAVED')
