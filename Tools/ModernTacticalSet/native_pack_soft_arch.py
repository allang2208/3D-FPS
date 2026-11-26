"""Sample the outside of the equipped garment around the shoulder arch."""
import json
from pathlib import Path
import sys
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import torso
from nape_backpack_author import tree
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118/Contact"
R.mkdir(exist_ok=True)
for rig,cy,cz in (("Jason",0.,115.),("Kaitlin",6.,109.)):
    garment=torso(rig)
    points=np.asarray(garment["positions"]);faces=np.asarray(garment["triangles"])
    surface=tree(points,faces)
    xs=np.arange(-23.,23.01,.25);n=720;a=np.arange(n)*2*np.pi/n
    dr=np.column_stack((np.zeros(n),np.cos(a),np.sin(a)))
    field=np.zeros((len(xs),n))
    for i,x in enumerate(xs):
        origin=np.array([x,cy,cz])
        for j,delta in enumerate(dr):
            hit=surface.ray_cast(Vector(origin+100*delta),Vector(-delta),105.)[0]
            if hit:field[i,j]=np.dot(np.array(hit)-origin,delta)
    np.savez(R/(rig+".npz"),xs=xs,radius=field,origin=np.array([0.,cy,cz]))

    zs=np.arange(cz-23.,cz+26.01,.25)
    dr=np.column_stack((np.cos(a),np.sin(a),np.zeros(n)))
    field=np.zeros((len(zs),n))
    # At the sides, cast only against the torso and carrier surfaces. Keep
    # outstretched arms from becoming the contact surface for the lower straps.
    center=points[faces].mean(1)
    arm={b["index"] for b in garment["bones"] if any(name in b["name"] for name in ("upperarm","lowerarm","hand","finger"))}
    arm_weight=np.array([sum(weight for bone,weight in group if bone in arm) for group in garment["weights"]])
    torso_faces=faces[(np.abs(center[:,0])<24)&(center[:,2]<cz+26)&(arm_weight[faces].mean(1)<.38)]
    body=tree(points,torso_faces)
    for i,z in enumerate(zs):
        origin=np.array([0.,cy,z])
        for j,delta in enumerate(dr):
            hit=body.ray_cast(Vector(origin+70*delta),Vector(-delta),75.)[0]
            if hit:field[i,j]=np.dot(np.array(hit)-origin,delta)
    np.savez(R/(rig+"-chest.npz"),xs=zs,radius=field,origin=np.array([0.,0.,cy]))
