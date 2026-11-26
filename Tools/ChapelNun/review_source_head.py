import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME'); O=P/'SourceAssets/ChapelNun20261115/HeadQualityR2'
O.mkdir(parents=True,exist_ok=True)
after='--after' in sys.argv
path=O/'Authored/Nun_Head_Hair_R2.blend' if after else P/'SourceAssets/ChapelNun20261115/ProductionR1/Authored/Nun_Head_Hair.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
head=bpy.data.objects['SK_NunHead']
mat=head.data.materials[0]; nt=mat.node_tree; shader=nt.nodes.get('Principled BSDF')
source=P/'SourceAssets/ChapelNun20261115/MeshyHeadR1/Source'
normal=nt.nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(source/'NunHead_R1_M00_normal.png'));normal.image.colorspace_settings.name='Non-Color'
nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(normal.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],shader.inputs['Normal'])
rough=nt.nodes.new('ShaderNodeTexImage');rough.image=bpy.data.images.load(str(source/'NunHead_R1_M00_roughness.png'));rough.image.colorspace_settings.name='Non-Color';nt.links.new(rough.outputs['Color'],shader.inputs['Roughness'])
shader.inputs['Subsurface Weight'].default_value=.06
hair=bpy.data.materials.new('ReviewBlackHair');hair.diffuse_color=(.009,.008,.007,1);hair.use_nodes=True
hs=next((n for n in hair.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or hair.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
out=next((n for n in hair.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or hair.node_tree.nodes.new('ShaderNodeOutputMaterial')
hair.node_tree.links.new(hs.outputs['BSDF'],out.inputs['Surface']);hs.inputs['Base Color'].default_value=(.009,.008,.007,1);hs.inputs['Roughness'].default_value=.46
for obj in bpy.data.objects:
    if obj.type=='CURVE':
        obj.data.bevel_depth=1.;obj.data.bevel_resolution=0;obj.data.resolution_u=1;obj.data.materials.clear();obj.data.materials.append(hair)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=840;scene.render.resolution_y=840;scene.render.resolution_percentage=100
if not scene.world: scene.world=bpy.data.worlds.new('ReviewWorld')
scene.world.color=(.18,.18,.18);scene.view_settings.view_transform='AgX'
def area(name,location,energy,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,1,158))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-35,45,195),85000,40);area('Fill',(40,15,170),35000,35);area('Rim',(0,-30,185),65000,25)
cam=bpy.data.cameras.new('ReviewCamera');ob=bpy.data.objects.new('ReviewCamera',cam);scene.collection.objects.link(ob);scene.camera=ob;cam.type='ORTHO';cam.ortho_scale=34;cam.clip_end=1000
for name,pos,target in [('front',(0,70,160),(0,0,155)),('threequarter',(45,55,174),(0,0,157)),('crown',(0,25,212),(0,0,162))]:
    ob.location=pos;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(O/(('after_' if after else 'before_')+name+'.png'));bpy.ops.render.render(write_still=True)
    if '--front-only' in sys.argv:break
print('SOURCE_REVIEW_COMPLETE',flush=True)
