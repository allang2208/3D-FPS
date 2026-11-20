"""Build and export body-fitted EXFIL reference helmets for the TS01 outfit."""
import argparse
import json
import os
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from exfil_reference_form import Crown, SET, OUT
from exfil_reference_liners import Anatomy, Studio, crown_board, inside, retention, unit


SLOTS=("Composite","Polymer","Rubber","Webbing","LoopPile","PadMesh","Metal","Label","Stitch","DarkPolymer")


def read(path):
    return json.loads(path.read_bytes())


def save_json(path,value):
    temporary=path.with_suffix(path.suffix+".creating")
    temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(",",":"),allow_nan=False),encoding="utf8")
    os.replace(temporary,path)


def shell(s,c):
    s.group_to("01 · Ballistic shell and binding")
    segments,rings=(224,82) if s.high else (112,32)
    aa=np.arange(segments)*2*np.pi/segments
    levels=[(t,0.) for t in np.linspace(1/rings,1.,rings)]
    levels += [(1.003,-.015),(1.007,-.060),(1.010,-.17),(1.011,-.32),
               (1.009,-.43),(1.005,-.51),(1.,-.54)]
    levels += [(t,-.54) for t in np.linspace(1.-1/rings,1/rings,rings-1)]
    # Polar distance on the surface gives the crown an unbroken disk UV.
    # The previous cylindrical map squeezed a full circumference into the
    # last few pixels at the peak and made the stipple disappear there.
    sample_t=np.linspace(0,1.012,145)
    sample_p=c.sample(aa[None,:],sample_t[:,None])
    arc=np.vstack((np.zeros(segments),np.cumsum(np.linalg.norm(np.diff(sample_p,axis=0),axis=2),axis=0)))
    uv_axes=np.column_stack((np.sin(aa),np.cos(aa)))
    vertices=[c.sample(0,0)];uvs=[(0,0)]
    for t,offset in levels:
        p=c.surface(aa,t,offset)
        vertices.extend(p)
        k=t*(len(sample_t)-1)/sample_t[-1]
        i=int(k)
        distance=arc[i]+(arc[i+1]-arc[i])*(k-i)
        uvs.extend(uv_axes*distance[:,None]/8.)
    vertices.append(c.sample(0,0)-[0,0,.54]);uvs.append((0,0))
    f=[(0,1+j,1+(j+1)%segments) for j in range(segments)]
    for i in range(len(levels)-1):
        for j in range(segments):
            a=1+i*segments+j;b=1+i*segments+(j+1)%segments
            f.append((a,b,b+segments,a+segments))
    end=len(vertices)-1
    f += [(end,end-segments+(j+1)%segments,end-segments+j) for j in range(segments)]
    s.mesh("Outer_Shell_Continuous_Mould",vertices,f,"Composite",uvs)
    # Continuous slim edge binding; at the brow the exposed lip reads as a
    # shallow horizontal step. The edge wraps through the high-cut ear opening.
    around=segments;axis=c.normal(aa,.991)
    down=unit(c.sample(aa,1.)-c.sample(aa,.985))
    poles=c.sample(aa,.993)
    profile=[(-.31,-.018),(-.29,.044),(-.25,.095),(-.18,.112),
             (.105,.102),(.21,.064),(.245,-.015),(.22,-.10),(-.28,-.12)]
    p=np.concatenate([poles+down*w+axis*h for w,h in profile],axis=0)
    f=[(i*around+j,i*around+(j+1)%around,((i+1)%len(profile))*around+(j+1)%around,
        ((i+1)%len(profile))*around+j) for i in range(len(profile)) for j in range(around)]
    s.mesh("Perimeter_Polymer_Bind",p,f,"Polymer")
    s.cord("Under_Rim_Seal",poles+down*.14-axis*.40,.057,"Rubber",True,8 if s.high else 5)
    # Central mating patch on the crown has clipped, softly rounded ends.
    def top_patch(u,v):
        point,n=crown_board(c,u*2.27,v*4.28-.4)
        return point+n*.014,n
    s.cushion("Crown_Loop_Attachment",top_patch,4.54,8.56,"LoopPile",.195,power=.34)
    # The unobstructed rear centre accepts a narrow patch block; it stops
    # above the trim and stays separate from the left and right ID fields.
    def rear_patch(u,v):
        a=np.pi+u*.36;t=.55+v*.137
        return c.surface(a,t,.010),c.normal(a,t)
    s.cushion("Rear_Identification_Loop",rear_patch,7.6,3.9,"LoopPile",.112,power=.27)


def head_ref(rig):
    source=SET/"HelmetHairFitR1/Inputs"
    head=read(source/f"{rig}_Head.json")
    h=head["bones"]["head"];b=read(source/f"{rig}_Body.json")["bones"]["head"]
    p=(np.asarray(head["positions"])-h["position"])@np.linalg.inv(h["axes"])@b["axes"]+b["position"]
    me=bpy.data.meshes.new("Native_reference_"+rig)
    me.from_pydata((p*[.01,-.01,.01]).tolist(),[],head["triangles"]);me.update()
    ob=bpy.data.objects.new("REFERENCE_ONLY_"+rig,me);bpy.context.scene.collection.objects.link(ob)
    ob.display_type="WIRE";ob.hide_render=True;ob.hide_set(True)
    return p,head["triangles"],b


