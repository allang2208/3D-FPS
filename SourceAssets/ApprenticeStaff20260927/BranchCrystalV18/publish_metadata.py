"""Publish the matching icon/labels after the actual mesh install has saved."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
receipt=json.loads((ROOT/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('The staff mesh install is not complete.')
for relative in ('Content/ColdSteelData/staffs.json','Content/ColdSteelData/staff-gunsmith.json','Content/ColdSteelData/Icons/apprentice_staff.png',
                 'SourceAssets/ApprenticeStaff20260927/author_staff.py','SourceAssets/ApprenticeStaff20260927/import_staff.py'):
    source=PROJECT/relative;backup=ROOT/'Before'/relative
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
path=PROJECT/'Content/ColdSteelData/staffs.json';data=json.loads(path.read_text(encoding='utf-8'))
data['ue_apprentice_staff']['desc']='法术学徒使用的天然木枝长杖，顶部以麻绳固定透明白水晶，杖身保留木纹与枝节。可单手持握、近身挥击，并按修习的元素更换杖头、杖冠与导魔部件。'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=PROJECT/'Content/ColdSteelData/staff-gunsmith.json';data=json.loads(path.read_text(encoding='utf-8'))
for column in data['columns']:
    if column['key']=='head_crystal':column['default']='白水晶杖头'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(ROOT/'Export/apprentice_staff.png',PROJECT/'Content/ColdSteelData/Icons/apprentice_staff.png')
for filename in ('author_staff.py','import_staff.py'):
    path=ROOT.parent/filename;text=path.read_text(encoding='utf-8')
    if 'BranchCrystalV18' not in text:
        marker='ROOT = Path(__file__).resolve().parent' if filename=='author_staff.py' else 'ROOT=Path(__file__).resolve().parent'
        script='author_model.py' if filename=='author_staff.py' else 'import_model.py'
        addition="\n# Current user-selected reference design; the old sphere-head branch below is archival.\nimport runpy\nrunpy.run_path(str(ROOT/'BranchCrystalV18/"+script+"'),run_name='__main__')\nraise SystemExit(0)"
        text=text.replace(marker,marker+addition,1);path.write_text(text,encoding='utf-8')
receipt['metadata_updated']=True
receipt['inventory_icon']='Content/ColdSteelData/Icons/apprentice_staff.png'
receipt['icon_source']='Blender authored V18 full assembly; production icon only'
(ROOT/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_V18_METADATA_PUBLISHED')
