from pathlib import Path
import os, subprocess,sys
base=Path(__file__).resolve().parent
project=Path("D:/FPS3D/FPSGAME")
src=project/"SourceAssets/OneHandAxe20261101/BladeVariants20261102/CrescentReferenceR4_20261104/FactoryFinish20261104/transfer_textures.py"
helper=project/"SourceAssets/HighlandClaymoreMeshy20260922/ClovenSurface20261002/BladeMetal20261002/author_textures.py"
program=src.read_text(encoding="utf-8-sig").replace("P.parents[3]/'HighlandClaymoreMeshy20260922/ClovenSurface20261002/BladeMetal20261002/author_textures.py'",f"Path({str(helper)!r})")
for kind in ("HeavyCleaver","FoldedArc"):
    directory=base/"R2Surface"/kind
    sys.argv=[str(src),"--workdir",str(directory)]
    exec(compile(program,str(src),"exec"),dict(__file__=str(src),__name__="__main__"))
