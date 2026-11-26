"""Cut new sleeves on each original native arm, retaining its own bind topology."""
import ast,sys,json,copy,math,hashlib
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write
from combat2_details import sew,DEST
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR2';OLD=P/'SourceAssets/ST6SleeveRepair20261018';BASE=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1'
text=(P/'Tools/ST6SleeveRepair/author.py').read_text();tree=ast.parse(text);code='\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','smooth','normals','build'])
code=code.replace('.07 * np.sin', '.30 * np.sin').replace('0.07 * np.sin','0.30 * np.sin').replace('0.045 * np.sin','0.13 * np.sin').replace('0.34 + 0.25 * (1 - cuff) + folds','0.46 + 0.65 * (1 - cuff) + folds')
code=code.replace('along / 25','along / 8').replace("coords[:, 0] *= 1.5","coords[:, 0] *= 4.6875").replace('dist[face] / 25','dist[face] / 8').replace('length / 25','length / 8').replace('thickness / 25','thickness / 8')
temp=R/'Authored/NativeSleeveBuild';temp.mkdir(exist_ok=True);ns=dict(json=json,copy=copy,math=math,hashlib=hashlib,Path=Path,bpy=bpy,bmesh=bmesh,np=np,Vector=Vector,read=read,OUT=temp);exec(compile(code,'combat_native_cut','exec'),ns)
native_rows={row['profile']:row for row in read(OLD/'before.json')['inventory']};plan=read(BASE/'plan.json');results=[]
for row in plan['rows']:
    rig=row['rig']
    if rig in ['Jason','Kaitlin']:continue
    current=read(BASE/'Inputs'/row['file'])
    if rig in native_rows:
        ns['build'](native_rows[rig]);s=read(temp/(rig+'.json'));names={b['name']:b['index'] for b in current['bones']};s['weights']=[[[names[n],w] for n,w in ws.items()] for ws in s['weights']];s['bones']=current['bones'];s['source']=current['source'];s['rig']=rig;s['material_slots']=['CombatRipstop','CombatCuff','CombatLining'];s['materials']=[DEST+'/Materials/M_'+m for m in s['material_slots']]
        sew(s)
    else:
        # These later native profiles retain their independently fitted sleeve
        # and are detailed in place; no other weapon's static pose is copied.
        s=current;s['materials']=[DEST+'/Materials/M_CombatCuff' if 'Cuff' in name else DEST+'/Materials/M_CombatLining' if 'Lining' in name else DEST+'/Materials/M_CombatRipstop' for name in s['material_slots']]
        from combat2_details import ns as detail_ns
        detail_ns['panels'](s)
    s['contract']='TS01 concept-fidelity native combat sleeve; original native arm cutting and paired facing, expanded cloth ease and localized compression folds, sewn cuff and arm details; native rest frame retained'
    file=R/'Authored'/f'shirt_fp_{rig}.json';write(file,s);results.append(dict(rig=rig,file=str(file),native=s['source']));write(R/'fp-authored.json',dict(completed=False,rows=results));print('TS01_R2_NATIVE_SLEEVE',rig,len(s['triangles']),flush=True)
write(R/'fp-authored.json',dict(completed=True,rows=results))
