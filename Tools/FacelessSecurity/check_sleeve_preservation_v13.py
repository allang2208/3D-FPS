"""Scoped preservation report for the sleeve repair; no rendering or game run."""
import bpy,json,hashlib,struct
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V13'
def digest(o,weights=True):
    h=hashlib.sha256()
    for v in o.data.vertices:
        h.update(struct.pack('<3f',*v.co))
        if weights:
            for g in v.groups:h.update((o.vertex_groups[g.group].name+':'+format(g.weight,'.8g')+';').encode())
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices));h.update(struct.pack('<I',f.material_index))
    return h.hexdigest()
snapshots={}
for rev in ['V11','V13']:
    bpy.ops.wm.open_mainfile(filepath=str(BASE/rev/('Authoring/FacelessSecurity_'+rev+'.blend')))
    rig=bpy.data.objects['root'];display=bpy.data.objects['Security_OutfitBody'];shirt=bpy.data.objects['Security_Uniform_SewnNeck_V11']
    hands={}
    for v in display.data.vertices:
        p=v.co;side='l' if p.x>0 else 'r';w=rig.matrix_world@rig.data.bones['hand_'+side].head_local;e=rig.matrix_world@rig.data.bones['lowerarm_'+side].head_local
        if abs(p.x)>.45 and (p-w).dot((w-e).normalized())>=.025:
            key=tuple(round(float(x),7) for x in p)
            hands[str(key)]=sorted((display.vertex_groups[g.group].name,round(g.weight,7)) for g in v.groups)
    snapshots[rev]={'body':digest(bpy.data.objects['Security_CompleteBody']),
        'uniform_geometry':digest(shirt,False),'hands':hands,
        'bone_reference':[(b.name,b.parent.name if b.parent else None,[list(r) for r in b.matrix_local]) for b in rig.data.bones],
        'other_parts':{o.name:digest(o) for o in bpy.context.scene.objects if o.type=='MESH' and o not in [display,shirt] and not o.name.startswith('Security_Cuff_')}}
a=snapshots['V11'];b=snapshots['V13']
report={k:a[k]==b[k] for k in ['body','uniform_geometry','hands','bone_reference','other_parts']}
report['unchanged_palm_finger_vertices']=len(b['hands']);report['game_tested']=False
(ROOT/'Diagnosis/preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SLEEVE_PRESERVATION '+json.dumps(report),flush=True)
if not all(report[k] for k in ['body','uniform_geometry','hands','bone_reference','other_parts']):raise RuntimeError('Unexpected preservation difference')
