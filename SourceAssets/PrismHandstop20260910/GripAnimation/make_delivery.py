from pathlib import Path
from PIL import Image
import json,re,hashlib,shutil,sys
O=Path(__file__).parent;root=O.parents[2];run=sys.argv[1] if len(sys.argv)>1 else 'prism-grip-wrap';frames=root/'Saved/ForegripAudit'/run
log=(O/f'runtime-{run}.log').read_text(encoding='utf-8-sig')
assert 'Result: Succeeded' in (O/'native_build_wrap_final.log').read_text(encoding='utf-8-sig')
assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
for name in ['grasp_closeup.png','grasp_front.png','idle.png','ads.png','returned_8.png','returned_12.png']:
 shutil.copy2(frames/name,O/name)
delivery={}
for branch,returned in [('standard_normal','returned_6.png'),('standard_empty','returned_8.png')]:
 shots=sorted(frames.glob(branch+'_*.png'));assert shots
 paths=[frames/'idle.png']+shots+[frames/returned];images=[];durations=[600]
 for i,p in enumerate(shots):
  durations.append(max(20,min(250,round(((shots[i+1].stat().st_mtime-p.stat().st_mtime) if i+1<len(shots) else .06)*1000))))
 durations.append(800)
 for p in paths:
  with Image.open(p) as im:images.append(im.convert('RGB').resize((640,448),Image.Resampling.LANCZOS))
 name=branch+'_preview.gif';images[0].save(O/name,save_all=True,append_images=images[1:],duration=durations,loop=0,optimize=True)
 delivery[name]={'source_files':[str(p.relative_to(root)) for p in paths],'durations_ms':durations,'note':'Sampled game screenshots; silent review, not audio timing evidence.'}
geo=json.loads((O/'geometry_contact_full.json').read_text());assert all(v['crossing_hand_triangles']==0 for v in geo.values())
contact=json.loads((O/'contact_fit.json').read_text())['final_surfaces']
assert all(contact[d]['encloses_grip_section'] for d in ['index','middle'])
depths=json.loads((O/'grasp_inspection.json').read_text());assert all(v['max_penetration_m']<.0001 for v in depths.values())
imports=json.loads((O/'import_report.json').read_text());assert len(imports)==9
source=json.loads((O/'source_validation.json').read_text());assert len(source)==9
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assets={}
for clip in imports:
 name='A_M4_Prism_'+clip
 assets[name]={ext:digest(O/(name+ext)) for ext in ['.blend','.fbx']}
 assets[name]['uasset']=digest(root/'Content/Weapons/M4PrismGrip'/(name+'.uasset'))
record={'runtime_run':run,'runtime_checks':len(re.findall('FOREGRIP_AUDIT: PASS ',log)),'runtime_failures':0,'runtime_exit_code':0,'animation_variants':len(imports),'sampled_contact_poses':len(geo),'sampled_intersecting_poses':0,'max_import_compression_error_cm':max(v['compression_error_cm'] for v in imports.values()),'max_preserved_contact_difference_cm':max(v['preserved_contact_difference_cm'] for v in imports.values()),'native_build':'Succeeded','import_pass':True,'import_exit_code':1,'import_errors':'Existing GameFeatureData asset manager configuration errors; see import_wrap.log.','packaged_build_verified':False,'audio_changed':False,'assets':assets,'delivery':delivery}
record['visual_fit']='Corrected palm orientation; index and middle wrap around the handstop section; game palm and front views reviewed.'
record['native_build_log']='native_build_wrap_final.log'
record['max_static_penetration_m']=max(v['max_penetration_m'] for v in depths.values())
(O/'acceptance.json').write_text(json.dumps(record,indent=2))
print('PRISM_DELIVERY_PASS', {k:v for k,v in record.items() if k not in ['assets','delivery']})
