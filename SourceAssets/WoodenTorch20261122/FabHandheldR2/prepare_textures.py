"""Extract the publisher's PBR maps and keep the original ZIP, FBX, BLEND and painter source."""
from pathlib import Path
from zipfile import ZipFile
import shutil

source=Path(__file__).resolve().parent
export=source/"Export"
export.mkdir(exist_ok=True)
with ZipFile(source/"Original/torchtextures.zip") as archive:
    for part in ("Wood","Cloth","Rope"):
        maps=["BaseColor","Normal","OcclusionRoughnessMetallic"]
        if part=="Cloth": maps.append("Opacity")
        for role in maps:
            key="ORM" if role=="OcclusionRoughnessMetallic" else role
            with archive.open("torch_"+part+"_"+role+".1001.png") as src, (export/("T_HandheldTorch_"+part+"_"+key+".png")).open("wb") as dst:
                shutil.copyfileobj(src,dst)
