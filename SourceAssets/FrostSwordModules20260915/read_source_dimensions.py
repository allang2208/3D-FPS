"""Read authoring dimensions and source texture boundaries; no render."""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'MeleeGuards20260915/OriginalGuardReference.blend'))
o=bpy.data.objects['FrostCrystalSword_Blade'];m=o.data
img=next(n.image for n in m.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and not any(s in n.image.name for s in ['normal','metallic','roughness']))
pix=np.empty(len(img.pixels),dtype=np.float32);img.pixels.foreach_get(pix);pix=pix.reshape(img.size[1],img.size[0],4)
uv=m.uv_layers[0].data
rows=[]
for f in m.polygons:
    p=f.center
    if -.31<p.z<.07:
        c=np.mean([pix[min(img.size[1]-1,int(uv[i].uv.y*img.size[1])),min(img.size[0]-1,int(uv[i].uv.x*img.size[0])),:3] for i in f.loop_indices],axis=0)
        rows.append({'p':list(p),'blue':bool(c[2]>c[0]*1.15 and c[1]>c[0]*1.1),'rgb':c.tolist()})
out={'bounds':[[min(v.co[i] for v in m.vertices),max(v.co[i] for v in m.vertices)] for i in range(3)],'slices':[],'blue_edge':[]}
for z in np.arange(-.31,.071,.01):
    vs=[v.co for v in m.vertices if z<=v.co.z<z+.01]
    if vs:out['slices'].append({'z':round(float(z),3),'x':[min(v.x for v in vs),max(v.x for v in vs)],'y':[min(v.y for v in vs),max(v.y for v in vs)]})
for x in np.arange(0,.081,.005):
    ps=[r['p'] for r in rows if r['blue'] and x<=abs(r['p'][0])<x+.005]
    if ps:out['blue_edge'].append({'x':round(float(x),3),'z_min':min(p[2] for p in ps),'z_max':max(p[2] for p in ps)})
(P/'source_dimensions.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
