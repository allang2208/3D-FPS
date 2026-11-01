"""Deploy the reviewed UE catalog PNG and record the completed M24 repair."""
import json,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
assets=json.loads((O/'import_receipt.json').read_text())
icons=json.loads((O/'icon_receipt.json').read_text())
checks=json.loads((O/'validation_receipt.json').read_text())
assert assets['complete'] and checks['complete']
assert 'WeaponIconCatalog: COMPLETE failures=0' in (O/'catalog_render.log').read_text(encoding='utf-8')
assert 'Result: Succeeded' in (O/'build_console.log').read_text(encoding='utf-8')
target=P/'Content/ColdSteelData/Icons/ue_m24.png';image=O/'UEReview/ue_m24.png'
backup=O/'BeforeIcons/ue_m24.png';backup.parent.mkdir(exist_ok=True)
if target.exists() and not backup.exists():shutil.copy2(target,backup)
shutil.copy2(image,target)
status={
    'date':'2026-10-27','status':'repaired_imported_integrated_built','weapon':'ue_m24',
    'skeletal_mesh':assets['mesh'],'skeleton':assets['skeleton'],
    'asset_family':'/Game/Weapons/M24/Repair20261027',
    'saved_mesh_animation_material_packages':len(assets['saved']),
    'saved_attachment_icon_packages':len(icons['saved']),
    'clips':list(assets['clips']),'rig_object_scale':[1,1,1],
    'root_causes':['extra 100x rig object scale','FBX UVs paired with glTF textures',
                   'lens OneMinus input disconnected','catalog export dereferenced an uninitialized subsystem'],
    'catalog_image':'Content/ColdSteelData/Icons/ue_m24.png',
    'catalog_image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
    'checks':{'saved_dimension_normal_tangent_readback':'passed',
              'eight_clips_three_samples_each':'passed',
              'reference_sight_span_cm':assets['checks']['sight_span_cm'],
              'attachment_registration_max_error_cm':max(checks['checks']['static_to_skeletal_marker_error_cm'].values()),
              'ue_actual_catalog_render':'passed; all M24 capture materials compiled',
              'catalog_bounds_cm':[10.981,142.950,30.760],
              'visual_review':'UE rifle catalog and Blender scope icon reviewed; UV patchwork removed'},
    'build':{'target':'FPSGAMEEditor Win64 Development','result':'Succeeded',
             'log':'Saved/BuildEditor/build-20261027-114112.log',
             'module':'Binaries/Win64/UnrealEditor-FPSGAME.dll'},
    'gameplay_or_network_tests_run':False,'user_acceptance':'pending',
    'editor_opened':False,'game_launched':False,
    'existing_editor_crashed_during_diagnostic':True,
    'editor_crash':'UE skeletal exporter assertion; diagnostic did not save assets; editor not reopened',
    'editable_source':'SourceAssets/M24Repair20261027/M24_Repaired_Editable.blend',
    'documentation':'Docs/Weapons/m24-repair-20261027.md'}
(O/'delivery_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('M24CustomScope20261026','M24Modular20261027'):
    file=O.parent/name/'delivery_status.json';historical=json.loads(file.read_text(encoding='utf-8'))
    historical['superseded_by']='SourceAssets/M24Repair20261027/delivery_status.json'
    historical['known_issues_corrected_by_successor']=['100x scale','UV/normal surface mismatch','backpack icon']
    file.write_text(json.dumps(historical,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M24_REPAIR_DELIVERED',status['catalog_image_sha256'])
