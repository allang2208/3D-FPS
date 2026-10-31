"""Archive former sample installers and make the retained authoring entries production-only."""
from pathlib import Path
import shutil,hashlib,json
R=Path(__file__).resolve().parent;ROOT=R.parent;PROJECT=R.parents[3]
archive=(PROJECT/'trash/cyberpunk-bedroom-pilot-retired-20261024/AuthoringEntries').resolve()
if not archive.is_relative_to((PROJECT/'trash').resolve()):raise RuntimeError('Invalid archive location')
rows=[]
for relative in ['install_level.py','publish.py','RefinementV2/install_level.py','RefinementV2/publish.py','RefinementV3/install_level.py']:
    p=(ROOT/relative).resolve();dest=(archive/relative).resolve()
    if not p.is_relative_to(ROOT.resolve()) or not dest.is_relative_to(archive):raise RuntimeError('Invalid entry location')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(p,dest)
    rows.append(dict(original=str(p),archive=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),reason='Sample installer replaced by formal-apartment entry'))
    parent="Path(__file__).resolve().parent"+('' if '/' not in relative else '.parent')
    if relative.endswith('install_level.py'):
        text=f'''"""Production bedroom installation; the standalone sample map is retired."""
from pathlib import Path
import runpy
ROOT={parent}
def apply_upgrade(world):
    return runpy.run_path(str(ROOT/'Integration20261024/install_level.py'))['apply_upgrade'](world)
def main():
    return runpy.run_path(str(ROOT/'Integration20261024/install_level.py'))['main']()
if __name__=='__main__':main()
'''
    else:
        text=f'''"""Publish the current bedroom assets into the existing apartment."""
from pathlib import Path
import runpy,sys
ROOT={parent}
sys.modules.pop('design',None)
sys.modules.pop('placements',None)
runpy.run_path(str(ROOT/'RefinementV3/publish.py'),run_name='__main__')
'''
    p.write_text(text,encoding='utf8')
p=ROOT/'design.py';s=p.read_text('utf8');s=s.replace("MAP='/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024'","MAP=SOURCE_MAP")
s=s.replace('One bedroom pilot: final-world metres, original apartment stays read-only.','Bedroom production authoring: final-world metres, integrated into the existing apartment.')
p.write_text(s,encoding='utf8')
for relative in ['RefinementV2/capture_geometry.py','RefinementV3/capture_geometry.py','RefinementV2/write_report.py','RefinementV3/write_report.py']:
    p=ROOT/relative;s=p.read_text('utf8').replace('/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024','/Game/GameMaps/L_CyberpunkApartment');p.write_text(s,encoding='utf8')
(R/'retired-entries.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('PRODUCTION_ENTRIES_ROUTED',len(rows))
