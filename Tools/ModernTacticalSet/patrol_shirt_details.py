"""Photograph the three exposed interfaces of the native TS01 shirt, gloves and trousers."""
import gzip
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art import mesh
from coyote_glove_materials import create as glove_materials
from field_pants_art_photo import area
from field_pants_materials import create as trouser_materials
from patrol_shirt_materials import create as shirt_materials

SET = HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113"
ROOT = SET/"PatrolShirtR2"
REVIEW = ROOT/"Review"
FLIP = np.array([1.,-1.,1.])


def apply_waist_fit(pos, faces, normals, grid):
    # Use the worn mesh's centimetre-space waist grid. The first channel
    # is the radial displacement used in patrol_shirt_world_native.cpp.
    def moved(points):
        radial = points[:,:2]-[0.,.8]
        angle = (np.arctan2(radial[:,1],radial[:,0])%(2*np.pi))*(96/(2*np.pi))
        u = np.floor(angle).astype(int)
        h = np.clip(2*(points[:,2]-92.),0.,36.)
        v = np.minimum(h.astype(int),35)
        s,t = angle-u,h-v
        low = (1.-s)*grid[v,u%96]+s*grid[v,(u+1)%96]
        high = (1.-s)*grid[v+1,u%96]+s*grid[v+1,(u+1)%96]
        distance = low*(1.-t)+high*t
        result = points.copy()
        radial /= np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-10)
        result[:,:2] += radial*distance[:,None]
        return result
    active = (pos[:,2]>=91.) & (pos[:,2]<110.) & (np.abs(pos[:,0])<=21.)
    waist = pos[active]
    delta = .025
    jacobian = np.stack([(moved(waist+v)-moved(waist-v))/(2*delta) for v in np.eye(3)*delta],axis=2)
    transform = np.tile(np.eye(3),(len(pos),1,1))
    transform[active] = np.swapaxes(np.linalg.pinv(jacobian),1,2)
    normals = np.einsum("fcij,fcj->fci",transform[faces],normals)
    normals /= np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-10)
    pos[active] = moved(waist)
    return pos,normals


def garment(file, materials, name, waist_grid=None):
    with (gzip.open(file,"rb") if file.suffix==".gz" else file.open("rb")) as stream:
        data = json.load(stream)
    slots = [s.rsplit("/",1)[-1].split(".")[0].removeprefix("M_") for s in data["material_slots"]]
    used = [i for i,s in enumerate(slots) if s in materials]
    indices = np.asarray(data["triangle_materials"])
    take = np.isin(indices,used)
    faces = np.asarray(data["triangles"])[take]
    vertices, compact = np.unique(faces.ravel(),return_inverse=True)
    pos = np.asarray(data["positions"])[vertices]
    normals = np.asarray(data["normals"])[take]
    if waist_grid is not None:
        pos,normals = apply_waist_fit(pos,compact.reshape(-1,3),normals,waist_grid)
    uv = np.asarray(data["uv"])[take]
    uv[:,:,1] = 1.-uv[:,:,1]
    mesh(name,pos*FLIP,compact.reshape(-1,3),normals*FLIP,uv,np.searchsorted(used,indices[take]),
         [slots[i] for i in used],materials)
    return {b["name"]:np.asarray(b["position"])*FLIP*.01 for b in data["bones"]}


def photograph(scene,camera,target,towards,span,tag):
    view = Vector(towards).normalized()
    up = Vector((0.,0.,1.))
    right = up.cross(view).normalized()
    up = view.cross(right)
    axes = Matrix((right,up,view)).transposed()
    centre = Vector(target)
    camera.matrix_world = Matrix.Translation(centre+view*1.9)@axes.to_4x4()
    camera.data.ortho_scale = span
    # Keep the opposite, out-of-focus torso out of the wrist macro.
    camera.data.clip_end = 2.035 if tag=="cuff-glove" else 4.
    softboxes = []
    for label,offset,energy,size,colour in (
            ("Key",(-.42,.49,.62),40.,.51,(1.,.96,.93)),
            ("Fill",(.51,.08,.51),17.,.66,(.94,.97,1.)),
            ("Rim",(.34,.63,-.48),25.,.47,(1.,.97,.95))):
        source = label+"_"+tag
        area(scene,source,centre+axes@Vector(offset),centre,energy,size,colour)
        softboxes.append(bpy.data.objects[source])
    scene.render.filepath = str(REVIEW/(tag+".png"))
    bpy.ops.render.render(write_still=True)
    for obj in softboxes:
        bpy.data.objects.remove(obj,do_unlink=True)


def main():
    arguments = sys.argv[sys.argv.index("--")+1:]
    shirt_path = Path(arguments[0])
    shots = set(arguments[1:]) or {"raglan-elbow","cuff-glove","tucked-waist"}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    grid = None
    if "tucked-waist" in shots:
        routes = json.loads((ROOT/"World/routes.json").read_bytes())
        key, = [k for k,row in routes.items() if row["rig"]=="Jason" and row["tactical"] and not row["owner"]]
        grid = np.fromfile(ROOT/"World/Fits"/(key+".bin"),dtype="<f4").reshape(37,96,-1)[:,:,0]
    bones = garment(shirt_path,shirt_materials(),"Patrol shirt",grid)
    garment(SET/"CoyoteGlovesR2/Authored/gloves_Jason.json",glove_materials(),"Coyote gloves")
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.10
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_x,scene.render.resolution_y = 710,660
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("Garment detail studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .33
    camera_data = bpy.data.cameras.new("Textile detail")
    camera_data.type = "ORTHO"
    camera_data.clip_start = .01
    camera = bpy.data.objects.new(camera_data.name,camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    shoulder,elbow,wrist = (bones[key+"_l"] for key in ("upperarm","lowerarm","hand"))
    REVIEW.mkdir(parents=True,exist_ok=True)
    if "raglan-elbow" in shots:
        photograph(scene,camera,.52*shoulder+.48*elbow,(1.,.40,.18),.39,"raglan-elbow")
    # Look down onto the outer left wrist from the glove side.
    if "cuff-glove" in shots:
        photograph(scene,camera,wrist+.15*(elbow-wrist),(1.,-.47,.39),.225,"cuff-glove")
    if "tucked-waist" in shots:
        garment(SET/"FieldTrousersR2/Authored/pants_tactical_Jason.json",trouser_materials(),"Field trousers")
        photograph(scene,camera,bones["pelvis"]+[0.,-.03,.130],(.26,-1.,.16),.45,"tucked-waist")


if __name__=="__main__":
    main()
