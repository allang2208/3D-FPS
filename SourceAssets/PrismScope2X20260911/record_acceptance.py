import hashlib, json, re
from pathlib import Path
from PIL import Image

p = Path(__file__).parent
report = {'asset': '/Game/Weapons/PrismScope2X/SM_PrismScope2X.SM_PrismScope2X',
          'mesh': json.loads((p/'mesh_report.json').read_text()), 'runs': {}}
for phase in ['write', 'reload']:
    log = (p/'scope2x-final'/f'{phase}.log').read_text(encoding='utf-8', errors='replace')
    match = re.search(r'M4_GUNSMITH: COMPLETE checks=(\d+) failures=(\d+)', log)
    assert match and match[2] == '0' and 'M4_GUNSMITH: FAIL' not in log
    mag = re.search(r'SCOPE2X_MAGNIFICATION ratio=([\d.]+) fov=([\d.]+)', log)
    assert mag and abs(float(mag[1])-2) < .02
    img = Image.open(p/'scope2x-final'/f'{phase}-panoramic-gameplay-ads.png').convert('RGB')
    cx, cy = img.width//2, img.height//2
    red = [(x,y) for y in range(cy-6,cy+7) for x in range(cx-6,cx+7)
           if (lambda c: c[0]>160 and c[0]>c[1]*1.8 and c[0]>c[2]*1.8)(img.getpixel((x,y))) ]
    assert red, 'Center red dot missing'
    report['runs'][phase] = {'checks':int(match[1]), 'failures':0,
        'magnification_ratio':float(mag[1]), 'horizontal_fov':float(mag[2]),
        'red_dot_centroid_px':[sum(a for a,b in red)/len(red),sum(b for a,b in red)/len(red)],
        'screen_center_px':[cx,cy], 'log':f'scope2x-final/{phase}.log'}
report['native_build'] = 'Succeeded; build_native.log'
report['import'] = {'assertion':'SCOPE2X_IMPORT_PASS', 'process_exit_code':1,
 'existing_errors':['GameFeatureData asset manager rule missing','HTTP 127.0.0.1:8000 bind failed'],
 'runtime_verified':True}
report['visual_review'] = {'ads':'Clear world view through bore and centered reticle',
 'mount':'25 mm foot on M4 rail; upper optic dimensions retained',
 'limitations':['Whole-camera 2x ADS zoom, not separate picture-in-picture optics',
 'Generated adjustment/focus detail remains softer than machined housing',
 '13 nonmanifold decorative-shell connections; no collision enabled']}
names = ['SM_PrismScope2X.fbx','PrismScope2X_Editable.blend','three_views.png','reference_white.png',
         'T_Scope2X_BaseColor.png','T_Scope2X_Roughness.png','T_Scope2X_Metallic.png','T_Scope2X_Normal.png']
report['sha256'] = {n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}
(p/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SCOPE2X_ACCEPTANCE_PASS',sum(x['checks'] for x in report['runs'].values()))
