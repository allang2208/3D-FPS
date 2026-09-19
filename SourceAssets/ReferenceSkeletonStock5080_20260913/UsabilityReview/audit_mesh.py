"""Read-only candidate geometry/UV/texture inspection requested by the user."""
from pathlib import Path
import io, json, struct
import numpy as np
import trimesh
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'seed_91379/textured_master_00001_.glb'
data=SOURCE.read_bytes()
length,kind=struct.unpack_from('<II',data,12)
g=json.loads(data[20:20+length]);binary=data[28+length:]
m=trimesh.load(SOURCE,force='mesh',process=False)
diag=float(np.linalg.norm(m.extents))
report={'source':str(SOURCE),'file_bytes':len(data),'vertices':len(m.vertices),'triangles':len(m.faces),'bounds':m.bounds.tolist(),'extents':m.extents.tolist(),'finite_positions':bool(np.isfinite(m.vertices).all()),'finite_normals':bool(np.isfinite(m.vertex_normals).all()),'near_zero_area_triangles':int((m.area_faces < diag*diag*1e-14).sum()),'material_definitions':g.get('materials',[]),'textures':[]}
uv=np.array(m.visual.uv)
duv=uv[m.faces]
ua=duv[:,1]-duv[:,0];ub=duv[:,2]-duv[:,0]
uv_area=np.abs(ua[:,0]*ub[:,1]-ua[:,1]*ub[:,0])*.5
report['uv']={'vertices':len(uv),'finite':bool(np.isfinite(uv).all()),'outside_unit_square':int(np.any((uv<0)|(uv>1),axis=1).sum()),'zero_area_triangles':int((uv_area<1e-12).sum()),'summed_triangle_uv_area':float(uv_area.sum()),'normal_texture_present':any('normalTexture' in mat for mat in g.get('materials',[]))}
# Recombine coincident positions only in an in-memory copy: GLB UV seams can
# otherwise appear to be holes. Never save this copy as the delivered model.
w=m.copy();w.merge_vertices(merge_tex=True,merge_norm=True,digits_vertex=6)
edges,counts=np.unique(np.sort(w.edges,axis=1),axis=0,return_counts=True)
components=trimesh.graph.connected_components(w.face_adjacency,nodes=np.arange(len(w.faces)),min_len=1)
sizes=sorted((len(c) for c in components),reverse=True)
report['topology_position_weld_1e6']={'vertices':len(w.vertices),'boundary_edges':int((counts==1).sum()),'more_than_two_faces_edges':int((counts>2).sum()),'watertight':bool(w.is_watertight),'winding_consistent':bool(w.is_winding_consistent),'surface_components':len(sizes),'component_face_counts_largest20':sizes[:20],'euler_number':int(w.euler_number)}
for idx,im in enumerate(g.get('images',[])):
    view=g['bufferViews'][im['bufferView']];start=view.get('byteOffset',0)
    image=Image.open(io.BytesIO(binary[start:start+view['byteLength']]))
    arr=np.array(image)
    report['textures'].append({'image_index':idx,'size':list(image.size),'mode':image.mode,'decode_ok':True,'channel_percentiles_0_50_95_100':np.percentile(arr.reshape(-1,arr.shape[-1]),[0,50,95,100],axis=0).tolist()})
raw=trimesh.load(ROOT/'seed_91379/raw_00001_.glb',force='mesh',process=False)
report['raw']={'vertices':len(raw.vertices),'triangles':len(raw.faces),'extents':raw.extents.tolist(),'note':'Raw export includes its own 90-degree reorientation; not overlaid without registration.'}
(OUT/'mesh_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
