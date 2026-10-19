"""Refresh only S12K entries using the authoritative registry generator inputs."""
from pathlib import Path
import importlib.util,re,json
P=Path('D:/FPS3D/FPSGAME')
spec=importlib.util.spec_from_file_location('preload_generator',P/'Tools/Performance/generate_preload_registry.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
literals,_=generator.collect(P/'Source/FPSGAME')
new=sorted({p.split('.')[0] for p in literals if p.startswith('/Game/Weapons/Saiga12K/') and not p.endswith(('_','/'))})
path=P/generator.GENERATED;source=path.read_text(encoding='utf8')
pattern=re.compile(r'^        TEXT\("(/Game/Weapons/Saiga12K/[^\"]+)"\),\n',re.M)
old=pattern.findall(source);matches=list(pattern.finditer(source))
if not matches:raise RuntimeError('Missing existing S12K registry section')
updated=source[:matches[0].start()]+''.join('        TEXT("'+p+'"),\n' for p in new)+source[matches[-1].end():]
count=len(re.findall(r'^        TEXT\(',updated,re.M))
updated=re.sub(r'PathCount = \d+;',f'PathCount = {count};',updated)
path.write_text(updated,encoding='utf8')
out=P/'SourceAssets/Saiga12KNetwork20261019/Receipts/preload.json'
out.write_text(json.dumps({'old':old,'new':new,'generated_path_count':count,'scope':'S12K entries only'},indent=2),encoding='utf8')
print('S12K preload entries',len(old),'->',len(new))
