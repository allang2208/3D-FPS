import hashlib,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
c=read(P/'Content/ColdSteelData/modular_outfits.json');items=read(P/'Content/ColdSteelData/items.json');path=c['items']['ue_leather_boots']['rig_meshes']['Jason'];saved=read(PREVIOUS/'saved_assets.json')['saved']['ue_leather_boots/Jason']
assert path==saved['asset'],'Current production boot changed since the prior revision'
disk=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
write(R/'inputs.json',dict(item='ue_leather_boots',recipe=c['items']['ue_leather_boots'],definition=items['ue_leather_boots'],source_asset=path,source_asset_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),author=str(PREVIOUS/'Authored/ue_leather_boots/Jason.json'),robe_inner=c['items']['ue_blue_mage_robe']['underlayer_meshes'][path],pants_routes={k:v.get('shoe_fit_meshes',{}).get('ue_leather_boots') for k,v in c['items'].items() if v.get('slot')==15},reference=str(OLD/'LeatherBoots_Concept_v1.png'),runtime_tested=False))
shutil.copyfile(OLD/'LeatherBoots_Concept_v1.png',R/'Reference.png')
print('TAILORED_BOOT_INPUTS_FROZEN')
