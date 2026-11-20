"""Pose the catalogue shirt and lay the existing armour item on its back."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art import mesh, unit
from field_pants_art_photo import shoot, write_static
from patrol_shirt_art import NAME, ROOT

KEY = "ue_modern_kevlar_vest"
ICON = ROOT/"Icons"
REVIEW = ROOT/"Review"
SHOULDER = ROOT.parent/"ShoulderFit20261118"
FLIP = np.array([1.,-1.,1.])


def setup():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"Models"/(NAME+"_GAME.blend")))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.12
    world = bpy.data.worlds.new("Neutral textile studio")
    world.use_nodes = True
    scene.world = world
    bg = next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs[0].default_value = (.72,.74,.76,1.)
    bg.inputs[1].default_value = .42
    cam = bpy.data.cameras.new("Catalogue orthographic")
    cam.type = "ORTHO"
    cam.clip_start = .001
    view = bpy.data.objects.new(cam.name,cam)
    scene.collection.objects.link(view)
    scene.camera = view
    return scene,view,bpy.data.objects[NAME]


def arm_pose(rig,folded):
    # Rotate in armature space about the actual garment's upper arm and elbow.
    # Evaluation then honours all twist and cloth groups from the wearable.
    for side,sign in (("l",1.),("r",-1.)):
        if folded:
            # Sleeve folds behind the carrier at the elbow, so the front
            # pouches keep their volume. The two cuffs nest at different levels.
            directions=((.71*sign,.51,-.50),(-.91*sign,.27,-.30 if sign>0 else -.12))
        else:
            directions=((.29*sign,.035,-.955),(.035*sign,-.16,-.985))
        for bone_name,end_name,direction in zip(("upperarm_","lowerarm_"),("lowerarm_","hand_"),directions):
            bone,tip = rig.pose.bones[bone_name+side],rig.pose.bones[end_name+side]
            here = bone.head.copy()
            rotation = (tip.head-here).normalized().rotation_difference(Vector(direction).normalized())
            bone.matrix = Matrix.Translation(here)@rotation.to_matrix().to_4x4()@Matrix.Translation(-here)@bone.matrix
            bpy.context.view_layer.update()


def carrier():
    from shoulder_inventory import patch_part
    raw = patch_part("Jason","vest","carrier")
    paths = list(dict.fromkeys(raw["materials"]))
    library = SHOULDER/"Models/TS01_Vest_Jason.blend"
    with bpy.data.libraries.load(str(library),link=False) as (existing,requested):
        names = []
        for path in paths:
            base = path.rsplit("/",1)[-1].split(".")[0]
            options = (base,"TS01_"+base.removeprefix("M_"))
            names.append(next(n for n in options if n in existing.materials))
        requested.materials = names
    mats = {}
    for m,path in zip(requested.materials,paths):
        m["UE material"] = path
        mats[m.name] = m
    names = list(mats)
    mapping = np.array([paths.index(path) for path in raw["materials"]])
    uv = np.array(raw["uv"])
    uv[:,:,1] = 1.-uv[:,:,1]
    return mesh("Existing carrier",np.array(raw["positions"])*FLIP,np.array(raw["triangles"]),
                np.array(raw["normals"])*FLIP,uv,mapping[np.array(raw["triangle_materials"])],names,mats)


def visible_geometry(items):
    sections,slots,paths = [],[],[]
    count = 0
    graph = bpy.context.evaluated_depsgraph_get()
    for ob in items:
        evaluated = ob.evaluated_get(graph)
        data = evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
        p = np.empty((len(data.vertices),3),np.float32)
        data.vertices.foreach_get("co",p.ravel())
        f = np.array([face.vertices[:] for face in data.polygons])
        n = np.empty((len(f),3,3),np.float32)
        data.corner_normals.foreach_get("vector",n.ravel())
        uv = np.empty((len(f),3,2),np.float32)
        data.uv_layers.active.data.foreach_get("uv",uv.ravel())
        uv[:,:,1] = 1.-uv[:,:,1]
        ids = np.array([face.material_index for face in data.polygons])
        idx = []
        for m in data.materials:
            name = m.name
            if name not in slots:
                slots.append(name)
                paths.append(m.get("UE material","/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/"
                                   "PatrolShirtR2/Materials/M_"+name))
            idx.append(slots.index(name))
        sections.append((p.copy(),f+count,n,uv,np.asarray(idx)[ids]))
        count += len(p)
        evaluated.to_mesh_clear()
    return (*[np.concatenate(col) for col in zip(*sections)],slots,paths)


def on_floor(points,hem):
    # Lay the shirt and the carrier front-up. The loose tail turns beneath
    # the torso around a fixed radius; the stiffer carrier stays above it.
    x,y,z = points.T
    radius = .031
    station = (hem+.116)-z
    angle = np.clip(station/radius,0,np.radians(148.))
    extra = np.maximum(station-radius*np.radians(148.),0)
    length = np.minimum(station,0)+radius*np.sin(angle)+extra*np.cos(angle)
    drop = radius*(np.cos(angle)-1)-extra*np.sin(angle)
    bulge = .0018*np.sin(x*29+z*9)
    # With no torso inside it the tail lies nearly flat, whereas the
    # plate carrier and its outer pockets retain depth above the fold.
    support = np.clip((z-hem-.14)/.15,0.,1.)
    support = support*support*(3.-2.*support)
    depth = -(.105+.455*support)*y+bulge
    return np.column_stack((x,length+depth*np.sin(angle),drop+depth*np.cos(angle)))


def main():
    for folder in (ICON,REVIEW):
        folder.mkdir(parents=True,exist_ok=True)
    mode = sys.argv[sys.argv.index("--")+1]
    scene,view,ob = setup()
    rig = ob.find_armature()
    arm_pose(rig,mode=="pickup")
    show_item = mode in ("icon","pickup")
    items = [ob,carrier()] if show_item else [ob]
    p,f,n,uv,ids,slots,paths = visible_geometry(items)
    if mode in ("front","rear"):
        shoot(scene,view,p,0. if mode=="front" else 180.,.012,REVIEW/(mode+".png"),1060,1210,1.075)
    elif mode=="icon":
        axes = shoot(scene,view,p,12.,.07,ICON/(KEY+".png"),480,480,1/.91)
        basis = np.stack((-axes[2],axes[0],axes[1]))
        write_static(ICON/"display.json",p@basis.T,f,n@basis.T,uv,ids,slots)
        (ICON/"materials.json").write_text(json.dumps(dict(zip(slots,paths)),indent=2))
    elif mode=="pickup":
        hem = float(p[:,2].min())
        folded = on_floor(p,hem)
        delta = .00008*np.eye(3)
        jac = np.stack([(on_floor(p+d,hem)-on_floor(p-d,hem))/.00016 for d in delta],axis=2)
        normals = unit(np.einsum("fcij,fcj->fci",np.linalg.inv(jac).transpose(0,2,1)[f],n))
        write_static(ICON/"pickup.json",folded,f,normals,uv,ids,slots)


if __name__=="__main__":
    main()
