"""Create the revision from the retained construction source; never rewrite V1."""
from pathlib import Path
import shutil
import json

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
MODEL=P.parent/'FinalTollHammerHeadV2'
MODEL.mkdir(exist_ok=True)
source=(P.parent/'FinalTollHammerHeadV1/author_model.py').read_text('utf-8')
start=source.index('def arch(')
end=source.index('\ndef join_group(',start)
replacement=(P/'bell_geometry.py').read_text('utf-8')
source=source[:start]+replacement+source[end:]
source=source.replace('SM_RuneboundWarhammer_FinalTollHammerHeads_V1','SM_RuneboundWarhammer_FinalTollHammerHeads_V2')
source=source.replace('FinalTollHammerHeads_V1.glb','FinalTollHammerHeads_V2.glb')
source=source.replace('"""Precision-author the Star Oath paired hammerheads;', '"""Refine the Final Toll paired hammerheads against the retained reference;')
(MODEL/'author_model.py').write_text(source,encoding='utf-8')
for rel in ('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp','Source/FPSGAME/Weapons/ModularSwordVisual.cpp','Source/FPSGAME/UI/ColdSteelIconResources.cpp'):
    # The current edited source is recorded as a production input, not a rollback snapshot.
    dest=P/'Sources'/Path(rel).name
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(ROOT/rel,dest)
build=(P.parent/'build.ps1').read_text('utf-8-sig')
(P/'build.ps1').write_text(build,encoding='utf-8-sig')
print(str(MODEL/'author_model.py'))
