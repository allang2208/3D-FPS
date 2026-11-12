"""Convert the generated framed master to the project's 1024 px UI PNG."""
from pathlib import Path
from PIL import Image
import hashlib,json
P=Path(__file__).resolve().parent
source=P/'peakwatch-framed-generated.png'
im=Image.open(source).convert('RGBA')
im=im.resize((1024,1024),Image.Resampling.LANCZOS)
# The modification-icon contract explicitly requires neutral gray, including reflections.
gray=im.convert('L')
im=Image.merge('RGBA',(gray,gray,gray,im.getchannel('A')))
name='bow_woodsteel_sight_highland_peakwatch_3_6x.png'
im.save(P/name)
(P/'icon-source.json').write_text(json.dumps(dict(
    method='imagegen with actual equipped part and approved metal-frame references',
    source=str(source),output=str(P/name),size=[1024,1024],
    geometry_reference='SourceAssets/WoodSteelLongbow20261026/Scope3to6V11/peakwatch_actual_part.png',
    frame_reference='SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png',
    model='/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V11/SM_Highland_Peakwatch3to6',
    postprocess='UI-size conversion; neutral grayscale; preserve generated alpha',
    sha256=hashlib.sha256((P/name).read_bytes()).hexdigest()),indent=2),encoding='utf-8')
