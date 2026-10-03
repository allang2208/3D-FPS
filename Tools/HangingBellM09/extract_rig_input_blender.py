"""Extract the V02 editable geometry for semantic rig authoring; no rendering or testing."""
import bpy,json,numpy as np
from mathutils import Matrix
from pathlib import Path
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
OUT=ROOT/"RigV03"
for d in ["Authoring","Exports","Records","Work"]:(OUT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/"Authoring/M09_Separated_Adjusted_v02.blend"))
arrays={};parts=[]
for ob in sorted([o for o in bpy.context.scene.objects if o.type=="MESH"],key=lambda o:int(o["part_id"])):
 pid=int(ob["part_id"]);prefix=f"p{pid}"
 xyz=np.empty((len(ob.data.vertices),3),np.float32);ob.data.vertices.foreach_get("co",xyz.ravel())
 m=np.array(Matrix.LocRotScale(ob.location,ob.rotation_euler,ob.scale));world=xyz@m[:3,:3].T+m[:3,3]
 arrays[prefix+"_positions"]=world.astype(np.float32)
 src=np.empty(len(xyz),np.int32);ob.data.attributes["source_vertex_id"].data.foreach_get("value",src)
 arrays[prefix+"_source_ids"]=src
 fixed=np.zeros(len(xyz),np.float32);group=ob.vertex_groups.get("M09_FixedAttachment")
 if group:
  for v in ob.data.vertices:
   for g in v.groups:
    if g.group==group.index:fixed[v.index]=g.weight;break
 arrays[prefix+"_fixed"]=fixed
 if pid in [8,9]:
  edges=np.empty((len(ob.data.edges),2),np.int32);ob.data.edges.foreach_get("vertices",edges.ravel())
  arrays[prefix+"_edges"]=edges
 parts.append({"id":pid,"name":ob.name,"vertices":len(xyz),"pivot":list(ob.location)})
meta={"input":str(ROOT/"Authoring/M09_Separated_Adjusted_v02.blend"),"parts":parts,
 "guides":{o.name:list(o.location) for o in bpy.context.scene.objects if o.type=="EMPTY"},
 "axes":"Blender Z up, front -Y, meters; 2.8 m source height retained"}
np.savez_compressed(OUT/"Work/rig_input.npz",**arrays)
(OUT/"Work/rig_input.json").write_text(json.dumps(meta,indent=2),encoding="utf8")
print("RIG_INPUT_SAVED",len(parts),sum(p["vertices"] for p in parts),flush=True)
