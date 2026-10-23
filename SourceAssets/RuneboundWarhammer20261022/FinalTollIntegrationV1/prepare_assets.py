"""Prepare a private authoring host and only new Final Toll asset destinations."""
from pathlib import Path
import json,re,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[2];S=P.parent/'StarOathIntegrationV1';H=P/'AuthorHost'
for file in ('author_isolated.py','build.ps1','author_icon.py'):
    text=(S/file).read_text('utf-8').replace('StarOath','FinalToll').replace('STAR_OATH','FINAL_TOLL').replace('star_oath','final_toll')
    (P/file).write_text(text,encoding='utf-8')
source=(S/'install_assets.py').read_text('utf-8').replace('StarOath','FinalToll').replace('STAR_OATH','FINAL_TOLL').replace('Star Oath','Final Toll')
start=source.index("m=material('M_FinalToll_Optical_Crystal')")
end=source.index("m=material('M_FinalToll_Rune_Energy')",start)
source=source[:start]+source[end:]
source=source.replace('default_value=u.LinearColor(.015,.27,1,1)','default_value=u.LinearColor(1,.64,.22,1)')
source=source.replace("m.set_editor_property('used_with_nanite',False)","m.set_editor_property('used_with_nanite',True)")
source=source.replace('nanite.enabled=False','nanite.enabled=True').replace('native_triangles=245625','native_triangles=111240').replace('nanite=False','nanite=True')
source=source.replace("nanite_reason='One rigid close-view module includes translucent crystal shells'","nanite_reason='Opaque rigid bell-cage head with explicit open geometry'")
source += '\nexec(compile((P/\'install_motion_vfx.py\').read_text(\'utf-8\'),str(P/\'install_motion_vfx.py\'),\'exec\'))\n'
(P/'install_assets.py').write_text(source,encoding='utf-8')
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'))
roles=[{'variant':'Default','scope':['clips'],'heavy':cfg['clips']['Warhammer.FullBody.Slam'],'upper':cfg['clips']['Warhammer.FullBody.Uppercut']}]
for key,value in cfg.get('body_variants',{}).items():
    if 'Warhammer.FullBody.Slam' in value.get('clips',{}):
        roles.append({'variant':key,'scope':['body_variants',key,'clips'],'heavy':value['clips']['Warhammer.FullBody.Slam'],'upper':value['clips']['Warhammer.FullBody.Uppercut']})
(P/'body_roles.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
paths=[row[k] for row in roles for k in ('heavy','upper')]
paths += ['/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1','/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel']
pending=paths[:];copied={}
while pending:
    package=pending.pop().split('.')[0]
    if package in copied or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',package):continue
    rel=Path(package[6:]).with_suffix('.uasset');src=ROOT/'Content'/rel
    if not src.exists():continue
    dest=H/'Content'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dest);copied[package]=str(src)
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if src.with_suffix(suffix).exists():shutil.copy2(src.with_suffix(suffix),dest.with_suffix(suffix))
    pending.extend(v.decode('ascii').split('.')[0] for v in re.findall(rb'/Game/[A-Za-z0-9_/\.]+',src.read_bytes()))
(P/'authoring_inputs.json').write_text(json.dumps(copied,indent=2),encoding='utf-8')
print('FINAL_TOLL_PRIVATE_INPUTS_READY',len(copied),flush=True)
