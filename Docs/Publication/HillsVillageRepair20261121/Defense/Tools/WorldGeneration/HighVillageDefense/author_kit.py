"""Fit the three Meshy originals; build a through-arch, hoist pocket and two real openings."""
import math
from pathlib import Path
import sys

import cv2
import numpy as np

from source_mesh import OUT, read_source, save_role, silhouette
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"VillagePerimeter"))
from wall_geometry import Mesh


def new_mesh(seed):
    shell=Mesh(seed)
    shell.groups["Iron"]={key:[] for key in next(iter(shell.groups.values()))}
    return shell


def box(m,x0,x1,y0,y1,z0,z1,slot="Mortar",solid=False):
    m.solid([[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)] for z in (z0,z1)],slot)
    if solid:m.collision(x0,x1,y0,y1,z0,z1)


def runs(values):
    padded=np.r_[False,values,False].astype(np.int8)
    change=np.diff(padded)
    return list(zip(np.flatnonzero(change==1),np.flatnonzero(change==-1)))


def bond_joints(rng, start, end, count):
    pitch=(end-start)/count
    return [start]+[start+pitch*i+rng.uniform(-.15,.15)*pitch for i in range(1,count)]+[end]


def wall_masonry(shell):
    # A solid backing behind both skins. A narrow tongue behind the stones closes
    # the joint between modules; the rest of each end is recessed for its returns.
    shell.block(-144,144,-73,83,-28,353)
    shell.block(-150,150,69,74,-28,353)
    beds=(-28,10,37,65,90,119,145,171,193,220,246,275,299,327,352)
    for row,(bottom,top) in enumerate(zip(beds,beds[1:])):
        for side in (-1,1):
            if side<0 and bottom>=193:
                continue   # The dressed Meshy facade rises from the old wall's shoulder.
            joints=bond_joints(shell.rng,-150,150,6+(row+(side==1))%2)
            for a,b in zip(joints,joints[1:]):
                shoulder=side<0 and top==193
                depth=shell.rng.uniform(98,100) if shoulder else shell.rng.uniform(95,100)
                embed=67 if row%3==0 else 73
                y0,y1=sorted((side*embed,side*depth))
                slot="YardSlate" if shell.rng.random()<.19 else "YardField"
                shell.stone(a-.3,b+.3,y0,y1,bottom-.6,top+.9,slot)
        for side in (-1,1):
            # The return faces are exposed when the adjacent 3 m bay is destroyed.
            joints=bond_joints(shell.rng,-79,85,3+row%2)
            for a,b in zip(joints,joints[1:]):
                x0,x1=sorted((side*133,side*150))
                slot="YardSlate" if shell.rng.random()<.16 else "YardField"
                shell.stone(x0,x1,a-.4,b+.4,bottom-.6,top+.9,slot)
    # A keyed capping course at the height of the former wall ties the two builds together.
    joints=bond_joints(shell.rng,-150,150,6)
    for a,b in zip(joints,joints[1:]):
        shell.stone(a-.3,b+.3,-101,-70,189,202,"YardCap")
    # Full-depth bedding supports the paving between joints; wearing faces meet the stair landing.
    box(shell,-150,150,-54,98,351,356,"Mortar")
    for j in range(2):
        joints=bond_joints(shell.rng,-150,150,5+j)
        for a,b in zip(joints,joints[1:]):
            y=-54+j*77
            shell.stone(a-.4,b+.4,y-.4,y+77.4,353,360,"YardCap")


def wall():
    from battlement_profile import fit_crest_x, MERLONS

    parts=read_source("A_HighWall","HighWallStone")
    shell=new_mesh(2717)
    groups={}
    for slot,part in parts:
        u,v,h=part.pos.T
        # This master carries its split-faced ashlars and projecting cornice on
        # the +v side. Turn that face outward (-Y), rotating X as well to preserve winding.
        x=np.interp(u,[0,.012,.988,1],[150,150,-150,-150])
        y=np.interp(v,[0,.16,.39,.46,.53,.65,1],[-46,-53,-75,-86,-95,-98,-100])
        # The full-width sill ends at 80.5% of the source height. The remainder
        # is the three real merlons. Preserve both faces, copings and original UVs.
        z=np.interp(h,[0,.73,.805,1],[0,360,393,480])
        x=fit_crest_x(x,z)
        fitted=part.moved(np.stack((x,y,z),axis=1))
        upper=fitted.clipped(lambda p:p[:,2]-193)
        if upper:
            groups.setdefault(slot,[]).append(upper)
    wall_masonry(shell)
    shell.collision(-150,150,-100,100,-28,360)
    shell.collision(-150,150,-98,-52,351,393)
    for x0,x1 in MERLONS:
        shell.collision(x0,x1,-96,-53,392,479)
    save_role("SM_HighWall",groups,shell)


