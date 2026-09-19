"""Read the problematic sky texture inputs; export their existing HDR pixels, no scene rendering."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/Saved/HillsSkyFix20260915')
out.mkdir(parents=True,exist_ok=True)
rows=[]
for name in ('T_HDR_Sunshine','T_HDR_Sunrise','T_HDR_Sunset','T_HDR_Night_00','T_HDR_Sunshine_02'):
    tex=u.load_asset('/Game/PWL_Light_Manager/Textures/HDR/'+name)
    row={'name':name}
    for prop in ('srgb','compression_settings','mip_gen_settings','lod_group','lod_bias','never_stream','max_texture_size'):
        row[prop]=str(tex.get_editor_property(prop))
    task=u.AssetExportTask()
    task.object=tex
    task.filename=str(out/(name+'.hdr'))
    task.automated=True
    task.prompt=False
    row['exported']=u.Exporter.run_asset_export_task(task)
    rows.append(row)
(out/'texture_sources.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
