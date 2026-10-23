"""Author seam motion masks and per-pack inertia calibration; no geometry reduction."""
import json,hashlib
from pathlib import Path
import numpy as np
from response_profiles import PROFILES as RESPONSE_PROFILES
from register_response_refit import apply as apply_response_refit
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022';(R/'Masks').mkdir(exist_ok=True)
specs=[('alice','ue_portable_backpack',R/'AliceFit',3.7,.85,2.4,.32),
       ('mountain','ue_mountain_backpack',P/'SourceAssets/BackpackHarnessRebuild20261020',3.3,.82,3.,.45),
       ('expedition','ue_expedition_backpack',P/'SourceAssets/ExpeditionBackpack20261022',2.8,.94,1.8,.24)]
rows=[];configs={}
for kind,item,root,freq,damping,angle,bounce in specs:
    source_manifest=json.loads((root/'manifest.json').read_text());all_min=[];all_max=[]
    for row in source_manifest['variants']:
        source=Path(row['source']);data=json.loads(source.read_text());v=np.asarray(data['positions']);t=np.asarray(data['triangles'])
        mask=np.ones(len(v));mask[:data['harness_vertex_count']]=0.
        for part in data['parts']:
            if part['name'].startswith('shoulder_return_') or part['name']=='padded_hip_belt':
                path=np.asarray(part['path']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
                ids=np.unique(t[part['side_faces']+part['cap_faces']]);_,nearest=cKDTree(path).query(v[ids])
                distance=np.minimum(arc[nearest],arc[-1]-arc[nearest]);blend=np.clip(distance/12.,0.,1.)
                mask[ids]=1.-blend*blend*(3-2*blend)
        # Keep the clasp, chest strap and torso stations fixed; only the sewn
        # bag ends interpolate into the full rigid-body movement field.
        rigid=v[np.unique(t[data['harness_face_count']:])];all_min.append(rigid.min(0));all_max.append(rigid.max(0))
        target=row['asset'] if kind=='alice' else '/Game/Characters/BackpackMotion20261022/'+kind.title()+'/'+row['asset'].split('/')[-1]
        mask_path=R/'Masks'/(kind+'_'+row['profile']+'.json')
        mask_path.write_text(json.dumps({'positions':data['positions'],'values':mask.tolist()},separators=(',',':')))
        rows.append({'kind':kind,'item':item,'profile':row['profile'],'shirt':row['shirt'],'source':str(source),
                     'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mask':str(mask_path),'mask_sha256':hashlib.sha256(mask_path.read_bytes()).hexdigest(),
                     'input_asset':row['asset'] if kind!='alice' else '/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SK_Jason_Backpack.SK_Jason_Backpack',
                     'asset':target,'new_geometry':kind=='alice'})
    lo=np.min(all_min,axis=0);hi=np.max(all_max,axis=0)
    configs[item]={'frequency_hz':freq,'damping':damping,'max_angle_degrees':angle,'max_bounce_cm':bounce,
                   'pivot':[0.,float(hi[1]-2.),134.],'bounds_min':lo.tolist(),'bounds_max':hi.tolist()}
    configs[item].update(RESPONSE_PROFILES[item])
plan={'revision':'BackpackInertiaR1_20261022','variants':rows,'settings':configs,
      'implementation':'post-pose damped inertia; local presentation only; vertex mask pins torso harness; conservative rear support correction',
      'inputs':['movement acceleration','evaluated torso angular velocity','native gait anchor acceleration','vertical acceleration at landing'],
      'reset_on':['equipment rebuild','teleport','frame gap over 350ms','hidden mesh','ragdoll'],
      'replication':'uses each pawn movement already replicated; no extra RPC or authority gameplay state',
      'runtime_tested':False,'new_pack_user_accepted_before_motion':True}
apply_response_refit(plan)
(R/'manifest.json').write_text(json.dumps(plan,indent=2))
print('BACKPACK_MOTION_SOURCES_READY',len(rows),flush=True)
