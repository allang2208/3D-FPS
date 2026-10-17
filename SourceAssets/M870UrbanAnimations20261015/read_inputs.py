"""Read source skeletal frames needed to author the retarget, without rendering."""
import bpy,json,math,re
from mathutils import Matrix,Vector,Euler
from pathlib import Path
O=Path(__file__).parent
def smd(path):
    names={};parents={};frames=[];row={};section='';frame=None
    for line in Path(path).read_text().splitlines():
        line=line.strip()
        if line in ('nodes','skeleton','triangles'):section=line;continue
        if line=='end':section='';continue
        if section=='nodes':
            m=re.match(r'(\d+) "([^"]+)" (-?\d+)',line)
            if m:names[int(m[1])]=m[2];parents[m[2]]=int(m[3])
        elif section=='skeleton':
            if line.startswith('time '):
                if row:frames.append(row)
                row={};frame=int(line.split()[1])
            elif line:
                values=line.split();n=names[int(values[0])];v=list(map(float,values[1:]));row[n]=Matrix.Translation(Vector(v[:3])*.0254)@Euler(v[3:],'XYZ').to_matrix().to_4x4()
    if row:frames.append(row)
    parents={n:names.get(p) for n,p in parents.items()}
    world=[]
    for row in frames:
        w={}
        def resolve(n):
            if n not in w:w[n]=(resolve(parents[n]) if parents[n] else Matrix.Identity(4))@row[n]
            return w[n]
        for n in row:resolve(n)
        world.append(w)
    return dict(parents=parents,rows=world)
def serial(row):return {n:[list(v) for v in m] for n,m in row.items()}
if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M870Tactical20261015/M870_Gameplay_Editable.blend'),use_scripts=False)
    r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;s.frame_set(0)
    target={n:r.matrix_world@r.pose.bones[n].matrix for n in r.pose.bones.keys()}
    names=['idle','draw','fire','cycle','reloadstart','reloadinsert','reloadend','reloadendCycle']
    source={n:smd(O/'Original/870/anims'/f'{n}.smd') for n in names}
    details={}
    for name,clip in source.items():
        rows=clip['rows'];indices=sorted(set([0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1]))
        chosen=[n for n in rows[0] if 'Finger' not in n and not n.endswith('_end')]
        details[name]=dict(frames=len(rows),samples={f:{n:[round(v,5) for v in rows[f][n].translation] for n in chosen} for f in indices})
    data=dict(target_idle=serial(target),target_rest=serial({b.name:r.matrix_world@b.matrix_local for b in r.data.bones}),target_parents={b.name:b.parent.name if b.parent else None for b in r.data.bones},source_summary=details,source_idle=serial(source['idle']['rows'][0]),target_actions={a.name:list(a.frame_range) for a in bpy.data.actions if a.name.startswith('A_M870_')})
    (O/'inputs.json').write_text(json.dumps(data,indent=2))
    print('M870_UC_INPUTS',json.dumps({n:c['frames'] for n,c in details.items()}))
