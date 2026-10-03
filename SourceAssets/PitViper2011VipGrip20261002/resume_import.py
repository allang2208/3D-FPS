"""Resume this batch's unsaved material after the first Python property error."""
from pathlib import Path
import unreal as u
O=Path(__file__).parent
mat=u.load_asset('/Game/Weapons/PitViper2011/VipGrip20261002/Materials/M_PitViper2011_VipViperGrip')
if mat:u.EditorAssetLibrary.set_metadata_tag(mat,'VipSurfaceAuthorJob',str(O))
script=O/'import_assets.py'
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__','__VIP_RESUME_OWN_MATERIAL__':True})
