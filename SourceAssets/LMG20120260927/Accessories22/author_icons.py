"""Produce 201 factory stock/rear-grip UI art with the established icon setup."""
from pathlib import Path
O=Path(__file__).resolve().parent
source=O.parent/'Authoring/author_attachment_icons.py'
code=source.read_text(encoding='utf8').split('# The existing shared bipod-false art')[0]
code=code.replace("O=Path(__file__).parent;R=O.parents[2]", "O=Path(__file__).parent;R=O.parents[2]")
code=code.replace("jobs={'optic':['RearSight'],'muzzle':['FactoryMuzzle'],'bipod':['BipodBase','BipodLegA','BipodLegB']}","jobs={'stock':['FactoryStock'],'reargrip':['FactoryRearGrip']}")
code=code.replace("O/'LMG201_Game_Editable.blend'", "O.parent/'Authoring/LMG201_Game_Editable.blend'")
code+='\n(O/"icons.json").write_text(json.dumps(report,indent=2),encoding="utf8")\n'
exec(compile(code,str(source),'exec'),{'__file__':str(O/'author_icons.py')})
