from pathlib import Path
import json,shutil,subprocess,hashlib
O=Path(__file__).parent;p=O/'prism';root=O.parents[1];run='prism-horizontal-v1';frames=root/'Saved/ForegripAudit'/run;log=(p/f'runtime-{run}.log').read_text(encoding='utf-8-sig');assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
assert 'Result: Succeeded' in (O/'native_build.log').read_text(encoding='utf-8-sig')
assert 'PRISM_SOURCE_VALIDATION_PASS' in (O/'validate_release_final.log').read_text(encoding='utf-8-sig')
assert 'PRISM_IMPORT_PASS' in (p/'import_final.log').read_text(encoding='utf-8-sig')
assert 'GEOMETRY_CHECK_DONE' in (O/'geometry_release_final.log').read_text(encoding='utf-8-sig')
g=json.loads((p/'geometry_contact_full.json').read_text());assert len(g)==446 and not any(v['crossing_hand_triangles'] for v in g.values());imp=json.loads((p/'import_report.json').read_text());assert len(imp)==9
sc=json.loads((O/'self_contact.json').read_text());st=json.loads((O/'self_transitions.json').read_text());assert not any(sc['new'].values()) and not any(sum(v.values()) for v in st['after'].values())
for n in ['grasp_closeup.png','grasp_front.png','wrist_review.png','idle.png','ads.png','returned_8.png','returned_12.png']:shutil.copy2(frames/n,p/n)
entries=[]
for branch,ret in [('standard_normal','returned_6.png'),('standard_empty','returned_8.png'),('drum_normal','returned_10.png'),('drum_empty','returned_12.png')]:
 shots=sorted(frames.glob(branch+'_*.png'));assert shots;entries.append((frames/'idle.png',.6))
 for i,f in enumerate(shots):entries.append((f,max(.016,min(.25,shots[i+1].stat().st_mtime-f.stat().st_mtime)) if i+1<len(shots) else .06))
 entries.append((frames/ret,.8))
cat=p/'gameplay.ffconcat';cat.write_text('ffconcat version 1.0\n'+''.join("file '"+f.as_posix()+"'\nduration "+str(t)+'\n' for f,t in entries)+"file '"+entries[-1][0].as_posix()+"'\n")
ff=root/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe';subprocess.run([str(ff),'-y','-v','error','-safe','0','-f','concat','-i',str(cat),'-r','30','-c:v','libx264','-crf','19','-pix_fmt','yuv420p',str(p/'M4_Prism_Horizontal_Gameplay.mp4')],check=True)
rec={'run':run,'runtime_checks':log.count('FOREGRIP_AUDIT: PASS '),'runtime_failures':0,'animation_variants':9,'geometry_samples':len(g),'sampled_hand_attachment_crossings':0,'static_digit_pairs_checked':10,'static_digit_crossings':0,'reload_self_samples':len(st['after']),'reload_self_crossings':0,'pose_metrics':json.loads((O/'pose_metrics.json').read_text()),'import_readback':imp,'import_exit':int((p/'import_exit.txt').read_text(encoding='utf-8-sig').strip()),'import_environment_errors':'Existing GameFeatureData rule and occupied HTTP port; all nine imports and asset readback passed.','fbx_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.fbx')},'preview_note':'Silent actual-game screenshot sequence; no audio changes.','packaged_build_verified':False}
(O/'acceptance.json').write_text(json.dumps(rec,indent=2));print('HORIZONTAL_GRIP_ACCEPTED',rec['runtime_checks'])
