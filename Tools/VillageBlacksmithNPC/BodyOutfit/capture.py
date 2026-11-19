import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
OUT=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
source=(P/'Tools/ChapelNun/capture_sources.py').read_text()
start=source.index('G=u.GeometryScript_AssetUtils')
end=source.index("head=capture(")
R=OUT
exec(source[start:end])
items=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['items']
for name,asset in {'shirt':items['ue_field_sweater_charcoal']['rig_meshes']['Jason'],
                   'trousers':items['ue_jeans']['shoe_fit_meshes']['ue_boots']['Jason'],
                   'boots':items['ue_boots']['rig_meshes']['Jason']}.items():
    capture(name,asset)
