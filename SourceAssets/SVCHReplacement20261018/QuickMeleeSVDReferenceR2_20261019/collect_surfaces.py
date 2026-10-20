"""Read the exact V9 glove coverage and blue-glove meshes seen in the user report."""
from pathlib import Path
source=Path(__file__).parent.parent/'ForegripFit20261019/collect_inputs.py'
code=source.read_text().split("profile_path=")[0]
start=code.index('ASSETS=');end=code.index('manifest={}')
code=code[:start]+'''ASSETS={
 'coverage':'/Game/Characters/ModularOutfit20260924/WristCoverage20260929/SVD/SK_SVD_d9b5ee5f40_WristCoverage',
 'glove':'/Game/Characters/ModularOutfit20260924/BlueMageGloves20261019/SVD/SK_SVD_BlueMageGloves'}
'''+code[end:]
exec(compile(code,str(source),'exec'),globals())
(I/'surfaces-manifest.json').write_text(json.dumps(manifest,indent=2))
