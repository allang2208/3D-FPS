from pathlib import Path
import json,hashlib,shutil,subprocess,sys
O=Path(__file__).parent;root=O.parents[1];summary={'family':'vertical_grip','shared_pose':json.loads((O/'shared_pose_validation.json').read_text()),'members':{},'packaged_build_verified':False,'audio_changed':False}
assert 'Result: Succeeded' in (O/'native_build.log').read_text(encoding='utf-8-sig')
for key,title,run in [('vertical','Vertical','vertical-family-v1'),('prism','Prism','prism-family-v1')]:
 p=O/key;frames=root/'Saved/ForegripAudit'/run;log=(p/f'runtime-{run}.log').read_text(encoding='utf-8-sig');assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
 g=json.loads((p/'geometry_contact_full.json').read_text());assert len(g)==446 and all(v['crossing_hand_triangles']==0 for v in g.values());assert 'GEOMETRY_CHECK_DONE' in (p/'check_geometry_final.log').read_text(encoding='utf-8-sig');assert title.upper()+'_SOURCE_VALIDATION_PASS' in (p/'validate_source_final.log').read_text(encoding='utf-8-sig');assert title.upper()+'_IMPORT_PASS' in (p/'import_final.log').read_text(encoding='utf-8-sig')
 imp=json.loads((p/'import_report.json').read_text());assert len(imp)==9;assert all(v['right_weapon_difference_cm']<.01 and v['preserved_contact_difference_cm']<.01 for v in imp.values())
 for n in ['grasp_closeup.png','grasp_front.png','wrist_review.png','idle.png','ads.png','returned_8.png','returned_12.png']:shutil.copy2(frames/n,p/n)
 entries=[]
 for branch,ret in [('standard_normal','returned_6.png'),('standard_empty','returned_8.png'),('drum_normal','returned_10.png'),('drum_empty','returned_12.png')]:
  shots=sorted(frames.glob(branch+'_*.png'));assert shots;entries.append((frames/'idle.png',.6))
  for i,f in enumerate(shots):entries.append((f,max(.016,min(.25,shots[i+1].stat().st_mtime-f.stat().st_mtime)) if i+1<len(shots) else .06))
  entries.append((frames/ret,.8))
 cat=p/'gameplay.ffconcat';cat.write_text('ffconcat version 1.0\n'+''.join("file '"+f.as_posix()+"'\nduration "+str(t)+'\n' for f,t in entries)+"file '"+entries[-1][0].as_posix()+"'\n")
 ff=root/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe';subprocess.run([str(ff),'-y','-v','error','-safe','0','-f','concat','-i',str(cat),'-r','30','-c:v','libx264','-crf','19','-pix_fmt','yuv420p',str(p/f'M4_{title}_Family_Gameplay.mp4')],check=True)
 rec={'run':run,'runtime_checks':log.count('FOREGRIP_AUDIT: PASS '),'runtime_failures':0,'geometry_samples':len(g),'sampled_intersections':0,'animation_variants':9,'import_exit':int((p/'import_exit.txt').read_text(encoding='utf-8-sig').strip()),'import_readback':imp,'profile':json.loads((p/'profile.json').read_text()),'fbx_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.fbx')},'preview_frames':len(entries),'preview_note':'Silent actual-game screenshot sequence, not audio verification'}
 (p/'acceptance.json').write_text(json.dumps(rec,indent=2));summary['members'][key]=rec
summary['generator_sha256']=hashlib.sha256((O/'build_family.py').read_bytes()).hexdigest();summary['total_runtime_checks']=sum(x['runtime_checks'] for x in summary['members'].values());(O/'family_acceptance.json').write_text(json.dumps(summary,indent=2));print('FAMILY_ACCEPTANCE_PASS',summary['total_runtime_checks'])
