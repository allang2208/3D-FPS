"""Preserve the V12 authored crown and its native assembly interfaces."""
import bpy, json, shutil, hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
S=P.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'GuanLei_V12_Editable.blend'))
source=json.loads((S/'model_manifest.json').read_text(encoding='utf-8'))
mesh=bpy.data.objects[source['mesh']]
used={p.material_index for p in mesh.data.polygons}
rows=[]
for i,slot in enumerate(mesh.material_slots):
    if i not in used: continue
    mat=slot.material
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    images={n.image.name:bpy.path.abspath(n.image.filepath) for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    row=dict(slot=mat.name,images=images)
    if mat.name=='M_OriginalHammer_ContextPBR':
        row.update(kind='native',tint=[.3,.29,.27],normal_strength=.65)
    elif mat.name.endswith('ThunderInlay'):
        row.update(kind='constant',base=list(bs.inputs['Base Color'].default_value)[:3],
            metallic=float(bs.inputs['Metallic'].default_value),roughness=float(bs.inputs['Roughness'].default_value),
            emission=[c*bs.inputs['Emission Strength'].default_value for c in list(bs.inputs['Emission Color'].default_value)[:3]])
    elif mat.name.startswith(('M_GuanLei12_','M_GuanLei11_')):
        family=mat.name.split('_',2)[2]
        row.update(kind='pbr',family='Steel' if family=='BurnishedEdge' else family,tint=[1.35]*3 if family=='BurnishedEdge' else [1.]*3,normal_strength=.8)
        if row['family'] not in ('Steel','Silver','Recess','Inlay'):raise RuntimeError('Unmapped material '+mat.name)
    else:raise RuntimeError('Unmapped material '+mat.name)
    rows.append(row)
(P/'Export').mkdir(exist_ok=True)
fbx=S/'Export'/(source['mesh']+'.fbx');out=P/'Export'/fbx.name
shutil.copy2(fbx,out)
recipe=dict(revision='GuanLeiClosedCrownV12',mesh=source['mesh'],source_blend=str(S/'GuanLei_V12_Editable.blend'),fbx=str(out),
    fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),triangles=source['triangles'],materials=rows,
    geometry_policy='Authored crown and native interfaces preserved; Nanite source, full fidelity fallback matching JiLei V14 integration. No performance claim.',
    normal_convention='OpenGL source; flip green on UE import',runtime_tested=False)
(P/'runtime_manifest.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_V12_RUNTIME_PREPARED',len(rows),source['triangles'],flush=True)
