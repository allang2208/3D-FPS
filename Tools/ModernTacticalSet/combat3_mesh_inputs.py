"""Read construction topology and local cloth RNA for the production author."""
import bpy,json,numpy as np
from pathlib import Path
S=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113')
for file in ['04_TacticalTrousers.blend','01_KevlarVest.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(S/'Models'/file))
    print(file,[(o.name,len(o.data.vertices),len(o.data.polygons),[m.name for m in o.data.materials]) for o in bpy.data.objects if o.type=='MESH'],flush=True)
for rig in ['Jason','Kaitlin']:
    d=json.loads((S/'CombatShirtR2/Authored'/f'shirt_detail_{rig}.json').read_text());p=np.array(d['positions']);f=np.array(d['triangles']);m=np.array(d['triangle_materials'])
    print(rig,[(slot,len(f[m==i]),np.min(p[np.unique(f[m==i])],0).tolist(),np.max(p[np.unique(f[m==i])],0).tolist()) for i,slot in enumerate(d['material_slots']) if (m==i).any()],flush=True)
ob=next(o for o in bpy.data.objects if o.type=='MESH');cloth=ob.modifiers.new('RNA_author_reference','CLOTH')
print('CLOTH_RNA',[(p.identifier,p.type) for p in cloth.settings.bl_rna.properties],flush=True)
