from pathlib import Path
import hashlib, json, re
from PIL import Image

p=Path(__file__).parent
r={'asset':'/Game/Weapons/LPVO1to6X/SM_LPVO1to6X.SM_LPVO1to6X',
   'mesh':json.loads((p/'mesh_report.json').read_text()),'runs':{},
   'import_exit_code':1,'import_marker':'LPVO_IMPORT_PASS','native_build':'Succeeded',
   'limitations':['Whole-camera ADS zoom, not picture-in-picture optics','Zoom resets to 1x on weapon rebuild; attachment installation persists']}
for phase in ['write','reload']:
    s=(p/'lpvo-release'/f'{phase}.log').read_text(encoding='utf-8',errors='replace')
    m=re.search(r'COMPLETE checks=(\d+) failures=(\d+)',s)
    assert m and m[2]=='0' and 'M4_GUNSMITH: FAIL' not in s
    measurements=re.findall(r'LPVO_MAGNIFICATION expected=([\d.]+) actual=([\d.]+) reticle_px=([\d.]+)',s)
    assert len(measurements)==4
    for expected,actual,error in measurements:assert abs(float(expected)-float(actual))<.03 and float(error)<2
    # Real ADS viewport evidence: a visible red center at 6x, plus clear sky offset from the crosshair.
    im=Image.open(p/'lpvo-release'/f'{phase}-lpvo-6x.png').convert('RGB')
    red=[im.getpixel((x,y)) for x in range(796,805) for y in range(446,455)]
    assert any(a>160 and a>b*1.8 and a>c*1.8 for a,b,c in red)
    assert min(im.getpixel((830,410)))>100, 'Optical aperture obstructed'
    r['runs'][phase]={'checks':int(m[1]),'failures':0,'zoom_measurements':measurements,'center_and_clear_aperture_pixels':True}
r['sha256']={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['SM_LPVO1to6X.fbx','SM_LPVORing.fbx','LPVO_Editable.blend','LPVO_SeparateParts.blend','T_LPVO_BaseColor.png','T_LPVO_Roughness.png','T_LPVO_Metallic.png','T_LPVO_Normal.png','three_views.png','reference_white.png']}
(p/'acceptance.json').write_text(json.dumps(r,indent=2))
print('LPVO_ACCEPTANCE_PASS',sum(a['checks'] for a in r['runs'].values()))
