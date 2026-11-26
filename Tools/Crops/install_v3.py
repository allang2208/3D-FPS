"""Install verified new crop packages and a stable ID catalog, without replacement."""
import hashlib
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parents[2]
ROOT = P / 'SourceAssets/CropsV3_20261022'
HOST = P / 'Saved/CropsV3ImportHost'
SOURCE = HOST / 'Content/Props/Crops/V3'
TARGET = P / 'Content/Props/Crops/V3'
CATALOG = P / 'Content/ColdSteelData/crop_models_v3.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    imported = json.loads((ROOT/'Receipts/ue-import.json').read_text())
    verified = json.loads((ROOT/'Receipts/ue-readback.json').read_text())
    assert imported['status']=='imported_saved'
    assert verified['status']=='reloaded_verified' and verified['independent_process_readback']
    assert verified['counts']=={'meshes':36,'materials':14,'material_instances':6,'textures':33}
    manifest=json.loads((ROOT/'Source/variant_manifest.json').read_text(encoding='utf-8'))
    mesh_rows={r['id']:r for r in verified['meshes']}
    catalog={
        'schema_version':1, 'model_version':'V3', 'asset_root':'/Game/Props/Crops/V3',
        'integration_scope':'asset_library_and_mapping_only', 'gameplay_consumer_implemented':False,
        'growth_mode':manifest['growth_mode'], 'units':'centimeters', 'root_origin_cm':[0,0,0],
        'selection_rule':manifest['selection_rule'], 'suggested_instance_scale_range':manifest['suggested_instance_scale_range'],
        'suggested_yaw_degrees':manifest['suggested_yaw_degrees'], 'position_jitter_rule':manifest['position_jitter_rule'],
        'tint_scope':manifest['tint_scope'], 'visible_fruit_count_is_cosmetic':True,
        'source_manifest':'SourceAssets/CropsV3_20261022/Source/variant_manifest.json',
        'crops':{}, 'assets':[]}
    for crop in manifest['crops']:
        variants={}
        for variant in manifest['variant_ids']:
            rows=sorted((a for a in manifest['assets'] if a['crop']==crop and a['variant']==variant),key=lambda a:a['stage'])
            assert [a['stage'] for a in rows]==[1,2,3]
            variants[variant]={'stable_seed':rows[0]['stable_seed'], 'foliage_tint':manifest['variant_tint_presets'][variant],
                               'stages':{str(a['stage']):mesh_rows[a['id']]['path'] for a in rows}}
        catalog['crops'][crop]={'item_definition_id':crop,'variants':variants}
    for asset in manifest['assets']:
        row=mesh_rows[asset['id']]
        catalog['assets'].append({'id':asset['id'],'crop':asset['crop'],'variant':asset['variant'],
            'stage':asset['stage'],'mesh':row['path'],'dimensions_cm':row['dimensions_cm'],
            'triangles_per_lod':row['triangles'],'lod_screen_sizes':row['lod_screen_sizes'],
            'materials':row['slots']})
    data=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if CATALOG.exists() and CATALOG.read_bytes()!=data:
        raise RuntimeError('Existing catalog differs; refusing replacement: '+str(CATALOG))
    assets=sorted(SOURCE.rglob('*'))
    assets=[p for p in assets if p.is_file()]
    assert len([p for p in assets if p.suffix=='.uasset'])==89
    expected={p.relative_to(SOURCE).as_posix() for p in assets}
    if TARGET.exists():
        unexpected={p.relative_to(TARGET).as_posix() for p in TARGET.rglob('*') if p.is_file()}-expected
        assert not unexpected, ('Unexpected target files',unexpected)
    for src in assets:
        dst=TARGET/src.relative_to(SOURCE)
        if dst.exists() and sha(dst)!=sha(src):
            raise RuntimeError('Existing target differs; refusing replacement: '+str(dst))
    installed=[]
    for src in assets:
        dst=TARGET/src.relative_to(SOURCE);dst.parent.mkdir(parents=True,exist_ok=True)
        existed=dst.exists()
        if not existed:shutil.copy2(src,dst)
        assert sha(src)==sha(dst)
        installed.append({'path':str(dst.relative_to(P)).replace('\\','/'),'bytes':dst.stat().st_size,
                          'sha256':sha(dst),'already_identical':existed})
    if not CATALOG.exists():CATALOG.write_bytes(data)
    receipt={'status':'installed', 'source_host':str(HOST), 'project':str(P/'FPSGAME.uproject'),
              'asset_root':'/Game/Props/Crops/V3','counts':verified['counts'],'uasset_count':89,
              'files':installed,'catalog':str(CATALOG.relative_to(P)).replace('\\','/'),
              'catalog_sha256':sha(CATALOG),'replaced_existing_assets':False,
              'runtime_tested':False,'shader_render_verified':False,'target_project_commandlet_loaded':False,
              'reason_for_isolated_host':'Concurrent FPSGAMEEditor build and unrelated commandlet; no game DLL or existing project assets loaded.',
              'host_independent_reload_verified':True,'installed_byte_hashes_verified':True}
    (ROOT/'Receipts/installed-assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'},indent=2))


if __name__=='__main__':
    main()
