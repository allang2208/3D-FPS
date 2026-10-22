"""Snapshot the current wardrobe routes as the oracle for the isolated UDP run."""
import hashlib,sys
from pathlib import Path
from boot_paths import P,R,OLD,read,write
out=Path(sys.argv[1]);items=read(P/'Content/ColdSteelData/modular_outfits.json')['items']
pants=items['ue_leather_pants'];boots=items['ue_leather_boots'];robe=items['ue_blue_mage_robe'];shirt=items['ue_field_sweater']
normal=pants['rig_meshes']['Jason'];fitted=pants['shoe_fit_meshes']['ue_leather_boots']['Jason']
def inner(path,with_boots):
    if path in robe['underlayer_meshes']:return robe['underlayer_meshes'][path]
    default=robe['pants_underlayer_default']
    return default.get('shoe_fit_meshes',{}).get('ue_leather_boots',{}).get('Jason',default['rig_meshes']['Jason']) if with_boots else default['rig_meshes']['Jason']
def shirt_fit(path):
    return shirt.get('pants_mesh_fit_meshes',{}).get(path,shirt.get('pants_fit_meshes',{}).get('ue_leather_pants',shirt['pants_fit_default']))['rig_meshes']['Jason']
saved=read(R/'saved_assets.json');old=read(OLD/'saved_assets.json');boot=boots['rig_meshes']['Jason']
expected=dict(pants=normal,pants_boots=fitted,pants_robe=inner(normal,False),pants_robe_boots=inner(fitted,True),boots=boot,boots_robe=robe['underlayer_meshes'][boot],shirt=shirt['rig_meshes']['Jason'],shirt_pants=shirt_fit(normal),shirt_pants_boots=shirt_fit(fitted),pickup=saved['displays']['pickup'],icon=saved['displays']['icon'],legacy_pickup=old['boots_pickup'],legacy_icon=old['boots_icon'])
for key,path in expected.items():
    assert path and (P/'Content'/(path.split('.')[0][6:]+'.uasset')).is_file(),(key,path)
write(out/'expected.json',expected)
write(out/'scenario.json',dict(item='ue_leather_boots',pants='ue_leather_pants',shirt='ue_field_sweater',robe='ue_blue_mage_robe',guest_masks=[31,30,29,15,31,0,31],host_masks=[31,15,0,29,30,31,31],reconnect=True,rapid_change_phase=4,legacy_shared_drop=True,enhancement_sentinel=7,rendered=False))
print('BOOT_WIRE_EXPECTED_READY',out,flush=True)
