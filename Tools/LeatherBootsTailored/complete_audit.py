"""Summarize evidence without treating headless networking as rendered acceptance."""
import hashlib,json
from pathlib import Path
from boot_paths import P,R,read,write
A=R/'Audit';cfg=read(P/'Content/ColdSteelData/modular_outfits.json')['items'];catalog=read(P/'Content/ColdSteelData/items.json');saved=read(R/'saved_assets.json');repair=read(A/'legacy_displays.json');published=read(R/'published.json');geometry=read(R/'saved_read.json')
assert repair['completed'] and len(repair['saved'])==4
def disk(path):return P/'Content'/(path.split('.')[0][6:]+'.uasset')
def exists(path):return bool(path) and disk(path).is_file()
boot=cfg['ue_leather_boots']['rig_meshes']['Jason'];robe=cfg['ue_blue_mage_robe'];shirt=cfg['ue_field_sweater']
assert boot==published['mesh'] and robe['underlayer_meshes'][boot]==published['robe_inner']
paths=[boot,published['robe_inner'],*saved['displays'].values(),saved['icon_texture'],*saved['materials'],*saved['robe_materials'],*repair['saved']]
assert all(exists(p) for p in paths)
pants=[]
for key,row in cfg.items():
    if row.get('slot')!=15:continue
    normal=row.get('rig_meshes',{}).get('Jason','');fit=row.get('shoe_fit_meshes',{}).get('ue_leather_boots',{}).get('Jason','')
    selected=fit or normal;inner=robe['underlayer_meshes'].get(selected,robe['pants_underlayer_default']['shoe_fit_meshes']['ue_leather_boots']['Jason'])
    top=shirt.get('pants_mesh_fit_meshes',{}).get(selected,shirt.get('pants_fit_meshes',{}).get(key,shirt['pants_fit_default']))['rig_meshes']['Jason']
    row=dict(item=key,normal=normal,boot_fit=fit,robe_inner=inner,shirt_fit=top,assets_exist=all(exists(p) for p in (normal,selected,inner,top)))
    assert row['assets_exist'];pants.append(row)
icon=R/'ue_leather_boots.png';icon_hash=hashlib.sha256(icon.read_bytes()).hexdigest()
assert all(hashlib.sha256((P/'Content/ColdSteelData'/p).read_bytes()).hexdigest()==icon_hash for p in repair['icons'])
assert catalog['ue_leather_boots']['world_mesh']==saved['displays']['pickup'] and catalog['ue_leather_boots']['ue_equipment_icon_mesh']==saved['displays']['icon']
cook=(P/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig');build=(P/'Source/FPSGAME/FPSGAME.Build.cs').read_text(encoding='utf-8-sig')
assert '+DirectoriesToAlwaysCook=(Path="/Game/Characters/ModularOutfit20260924")' in cook
assert '$(ProjectDir)/Content/ColdSteelData/...' in build
report=dict(scope='LeatherBoots TailoredV2 plus its leather trousers, ranger shirt, robe and historical item presentation routes',asset_integration_complete=True,legacy_presentation_repaired=True,legacy_assets=len(repair['saved']),legacy_pngs=len(repair['icons']),pants_routes=pants,cook_and_json_staging_configured=True,wearable_lods={k:[lod['triangles'] for lod in v['lods']] for k,v in geometry['meshes'].items()},open_findings=[dict(severity='performance',issue='All three wearable LODs retain 214916 triangles per pair; distance LODs do not reduce geometry.',status='not changed; needs reduction and silhouette/deformation review')],boundaries=['No rendered gameplay acceptance in this audit','No dedicated server, three simultaneous players, cross-machine packaged build or GPU frame-time capture'],evidence=dict(legacy='legacy_displays.json',prior_saved_meshes='../saved_read.json',prior_source_pose_check='../model_check.json'))
if (A/'DistanceLODs/geometry_check.json').exists():
    lod_check=read(A/'DistanceLODs/geometry_check.json');lod_read=read(A/'DistanceLODs/read_back.json');lod_saved=read(A/'DistanceLODs/saved.json')
    assert lod_check['completed'] and lod_read['completed']
    report['wearable_lods']={path:[lod['triangles'] for lod in row['lods']] for path,row in lod_read['meshes'].items()}
    report['open_findings']=[];report['distance_lod_check']=lod_check;report['distance_lod_saved']=True
    report['evidence']['distance_lods']='DistanceLODs/read_back.json'
    paths.extend(row['policy'] for row in lod_saved['meshes'].values())
wire=read(A/'wire-receipt.json') if (A/'wire-receipt.json').exists() else None
if wire:
    cases=read(Path(wire['directory'])/'host.json');report['wire']=wire;report['wire_cases']=len(cases['cases']);report['wire_all_cases_passed']=bool(cases['passed']) and len(cases['cases'])==14 and all(r['passed'] for r in cases['cases']);report['evidence']['wire']=wire['directory'];report['wire_status']='passed' if report['wire_all_cases_passed'] else 'failed'
else:
    report['wire_all_cases_passed']=False;report['wire_status']='blocked_before_host_ready';report['boundaries'].append('Network test not completed; see Wire startup logs')
    failures=[]
    for run in sorted((A/'Wire').iterdir()):
        log=run/'host.log'
        if not log.exists():continue
        text=log.read_text(encoding='utf-8-sig',errors='replace')
        if 'EXCEPTION_ACCESS_VIOLATION' in text:
            failures.append(dict(directory=str(run),host_ready='MAGE_WIRE_HOST_READY' in text,stack_site='UFPSPlayerBodyComponent::InitializeBody line 291: LoadObject<UAnimSequence>',result='access violation during startup'))
    report['startup_failures']=failures
    report['startup_diagnostic']=dict(last_uncompleted_load='/Game/Characters/JasonPlayer20261003/TwinblastDual20261022/Retargeted/J_Twinblast_Idle',source='Wire/20261022-143453/host.log',interpretation='Last package started immediately before the crash; root cause not proven. Initial compression/resave retained the sampled motion but did not resolve the crash.',animation_warmup='150 body clips loaded/compressed in a commandlet with zero errors; retry still crashed')
    report['open_findings'].append(dict(severity='validation_blocker',issue='Headless listen host crashes before the wardrobe test starts',status='startup repair and wire retest pending'))
if (A/'StartupRepair/retarget_reference_repair.json').exists():report['startup_reference_repair']=read(A/'StartupRepair/retarget_reference_repair.json')
if (A/'StartupRepair/skeleton_curve_metadata.json').exists():
    report['startup_curve_metadata_repair']=read(A/'StartupRepair/skeleton_curve_metadata.json')
    report['startup_curve_metadata_repair']['runtime_retest_pending']=not report['wire_all_cases_passed']
    report['evidence']['startup_root_cause']='StartupRepair/resolved-stack.txt'
    report['evidence']['startup_repair']='StartupRepair/skeleton_curve_metadata.json'
if (A/'legacy_saved_check.json').exists():report['legacy_fresh_read']=read(A/'legacy_saved_check.json')['completed']
report['current_assets_sha256']={p:hashlib.sha256(disk(p).read_bytes()).hexdigest() for p in paths}
write(A/'completion_review.json',report)
print(json.dumps({k:report[k] for k in ('asset_integration_complete','legacy_presentation_repaired','wire_all_cases_passed','open_findings')},ensure_ascii=False,indent=2))