def arch_curve(x,half,peak):
    rise=peak-340.
    radius=(half*half+rise*rise)/(2*rise)
    return peak-radius+np.sqrt(np.maximum(0.,radius*radius-np.minimum(np.abs(x),half)**2))


def field_courses(m,x0,x1,y0,y1,base,top,outer_only=False):
    d=22;row=0;z=base
    while z<top-1:
        h=min(30.,top-z)
        x=x0
        while x<x1-1:
            span=(27 if row%2 else 43) if x==x0 else m.rng.uniform(38,60)
            end=min(x+span,x1)
            if x1-end<10:end=x1
            mat="YardSlate" if m.rng.random()<.15 else "YardField"
            m.stone(x,end,y0-d*.5,y1+d*.5,z,z+h,mat)
            x=end
        z+=h;row+=1


def crown(m,outer,top):
    base=top-73
    for y in (-131,131):
        box(m,-outer,outer,y-18,y+18,base-14,base+9,"YardCap")
        count=max(4,round(outer*2/136));pitch=outer*2/count
        for i in range(count):
            mid=-outer+(i+.5)*pitch;w=pitch*.58
            box(m,mid-w/2,mid+w/2,y-19,y+19,base,top-12,"YardField")
            m.stone(mid-w/2-4,mid+w/2+4,y-24,y+24,top-15,top,"YardCap")
    for x in (-outer+18,outer-18):
        for y in (-63,63):
            box(m,x-18,x+18,y-27,y+27,base,top-9,"YardField")
            m.stone(x-23,x+23,y-32,y+32,top-14,top,"YardCap")


def hoist(m,half,top):
    # Pair of fixed, recessed guide rails. Their channels stay clear of the 18cm gate.
    for s in (-1,1):
        c=s*(half+9)
        for y in (-13,13):
            box(m,c-5,c+5,y-2,y+2,0,top-42,"Iron")
        box(m,c-4,c+4,-12,12,top-51,top-45,"Iron")
    for x in (-half*.56,half*.56):
        # The horizontal axle stays above the moving grille's top eye in its open pose.
        box(m,x-15,x+15,-30,30,top-36,top-27,"Iron")


def grille(parts,mask,west):
    from grille_repair import fill_missing_links, joined_east_grid

    width,height=(875.,495.) if west else (675.,475.)
    groups={};shell=new_mesh(3814)
    count,labels,stats,_=cv2.connectedComponentsWithStats((mask==0).astype(np.uint8),8)
    holes=[r for r in stats[1:] if r[0]>0 and r[1]>0 and r[0]+r[2]<len(mask) and r[1]+r[3]<len(mask)
           and r[4]>25 and r[3]>3 and r[2]>3]
    physical_lattice=len(holes)>=16
    for slot,part in parts:
        u,v,h=part.pos.T
        if physical_lattice:
            master=part.moved(np.stack(((u-.5)*875,(v-.5)*18,h*495.),axis=1))
            links=list(fill_missing_links(master))
            if west:
                fitted=[master,*links]
            else:
                # Only the rightmost repair survives removal of four middle bays.
                outer=links[-1]
                fitted=[*joined_east_grid(master),outer.moved(outer.pos-[100.,0.,0.])]
            groups.setdefault(slot,[]).extend(piece.moved(piece.pos*[1.,1.,height/495.]) for piece in fitted)
            continue
        p=part.moved(np.stack(((u-.5)*875,(v-.5)*18,h*height),axis=1))
        # A filled-in generated lattice must never put an opaque sheet across
        # the road. Preserve its actual lift lugs and decorated top rail.
        p=p.clipped(lambda xyz:xyz[:,2]-height*.86)
        if not p:continue
        entries=groups.setdefault(slot,[])
        if west:entries.append(p)
        else:
            # The two jambs, lifting eyes and bar thickness are saved at native
            # scale. Remove complete middle bays instead of squeezing the mesh.
            for side in (-1,1):
                half=p.clipped(lambda xyz:side*xyz[:,0]-100.)
                if half:entries.append(half.moved(half.pos+[-side*100.,0.,0.]))
    if not physical_lattice:
        cols=19 if west else 15
        for x in np.linspace(-width/2+4,width/2-4,cols):
            box(shell,x-4,x+4,-3.8,3.8,0,height*.90,"Iron")
        for z in np.linspace(22,height*.86,10):
            box(shell,-width/2,width/2,2.5,8.5,z-4,z+4,"Iron")
    shell.collision(-width/2,width/2,-9,9,0,height)
    save_role("SM_IronGrille"+("West" if west else "East"),groups,shell)


if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    names=set(sys.argv[1:]) or {"wall","portal","grille"}
    if "wall" in names:wall()
    if "portal" in names:
        from gate_gallery import make_gallery_portal

        for west in (True,False):make_gallery_portal(west)
    if "grille" in names:
        parts=read_source("C_WestGrille","GrilleIron")
        mask=silhouette(parts)
        for west in (True,False):grille(parts,mask,west)
