"""Fit shared centimetre optics to the measured native cover rail."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;p=r.parents[2]
d=json.loads((r/'current_assets.json').read_text());interfaces=json.loads((p/'SourceAssets/M24CommonOptics20261028/interfaces.json').read_text())
def unit(v):return np.asarray(v)/np.linalg.norm(v)
def matrix(v):
    a=np.eye(4);a[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.array(v[7:]);a[:3,3]=v[:3];return a
cover=matrix(d['frames']['PKM_Cover'])
# Rail crown in original art centimetres. Native UE component = (Y,X,Z)+offset.
slope=-.0141819599;side_slope=.0000374318241
forward=unit([0.,-1.,-slope]);up=unit([-side_slope,-slope,1.]);right=unit(np.cross(up,forward));up=np.cross(forward,right)
frame=np.column_stack((forward,right,up));center_y=.18857792
def mounted(rawx,footz,raise_cm=0.):
    center=np.array([5.45+center_y,rawx-28.6,slope*rawx+side_slope*center_y+9.82525690-5.3])
    a=np.eye(4);a[:3,:3]=frame;a[:3,3]=center+up*(raise_cm+.01-footz)
    b=np.linalg.inv(cover)@a;scale=np.linalg.norm(b[:3,:3],axis=0);rotation=b[:3,:3]/scale
    return {'position':b[:3,3].tolist(),'rotation_xyzw':R.from_matrix(rotation).as_quat().tolist(),'scale':scale.tolist()}
assets={};rail={'length_cm':15.,'width_cm':2.12,'height_cm':.65,'source_center_x_cm':1.6,'source_forward_bounds_cm':[-5.9,9.1], 'mount':mounted(1.6,0.),'target':'/Game/Weapons/M249/CommonOptics20261108/SM_M249_CommonRail'}
for key,src in d['optics'].items():
    row=dict(src);row['target']='/Game/Weapons/M249/CommonOptics20261108/SM_M249_'+key
    if key in interfaces and 'contact_bounds_cm' in interfaces[key]:
        lo,hi=interfaces[key]['contact_bounds_cm'];footz=(lo[2]+hi[2])*.5
        seat=key in ('eoth_holographic','kv_scope_4x')
        # Front-seat long oculars; retain original physical scale and foot span.
        rawx=2.8 if key in ('lpvo_1_6x','kv_scope_4x') else 5.+(lo[0]+hi[0])*.5
        if seat:rawx=min(rawx,9.1+lo[0]-.35)
        row.update(mount=mounted(rawx,footz,.65 if seat else 0.),seat=seat,foot_plane_cm=footz,
            source_foot_span_cm=[rawx-hi[0],rawx-lo[0]],source_anchor_x_cm=rawx)
    assets[key]=row
out={'assets':assets,'rail':rail,'attachment_bone':'PKM_Cover','factory_slots':['M249_OpticalHousing','M249_MagnifierGlass','M249_MagnifierReticle'],'runtime_tested':False}
(r/'optic_recipe.json').write_text(json.dumps(out,indent=2))
def cpp(a):
    q=a['rotation_xyzw'];v=a['position'];s=a['scale']
    return 'FTransform(FQuat('+','.join(f'{x:.10f}' for x in q)+'),FVector('+','.join(f'{x:.10f}' for x in v)+'),FVector('+','.join(f'{x:.10f}' for x in s)+'))'
lines=['#pragma once','#include "CoreMinimal.h"','// Authored from Repair12/optic_recipe.json; native cover-local units.','namespace M249OpticCoordinates','{','inline FTransform Mount(const FString& Key)','{']
for k,v in assets.items():
    if 'mount' in v:lines.append(f'    if(Key==TEXT("{k}"))return {cpp(v["mount"])};')
lines+=['    return FTransform::Identity;','}',f'inline FTransform RailMount(){{return {cpp(rail["mount"])};}}','}','']
(p/'Source/FPSGAME/Weapons/M249OpticCoordinates.h').write_text('\n'.join(lines))
print('M249 common optics fitted',sum('mount' in x for x in assets.values()))
