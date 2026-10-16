import bpy,json
from pathlib import Path
root=Path(r'D:/FPS3D/FPSGAME/SourceAssets/PotionWorkbenchDesign20261015/ModelV1')
src=Path(r'D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchApproved20261006/Authored/GunWorkbench_GameReady.blend')
with bpy.data.libraries.load(str(src),link=False) as (a,b):
    b.materials=[n for n in a.materials if 'BenchWood' in n or 'EndGrain' in n]
record=[]
for m in b.materials:
    entry={'material':m.name,'nodes':[],'links':[]}
    if m.use_nodes:
        for n in m.node_tree.nodes:
            d={'name':n.name,'type':n.type}
            if n.type=='TEX_IMAGE' and n.image:
                im=n.image;name='Source_'+im.name.replace('/','_').replace('\\','_')
                if not name.lower().endswith(('.png','.jpg','.jpeg')): name+='.png'
                target=root/'Textures'/name
                im.filepath_raw=str(target);im.file_format='PNG' if target.suffix.lower()=='.png' else 'JPEG';im.save()
                d.update(image=im.name,file=str(target),colorspace=im.colorspace_settings.name)
            entry['nodes'].append(d)
        entry['links']=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]
    record.append(entry)
(root/'Receipts/source_materials.json').write_text(json.dumps(record,indent=2),'utf8')
print(json.dumps(record,indent=2),flush=True)
