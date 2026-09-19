"""FPSGAME-only final import, retaining the three replaced packages for rollback."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if project != ROOT.parents[2].resolve():
    raise RuntimeError('Run this installation in FPSGAME.uproject, not the authoring project')
folder=project/'Content/Monsters/Mutant3Meshy/Animations'
backup=ROOT/'previous_packages'; backup.mkdir(exist_ok=True)
records=[]
for role in ['Running','RunFast','Stagger']:
    for suffix in ['.uasset','.uexp','.ubulk']:
        file=folder/('A_Mutant3_'+role+suffix)
        if not file.is_file(): continue
        dest=backup/file.name
        if not dest.exists(): shutil.copy2(file,dest)
        records.append({'original':str(file),'backup':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
(ROOT/'previous_packages.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
source=ROOT/'import_replacements.py'
exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),{'__file__':str(source),'__name__':'__main__'})
updated=json.loads((ROOT/'animation_contract.json').read_text())
contract_path=ROOT.parent/'animation_contract.json'
contract=json.loads(contract_path.read_text()); contract['clips'].update(updated['clips'])
contract['active_revision']='revision2'; contract['state']='Three revised animations installed; gameplay testing remains with user'
contract_path.write_text(json.dumps(contract,indent=2),encoding='utf-8')
delivery_path=ROOT.parent/'ue_delivery.json'
delivery=json.loads(delivery_path.read_text())
for role,item in updated['clips'].items(): delivery['clips'][role].update(item)
delivery['active_revision']='revision2'; delivery['state']=contract['state']
delivery_path.write_text(json.dumps(delivery,indent=2),encoding='utf-8')
(ROOT/'installed.json').write_text(json.dumps({'project':str(project),'assets':json.loads((ROOT/'import_delivery.json').read_text()),
    'runtime_tested':False,'changes':'Only Running, RunFast and Stagger replaced; unchanged native code'},indent=2),encoding='utf-8')
u.log('MUTANT3_REVISION2_INSTALLED')
