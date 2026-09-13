"""Prepare a metal-only tile from the active M4 receiver's existing atlas."""
from pathlib import Path
from PIL import Image
import json
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
source=O.parent/'M4Infima/SK_M4_Infima.fbm'
# Same receiver region as the accepted M4 vertical grip; image Y is inverted.
region=(.53,.16,.65,.21)
files={}
for key in ['BaseColor','Roughness']:
 im=Image.open(source/('Body_'+key+'.png')).convert('RGB')
 box=tuple(round(v*(im.width if i%2==0 else im.height)) for i,v in enumerate(region))
 tile=im.crop(box)
 dest=T/('T_M4_Receiver_'+key+'.png');tile.save(dest);files[key]=str(dest)
(O/'profiles.json').write_text(json.dumps({
 'M4':{'reference_material':'/Game/Weapons/M4InfimaV3/Body_001','source':str(source),'crop_image_coordinates':region,'physical_tile_m':[.12,.05],'textures':files,'response':'Existing MF_PhongToMetalRoughness conversion, SpecularColor=.2; preserve current receiver sRGB shininess sampling.'},
 'AKM':{'reference_material':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR','source':str(O.parent/'AKMArmSupport20260911/Metal'),'crop_image_coordinates':[.055,.908,.285,.947],'physical_tile_m':[.12,.025],'response':'Existing Soviet receiver Base_color, Metallic and Roughness tile.'}},indent=2))
