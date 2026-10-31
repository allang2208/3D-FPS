from pathlib import Path
import shutil
R=Path(__file__).resolve().parent;backup=R/'Revisions/BeforeRiverfront20261026';backup.mkdir(parents=True,exist_ok=True)
for name in ('make_layout.py','layout.json','geometry.json','assets_saved.json','installed.json','delivery.json','sync_delivery.py'):
    target=backup/name
    if not target.exists():shutil.copy2(R/name,target)
source=(backup/'make_layout.py').read_text(encoding='utf8').split("for zd in [z for z in D['zones'] if z['id']!='P4']:")[0]
source=source.replace("R=Path(__file__).resolve().parent;P=R.parents[1]","R=Path(__file__).resolve().parent;P=R.parents[1]")
source=source.replace("I=json.loads((R/'inputs.json').read_text())","I=json.loads((R/'inputs_riverfront.json').read_text(encoding='utf8'))")
(R/'layout_primitives.py').write_text(source,encoding='utf8')
source=(R/'read_inputs.py').read_text(encoding='utf8').replace("R/'inputs.json'","R/'inputs_riverfront.json'")
(R/'read_riverfront_inputs.py').write_text(source,encoding='utf8')
print('RIVERFRONT_AUTHORING_INPUTS_PREPARED')
