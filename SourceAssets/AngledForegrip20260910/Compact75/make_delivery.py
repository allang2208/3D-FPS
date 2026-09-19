import json,re,sys,subprocess,hashlib
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[2];run=sys.argv[1];frames=ROOT/'Saved/ForegripAudit'/run
log=(O/f'runtime-{run}.log').read_text(encoding='utf-8-sig')
assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
imports=json.loads((O/'import_report.json').read_text());assert all('/M4AngledForegripCompact75/' in imports[n]['asset'] for n in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty'])
geometry=json.loads((O/'geometry_contact_full.json').read_text());assert len(geometry)==814 and all(v['crossing_hand_triangles']==0 for v in geometry.values())
sources=json.loads((O/'source_validation.json').read_text());assert len(sources)==9
assert all(max(v.values())<.0001 for v in sources.values())
assert (frames/'grasp_closeup.png').exists()
lines=[];count=0;duration=0
for prefix in ['standard_normal','standard_empty','drum_normal','drum_empty']:
 paths=sorted(frames.glob(prefix+'_*.png'));assert paths,prefix
 for i,p in enumerate(paths):
  hold=min(.25,max(1/60,paths[i+1].stat().st_mtime-p.stat().st_mtime)) if i+1<len(paths) else .35
  lines.extend(["file '"+p.as_posix()+"'",f'duration {hold:.6f}']);duration+=hold;count+=1
lines.extend(["file '"+(frames/'grasp_closeup.png').as_posix()+"'",'duration 2',"file '"+(frames/'grasp_closeup.png').as_posix()+"'"])
(O/'preview_frames.txt').write_text('\n'.join(lines),encoding='utf8')
ff=ROOT/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
subprocess.run([str(ff),'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(O/'preview_frames.txt'),'-vf','fps=30,format=yuv420p','-c:v','libx264','-crf','20','-movflags','+faststart',str(O/'M4_foregrip_gameplay.mp4')],check=True)
module=re.findall(r"UnrealEditor-FPSGAME-[^'\"\s/\\]+\.dll",log)
report={'run':run,'runtime_passes':log.count('FOREGRIP_AUDIT: PASS'),'runtime_failures':0,'modules':sorted(set(module)),'geometry_samples':len(geometry),'finger_grip_intersections_in_sampled_poses':0,'source_validation':sources,'import_validation':imports,'game_frames':count,'preview':'M4_foregrip_gameplay.mp4','preview_note':'Actual runtime screenshots; variable frame holds follow capture file timestamps, clamped to 1/60..0.25 seconds. Silent visual review, not audio synchronization evidence.','editable':'M4_AngledForegrip_Integrated_Editable.blend','grasp_parameters':json.loads((O/'fit_final.json').read_text())['compact_fit'],'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'SM_M4_AngledForegrip.fbx',O/'M4_AngledForegrip_Integrated_Editable.blend']}}
(O/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('FOREGRIP_DELIVERY_PASS',report['runtime_passes'],count)
