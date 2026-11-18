"""Read the actual low-wall bindings and export their scanned stone references."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelShrineForecourt20261116/WallStoneR3')
OUT.mkdir(parents=True,exist_ok=True)
report={'meshes':{},'textures':{}}
for role in ('YardWallA','YardWallB','YardPier'):
    m=u.load_asset('/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_Chapel'+role)
    report['meshes'][role]=[]
    for slot in m.get_editor_property('static_materials'):
        mat=slot.material_interface
        row={'slot':str(slot.material_slot_name),'material':mat.get_path_name(),'textures':[]}
        for n in u.MaterialEditingLibrary.get_material_expressions(mat.get_base_material()):
            if isinstance(n,u.MaterialExpressionTextureSample):
                t=n.get_editor_property('texture')
                if t:row['textures'].append(t.get_path_name())
        report['meshes'][role].append(row)
for scan in ('01A','02A','03A'):
    t=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_'+scan+'_BaseColor')
    task=u.AssetExportTask();task.object=t;task.filename=str(OUT/(scan+'-BaseColor.png'))
    task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Stone export '+scan)
    report['textures'][scan]={k:str(t.get_editor_property(k)) for k in ('virtual_texture_streaming','max_texture_size','lod_bias','filter','compression_settings','srgb','never_stream')}
m=u.load_asset('/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal')
report['pedestal_uv_density']=str(m.get_editor_property('static_materials')[0].get_editor_property('uv_channel_data'))
(OUT/'wall-material-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CHAPEL_WALL_STONE_READ',flush=True)
