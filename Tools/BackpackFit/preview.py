"""Build an isolated author-geometry snapshot for the requested comparison."""
import copy,hashlib,json,os,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactFitR3'));O=R/'Preview'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
O.mkdir(exist_ok=True);(O/'Capture').mkdir(exist_ok=True)
plan=read(R/'plan.json');records=read(R/'captured.json');authored=read(R/'authored.json')
for row in authored['statics']+authored['rows']:
    path=row['asset']+'.'+row['asset'].rsplit('/',1)[-1];old=records[row['source']];folder=O/'Capture'/hashlib.sha256(path.encode()).hexdigest()[:16];folder.mkdir(exist_ok=True)
    shutil.copy2(row['positions'],folder/'positions.bin');shutil.copy2(Path(old['folder'])/'triangles.bin',folder/'triangles.bin')
    if old.get('mask_valid'):shutil.copy2(Path(old['folder'])/'mask.bin',folder/'mask.bin')
    new=copy.deepcopy(old);new.update(path=path,folder=str(folder),geometry='authored preview, not yet imported');new.pop('render_vertices',None);new.pop('render_triangles',None);records[path]=new
for row in plan['rows']:
    authored_row=next((a for a in authored['rows'] if a['rig']==row['rig'] and a['item']==row['item'] and a['shirt']==row['shirt']),None)
    if not authored_row:continue
    row['mesh']=authored_row['asset']+'.'+authored_row['asset'].rsplit('/',1)[-1]
    for key in ['rigid_mesh','rigid_location','rigid_rotation_quat']:
        if key in authored_row:row[key]=authored_row[key]
plan.update(scope='authored prospective reference geometry, not yet imported; same current route matrix',geometry_stage='authored_preview')
(O/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8');(O/'captured.json').write_text(json.dumps(records,indent=2))
print('BACKPACK_FIT_PREVIEW_PREPARED',len(authored['rows']))
