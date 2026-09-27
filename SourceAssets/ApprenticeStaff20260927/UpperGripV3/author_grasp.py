"""Transfer the accepted VRE 80% fist into UE anatomical right-hand coordinates.
Authors runtime pose data; does not render, launch UE or run acceptance checks.
"""
import json
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
SOURCE=PROJECT/'SourceAssets/MannyGraspDonor20260912'
ref=json.loads((SOURCE/'target_reference.json').read_text())['bones']
fit=json.loads((SOURCE/'Opening/0.8/aligned_fit.json').read_text())
rest={n:Matrix(v['rest']) for n,v in ref.items()}
posed={'hand_l':rest['hand_l'].copy()}
# The donor matrices are Blender space. Native V7 component-space positions
# are in UE space: centimetres, with Y reflected. This coordinate conversion
# is separate from changing the anatomical left hand into the right hand.
blender_to_ue=Matrix.Diagonal((1,-1,1))
forward=(blender_to_ue@(rest['middle_01_l'].translation-rest['hand_l'].translation)).normalized()
across=blender_to_ue@(rest['index_01_l'].translation-rest['pinky_01_l'].translation)
across=(across-forward*across.dot(forward)).normalized()
frame=Matrix((across,forward,across.cross(forward))).transposed()
mirror=Matrix.Diagonal((1,1,-1))
rows=[]
for name,basis in fit['basis'].items():
    parent=ref[name]['parent']
    posed[name]=posed[parent]@rest[parent].inverted()@rest[name]@Matrix(basis)
    deformation=posed[name].to_quaternion().to_matrix()@rest[name].to_quaternion().to_matrix().transposed()
    ue_deformation=blender_to_ue@deformation@blender_to_ue
    canonical=mirror@frame.transposed()@ue_deformation@frame@mirror
    q=canonical.to_quaternion().normalized()
    rows.append((name[:-1]+'r',[q.x,q.y,q.z,q.w]))
lines=['// V4: Blender-to-UE coordinate conversion, then anatomical left-to-right transfer.',
       '// Source: SourceAssets/ApprenticeStaff20260927/UpperGripV3/author_grasp.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffGripDonor {',
       'struct FEntry { const TCHAR* Bone; FQuat Deformation; };','inline const FEntry Fingers[]={']
lines += ['    {TEXT("'+name+'"),FQuat('+','.join(f'{v:.10f}' for v in q)+')},' for name,q in rows]
lines += ['};','}']
dest=PROJECT/'Source/FPSGAME/Weapons/Staff/StaffGripDonor.h'
dest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'ClosedGripV4/grasp-source.json').write_text(json.dumps({'revision':4,'source':str(SOURCE/'Opening/0.8/aligned_fit.json'),
    'native_rig':'V7 M4 rest frames resolved at mesh load','method':'Blender Y reflection before anatomical mirror; preserve accepted group grasp; no finger translations/scales',
    'fingers':dict(rows)},indent=2),encoding='utf-8')
print('STAFF_V4_GRASP_AUTHORED',len(rows))
