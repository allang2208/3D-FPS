"""Replace only detached torso adornments; retain the current garment surfaces."""
import copy,json,hashlib,sys,gc
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'FacingFix20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from author_body import append_trim,fitted_tree
from geometry import normals,write

def main():
    OUT.mkdir(exist_ok=True);report={'completed':False,'profiles':{},'runtime_tested':False}
    cfg=P/'Content/ColdSteelData/modular_outfits.json'
    before=OUT/'modular_outfits-before.json'
    if not before.exists():before.write_bytes(cfg.read_bytes())
    for profile in ('Body','Body_Owner','Jason','Jason_Owner'):
        src=R/'Authored/Body'/(profile+'.json');backup=OUT/'Before'/(profile+'.json');backup.parent.mkdir(exist_ok=True)
        if not backup.exists():backup.write_bytes(src.read_bytes())
        raw=backup.read_bytes();d=json.loads(raw);faces=np.asarray(d['triangles']);mats=np.asarray(d['triangle_materials'])
        # Adornments are separate islands; the collar and torso share their
        # embroidery/lining slots. Keep whole body islands, not slot-wide cuts.
        parent=list(range(len(d['positions'])))
        def root(a):
            while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
            return a
        for a,b,c in faces:
            a,b,c=int(a),int(b),int(c);parent[root(b)]=root(a);parent[root(c)]=root(a)
        solid={root(int(v)) for fi in np.flatnonzero(np.isin(mats,[0,1,2,3,4,9])) for v in faces[fi]}
        keep=[i for i,f in enumerate(faces) if root(int(f[0])) in solid]
        used=sorted({v for fi in keep for v in d['triangles'][fi]});remap={v:i for i,v in enumerate(used)}
        fixed=copy.deepcopy(d)
        fixed['positions']=[d['positions'][i] for i in used];fixed['weights']=[d['weights'][i] for i in used]
        for key in ('uv','normals','triangle_materials'):fixed[key]=[d[key][i] for i in keep]
        fixed['triangles']=[[remap[v] for v in d['triangles'][fi]] for fi in keep]
        # The fitting BVH contains only the retained body/lining/skirt, never
        # old strips or a front-facing hood that could intercept the new rays.
        cast=fitted_tree(fixed);trim={k:copy.deepcopy(v) for k,v in fixed.items() if k not in ('positions','weights','triangles','normals','uv','triangle_materials')}
        trim.update(positions=[],weights=[],triangles=[],normals=[],uv=[],triangle_materials=[])
        scale=d['cloth_dimensions']['scale'];top=d['bones'].get('neck_02',d['bones']['neck_01'])['position'][2]-.45*scale
        append_trim(trim,cast,d['cloth_dimensions']['waist_cm'],top,not profile.endswith('_Owner'))
        pts=np.asarray(trim['positions']);tri=np.asarray(trim['triangles']);trim['normals']=normals(pts,tri)[tri].tolist()
        offset=len(fixed['positions'])
        for key in ('positions','weights','normals','uv','triangle_materials'):fixed[key].extend(trim[key])
        fixed['triangles'].extend([[v+offset for v in f] for f in trim['triangles']])
        fixed['facing_revision']='20261020-native-forward-v1'
        fixed['contract']=d['contract']+'; native toe-facing chest trim and clasp; fitted rear hood and lining'
        target=OUT/'Authored'/f'{profile}.json';write(target,fixed);write(src,fixed)
        report['profiles'][profile]={'before_sha256':hashlib.sha256(raw).hexdigest(),'author_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'author_file':str(target),'retained_triangles':len(keep),'replaced_triangles':len(faces)-len(keep),'new_adornment_triangles':len(trim['triangles']),'forward_axis':'+Y','runtime_tested':False}
        write(OUT/'authored.json',report);print('ROBE_FACING_AUTHORED',profile,flush=True);del fixed,d,trim,cast;gc.collect()
    report['completed']=True;write(OUT/'authored.json',report)
if __name__=='__main__':main()
