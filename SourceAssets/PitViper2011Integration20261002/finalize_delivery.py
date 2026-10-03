"""Record actual production outcomes; does not load/check/test game assets."""
import json
from pathlib import Path
from datetime import datetime,timezone
O=Path(__file__).parent
assets=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
pending_build={'status':'pending_regular_editor_build','base_dll_updated_by_this_task':False,
 'regular_build':'Blocked before launching UBT: active FPSGAME editor. Existing editor/PIE retained.',
 'live_coding_result':'CompileNotStarted','live_coding_attempts':2,'patch_applied':False,
 'evidence':'livecoding_result_02.txt','next_step':'Close the existing editor normally, then run build_editor.ps1',
 'runtime_tested':False}
build_path=O/'build_receipt.json'
build=json.loads(build_path.read_text(encoding='utf-8-sig')) if build_path.exists() else pending_build
if not build_path.exists():build_path.write_text(json.dumps(build,ensure_ascii=False,indent=2),encoding='utf8')
fire_job=O.parent/'PitViper2011Fire20261002'
fire_source=fire_job/'source_receipt.json'
if fire_source.exists():
 fire_build=fire_job/'build_receipt.json'
 build=json.loads(fire_build.read_text(encoding='utf-8-sig')) if fire_build.exists() else dict(status='pending_regular_editor_build',runtime_tested=False)
native_saved=build.get('status')=='Succeeded'
sharing_path=O.parent/'WeaponAnimationSharing20261002/production_summary.json'
sharing=json.loads(sharing_path.read_text(encoding='utf-8')) if sharing_path.exists() else None
profile_count=sharing['totals']['saved_profiles'] if sharing else 0
delivery={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
 'definition':'ue_pit_viper2011','name':'Pit Viper 2011','ammo':'ammo_9','capacity':15,'automatic':False,
 'status':'assets_saved_and_runtime_source_connected; '+('native_build_saved' if native_saved else 'native_build_pending'),
 'actual_saved_packages':len(assets['saved'])+profile_count,'weapon_import_saved_packages':len(assets['saved']),'meshes':assets['meshes'],
 'saved_animation_count':len(assets['animations']),'material_slots':assets['materials'],
 'catalog_published':assets.get('catalog_published',False),'outfit_profile_keys':assets.get('profiles',[]),
 'regular_dll_build':build.get('status'),'live_coding':'CompileNotStarted; no patch success claimed',
 'source':{'author':'D_U (DU1701)','license':'CC BY 4.0','credential_saved':False,'temporary_url_saved':False},
 'runtime_tested':False,'acceptance_rendered':False,
 'source_changes_receipt':'runtime_edits.json','shared_bridge_change':'Optional RequestTimeoutSeconds, default unchanged at 100; long compile request used 600.',
 'user_testing':'After the regular Editor build, start the game normally and use the existing armory/warehouse flow.'}
if sharing:
 delivery['animation_sharing']=dict(complete=sharing['complete'],saved_profiles=profile_count,
  converted_variants=sharing['unique_variants_without_full_clip_reference'],
  retained_pairs=sharing['totals']['retained_pairs'],bytes=sharing['totals']['bytes'],keys=sharing['totals']['keys'],
  author_full_clip_count=len(assets['animations']),independent_full_clip_family_count=len(assets['animations'])-sharing['unique_variants_without_full_clip_reference'],
  producer='SourceAssets/WeaponAnimationSharing20261002/run_install.ps1',source_animations_deleted=False,
  runtime_tested=False,cook_size_measured=False)
if fire_source.exists():
 fire_delivery=fire_job/'delivery_receipt.json'
 delivery['fire_upgrade']=json.loads(fire_delivery.read_text(encoding='utf-8')) if fire_delivery.exists() else dict(status='source_saved',reference='M1911 pistol',runtime_tested=False)
fire_audio=O.parent/'PitViper2011FireAudio20261002/import_receipt.json'
if fire_audio.exists():delivery['fire_audio']=json.loads(fire_audio.read_text(encoding='utf8'))
pistol_suppressed=O.parent/'PitViper2011FireAudio20261002/suppressed_import_receipt.json'
if pistol_suppressed.exists():delivery['pistol_shared_suppressed_audio']=json.loads(pistol_suppressed.read_text(encoding='utf8'))
(O/'delivery_receipt.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
print('DELIVERY_RECORDED',delivery['actual_saved_packages'],'saved packages;',len(assets['animations']),'author animations;',profile_count,'delta profiles;',build.get('status'))
