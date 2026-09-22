from pathlib import Path
import bpy,json,shutil
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('D:/FPS3D/VaultCache/FabLibrary/Ultimate_Garage_Tools_Pack__10_Items__-_Game_Ready__FREE_-eba94efa/blender')
shutil.copy2(SOURCE/'hand_tools_set.blend',ROOT/'Sources/PublisherHandTools.blend')
shutil.copy2(SOURCE/'metadata',ROOT/'Sources/fab-blender-metadata.json')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Sources/PublisherHandTools.blend'))
dest=ROOT/'Sources/Textures';dest.mkdir(exist_ok=True)
images=[]
for im in bpy.data.images:
    if im.type!='IMAGE' or im.size[0]==0:continue
    name=Path(im.name).stem.replace(' ','_')+'.png'
    im.filepath_raw=str(dest/name);im.file_format='PNG';im.save()
    images.append(dict(name=im.name,path=str(dest/name),size=list(im.size),colorspace=im.colorspace_settings.name))
materials=[]
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    materials.append(dict(name=mat.name,nodes=[dict(name=n.name,type=n.type,
        image=n.image.name if n.type=='TEX_IMAGE' and n.image else None,
        operation=getattr(n,'operation',None)) for n in mat.node_tree.nodes],
        links=[dict(source=l.from_node.name,output=l.from_socket.name,target=l.to_node.name,input=l.to_socket.name) for l in mat.node_tree.links]))
groups=[]
for group in bpy.data.node_groups:
    groups.append(dict(name=group.name,nodes=[dict(name=n.name,type=n.type,image=n.image.name if n.type=='TEX_IMAGE' and n.image else None,attribute=getattr(n,'attribute_name',None)) for n in group.nodes],links=[dict(source=l.from_node.name,output=l.from_socket.name,target=l.to_node.name,input=l.to_socket.name) for l in group.links]))
attributes=[]
for ob in bpy.data.objects:
    if ob.type=='MESH':attributes.append(dict(name=ob.name,attributes=[dict(name=a.name,type=a.data_type,domain=a.domain) for a in ob.data.attributes]))
result=dict(images=images,materials=materials,groups=groups,attributes=attributes,objects=[dict(name=o.name,type=o.type) for o in bpy.data.objects])
(ROOT/'Receipts/atlas-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('FAB_ATLAS_INPUTS '+json.dumps(result))
