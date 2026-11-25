"""Export a centimeter-scale rigged mill keeper and a matching relaxed work idle."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from keeper_fabrics import FABRICS, author_shader, material_paths
from keeper_skirt import lower_belt_edge, tailor_skirt
from keeper_workcloth import PANEL_NAMES, bind_blender
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parents[3]/"SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1/Assembly"
rig=np.load(ROOT/"Rig.npz")
spec=json.loads((ROOT/"assembly.json").read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.unit_settings.scale_length=.01
reflection=np.diag([1,-1,1])
arm=bpy.data.armatures.new("Kaitlin petite")
rig_obj=bpy.data.objects.new("Armature",arm)
scene.collection.objects.link(rig_obj)
bpy.context.view_layer.objects.active=rig_obj
rig_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
names=rig["names"].tolist()
for i,name in enumerate(names):
    bone=arm.edit_bones.new(name)
    bone.head=rig["positions"][i] @ reflection
    basis=reflection @ rig["axes"][i].T @ reflection
    bone.tail=bone.head+Vector(basis[:,1])*2.
    bone.align_roll(Vector(basis[:,2]))
    if rig["parents"][i]>=0: bone.parent=arm.edit_bones[names[rig["parents"][i]]]
bpy.ops.object.mode_set(mode="OBJECT")


def material(name):
    existing=bpy.data.materials.get(name)
    if existing:return existing
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    shader=mat.node_tree.nodes.get("Principled BSDF")
    if isinstance(spec["materials"][name],dict):
        for channel,file in spec["materials"][name].items():
            node=mat.node_tree.nodes.new("ShaderNodeTexImage")
            node.image=bpy.data.images.load(str(ROOT/file),check_existing=True)
            if channel!="BC":node.image.colorspace_settings.name="Non-Color"
            output=node.outputs["Color"]
            if channel=="N":
                normal=mat.node_tree.nodes.new("ShaderNodeNormalMap");mat.node_tree.links.new(output,normal.inputs["Color"]);output=normal.outputs["Normal"]
            mat.node_tree.links.new(output,shader.inputs[{"BC":"Base Color","N":"Normal","R":"Roughness","M":"Metallic"}[channel]])
    elif name in PANEL_NAMES:
        bind_blender(mat,shader,name)
    elif name in FABRICS:
        author_shader(mat, shader, name, Path(__file__).resolve().parents[3] /
                      "SourceAssets/WitchRebuilt20260921/Refinement20260922/Textures")
    else:
        colors={"Hands":(.55,.32,.22),"Skirt":(.105,.125,.095),"WorkLinen":(.48,.40,.29),
                "Belt":(.13,.07,.035),"Leather":(.11,.065,.04),"Sole":(.04,.03,.025),
                "Thread":(.30,.22,.15),"Cuff":(.62,.54,.43),"NeckLinen":(.62,.54,.43),"Apron":(.55,.46,.32)}
        shader.inputs["Base Color"].default_value=(*colors[name],1)
    return mat


def surface(name,p,faces,uv,slots,ids):
    me=bpy.data.meshes.new(name);me.from_pydata(p,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
    for slot in slots:me.materials.append(material(slot))
    me.polygons.foreach_set("material_index",np.asarray(ids,np.int32))
    me.polygons.foreach_set("use_smooth",np.ones(len(faces),bool))
    tex=np.asarray(uv).copy();tex[:,:,1]=1-tex[:,:,1]
    me.uv_layers.new(name="UVMap").data.foreach_set("uv",tex.astype("f").ravel())
    return ob


def bind(ob):
    ob.parent=rig_obj
    mod=ob.modifiers.new("Kaitlin rig","ARMATURE");mod.object=rig_obj


def apron(dress):
    me=dress.data
    coords=[v.co for v in me.vertices]
    pieces={s: [poly.vertices[:] for poly in me.polygons if me.materials[poly.material_index].name==s]
            for s in ("Belt","SkirtPanels")}
    skirt=pieces["SkirtPanels"]
    tree=BVHTree.FromPolygons(coords,skirt,all_triangles=True)
    belt=BVHTree.FromPolygons(coords,pieces["Belt"],all_triangles=True)
    belt_points=np.asarray(coords)[np.asarray(pieces["Belt"])]
    p=[];uv=[];weights=[];tris=[]
    widths=np.r_[-1., -.978, np.linspace(-.95,.95,47), .978, 1.]
    lengths=np.r_[0.,.008,.018,.031,np.linspace(.047,.96,43), .978, .99, 1.]
    nx=len(widths)-1
    tops=[lower_belt_edge(belt_points,s*9.35)+.65 for s in widths]
    for row,t in enumerate(lengths):
        for col,s in enumerate(widths):
            z=(1.-t)*tops[col]+t*(38.9+1.35*s*s)+t*t*(.75*np.sin(5.5*s+.35)+.45*s)
            x=s*(9.35+5.85*t)+.40*t*t
            ray=Vector((x,-60,z))
            hit,normal,k,_=tree.ray_cast(ray,Vector((0,1,0)),100)
            if hit is None and t<.04:
                hit,normal,k,_=tree.ray_cast(Vector((x,-60,z-1.5)),Vector((0,1,0)),100)
            if hit is None:raise RuntimeError("Apron outside skirt")
            ids=skirt[k]
            bary=barycentric_transform(hit,*(me.vertices[i].co for i in ids),
                    Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
            w={}
            for i,a in zip(ids,bary):
                for g in me.vertices[i].groups:w[g.group]=w.get(g.group,0.)+max(0.,a)*g.weight
            weights.append(w)
            gather=.5*(1.-np.cos(np.pi*(3.08*s+.27*np.sin(3.1*t+2.8*s)+.12*t*s)))
            pleats=(.5+.5*np.cos(np.pi*(6.4*s+.15)))**3*np.exp(-t*6.)
            hem=.16*(np.exp(-((1.-abs(s)-.024)/.018)**2)+np.exp(-((1.-t-.014)/.011)**2))
            fall=np.clip(t/.07,0.,1.)
            fall=fall*fall*(3.-2.*fall)
            clearance=.40+fall*(.23*t+(1.08+.40*t)*gather+.68*pleats+hem)
            y=hit.y-clearance
            if z>=tops[col]-.70:
                belt_hit,_,_,_=belt.ray_cast(ray,Vector((0,1,0)),100)
                # Below the front waistband a ray can still hit the lower rear
                # half of the belt. That side cannot anchor the front apron.
                if belt_hit is not None and belt_hit.y<hit.y+.20:
                    y=max(y,belt_hit.y+.22)
            p.append(Vector((x,y,z)))
            uv.append(((s+1.)*.5,t))
            if row and col:
                i=len(p)-1;tris.extend([(i-nx-2,i-1,i),(i-nx-2,i,i-nx-1)])
    # A separately cut patch with an open mouth, secured into the front panel.
    from keeper_workcloth import pocket_uv
    grid_u=(widths+1.)*.5
    columns=len(widths)
    pocket_start=len(p)
    pocket_cols=17
    for j,v in enumerate(np.linspace(0.,1.,17)):
        for i,u in enumerate(np.linspace(0.,1.,pocket_cols)):
            pu,pv=pocket_uv(u,v)
            col=np.searchsorted(grid_u,pu)-1
            row=np.searchsorted(lengths,pv)-1
            fu=(pu-grid_u[col])/(grid_u[col+1]-grid_u[col])
            fv=(pv-lengths[row])/(lengths[row+1]-lengths[row])
            a=row*columns+col
            # Use the actual diagonal of the skinned apron face.
            corners=((a,1.-fv),(a+columns,fv-fu),(a+columns+1,fu)) if fv>=fu else (
                (a,1.-fu),(a+columns+1,fv),(a+1,fu-fv))
            point=Vector((0,0,0))
            w={}
            for idx,amount in corners:
                point+=p[idx]*amount
                for bone,weight in weights[idx].items():
                    w[bone]=w.get(bone,0.)+amount*weight
            belly=np.sin(np.pi*u)**.8
            point.y-=.16+belly*(.47*np.sin(np.pi*v)+.94*np.exp(-v*7.))+.13*np.exp(-((v-.065)/.04)**2)
            p.append(point);weights.append(w);uv.append((pu,pv))
            if j and i:
                b=pocket_start+j*pocket_cols+i
                tris.extend(((b-pocket_cols-1,b-1,b),(b-pocket_cols-1,b,b-pocket_cols)))
    tri=np.asarray(tris)
    ob=surface("Apron",p,tri,np.asarray(uv)[tri],["Apron"],np.zeros(len(tri)))
    gs={g.index:ob.vertex_groups.new(name=g.name) for g in dress.vertex_groups}
    for i,w in enumerate(weights):
        denom=sum(w.values())
        for b,a in w.items():
            if a>0:gs[b].add([i],a/denom,"REPLACE")
    # The folded rim has depth at the sides and hem when viewed from the mill doorway.
    bpy.context.view_layer.objects.active=ob
    rim=ob.modifiers.new("Apron turned edge","SOLIDIFY")
    rim.thickness=.12
    rim.offset=-1.
    bpy.ops.object.modifier_apply(modifier=rim.name)
    bind(ob)


objects=[]
spec["materials"].update(material_paths())
for name in ("Body","Dress","Boots","Head","Base"):
    with np.load(ROOT/(name+".npz")) as src:
        d=dict(src)
    if name=="Dress":
        tailor_skirt(d)
        d["mats"]=["SkirtPanels" if s=="Skirt" else str(s) for s in d["mats"]]
    if name=="Head":
        # The underlying captured native neck was shaded as a cuff in R2. The
        # turned garment edge now meets the weighted Meshy skin directly.
        keep=d["ids"] != d["mats"].tolist().index("NeckLinen")
        verts, reduced=np.unique(d["tri"][keep],return_inverse=True)
        for key in ("p","w","j"):d[key]=d[key][verts]
        for key in ("ids","uv","n"):d[key]=d[key][keep]
        d["tri"]=reduced.reshape(-1,3)
        d["mats"]=d["mats"][:-1]
    tri=d["tri"]
    ob=surface(name,d["p"] @ reflection,tri,d["uv"],list(d["mats"]),d["ids"])
    if "n" in d:
        ob.data.normals_split_custom_set((d["n"].reshape(-1,3) @ reflection).tolist())
    joints=d["j"];weights=d["w"]
    groups={i:ob.vertex_groups.new(name=names[i]) for i in np.unique(joints[weights>0])}
    for vi,(bones,ws) in enumerate(zip(joints,weights)):
        for bone,w in zip(bones,ws):
            if w>0:groups[bone].add([vi],float(w),"REPLACE")
    if name=="Dress":apron(ob)
    if name in ("Dress","Boots"):
        bpy.context.view_layer.objects.active=ob
        dec=ob.modifiers.new("Cloth and leather triangulation","DECIMATE")
        dec.ratio=.40 if name=="Dress" else .18
        bpy.ops.object.modifier_apply(modifier=dec.name)
    bind(ob)
    if name=="Base":
        base=ob
        ob.name="SK_MillKeeper_Base"
        ob.hide_render=True
        ob.hide_set(True)
    else: objects.append(ob)

# Keep the production FBX as a single skeletal mesh; the source blend retains named parts.
scene.render.fps=10
scene.frame_start=1; scene.frame_end=len(rig["idle"])
for i,name in enumerate(names):
    keys=rig["idle"][:,i,3:7]
    rest_rotation=rig["reference"][i,3:7]
    if np.max(np.abs(keys-rest_rotation))<1e-6: continue
    pb=rig_obj.pose.bones[name]
    # Reflection across Y changes a quaternion's axial vector by (-x,+y,-z).
    q0=Quaternion((rest_rotation[3],-rest_rotation[0],rest_rotation[1],-rest_rotation[2])).inverted()
    previous=None
    for f,key in enumerate(keys,1):
        q=q0 @ Quaternion((key[3],-key[0],key[1],-key[2]))
        if previous:q.make_compatible(previous)
        pb.rotation_quaternion=q;pb.keyframe_insert("rotation_quaternion",frame=f)
        previous=q
rig_obj.animation_data.action.name="A_MillKeeper_Idle"
scene.frame_set(1)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"MillKeeper.blend"))
bpy.ops.object.select_all(action="DESELECT")
if "--outfit-only" not in sys.argv:
    base.hide_set(False);base.select_set(True);rig_obj.select_set(True)
    bpy.context.view_layer.objects.active=base
    bpy.ops.export_scene.fbx(filepath=str(ROOT/"SK_MillKeeper_Base.fbx"),use_selection=True,object_types={"ARMATURE","MESH"},
        axis_forward="Y",axis_up="Z",apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        add_leaf_bones=False,bake_anim=False,mesh_smooth_type="FACE",path_mode="STRIP")
bpy.ops.object.select_all(action="DESELECT")
for ob in list(scene.objects):
    if ob.type=="MESH" and ob!=base:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.object.join()
objects[0].name="SK_MillKeeper"
rig_obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(ROOT/"SK_MillKeeper.fbx"),use_selection=True,object_types={"ARMATURE","MESH"},
    axis_forward="Y",axis_up="Z",apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
    add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=.05,mesh_smooth_type="FACE",path_mode="STRIP",use_tspace=True)
(ROOT/"assembly.json").write_text(json.dumps(spec,indent=2))
