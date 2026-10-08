"""Resume our known new material after the unconnected desaturation input."""
import unreal as u,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
m=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/CommonGrips20261005/Materials/M_XuanChi_GripCopper')
if m:u.EditorAssetLibrary.set_metadata_tag(m,'XuanChiGripRevision','XuanChiCommonGrips20261005')
runpy.run_path(str(P/'install_assets.py'),run_name='xuanchi_common_grips_resume')
