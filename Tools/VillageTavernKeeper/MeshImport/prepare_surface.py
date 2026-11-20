"""Pack the original atlas masks without resampling."""
from pathlib import Path

from PIL import Image


PROJECT = Path(__file__).resolve().parents[3]
FULL_BODY = PROJECT / "SourceAssets/VillageTavernKeeper/FullBody"
source = FULL_BODY / "MeshyR1/Textures"
output = FULL_BODY / "UEAuthoringR1"
output.mkdir(exist_ok=True)
with Image.open(source / "M0_roughness.png") as rough, Image.open(source / "M0_metallic.png") as metal:
    if rough.size != metal.size:
        raise ValueError("The two source masks must share an atlas resolution.")
    packed = Image.merge("RGB", (Image.new("L", rough.size, 255), rough.getchannel("R"), metal.getchannel("R")))
    packed.save(output / "T_TavernKeeper_ORM.png")
