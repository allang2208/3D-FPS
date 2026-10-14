"""Author world-body buttpad contacts from saved rifle surfaces. No asset writes."""
import json, re
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); R=Path(__file__).parent
sources={
 'ue_akm':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'ue_m4a1':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 'ue_qbz191':'/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny'}
for key,header in [('ue_hk416','HK416'),('ue_ash12','ASH12'),('ue_m16a2','M16'),('ue_a762','A762'),
                   ('ue_svd','SVD'),('ue_lmg201','LMG201'),('ue_pkm_lowpoly','PKMLowpoly')]:
    s=(P/f'Source/FPSGAME/Weapons/{header}WeaponAssets.h').read_text(encoding='utf-8-sig')
    sources[key]=re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)',s)[1]

G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
out={}
for key,path in sources.items():
    a=u.load_asset(path)
    if not a:raise RuntimeError(path)
    mod=u.SkeletonModifier();mod.set_skeletal_mesh(a)
    root=mod.get_bone_transform('WPN_root',True)
    rear=mod.get_bone_transform('WPN_RearSight',True).translation
    front=mod.get_bone_transform('WPN_FrontSight',True).translation
    up=root.rotation.rotate_vector(u.Vector(0,0,1))
    axis=front-rear;axis=(axis-up*axis.dot(up)).normal()
    side=up.cross(axis).normal()
    dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(str(status))
    _,vectors,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(vectors)
    _,indices,_=Q.get_all_triangle_indices(dm,False);tris=L.convert_triangle_list_to_array(indices)
    slots=[str(m.material_slot_name) for m in a.materials]
    stock={i for i,n in enumerate(slots) if 'stock' in n.lower()}
    # Bullpup stocks may share the receiver material. Exclude all arm sections.
    keep=stock or {i for i,n in enumerate(slots) if not any(s in n.lower() for s in ['skin','glove','sleeve','manny','hands']) and n.lower()!='hand'}
    ids=set()
    for ti,t in enumerate(tris):
        if u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0] in keep:ids.update([t.x,t.y,t.z])
    coords=[(points[i].dot(axis),points[i].dot(side),points[i].dot(up)) for i in ids]
    back=min(v[0] for v in coords)
    # Slanted/curved buttplates can span several cm along the barrel axis.
    # Retain their rear envelope but center the complete contact patch vertically.
    pad=[v for v in coords if v[0]<back+4.0]
    lateral=(min(v[1] for v in pad)+max(v[1] for v in pad))*.5
    vertical=(min(v[2] for v in pad)+max(v[2] for v in pad))*.5
    contact=axis*back+side*lateral+up*vertical
    local=root.inverse_transform_location(contact)
    out[key]={'mesh':a.get_path_name(),'stock_root':xyz(local),'stock_cs':xyz(contact),
              'source_slots':[slots[i] for i in sorted(keep)],'rear_surface_width_cm':max(v[1] for v in pad)-min(v[1] for v in pad),
              'rear_surface_height_cm':max(v[2] for v in pad)-min(v[2] for v in pad)}
    print('RIFLE_STOCK_CONTACT',key,xyz(local),out[key]['source_slots'],flush=True)
(R/'stock-contacts.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
lines=['#pragma once','#include "CoreMinimal.h"','',
       '// Generated from saved stock surfaces by read_stock_contacts.py.',
       '// WPN_root units (including the native FBX 100x scale), not wrist centimetres.',
       'namespace FPSBodyRifleStock','{','inline const FVector* Find(const FString& Mesh)','{']
for i,row in enumerate(out.values()):
    v=','.join(f'{n:.10f}' for n in row['stock_root'])
    lines.extend([f'    static const FVector Stock{i}({v});',
                  f'    if(Mesh==TEXT("{row["mesh"]}"))return &Stock{i};'])
lines.extend(['    return nullptr;','}','}',''])
(P/'Source/FPSGAME/Characters/FPSBodyRifleStockContacts.h').write_text('\n'.join(lines),encoding='utf-8')
print('RIFLE_STOCK_CONTACTS_SAVED',len(out),flush=True)
