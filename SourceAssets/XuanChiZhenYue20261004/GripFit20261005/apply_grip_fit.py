"""Place the ornate hilt 4.5 cm higher relative to the shared two-hand grip."""
import json
from pathlib import Path

P=Path(__file__).resolve().parent
catalog_path=P.parents[2]/'Content/ColdSteelData/xuanchi-zhenyue-modules.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
original=json.loads((P/'Before/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
mount=catalog['bone_mount'];base=original['bone_mount']['location_cm']
x,y,z,w=mount['rotation_xyzw']
# Static parts use centimeter geometry; the imported weapon bone carries a
# compensating 100x scale. Convert the 4.5 cm local sword-axis adjustment into
# the bone's space through the existing mount scale and rotation.
axial=4.5*mount['scale'][2]
delta=[2*(x*z+w*y)*axial,2*(y*z-w*x)*axial,(1-2*(x*x+y*y))*axial]
mount['location_cm']=[a+b for a,b in zip(base,delta)]
temp=catalog_path.with_suffix('.grip-fit.tmp')
temp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
temp.replace(catalog_path)
receipt={'weapon':'ue_xuanchi_zhenyue','saved_catalog':str(catalog_path),
    'hand_grip_shift_sword_local_cm':[0,0,-4.5],
    'additional_lowering_from_previous_cm':2.0,
    'method':'Weapon-specific rigid mounting adjustment; preserve shared hand shape, spacing and animation tracks',
    'before_mount_location_cm':base,'after_mount_location_cm':mount['location_cm'],
    'geometry_materials_tassel_unchanged':True,
    'activation':'Start a new play session to reload the modular sword catalog',
    'build_required':False,'game_tested':False}
(P/'grip_fit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_GRIP_FIT_SAVED '+json.dumps(receipt))
