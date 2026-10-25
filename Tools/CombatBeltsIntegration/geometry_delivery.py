"""Repair collapsed bevel UVs and duplicate faces in the native delivery mesh."""
from collections import defaultdict
from math import sqrt
from statistics import median


def prepare_geometry(data):
    # Preserve authored positions, normals, weights and all valid UV islands.
    # Only zero-area/identical faces are removed; there is no LOD0 decimation.
    positions=data['positions'];scales=defaultdict(list);signs=defaultdict(int)
    areas=[];determinants=[]
    for face,uv,slot in zip(data['triangles'],data['uv'],data['triangle_materials']):
        a,b,c=(positions[v] for v in face)
        e=[b[j]-a[j] for j in range(3)];f=[c[j]-a[j] for j in range(3)]
        cross=[e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]]
        area=sqrt(sum(v*v for v in cross));areas.append(area)
        det=(uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0])
        determinants.append(det)
        if area>1.e-9 and abs(det)>1.e-12:
            scales[slot].append(sqrt(abs(det)/area));signs[slot]+=1 if det>0 else -1
    density={slot:median(values) for slot,values in scales.items()}
    seen={};keep=[];counts=dict(collapsed_uv_faces=0,zero_area_faces_removed=0,duplicate_faces_removed=0,overlapping_faces_split=0)
    for fi,face in enumerate(data['triangles']):
        if areas[fi]<=1.e-9:
            counts['zero_area_faces_removed']+=1;continue
        # Match the UE DynamicMesh corner identity before assigning face IDs.
        key=tuple(sorted(face));slot=data['triangle_materials'][fi]
        corners=tuple(sorted((vi,*[round(v,7) for v in data['normals'][fi][ci]+data['uv'][fi][ci]]) for ci,vi in enumerate(face)))
        if key in seen:
            old_slot,old_corners=seen[key]
            if slot==old_slot and corners==old_corners:
                counts['duplicate_faces_removed']+=1;continue
            # An intentional second surface with different attributes stays.
            new_face=[]
            for vi in face:
                new_face.append(len(positions));positions.append(list(positions[vi]))
                if data.get('weights'):data['weights'].append([list(v) for v in data['weights'][vi]])
            data['triangles'][fi]=face=new_face
            counts['overlapping_faces_split']+=1
        else:seen[key]=(slot,corners)
        if abs(determinants[fi])<=1.e-12:
            uv=data['uv'][fi];p=[positions[vi] for vi in face]
            edges=[]
            for i in range(3):
                j=(i+1)%3;k=(i+2)%3
                length=sqrt(sum((p[j][v]-p[i][v])**2 for v in range(3)))
                uv_length=sqrt(sum((uv[j][v]-uv[i][v])**2 for v in range(2)))
                if length>1.e-9:edges.append((uv_length,length,i,j,k))
            uv_length,length,i,j,k=max(edges)
            axis=[(p[j][v]-p[i][v])/length for v in range(3)]
            along=sum((p[k][v]-p[i][v])*axis[v] for v in range(3))
            height=areas[fi]/length
            if uv_length>1.e-7:
                scale=uv_length/length;direction=[(uv[j][v]-uv[i][v])/uv_length for v in range(2)]
            else:
                scale=density.get(slot,1.);direction=[1.,0.]
                uv[j]=[uv[i][0]+length*scale,uv[i][1]]
            side=1. if signs[slot]>=0 else -1.
            uv[k]=[uv[i][0]+scale*(along*direction[0]-side*height*direction[1]),
                   uv[i][1]+scale*(along*direction[1]+side*height*direction[0])]
            counts['collapsed_uv_faces']+=1
        keep.append(fi)
    for field in ('triangles','normals','uv','triangle_materials'):
        data[field]=[data[field][i] for i in keep]
    data['delivery_geometry_revision']='uv-and-topology-r2'
    data['delivery_repairs']=counts
    return data
