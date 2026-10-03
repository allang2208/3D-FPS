"""Check the actual weighted foot surfaces, in addition to analytic IK targets."""
import bpy,json,ast,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;OLD=OUT.parent/'AuthoringV1'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_PolishV2.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');arm=rig.data
rest={b.name:b.matrix_local.copy() for b in arm.bones};rest_inv={n:m.inverted() for n,m in rest.items()}
v=np.load(OLD/'source_vertices.npy');skin=np.load(OUT/'skin_weights.npz')
names=list(skin['bone_names']);indices=skin['indices'];values=skin['weights']
spec=json.loads((OLD/'skeleton_spec.json').read_text());byname={s['name']:s for s in spec}
meta=json.loads((OLD/'source_geometry.json').read_text());limbs={}
for key,pad in meta['feet_centres_m'].items():
    kind,side=key.split('.');bones=[kind+'_'+r+'.'+side for r in ('upper','lower','palm')]
    limbs[key]={'pad':Vector(pad),'shoulder':Vector(byname[bones[0]]['head']),
        'elbow':Vector(byname[bones[1]]['head']),'wrist':Vector(byname[bones[2]]['head']),
        'parent':byname[bones[0]]['parent'],'bones':bones,
        'toe_bones':[n for n in names if n.startswith(kind+'_digit_') and n.endswith('.'+side)]}
for file,functions in [(OLD/'rig_and_animate.py',{'smooth','segment_distance','sstep','lerp','track','rotation','around','aim_matrix','solve_limb'}),(OUT/'author_polish.py',{'pose'})]:
    for node in ast.parse(file.read_text()).body:
        if isinstance(node,ast.FunctionDef) and node.name in functions:exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'))
nearest=np.argmin(((v[:,None,:2]-np.asarray([list(d['pad'])[:2] for d in limbs.values()])[None,:,:])**2).sum(axis=2),axis=1)
report={}
rest_np=np.asarray([np.asarray(rest_inv[n],dtype=np.float32) for n in names])
for role,count in [('Run',21),('Move',31)]:
    report[role]={}
    for region,key in enumerate(limbs):
        selection=np.where((nearest==region)&(v[:,2]<.04))[0][::4]
        points=np.column_stack([v[selection],np.ones(len(selection))]);si=indices[selection];sw=values[selection]
        heights=[]
        for f in range(count):
            target,info=pose(f/30,role)
            if not info[key]['stance']:continue
            matrices=np.asarray([np.asarray(target[n],dtype=np.float32) for n in names])@rest_np
            z=np.zeros(len(selection))
            for k in range(4):z+=(matrices[si[:,k],2,:]*points).sum(axis=1)*sw[:,k]
            heights.append(float(np.min(z)))
        report[role][key]={'support_surface_min_cm':min(heights)*100,'support_surface_max_cm':max(heights)*100,'surface_samples':len(selection)}
(OUT/'surface_contact_checks.json').write_text(json.dumps(report,indent=2))
print('SLAG_SKIN_CONTACT '+json.dumps(report),flush=True)