def payload(objs, exported_counts=None):
    p=[];faces=[];normal=[];tex=[];material=[]
    for obj in objs:
        me=obj.data
        me.calc_loop_triangles()
        offset=len(p);local=np.array([v.co[:] for v in me.vertices],dtype=float)
        world=np.array(obj.matrix_world)
        pts=local@world[:3,:3].T+world[:3,3]
        p.extend((pts*[100.,-100.,100.]).tolist())
        remap=[]
        for slot in me.materials:
            name=slot.name.removeprefix("H1_").split(".")[0]
            if name not in SLOTS:raise ValueError(f"Unknown material {slot.name} on {obj.name}")
            remap.append(SLOTS.index(name))
        uv=me.uv_layers.active
        if uv is None:raise RuntimeError(f"No UV on {obj.name}")
        cn=np.array([n.vector[:] for n in me.corner_normals])
        cn=unit(cn@np.linalg.inv(world[:3,:3]))*[1,-1,1]
        coords=np.asarray([u.uv[:] for u in uv.data]);coords[:,1]=1.-coords[:,1]
        triangles=list(me.loop_triangles)
        if not triangles:continue
        loops=np.asarray([t.loops[:] for t in triangles],dtype=int)
        f=np.asarray([t.vertices[:] for t in triangles],dtype=int)
        xf=local[f];cross=np.cross(xf[:,1]-xf[:,0],xf[:,2]-xf[:,0])
        keep=(cross**2).sum(1)>1.e-26
        if exported_counts is not None:
            exported_counts[obj.name]=int(keep.sum())
        faces.extend((f[keep]+offset).tolist())
        normal.extend(cn[loops[keep]].tolist())
        tex.extend(coords[loops[keep]].tolist())
        material.extend([remap[t.material_index] for t,ok in zip(triangles,keep) if ok])
    return dict(positions=p,triangles=faces,normals=normal,uv=tex,triangle_materials=material,material_slots=["H1_"+n for n in SLOTS])


def build(rig,high,shell_only=False,draft=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.view.use_translate_new_dataname=False
    for name in ("Authored","Models","Exports"):
        (OUT/name).mkdir(parents=True,exist_ok=True)
    from exfil_reference_materials import create
    mats=create()
    s=Studio(mats,high,rig);c=Crown(rig)
    hp,hf,body=head_ref(rig);anatomy=Anatomy(hp,hf,c)
    shell(s,c);inside(s,c);retention(s,c,anatomy)
    if not shell_only:
        import exfil_reference_hardware as hardware
        hw=bpy.data.collections.new("04 · Side rails, shroud and identification")
        bpy.context.scene.collection.children.link(hw)
        before=set(bpy.data.objects)
        hardware.build(c,rig,high)
        for ob in list(set(bpy.data.objects)-before):
            if ob.type=="MESH" and ob.users_collection:
                for col in list(ob.users_collection):col.objects.unlink(ob)
                hw.objects.link(ob)
    bpy.context.view_layer.update()
    meshes=[ob for ob in bpy.context.scene.objects if ob.type=="MESH" and not ob.name.startswith("REFERENCE_ONLY_") and not ob.hide_render]
    for ob in meshes:
        bpy.context.view_layer.objects.active=ob
        for mod in list(ob.modifiers):
            if mod.show_render:bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.context.scene["AssetRevision"]="ExfilReferenceR4"
    bpy.context.scene["AuthoringUnits"]="Blender metres; UE centimetres; native +Y is forward"
    stage="HIGH" if high else "GAME"
    if shell_only or draft:
        name="exfil_shell_only" if shell_only else "exfil_assembly_draft"
        temporary=Path(os.environ["TEMP"])/f"{name}_{rig}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(temporary));return
    basename=f"TS01_Helmet_{rig}"
    # Keep textures linked to their authoring files. The FBX transfers the
    # material bindings, while the packaged UE textures retain editable sources.
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Models"/(basename+"_"+stage+".blend")))
    counts={}
    for ob in meshes:
        ob.data.calc_loop_triangles();counts[ob.name]=len(ob.data.loop_triangles)
    if not high:
        bpy.ops.export_scene.fbx(filepath=str(OUT/"Exports"/(basename+".fbx")),
            use_selection=True,object_types={"MESH"},apply_unit_scale=True,bake_anim=False,
            mesh_smooth_type="FACE",axis_forward="-Y",axis_up="Z",path_mode="RELATIVE")
        data=payload(meshes,counts)
        save_json(OUT/"Authored"/f"helmet_{rig}_world.json",data)
        from exfil_wear_retention import fit
        fit(data,counts,hp,hf,body)
        axes=np.asarray(body["axes"]);data["positions"]=((np.asarray(data["positions"])-body["position"])@np.linalg.inv(axes)).tolist()
        data["normals"]=unit(np.asarray(data["normals"])@axes.T).tolist()
        data["attachment_frame"]=body
        save_json(OUT/"Authored"/f"helmet_{rig}_wear.json",data)
    save_json(OUT/"Authored"/f"parts-{rig}-{stage}.json",dict(rig=rig,stage=stage,triangles=sum(counts.values()),parts=counts))
    print("EXFIL_MODEL_FINISHED",rig,stage,len(counts),sum(counts.values()),flush=True)


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("rig",choices=("Jason","Kaitlin"))
    args.add_argument("stage",choices=("GAME","HIGH"))
    args.add_argument("--shell-only",action="store_true")
    args.add_argument("--draft",action="store_true")
    options=args.parse_args(sys.argv[sys.argv.index("--")+1:])
    build(options.rig,options.stage=="HIGH",options.shell_only,options.draft)
