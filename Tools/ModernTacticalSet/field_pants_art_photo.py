"""Photograph the trousers and derive the upright display and folded floor pickup."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix,Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from field_pants_art import MODELS,NAME,ROOT,unit

REVIEW=ROOT/"Review"
ICON=ROOT/"Icons"
KEY="ue_modern_tactical_pants"


def setup():
    bpy.ops.wm.open_mainfile(filepath=str(MODELS/(NAME+"_GAME.blend")))
    ob=bpy.data.objects[NAME]
    scene=bpy.context.scene
    scene.render.engine="CYCLES";scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.film_transparent=True
    scene.view_settings.view_transform="AgX";scene.view_settings.look="AgX - Medium High Contrast"
    scene.view_settings.exposure=-1.90
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
    cam=bpy.data.cameras.new("Garment portrait");cam.type="ORTHO";cam.clip_start=.001
    view=bpy.data.objects.new(cam.name,cam);scene.collection.objects.link(view);scene.camera=view
    world=bpy.data.worlds.new("Neutral studio bounce");world.use_nodes=True;scene.world=world
    node=next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    node.inputs[0].default_value=(.62,.66,.69,1);node.inputs[1].default_value=.36
    return ob,scene,view


def area(scene,name,location,center,power,size,tint):
    lamp=bpy.data.lights.new(name,"AREA");lamp.energy=power;lamp.size=size;lamp.color=tint
    ob=bpy.data.objects.new(name,lamp);scene.collection.objects.link(ob)
    ob.location=Vector(location)
    ob.rotation_euler=(Vector(center)-ob.location).to_track_quat("-Z","Y").to_euler()


def shoot(scene,view,p,angle,tilt,path,width,height,pad):
    theta=np.radians(angle)
    towards=unit(np.array([np.sin(theta),-np.cos(theta),tilt]))
    right=unit(np.cross([0,0,1],towards));up=np.cross(towards,right)
    axes=np.stack([right,up,towards])
    proj=p@axes.T
    center=(proj.min(0)+proj.max(0))*.5@axes
    view.matrix_world=Matrix.Translation(Vector(center+towards*2))@Matrix(axes.T.tolist()).to_4x4()
    size=np.ptp(proj,axis=0);aspect=width/height
    view.data.ortho_scale=float(max(size[0]/min(aspect,1.),size[1]/min(1/aspect,1.))*pad)
    for ob in list(scene.objects):
        if ob.type=="LIGHT":bpy.data.objects.remove(ob,do_unlink=True)
    for name,offset,power,diameter,color in (
        ("Broad softbox",[-.79,.72,1.0],64,.85,(1.,.97,.92)),
        ("Bounced fill",[.76,-.18,.76],25,.88,(.92,.96,1.)),
        ("Fabric edge",[.66,.59,-.43],65,.67,(1.,.96,.89))):
        area(scene,name,center+np.array(offset)@axes,center,power,diameter,color)
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return axes


def fold(p,waist):
    # Ease the lower legs beneath the thighs. The upper fabric is flattened
    # in depth as it settles and the knee rounds a finite-radius bend.
    x,y,z=p.T
    start=.405+.012*np.sin(x*8.7)
    radius=.046
    phi=np.radians(166.)
    station=waist-z-start
    angle=np.clip(station/radius,0.,phi)
    beyond=np.maximum(station-radius*phi,0.)
    track=start+np.minimum(station,0)+radius*np.sin(angle)+beyond*np.cos(angle)
    elevation=radius*(np.cos(angle)-1.)-beyond*np.sin(angle)
    depth=-y*.29+.0024*np.sin(27*x+5*track)
    return np.column_stack((x,track+depth*np.sin(angle),elevation+depth*np.cos(angle)))


def write_static(file,p,tri,n,uv,mat,slots):
    p=p-(p.min(0)+p.max(0))*.5
    data=dict(positions=np.round(p*100,6).tolist(),triangles=tri.tolist(),normals=np.round(n,6).tolist(),
        uv=np.round(uv,7).tolist(),triangle_materials=mat.tolist(),material_slots=slots)
    file.write_text(json.dumps(data,separators=(",",":")))


def item_art(ob,p,axes):
    m=ob.data
    corners=np.array([p.vertices[:] for p in m.polygons])
    ids=np.array([p.material_index for p in m.polygons])
    normal=np.empty(len(m.loops)*3,np.float32);m.corner_normals.foreach_get("vector",normal)
    normal=normal.reshape(-1,3,3)
    uv=np.empty(len(m.loops)*2,np.float32);m.uv_layers.active.data.foreach_get("uv",uv)
    uv=uv.reshape(-1,3,2);uv[:,:,1]=1.-uv[:,:,1]
    render_basis=np.stack((-axes[2],axes[0],axes[1]))
    slots=[m.name for m in ob.data.materials]
    write_static(ICON/"display.json",p@render_basis.T,corners,normal@render_basis.T,uv,ids,slots)
    waist=p[:,2].max()
    folded=fold(p,waist)
    delta=.00004*np.eye(3)
    jac=np.stack([(fold(p+axis,waist)-fold(p-axis,waist))/.00008 for axis in delta],axis=2)
    folded_normals=unit(np.einsum("fcij,fcj->fci",np.linalg.inv(jac).transpose(0,2,1)[corners],normal))
    write_static(ICON/"pickup.json",folded,corners,folded_normals,uv,ids,slots)


def main():
    for path in (REVIEW,ICON):path.mkdir(parents=True,exist_ok=True)
    ob,scene,view=setup()
    p=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get("co",p)
    p=p.reshape(-1,3).astype(float)
    mode=sys.argv[sys.argv.index("--")+1]
    if mode in ("front","rear","side"):
        angle={"front":0.,"rear":180.,"side":76.}[mode]
        shoot(scene,view,p,angle,.035,REVIEW/(mode+".png"),720,1080,1.075)
        return
    axes=shoot(scene,view,p,15.,.055,ICON/(KEY+".png"),320,480,1/.91)
    item_art(ob,p,axes)
    meta=json.loads((MODELS/"models.json").read_bytes())
    record={k:meta[k] for k in ("source","source_sha256")}
    if hashlib.sha256((ROOT/record["source"]).read_bytes()).hexdigest()!=record["source_sha256"]:
        raise RuntimeError("The garment source changed after the artist master was saved")
    record.update(standard_icon="Icons/"+KEY+".png",pickup="Icons/pickup.json",display="Icons/display.json",
        icon_pixels=[320,480],fill=.91,world_presentation="empty garment with both legs laid back at the knees")
    (ROOT/"artwork.json").write_text(json.dumps(record,indent=2))


if __name__=="__main__":main()
