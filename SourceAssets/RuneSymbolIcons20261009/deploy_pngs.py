"""Deploy seven semantic rune masters to shared and existing compatible keys."""
from pathlib import Path
import json, shutil

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
spec=json.loads((P/'generation-prompts.json').read_text(encoding='utf-8'))
manifest=[]
for entry in spec['entries']:
    key='blade_2_'+entry['id']
    source=P/'Masters'/(key+'.png')
    if not source.exists():raise RuntimeError('Generate every master before deployment: '+key)
    destinations={icons/(key+'.png')}
    destinations.update(icons.rglob('*_'+key+'.png'))
    if (icons/'FramedFirearms'/(key+'.png')).exists():destinations.add(icons/'FramedFirearms'/(key+'.png'))
    for dest in sorted(destinations):
        relative=dest.relative_to(ROOT)
        for old in [dest,dest.with_suffix('.uasset')]:
            if old.exists():
                backup=P/'Before'/old.relative_to(ROOT)
                backup.parent.mkdir(parents=True,exist_ok=True)
                if not backup.exists():shutil.copy2(old,backup)
        shutil.copy2(source,dest)
        manifest.append({'id':entry['id'],'name':entry['name'],'source':str(source),
            'png':str(dest),'asset':'/Game/'+relative.relative_to('Content').with_suffix('').as_posix()})
(P/'deployment.json').write_text(json.dumps({'masters':len(spec['entries']),'icons':manifest,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# The active haste mask generator also references the current semantic icon.
old_root=ROOT/'SourceAssets/HasteRune20261009'
author=old_root/'author_assets.py'
text=author.read_text(encoding='utf-8').replace("HasteRuneYellowIcon20261009/blade_2_haste_rune.png","RuneSymbolIcons20261009/Masters/blade_2_haste_rune.png")
backup=P/'Before/SourceAssets/HasteRune20261009/author_assets.py'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(author,backup)
author.write_text(text,encoding='utf-8')
shutil.copy2(P/'Masters/blade_2_haste_rune.png',old_root/'blade_2_haste_rune.png')
design_file=old_root/'design.json'
design=json.loads(design_file.read_text(encoding='utf-8'))
design['icon_source']='../RuneSymbolIcons20261009/Masters/blade_2_haste_rune.png'
design['source']='Original project wind mask; imagegen rune-symbol icon following Zhenmo/Jingang framing'
design_file.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RUNE_SYMBOL_PNGS_DEPLOYED '+str(len(manifest)))
