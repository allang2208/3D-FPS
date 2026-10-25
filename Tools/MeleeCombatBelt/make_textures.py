"""Reuse project textiles and author original physical-scale leather/metal PBR."""
from pathlib import Path
import ast,json,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,distance_transform_edt

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/MeleeCombatBelt20261025/ModelR1'
T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(2026102517)

# Freeze the existing authored material-field functions, without executing the
# other asset's publication or touching its surfaces.
text=(Path(__file__).with_name('surface_fields.py')).read_text(encoding='utf-8')
exec(compile(text,'melee_original_surface_fields','exec'))
old=P/'SourceAssets/TacticalMagazineBelt20261024'
sources=json.loads((old/'textures.json').read_text(encoding='utf-8-sig'))['maps']
rows=[]
for old_name,name in [('Belt_CharcoalNylon','Melee_CharcoalNylon'),('Belt_BlackWebbing','Melee_BlackWebbing'),('Belt_SpacerMesh','Melee_SpacerMesh')]:
    row=dict(next(r for r in sources if r['name']==old_name));row['name']=name;row['source']='project authored textile: '+old_name
    for channel in ('BaseColor','Normal','ORM','Height'):shutil.copy2(old/'Textures'/f'T_{old_name}_{channel}.png',T/f'T_{name}_{channel}.png')
    shutil.copy2(old/'Textures'/f'HIGH_{old_name}.npz',T/f'HIGH_{name}.npz')
    rows.append(row)
rows+= [field('Melee_OxbloodLeather',[.055,.021,.014],.55,0,'leather',4096),
         field('Melee_BurnishedEdge',[.034,.011,.008],.40,0,'edge',2048),
         field('Melee_GraphiteMetal',[.11,.12,.135],.44,.65,'metal',2048),
         field('Melee_BrushedTitanium',[.40,.42,.44],.33,.96,'metal',2048),
         field('Melee_DarkLining',[.009,.010,.012],.91,0,'suede',2048)]
(R/'textures.json').write_text(json.dumps({'completed':True,'maps':rows,'normal_convention':'OpenGL','ue_flip_normal_green':True,'orm_channels':'R=AO G=roughness B=metallic','base_color_encoding':'sRGB; new colors authored in linear space','no_external_images_modified':True},indent=2)+'\n',encoding='utf-8')
print('MELEE_BELT_PBR_SAVED',len(rows),'materials',flush=True)
