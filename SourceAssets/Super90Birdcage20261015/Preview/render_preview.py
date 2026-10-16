"""Render the installed mesh exports using the runtime mounting frame."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
R=json.loads((O/'capture.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
s.render.engine='CYCLES';s.cycles.samples=80;s.cycles.use_denoising=True
s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.view_settings.view_transform='AgX';s.view_settings.exposure=0

def material(name,color,rough=.4,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nodes=m.node_tree.nodes;nodes.clear()
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*color[:3],1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m,bs

def image_node(m,path,color=False):
    spec=R['textures'].get(path)
    if not spec:return None
    im=bpy.data.images.load(spec['file'],check_existing=True)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'
    node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=im
    return node

materials={}
for path,spec in R['materials'].items():
    p=spec['scalars'];v=spec['vectors'];t=spec['textures']
    if 'FinishColor' not in v:continue
    color=v.get('FinishColor',(.035,.036,.038,1))
    m,bs=material(spec['name']+'_Preview',color,p.get('Roughness',.42),p.get('Metallic',1))
    materials[spec['name']]=m
    weight=p.get('SourceColorWeight',0)
    source=t.get('SourceBaseColor') or t.get('SourceColor')
    if weight and source:
        node=image_node(m,source,True)
        if node:
            mix=m.node_tree.nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=weight
            mix.inputs[1].default_value=(*color[:3],1)
            m.node_tree.links.new(node.outputs['Color'],mix.inputs[2])
            m.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
    source=t.get('SurfaceNormal')
    # The engine placeholder is a brick normal, not an authored flat input.
    # Preserve actual source detail normals and the birdcage's saved flat normal.
    if source and '/Engine/EngineMaterials/DefaultNormal' not in source:
        node=image_node(m,source)
        if node:
            normal=m.node_tree.nodes.new('ShaderNodeNormalMap')
            m.node_tree.links.new(node.outputs['Color'],normal.inputs['Color'])
            m.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])

def imported(key):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=R['assets'][key]['fbx'],use_anim=False)
    created=set(bpy.data.objects)-before;meshes=[]
    for obj in created:
        if obj.type!='MESH':continue
        obj.data.transform(obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
        obj.modifiers.clear()
        if key=='super90':
            normals=[n.vector.copy() for n in obj.data.corner_normals]
            attr=obj.data.attributes.new('PreviewSourceNormal','FLOAT_VECTOR','CORNER')
            for value,normal in zip(attr.data,normals):value.vector=normal
            bm=bmesh.new();bm.from_mesh(obj.data)
            remove=[]
            for face in bm.faces:
                index=face.material_index
                name=obj.data.materials[index].name if index<len(obj.data.materials) else ''
                if any(word.lower() in name.lower() for word in ('Skin','Manny','BarePalm','Sleeve','Glove')):
                    remove.append(face)
                elif name=='M_S90_12gauge' or name.startswith('M_S90_12gauge.'):
                    remove.append(face)
            bmesh.ops.delete(bm,geom=remove,context='FACES')
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
            bm.to_mesh(obj.data);bm.free()
            attr=obj.data.attributes.get('PreviewSourceNormal')
            normals=[tuple(value.vector.normalized()) for value in attr.data]
            for face in obj.data.polygons:face.use_smooth=True
            obj.data.normals_split_custom_set(normals)
        for slot in obj.material_slots:
            name=slot.material.name if slot.material else ''
            base=next((n for n in materials if name==n or name.startswith(n+'.') or name.startswith(n+'_')),None)
            if base:slot.material=materials[base]
        meshes.append(obj)
    for obj in created:
        if obj.type!='MESH':bpy.data.objects.remove(obj,do_unlink=True)
    return meshes

gun=imported('super90')
birdcage=imported('birdcage')
# Runtime UE frame is (0,-49.9307,-74.43155) cm, forward -Y, up +Z.
# FBX export is mapped back into Blender using (x,-y,z)/100 exactly once.
seat=Matrix(((0,-1,0,0),(1,0,0,.499307),(0,0,1,-.7443155),(0,0,0,1)))
for obj in birdcage:obj.matrix_world=seat
all_meshes=gun+birdcage
points=[obj.matrix_world@v.co for obj in all_meshes for v in obj.data.vertices]
lo=Vector([min(p[i] for p in points) for i in range(3)])
hi=Vector([max(p[i] for p in points) for i in range(3)])
center=(lo+hi)*.5

floor,bs=material('Neutral studio ground',(.5,.51,.53),.78,0)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,lo.z-.035))
bpy.context.object.name='PreviewGround';bpy.context.object.data.materials.append(floor)
s.world=bpy.data.worlds.new('Neutral studio');s.world.use_nodes=True
nodes=s.world.node_tree.nodes;nodes.clear()
bg=nodes.new('ShaderNodeBackground');out=nodes.new('ShaderNodeOutputWorld')
bg.inputs['Color'].default_value=(.33,.36,.4,1);bg.inputs['Strength'].default_value=.3
s.world.node_tree.links.new(bg.outputs[0],out.inputs['Surface'])
for name,loc,energy,size in [('Large key',(1.2,-.3,1.1),150,1.7),
                             ('Long rim',(-.8,.55,.6),114,1.4),
                             ('Front fill',(1.1,1.5,-.25),54,1.0)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);s.collection.objects.link(obj);obj.location=loc
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()

def camera(name,eye,target,width):
    data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=width;data.lens=70
    data.clip_start=.001;data.clip_end=100
    obj=bpy.data.objects.new(name,data);s.collection.objects.link(obj);obj.location=eye
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

overall=camera('Overall',center+Vector((2.8,.21,.18)),center,(hi.y-lo.y)*1.12)
close=camera('Muzzle_Junction',Vector((.8,.65,-.57)),Vector((0,.512,-.752)),.31)
shots=[(overall,'super90_birdcage_overall.png',2400,850),(close,'super90_birdcage_connection.png',2000,850)]
s.camera=overall
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Birdcage_AssemblyPreview.blend'))
for cam,filename,width,height in shots:
    s.camera=cam;s.render.resolution_x=width;s.render.resolution_y=height
    s.render.filepath=str(O/filename)
    bpy.ops.render.render(write_still=True)
receipt={'type':'Blender render of current exported game geometry',
         'source_assets':R['assets'],'mount_ue_cm':[0,-49.9307,-74.43155],
         'mount_blender':[list(row) for row in seat],
         'assembly_bounds_m':[list(lo),list(hi)],
         'images':[str(O/f) for _,f,_,_ in shots],
         'note':'Neutral studio light; WS1 base color, roughness and source normal approximation. Not an engine screenshot.',
         'game_assets_modified':False}
(O/'preview_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SUPER90_BIRDCAGE_PREVIEW_RENDERED',flush=True)
