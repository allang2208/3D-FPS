from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text('utf-8-sig'))
models=read('model_manifest.json');installed=read('Receipts/installation.json')
published=read('Receipts/publication.json');builds=read('Receipts/native-build.json')
report=dict(stage='models_original_marks_icons_and_catalog_published',
    item_ids=list(published['after']),counts=dict(meshes=3,materials=3,pbr_textures=9,icons=3,active_packages=len(installed['packages'])),
    models={key:dict(mesh=a['mesh'],dimensions_cm=a['actual_dimensions_cm'],triangles=a['triangles_lod0'],source_components=a['source_components']) for key,a in models['assets'].items()},
    brand_art='Project-authored three offset rails with COLD STEEL and CS-G3 / CS-D4 / CS-S2 identifiers',
    removed_reference_markings=['MSI','TORX','GeForce RTX','VENTUS','HyperX','FURY','Samsung','990','MZ-V9','K4A8G','SEC','country of manufacture'],
    other_hardware='NIC / HDD / CPU / RAID / compute accelerator retain existing original CS facility markings',
    texture_resolution=4096,source_formats=['Blender','FBX','GLB','PNG PBR'],
    old_assets_preserved=True,old_branded_directory_removed_from_explicit_cook=True,
    footprints_changed=False,rarities_changed=False,prices_changed=False,
    icons_rendered=True,additional_previews_rendered=False,tests_run=False,game_started=False,
    native_build=builds,saved_instance_migration='Editor and Game builds succeeded; existing profile-load migration uses current catalog appearance',
    gpu_tangent_frame='UE MikkTSpace rebuild enabled, imported split normals retained',
    import_warnings=['GPU FBX importer reports near-zero tangent and binormal vectors; target mesh rebuilds tangents in UE. Runtime appearance not tested.'])
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ORIGINAL_MARKS_DELIVERY_SAVED',report['models'])
