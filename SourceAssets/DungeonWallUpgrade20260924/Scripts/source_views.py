"""Small working views used while authoring textures, not game renders."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Sources/WorkingViews';OUT.mkdir(parents=True,exist_ok=True)
paths={'plaster':ROOT/'Sources/PolyHaven/plastered_wall_diff_4k.jpg',
       'fab_atlas':Path('D:/FPS3D/VaultCache/FabLibrary/Angled_Concrete_Wall_Section_with_Heavy_Damage-0b06ec58/fbx/fmp_mbl_exp_cws05_fbx_v0_extracted/FMP_MBL_EXP_CWS05_FBX_v01/Textures/8K/T_FMP_MBL_EXP_CWS05_v01_BaseColor_8K_UDIM.1001.png')}
for name,p in paths.items():
    with Image.open(p) as im:
        im.thumbnail((1600,1600));im.convert('RGB').save(OUT/(name+'.jpg'),quality=94)
