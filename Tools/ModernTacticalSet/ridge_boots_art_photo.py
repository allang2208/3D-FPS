"""Photograph the outside of a right boot and arrange both real lasts for inventory."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from coyote_glove_art import mesh, unit
from field_pants_art_photo import area, write_static
from ridge_boots_art import NAME, ROOT

ICON = ROOT/"Icons"
REVIEW = ROOT/"Review"
KEY = "ue_modern_tactical_boots"
Z = np.array([0.,0.,1.])


def studio():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"Models"/(NAME+"_GAME.blend")))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 112
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -.85
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("Neutral studio")
    world.use_nodes = True
    scene.world = world
    bounce = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bounce.inputs[0].default_value = (.75,.78,.82,1.)
    bounce.inputs[1].default_value = .31
    return scene


def relaxed_shaft(points, faces, normals):
    # The wearable includes room for the gathered cuff. On the floor the
    # untensioned quarters draw in again above the instep of the empty boot.
    heel = points[points[:,2] < .055,0].min()
    t = np.clip((points[:,2] - .095) / .155, 0., 1.)
    weight = t*t*(3. - 2.*t)
    slope = 6.*t*(1. - t) / .155
    xscale, yscale = 1. - .185*weight, 1. - .075*weight
    zx = (-.185*(points[:,0] - heel) + .002)*slope
    zy = -.075*points[:,1]*slope
    points[:,0] = heel + (points[:,0] - heel)*xscale + .002*weight
    points[:,1] *= yscale
    normals[:,:,0] /= xscale[faces]
    normals[:,:,1] /= yscale[faces]
    normals[:,:,2] -= zx[faces]*normals[:,:,0] + zy[faces]*normals[:,:,1]
    normals /= np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1.e-9)


def arrangement(pair, sole_only=False):
    ob = bpy.data.objects[NAME]
    ob.hide_render = True
    data = ob.data
    p = np.empty((len(data.vertices),3),np.float32)
    data.vertices.foreach_get("co",p.ravel())
    faces = np.array([f.vertices[:] for f in data.polygons])
    normals = np.empty((len(faces),3,3),np.float32)
    data.corner_normals.foreach_get("vector",normals.ravel())
    uv = np.empty((len(faces),3,2),np.float32)
    data.uv_layers.active.data.foreach_get("uv",uv.ravel())
    ids = np.array([f.material_index for f in data.polygons])
    mats = {m.name:m for m in data.materials}
    slots = list(mats)
    coords, packed_faces, ns, maps, materials = [], [], [], [], []
    for side in (("r","l") if pair else ("r",)):
        # The two lasts have a native toe-out angle. Remove it before
        # arranging them, retaining the actual instep and outer quarter.
        bones = ob.parent.data.bones
        foot = np.array(bones["foot_"+side].head_local)
        forward = np.array(bones["ball_"+side].head_local)-foot
        forward[2] = 0.
        forward = unit(forward)
        axes = np.stack((forward, np.cross(Z,forward), Z))
        side_faces = (p[faces,0].mean(axis=1)>0) == (side=="l")
        if sole_only:
            # The reference is a separate outsole mould photographed flat.
            # Suppress collar and pull-tab overhangs for the corresponding plate.
            side_faces &= ids==slots.index("RB_Outsole")
        verts, ix = np.unique(faces[side_faces].ravel(),return_inverse=True)
        points = (p[verts]-foot)@axes.T
        points[:,2] -= points[:,2].min()
        indices = ix.reshape(-1,3)
        shaped_normals = normals[side_faces]@axes.T
        if not sole_only:
            relaxed_shaft(points,indices,shaped_normals)
        if side=="l":
            theta = np.radians(7.)
            rot = np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1.]])
            points = points@rot.T + np.array([-.052,.131,0])
            shaped_normals = shaped_normals@rot.T
        ids_offset = sum(len(a) for a in coords)
        packed_faces.append(indices+ids_offset)
        coords.append(points)
        ns.append(shaped_normals)
        maps.append(uv[side_faces])
        materials.append(ids[side_faces])
    arrays = tuple(np.concatenate(v) for v in (coords,packed_faces,ns,maps,materials))
    p,t,n,uv,ids = arrays
    mesh("TS01 product pose",p*100,t,n,uv,ids,slots,mats)
    return p,t,n,uv,ids,slots


def photograph(scene,p,towards,up_hint,path,width,height,pad):
    towards = unit(np.array(towards,dtype=float))
    right = unit(np.cross(up_hint,towards))
    up = np.cross(towards,right)
    axes = np.stack((right,up,towards))
    proj = p@axes.T
    center = ((proj.min(0)+proj.max(0))*.5)@axes
    data = bpy.data.cameras.new("Product camera")
    data.type = "ORTHO"
    data.clip_start = .001
    view = bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(view)
    scene.camera = view
    view.matrix_world = Matrix.Translation(Vector(center+2*towards))@Matrix(axes.T.tolist()).to_4x4()
    w,h,_ = np.ptp(proj,axis=0)
    aspect = width/height
    data.ortho_scale = max(w/min(aspect,1.), h/min(1./aspect,1.))*pad
    lights = (
        ("Upper front softbox",(-.43,.65,.72),30.,.60,(1.,.97,.94)),
        ("Quarter fill",(.52,.08,.50),10.,.68,(.94,.97,1.)),
        ("Heel rim",(.31,.53,-.44),24.,.45,(1.,.96,.91)))
    if towards[2] < -.99:
        lights = (("Tread rake",(-.44,.43,.20),17.,.23,(1.,.97,.94)),
                  ("Rubber fill",(.40,-.18,.59),6.,.64,(.95,.97,1.)))
    for label,offset,power,size,tint in lights:
        area(scene,label,center+offset@axes,center,power,size,tint)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return axes


def main():
    for dest in (ICON,REVIEW):
        dest.mkdir(parents=True,exist_ok=True)
    mode = sys.argv[sys.argv.index("--")+1]
    scene = studio()
    points,faces,normals,uv,ids,slots = arrangement(pair=mode=="icon",sole_only=mode=="sole")
    if mode=="side":
        photograph(scene,points,(0,-1,.04),Z,REVIEW/"lateral.png",1248,1152,1.09)
    elif mode=="sole":
        photograph(scene,points,(0,0,-1),np.array([0.,-1.,0.]),REVIEW/"outsole.png",896,430,1.075)
    elif mode=="quarter":
        photograph(scene,points,(.82,-1,.27),Z,REVIEW/"three-quarter.png",1200,1260,1.09)
    elif mode=="icon":
        axes = photograph(scene,points,(.81,-1,.48),Z,ICON/(KEY+".png"),320,480,1.07)
        uv = uv.copy()
        uv[:,:,1] = 1.-uv[:,:,1]
        # UE item view faces toward -X. Both file bases undo Blender's
        # handedness change without disturbing custom normals or UV seams.
        display_axes = np.stack((-axes[2],axes[0],axes[1]))
        ground_axes = np.diag([1.,-1.,1.])
        for role,basis in (("display",display_axes),("pickup",ground_axes)):
            write_static(ICON/(role+".json"),points@basis.T,faces,normals@basis.T,uv,ids,slots)
    else:
        raise ValueError(mode)


if __name__ == "__main__":
    main()
