"""Generate two isolated mesh import batches and the original-entry assignment."""
from pathlib import Path
TOOLS=Path(__file__).resolve().parent
for role in ['outfit','clothing']:
    script=(TOOLS/('import_mesh_'+role+'.py')).read_text(encoding='utf-8').replace('V01','V04')
    script=script.replace('Background import into an independent security namespace; no game/preview tests.',
        'Import researcher stable cloth-field revision; no game/preview tests.')
    script=script.replace('def save(asset):\n',"def save(asset):\n    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')\n")
    script=script.replace('Saved V04 candidate; not rendered or gameplay tested',
        'V04 fixed garment cage, smooth sewn weights and temporal ease; not gameplay tested')
    (TOOLS/('import_stable_'+role+'_v04.py')).write_text(script,encoding='utf-8')

script=(TOOLS/'apply_waist_v03.py').read_text(encoding='utf-8')
script=script.replace("ROOT=BASE/'V03'","ROOT=BASE/'V04'")
script=script.replace("ROOT/'waist_curves.json'","ROOT/'stable_curves.json'").replace("ROOT/'waist_manifest.json'","ROOT/'stable_manifest.json'")
script=script.replace("oldnames=json.loads((BASE/'V02/export_receipt.json').read_text(encoding='utf-8'))['morph_names']",
    "oldnames=set()\nfor version in ['V01','V02','V03']:\n    oldnames.update(json.loads((BASE/version/'export_receipt.json').read_text(encoding='utf-8'))['morph_names'])")
script=script.replace("['SK_FacelessResearcher_V02','SK_FacelessResearcher_V03']","['SK_FacelessResearcher_V03','SK_FacelessResearcher_V04']")
script=script.replace("DEST+'/SK_FacelessResearcher_V03'","DEST+'/SK_FacelessResearcher_V04'").replace("DEST+'/SK_FacelessResearcher_Clothing_V03'","DEST+'/SK_FacelessResearcher_Clothing_V04'")
script=script.replace("'/Animations/V03/A_Researcher_'","'/Animations/V04/A_Researcher_'").replace("+'_V03'","+'_V04'")
script=script.replace('Save both V03 meshes','Save both V04 meshes')
script=script.replace('V03 continuous 360-degree waist band and clothed-body envelope; source bone tracks and rate retained',
    'V04 fixed cloth cage, sewn-surface skin smoothing, scalar radial ease and temporal filtering; unchanged source bone tracks/rate')
script=script.replace('V03 M-05 circumferential waist/hem contact in idle, walk, attack and stagger',
    'V04 M-05 continuous garment deformation; earlier unstable corrections removed')
script=script.replace('RESEARCHER_WAIST_V03_SAVED','RESEARCHER_STABLE_V04_SAVED')
(TOOLS/'apply_stable_v04.py').write_text(script,encoding='utf-8')
print('Researcher V04 import and assignment batches written')
