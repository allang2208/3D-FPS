"""Prepare the scoped pistol archive and separate the live authoring dependencies."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
out=root/'Docs/Weapons/pistol-publication-20260915'
out.mkdir(parents=True,exist_ok=True)
live=root/'SourceAssets/DanWesson715PalmClearance20260915'
donor=root/'SourceAssets/DanWesson715DonorPress20260915'
source=(donor/'author_actions.py').read_text(encoding='utf-8')
basis=source.split('\ndef elbow_for(')[0]
basis=basis.replace('_donor_dir','_basis_dir')
basis=basis.replace("skin=json.loads((O.parent/'DanWesson715EjectHand20260915/authoring-geometry.json').read_text(encoding='utf-8'))\npalm_vertices=[Vector(v) for v in skin['hand_vertices']]\n",'')
basis=basis.replace('Starts from LeftRecovery, not the rejected EjectHand pose.',
                    'Retained reference preparation from the archived DonorPress author; starts from LeftRecovery.')
(live/'reference_basis.py').write_text(basis,encoding='utf-8')
entry=(live/'author_actions.py').read_text(encoding='utf-8')
start=entry.index('_donor_file=')
end=entry.index('O=_clearance_dir;',start)
entry=entry[:start]+"_basis_file=_clearance_dir/'reference_basis.py'\n__file__=str(_basis_file)\nexec(compile(_basis_file.read_text(encoding='utf-8'),str(_basis_file),'exec'),globals())\n"+entry[end:]
(live/'author_actions.py').write_text(entry,encoding='utf-8')
importer=(root/'SourceAssets/DanWesson715EjectHand20260915/import_assets.py').read_text(encoding='utf-8')
importer=importer.replace('compact extractor-press','palm-clearance extractor-press').replace('DW715_EJECT_HAND_','DW715_PALM_CLEARANCE_')
(live/'import_assets.py').write_text(importer,encoding='utf-8')
(live/'Reference').mkdir(exist_ok=True)
(live/'Reference/README.md').write_text((donor/'README.md').read_text(encoding='utf-8').split('## 制作方法')[0].replace('../DanWesson715Upgrade20260914/Reference/','../../DanWesson715Upgrade20260914/Reference/')+'\n资料点云图及旧版制作记录已随 DonorPress 归档；当前动作依赖为上游 Reference/donor-poses.json，不从 trash 读取。\n',encoding='utf-8')

moves=[]
def retire(path,reason,replacement):
    path=root/path
    if path.exists():moves.append({'source':path.relative_to(root).as_posix(),'reason':reason,'replacement':replacement})
for version in ('EjectHand','DonorPress'):
    retire(f'SourceAssets/DanWesson715{version}20260915','User rejected single-wield press pose','SourceAssets/DanWesson715PalmClearance20260915')
    retire(f'Content/Weapons/DanWesson715/{version}20260915','Superseded single-wield animation assets','Content/Weapons/DanWesson715/PalmClearance20260915')
for version in ('ReferencePoseV2','SprintReferenceV4'):
    retire(f'SourceAssets/PistolDualWield20260914/{version}','Superseded dual-wield pose or sprint output','NaturalAimV3 / SprintSmoothV5 / RevolverReloadFlickV6')
for family in ('M1911','DW715'):
    for side in ('r','l'):
        base=f'Content/Weapons/PistolDualWield20260914/{family}/{side}'
        for version in ('Animations','ReferencePoseV2','SprintReferenceV4'):
            retire(f'{base}/{version}','No longer loaded by current dual-wield animation routing','NaturalAimV3 / SprintSmoothV5 / RevolverReloadFlickV6')
        retire(f'SourceAssets/PistolDualWield20260914/{family}/{side}/Animations','Superseded initial animation exports; mesh source retained','NaturalAimV3 / SprintSmoothV5 / RevolverReloadFlickV6')
        for folder in (root/f'{base}/NaturalAimV3/Animations',root/f'SourceAssets/PistolDualWield20260914/NaturalAimV3/{family}/{side}/Animations'):
            if not folder.exists():continue
            for path in sorted(folder.iterdir()):
                name=path.stem
                if '_sprint' in name or (family=='DW715' and ('_single_' in name or '_speed_' in name)):
                    retire(path.relative_to(root),'Superseded sprint/revolver reload clip in mixed V3 output','SprintSmoothV5 / RevolverReloadFlickV6')

plan={'project_root':root.as_posix(),'archive_root':'trash/pistol-animation-20260915','moves':moves,
      'scope':'This conversation pistol animation outputs only; preserve active authoring inputs and parallel work'}
(out/'archive-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'planned_moves':len(moves),'plan':str(out/'archive-plan.json')}))
