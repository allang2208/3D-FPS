from pathlib import Path
import json,re,hashlib,shutil,subprocess,sys
O=Path(__file__).parent;root=O.parents[2];run=sys.argv[1];frames=root/'Saved/ForegripAudit'/run
log=(O/f'runtime-{run}.log').read_text(encoding='utf-8-sig');assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
# UI code and attachment model are unchanged; prior UI evidence stays in Integration.
geo=json.loads((O/'geometry_contact_full.json').read_text());assert len(geo)==446 and all(v['crossing_hand_triangles']==0 for v in geo.values())
imp=json.loads((O/'import_report.json').read_text());clips={k:v for k,v in imp.items() if isinstance(v,dict) and 'duration' in v};assert len(clips)==9
assert all(v['right_weapon_difference_cm']<.01 and v['preserved_contact_difference_cm']<.01 for v in clips.values())
source=json.loads((O/'source_validation.json').read_text());assert len(source)==9
assert 'VERTICAL_SOURCE_VALIDATION_PASS' in (O/'validate_source_final.log').read_text(encoding='utf-8-sig')
for n in ['idle.png','ads.png','grasp_closeup.png','grasp_front.png','wrist_review.png','returned_8.png','returned_12.png']:shutil.copy2(frames/n,O/n)
entries=[]
for branch,returned in [('standard_normal','returned_6.png'),('standard_empty','returned_8.png'),('drum_normal','returned_10.png'),('drum_empty','returned_12.png')]:
 shots=sorted(frames.glob(branch+'_*.png'));assert shots
 entries.append((frames/'idle.png',.6))
 for i,p in enumerate(shots):entries.append((p,max(.016,min(.25,shots[i+1].stat().st_mtime-p.stat().st_mtime)) if i+1<len(shots) else .06))
 entries.append((frames/returned,.8))
concat=O/'gameplay.ffconcat';concat.write_text('ffconcat version 1.0\n'+''.join("file '"+p.as_posix()+"'\nduration "+str(t)+'\n' for p,t in entries)+"file '"+entries[-1][0].as_posix()+"'\n")
ff=root/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
r=subprocess.run([str(ff),'-y','-v','error','-safe','0','-f','concat','-i',str(concat),'-r','30','-c:v','libx264','-crf','19','-pix_fmt','yuv420p',str(O/'M4_VerticalForegrip_Gameplay.mp4')],capture_output=True);assert r.returncode==0,r.stderr
hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in O.glob('*.fbx')}
assert 'ARM_SUPPORT_PASS' in (O/'validate_arm_final.log').read_text(encoding='utf-8-sig')
assert 'Result: Succeeded' in (O/'native_build.log').read_text(encoding='utf-8-sig')
record={'arm_comparison':json.loads((O/'arm_validation.json').read_text()),'runtime_run':run,'runtime_checks':log.count('FOREGRIP_AUDIT: PASS '),'runtime_failures':0,'ui_note':'UI and compact mesh unchanged; prior 24-check report retained in Compact75','animation_variants':9,'geometry_samples':len(geo),'sampled_intersections':0,'source_contract':source,'import_clips':clips,'material_assignment':'Existing M4VerticalGripCompact75 static mesh and M4 material unchanged','import_exit_code':1,'import_note':'Import and readback passed; process exit 1 includes existing GameFeatureData configuration errors. New game process independently passed.','native_build':'Animation resource path updated; build suffix 2026095421','packaged_build_verified':False,'preview_note':'Actual game screenshots assembled in capture order using bounded capture-time intervals; silent visual preview, not audio verification.','preview_frames':len(entries),'fbx_sha256':hashes,'visual_review':'New game wrist, palm, front and first-person views reviewed; elbow opened toward shooter left; whole grasp rotated 25 degrees about grip axis, original finger curls and arm mesh retained.'}
(O/'acceptance.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print({k:record[k] for k in ['runtime_checks','runtime_failures','geometry_samples','sampled_intersections','preview_frames']})



