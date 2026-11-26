"""Include the native cloth shoulder sections in empty-garment display sources."""
from shirt_geometry import *
for rig in ['Jason','Kaitlin']:
    body=read(R/'Inputs'/f'Body_{rig}.json');oldcount=sum(m in [3,8,9] for m in body['triangle_materials']);body=subset(body,[m in [0,1,3,8,9] for m in body['triangle_materials']]);body['materials']=[DEST+'/Materials/M_CombatFabric',DEST+'/Materials/MI_CombatTorso_'+rig];body['material_slots']=['CombatNativeShoulder','CombatKnitTorso'];body['triangle_materials']=[0 if m in [0,1] else 1 for m in body['triangle_materials']]
    for kind in ['shirt_standalone','outfit_display']:
        path=R/'Authored'/f'{kind}_{rig}.json'
        if not path.exists():continue
        d=read(path)
        if d.get('body_display_sections')==[0,1,3,8,9]:continue
        d=subset(d,[i<len(d['triangles'])-oldcount for i in range(len(d['triangles']))]);merge(d,body);d['body_display_sections']=[0,1,3,8,9];write(path,d);print('TS01_DISPLAY_SHOULDERS',rig,kind,flush=True)
