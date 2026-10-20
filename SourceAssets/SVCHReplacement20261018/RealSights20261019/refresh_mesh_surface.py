"""Continue this not-yet-activated asset after authoring UV/normal refinements."""
import unreal as u,json,copy,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/SVCH/Replacement20261018/RealSights20261019';MESH=ROOT+'/SK_SVCH_RealFoldingSights'
DONOR='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/SK_SVCH_SightsR2_ElbowFit'
PROFILE='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip'
receipt=json.loads((O/'install_receipt.json').read_text());receipt['complete']=False
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
donor=load(DONOR);materials={str(s.material_slot_name):s.material_interface for s in donor.materials};materials['SVCH_New_FactorySights']=load(ROOT+'/Materials/M_SVCH_RealFoldingSights')
# This revision's import vertex indices changed. Remove its stale imported
# targets in memory before reimport; the exact native 18-target transfer below
# recreates and saves them. The source arm assets/profile are never modified.
current=load(MESH);current.modify()
for morph in list(current.get_editor_property('morph_targets')):
 current.remove_morph_target(morph.get_name(),False)
code=(O/'install_real_sights.py').read_text();code=code[code.index('options=u.FbxImportUI()'):].replace('task.automated=True;task.save=False;task.options=options','task.automated=True;task.replace_existing=True;task.save=False;task.options=options')
exec(compile(code,str(O/'install_real_sights.py'),'exec'),globals())
