"""Author M24-only mounting and sight sockets from measured rail interfaces."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
root=O.parents[1]
sources=json.loads((O/'sources.json').read_text())
geo=json.loads((O/'interfaces.json').read_text())
rail=geo['rail']['crown_bounds_cm']; rear,front=rail[0][1],rail[1][1]; top=rail[1][2]
contact={'holographic':.1929415,'panoramic_red_dot':.25,'prism_scope_2x':.125,'lpvo_1_6x':.125,'eoth_holographic':.1374,'kv_scope_4x':.0065,'thermal_scope':0.}
aim={'holographic':[-.653782,0,5.175324],'panoramic_red_dot':[2.125,0,3.25],'prism_scope_2x':[-6.15,0,4.],'lpvo_1_6x':[-12.15,0,4.]}
recipe={'rail_source_cm':rail,'assets':{},'preserved':'Original shared geometry, UVs, optical materials; M24 arms, gun and action transforms unchanged.'}
for key,source in sources.items():
    row=dict(source);row['target']='/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_'+key
    sockets=row['sockets']
    if key in aim:
        r=aim[key];f=[r[0]+10,r[1],r[2]]
        if key=='prism_scope_2x':f=[6.10,0,4.]
        if key=='lpvo_1_6x':f=[12.10,0,4.]
        sockets.update({n:{'location':p,'rotation':[0,0,0]} for n,p in {'SightRear':r,'SightFront':f,'SightUp':[r[0],r[1],r[2]+1]}.items()})
    if key=='lpvo_1_6x':sockets['ZoomRing']={'location':[-7.1,0,4.],'rotation':[0,0,0]}
    if key in contact:
        feet=geo[key]['contact_bounds_cm']
        along=(rear+front-feet[0][0]-feet[1][0])*.5
        # Put the long oculars forward of the unchanged bolt-hand sweep, with
        # both original feet still on the actual crown and 5 mm edge support.
        if key in ('lpvo_1_6x','kv_scope_4x'):
            along=min(along+3.,front-feet[1][0]-.5)
        row['source_translation_cm']=[0,round(-along,7),round(top-contact[key],7)]
        row['yaw_degrees']=-90
        row['contact_plane_local_z_cm']=contact[key]
        row['contact_span_source_forward_cm']=[along+feet[0][0],along+feet[1][0]]
        row['ocular_forward_delta_cm']=along+sockets['SightRear']['location'][0]+.1819224795
    recipe['assets'][key]=row
(O/'fit_recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
lines=['#pragma once','#include "CoreMinimal.h"','','// SourceAssets/M24CommonOptics20261028/fit_recipe.json; centimetres, +X optic to -Y M24.', 'namespace M24OpticCoordinates','{','inline FTransform InSource(const FString& Key)','{','    FVector Position=FVector::ZeroVector;']
for key,row in recipe['assets'].items():
    if 'source_translation_cm' in row:
        p=row['source_translation_cm'];lines.append(f'    if(Key==TEXT("{key}"))Position=FVector({p[0]:.7f}f,{p[1]:.7f}f,{p[2]:.7f}f);')
lines+=['    return FTransform(FQuat(FVector::UpVector,-PI*.5f),Position);','}','inline float OcularForwardCM(const FString& Key)','{']
for key,row in recipe['assets'].items():
    if 'ocular_forward_delta_cm' in row:lines.append(f'    if(Key==TEXT("{key}"))return {row["ocular_forward_delta_cm"]:.7f}f;')
lines+=['    return 0.f;','}','}','']
(root/'Source/FPSGAME/Weapons/M24OpticCoordinates.h').write_text('\n'.join(lines),encoding='utf-8')
print('M24_OPTIC_FIT_AUTHORED',len(contact))
