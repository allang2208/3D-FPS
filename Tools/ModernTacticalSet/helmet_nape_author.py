"""Extend the manufactured R2 helmet shell down the occiput on its native head."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).parent))
import helmet_contour_author as r2
from helmet_hair_mesh_clean import clean

detail=r2.detail
A=detail.A
SET=r2.ROOT
OUT=SET/"HelmetNapeR3"


class Nape:
    def __init__(self,rig):
        self.crown=r2.Crown(rig)
        self.p=np.load(OUT/"Authored"/f"nape-profile-{rig}.npz")
        self.origin=self.p["origin"]
        self.top=float(self.p["top"])
        self.angles=self.p["angles"]
        self.depths=self.p["depths"]
        self.adjustments=[self.p[key] for key in ("radial_delta","depth_delta")]

    def warp(self,points):
        points=np.asarray(points).reshape(-1,3)
        xy=points[:,:2]-self.origin[:2]
        radius=np.linalg.norm(xy,axis=1)
        angle=np.abs(np.arctan2(xy[:,0],xy[:,1]))/(self.angles[1]-self.angles[0])
        depth=(self.top-points[:,2]-self.depths[0])/(self.depths[1]-self.depths[0])
        angle=np.clip(angle,0,len(self.angles)-1.00001)
        depth=np.clip(depth,0,len(self.depths)-1.00001)
        i=depth.astype(int)
        j=angle.astype(int)
        v=depth-i
        u=angle-j
        dr,dz=[(1-v)*((1-u)*q[i,j]+u*q[i,j+1])+v*((1-u)*q[i+1,j]+u*q[i+1,j+1]) for q in self.adjustments]
        result=points.copy()
        result[:,:2]+=xy/np.maximum(radius[:,None],1e-8)*dr[:,None]
        result[:,2]-=dz
        return result

    def surface(self,a,t,offset=0.):
        return self.warp(self.crown.surface(a,t,offset))[0]

    def rail(self,points):
        # Keep the injection-moulded rail slim and above the extended skirt.
        # Recover the new shell's cross-section at the rail's own elevation.
        xyz=self.warp(points)
        target_z=points[:,2]+.27*(xyz[:,2]-points[:,2])
        direction=points[:,:2]-self.origin[:2]
        radius=np.linalg.norm(direction,axis=1)
        direction/=radius[:,None]
        a=abs(np.arctan2(direction[:,0],direction[:,1]))/(self.angles[1]-self.angles[0])
        a=np.clip(a,0,len(self.angles)-1.00001)
        j=a.astype(int)
        u=a-j
        orig=self.p["old_radius"]
        new=orig+self.adjustments[0]
        deformed_z=self.top-self.depths[:,None]-self.adjustments[1]
        for k in range(len(points)):
            src=orig[:,j[k]]*(1-u[k])+orig[:,j[k]+1]*u[k]
            dst=new[:,j[k]]*(1-u[k])+new[:,j[k]+1]*u[k]
            heights=deformed_z[:,j[k]]*(1-u[k])+deformed_z[:,j[k]+1]*u[k]
            off=radius[k]-np.interp(self.top-points[k,2],self.depths,src)
            r=np.interp(target_z[k],heights[::-1],dst[::-1])+off
            xyz[k,:2]=self.origin[:2]+direction[k]*r
        xyz[:,2]=target_z
        return xyz

    def ring(self,a):
        return self.surface(a,1.)


def mesh_strip(name,rows,mat,thickness):
    rows=np.asarray(rows)
    n,w=rows.shape[:2]
    faces=[[i*w+j,i*w+j+1,(i+1)*w+j+1,(i+1)*w+j] for i in range(n-1) for j in range(w-1)]
    ob=A.mesh(name,rows.reshape(-1,3).tolist(),faces,mat,thickness=thickness,do_bind=False)
    detail.project_uv(ob)
    detail.finish_normals(ob)
    return ob


def nape_pad(fit):
    # A broad continuous cradle sits partly under the shell binding. The lower
    # rolled edge follows the neck while the flanks turn back up behind the ears.
    rows=[]
    for a in np.linspace(2.19,2*np.pi-2.19,87):
        rim=fit.ring(a)
        direction=np.array([np.sin(a),np.cos(a),0])
        across=abs(a-np.pi)/(.952)
        half=1.15-.62*across**2
        center_z=rim[2]-.56+.44*across**2
        row=[]
        for h in np.linspace(-1,1,9):
            inset=.66+.16*(1-h)**2-.12*(1-h*h)
            pt=rim-direction*inset
            pt[2]=center_z+h*half
            row.append(pt)
        rows.append(row)
    rows=np.asarray(rows)
    mesh_strip("Occipital_Padded_Cradle",rows,"PadMesh",.27)
    for j in (0,-1):
        detail.tube(f"Occipital_Bound_Cradle_{j}",rows[:,j],.071,"Webbing",8)
    # Backward-facing dimpled dial and its spindle are reused as a rigid assembly.
    back=fit.ring(np.pi)
    return back+np.array([0,.52,-.55])


def rear_yoke(fit,head,side):
    anchor=fit.surface(2.34*side,.992,-.16)
    points=[]
    center=fit.crown.old["center"]
    # Start tangentially under the new shell; curve forward across the soft
    # tissue below the ear and meet the unchanged R2 chin-sling endpoint.
    stages=[0,.22,.55,.78,1.]
    yaw=np.asarray([2.34,2.12,1.78,1.35,.88])*side
    heights=[anchor[2],anchor[2]-.70,fit.top-17.95,fit.top-19.15,fit.top-20.5]
    for t in np.linspace(0,1,49):
        theta=np.interp(t,stages,yaw)
        z=np.interp(t,stages,heights)
        skin,axis=r2.radial_hit(head,center,theta,z)
        start=anchor.copy()
        start[2]=z
        w=np.clip(t/.28,0,1)
        w=w*w*(3-2*w)
        points.append((1-w)*start+w*(skin+axis*.54))
    points=np.asarray(points)
    rows=[]
    for k,v in enumerate(points):
        theta=math.atan2(v[0]-center[0],v[1]-center[1])
        axis=np.array([np.sin(theta),np.cos(theta),0.])
        tangent=detail.unit(points[min(k+1,len(points)-1)]-points[max(k-1,0)])
        cross=detail.unit(np.cross(tangent,axis))
        row=[]
        for width in np.linspace(-.63,.63,5):
            pt=v+cross*width
            angle=math.atan2(pt[0]-center[0],pt[1]-center[1])
            skin,out=r2.radial_hit(head,center,angle,pt[2])
            pt+=out*max(0,.33-np.dot(pt-skin,out))
            row.append(pt)
        rows.append(row)
    rows=np.asarray(rows)
    mesh_strip("Posterior_Retention_Yoke_"+str(side),rows,"Webbing",.14)
    for j in (0,-1):
        detail.tube(f"Posterior_Yoke_Selvedge_{side}_{j}",rows[:,j],.04,"Webbing",6)


def native_points(ob):
    return np.array([A.nativept(ob.matrix_world@v.co) for v in ob.data.vertices])


def radial_audit(rig,fit,old_rim,new_rim,shell):
    def ring_samples(points,deg):
        xy=points[:,:2]-fit.origin[:2]
        a=np.degrees(np.arctan2(xy[:,0],xy[:,1]))
        diff=abs((a-deg+180)%360-180)
        band=points[diff<2.1]
        lowest=band[np.argmin(band[:,2])]
        return [float(lowest[2]),float(np.linalg.norm(lowest[:2]-fit.origin[:2]))]
    sections={}
    for deg in (-150,-135,-90,0,90,135,150,180):
        before=ring_samples(old_rim,deg)
        after=ring_samples(new_rim,deg)
        sections[str(deg)]=dict(before_z_cm=before[0],after_z_cm=after[0],drop_cm=round(before[0]-after[0],3),radial_inset_cm=round(before[1]-after[1],3))
    q=np.load(SET/"HelmetHairFitR1"/f"{rig}-hair-envelope.npz")["positions"]
    xy=q[:,:2]-fit.origin[:2]
    a=abs(np.arctan2(xy[:,0],xy[:,1]))
    depth=fit.top-q[:,2]
    edge_old=np.interp(a,fit.angles,fit.p["edge"])
    edge_new=edge_old+np.interp(a,fit.angles,fit.p["drop"])
    keep=(a>np.radians(105))&(depth>edge_old-2.0)&(depth<edge_new-.30)
    cloud=np.unique(np.round(q[keep]/.1).astype(np.int32),axis=0)*.1
    vertices=native_points(shell)
    triangles=[tuple(p.vertices) for p in shell.data.polygons]
    tree=BVHTree.FromPolygons(vertices.tolist(),triangles)
    outside=missing=0
    minimum=100.
    for v in cloud:
        axis=Vector((v[0]-fit.origin[0],v[1]-fit.origin[1],0)).normalized()
        center=Vector((fit.origin[0],fit.origin[1],v[2]))
        hit=tree.ray_cast(center+axis*35.,-axis,35.)[0]
        if hit is None:
            missing+=1
            continue
        dist=(hit-Vector(v)).dot(axis)
        minimum=min(dist,minimum)
        outside+=int(dist<0)
    return dict(rim_sections=sections,protected_native_head_and_groom_points=int(keep.sum()),voxel_cm=.1,
                posterior_voxels=len(cloud),uncovered=missing,outside_shell=outside,min_outer_radial_margin_cm=minimum)


def build(rig):
    fit=Nape(rig)
    (OUT/"Models").mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SET/"HelmetContourR2/Models"/f"TS01_Helmet_{rig}_GAME.blend"))
    bpy.context.preferences.filepaths.save_version=0
    detail.HIGH=False
    A.MATS={k:bpy.data.materials["H1_"+k] for k in detail.FAMILIES}
    A.OBJECTS=[]
    h=json.loads((SET/"HelmetHairFitR1/Inputs"/f"{rig}_Head.json").read_bytes())
    body=json.loads((SET/"HelmetHairFitR1/Inputs"/f"{rig}_Body.json").read_bytes())
    frame=body["bones"]["head"]
    hf=h["bones"]["head"]
    hp=(np.asarray(h["positions"])-hf["position"])@np.linalg.inv(hf["axes"])@frame["axes"]+frame["position"]
    heads=BVHTree.FromPolygons(hp.tolist(),h["triangles"],all_triangles=True)
    rim=bpy.data.objects["Continuous_Rubber_Edge_Binding"]
    before=native_points(rim)
    hardware=native_points(bpy.data.objects["Knurled_Rear_Fit_Dial"])
    dial_center=(hardware.min(0)+hardware.max(0))*.5
    dial_target=nape_pad(fit)
    new_parts=set(A.OBJECTS)
    for ob in list(bpy.context.scene.objects):
        if ob.type!="MESH" or ob.name.startswith("REFERENCE_ONLY_") or ob in new_parts:
            continue
        if ob.name.startswith(("Occipital_Cradle","Rear_Nape_Yoke")):
            bpy.data.objects.remove(ob,do_unlink=True)
            continue
        points=native_points(ob)
        if ob.name.startswith(("Knurled_","Dial_")):
            revised=(points-dial_center)*.87+dial_target
        elif ob.name.startswith(("ARC_Rail","Rail_")):
            revised=fit.rail(points)
        elif ob.name.startswith(("Continuous_","Crown_Fabric","Crown_Attachment","Rear_Identification","Removable_Comfort","Yoke_Attachment_")):
            revised=fit.warp(points)
        else:
            revised=points
        if np.max(abs(points-revised))>.00001:
            inv=ob.matrix_world.inverted()
            for v,pt in zip(ob.data.vertices,revised):
                v.co=inv@Vector(detail.xyz(pt))
            detail.finish_normals(ob)
        A.OBJECTS.append(ob)
    for side in (-1,1):
        rear_yoke(fit,heads,side)
    for ob in A.OBJECTS:
        clean(ob)
    bpy.context.scene["Revision"]="HelmetNapeR3"
    bpy.ops.object.select_all(action="DESELECT")
    for ob in A.OBJECTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active=bpy.data.objects["Continuous_Composite_Shell"]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Models"/f"TS01_Helmet_{rig}_GAME.blend"))
    src=OUT/"Authored"
    d=detail.payload(A.OBJECTS)
    detail.write(src/f"helmet_{rig}_world.json",d)
    axes=np.asarray(frame["axes"])
    d["positions"]=((np.asarray(d["positions"])-frame["position"])@np.linalg.inv(axes)).tolist()
    normals=np.asarray(d["normals"])@axes.T
    d["normals"]=(normals/np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-8)).tolist()
    d["attachment_frame"]=frame
    detail.write(src/f"helmet_{rig}_wear.json",d)
    report=radial_audit(rig,fit,before,native_points(rim),bpy.data.objects["Continuous_Composite_Shell"])
    (src/f"{rig}-nape-fit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("NAPE_AUTHORED",rig,len(d["triangles"]),report,flush=True)


if __name__=="__main__":
    build(sys.argv[-1])
