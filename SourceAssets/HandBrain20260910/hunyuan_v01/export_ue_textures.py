import bpy,json,numpy as np,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'delivery/HandBrain_Animated.blend'))
out=root/'delivery/textures';out.mkdir(exist_ok=True)
def find_image(socket,seen=None):
    seen=seen or set()
    for link in socket.links:
        node=link.from_node
        if node.name in seen:continue
        seen.add(node.name)
        if node.type=='TEX_IMAGE':return node.image
        for inp in node.inputs:
            found=find_image(inp,seen)
            if found:return found
    return None
manifest={}
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    bs=next(n for n in obj.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    maps={}
    for semantic,socket in [('BaseColor','Base Color'),('Normal_DirectX','Normal'),('Roughness','Roughness')]:
        src=find_image(bs.inputs[socket])
        if src is None:continue
        dst=src.copy();dst.name=obj.name+'_'+semantic
        data=np.empty(len(src.pixels),dtype=np.float32);src.pixels.foreach_get(data);pixels=data.reshape(-1,4)
        if semantic=='Normal_DirectX':pixels[:,1]=1-pixels[:,1]
        elif semantic=='Roughness':pixels[:,:3]=pixels[:,1,None]
        dst.pixels.foreach_set(data)
        dst.filepath_raw=str(out/(dst.name+'.png'));dst.file_format='PNG';dst.save()
        maps[semantic]={'file':'textures/'+dst.name+'.png','sRGB':semantic=='BaseColor'}
    maps['Metallic']=0
    manifest[obj.name]=maps
(root/'delivery/ue_materials.json').write_text(json.dumps(manifest,indent=2))
