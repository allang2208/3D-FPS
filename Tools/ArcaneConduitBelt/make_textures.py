"""Physical-scale indigo leather, lining and metals for the arcane belt."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,distance_transform_edt
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArcaneConduitBelt20261025/ModelR1';T=R/'Textures'
T.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(2026102523)
exec(compile(Path(__file__).with_name('surface_fields.py').read_text(encoding='utf-8'),'arcane_surface_fields','exec'))
rows=[
    field('Arcane_IndigoLeather',[.013,.022,.049],.54,0,'leather',4096),
    field('Arcane_BurnishedEdge',[.009,.013,.024],.43,0,'edge',2048),
    field('Arcane_NavyLining',[.011,.016,.024],.89,0,'suede',2048),
    field('Arcane_SatinSilver',[.48,.47,.435],.36,.97,'metal',2048),
    field('Arcane_OxidizedSilver',[.10,.105,.115],.51,.88,'metal',2048),
    field('Arcane_ChampagneBrass',[.34,.235,.105],.42,.96,'metal',2048)
]
(R/'textures.json').write_text(json.dumps({'completed':True,'maps':rows,'normal_convention':'OpenGL','ue_flip_normal_green':True,'orm_channels':'R=AO G=roughness B=metallic','base_color_encoding':'sRGB, authored from linear reflectance','additional_shader_materials':['thread','smoky violet quartz','low intensity rune enamel','dark engraved channel']},indent=2)+'\n',encoding='utf-8')
print('ARCANE_PBR_SAVED',len(rows),'material families',flush=True)
