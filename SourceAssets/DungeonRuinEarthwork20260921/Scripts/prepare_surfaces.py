"""Export source maps and read their parent output wiring for material adaptation."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
data=json.loads((ROOT/'Sources/source-manifest.json').read_text())
paths={}
for ident in ('ridge_a','gravel','stone_scatter','stone_patch'):
    rec=data['materials'][data['source_assets'][ident]['materials'][0]['path']]
    for key,path in rec.get('textures',{}).items():
        if key in ('BaseColour','Normals','BaseColorTexture','NormalTexture','MetallicRoughnessTexture'):
            paths[path]=None
paths['/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Albedo']=None
paths['/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Normal']=None
paths['/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_RHAOM']=None
out={}
for path in paths:
    tex=u.load_asset(path)
    dst=ROOT/'Sources'/(tex.get_name()+'.tga')
    task=u.AssetExportTask();task.object=tex;task.filename=str(dst);task.automated=True
    task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterTGA()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export source map '+path)
    out[path]={'file':str(dst),'srgb':tex.srgb,'virtual':tex.virtual_texture_streaming}
(ROOT/'Sources/surface-maps.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
mat=u.load_asset('/Game/RuralAustralia/Presets/M_Nature_01')
roots={}
for prop in ('BASE_COLOR','ROUGHNESS','AMBIENT_OCCLUSION','NORMAL'):
    node=u.MaterialEditingLibrary.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+prop))
    roots[prop]=str(node)
    if node:
        for name in ('a','b','input','texture','parameter_name'):
            try:roots[prop+'_'+name]=str(node.get_editor_property(name))
            except Exception:pass
(ROOT/'Sources/ridge-material-wiring.json').write_text(json.dumps(roots,indent=2),encoding='utf-8')
print('SOURCE_MAPS_EXPORTED',len(out),json.dumps(roots))
