"""Apply the two-view facial fit on the bound skeleton. Keep the collar boundary and all skin weights."""
from pathlib import Path
import bpy
import numpy as np

root=Path(__file__).resolve().parents[5]
home=root/'SourceAssets/HillsVillageStable'
out=home/'StablemasterLikenessR6'
bpy.ops.wm.open_mainfile(filepath=str(home/'StablemasterHeadR5/StablemasterNative.blend'))
bpy.context.preferences.filepaths.save_version=0
obj=bpy.data.objects['SK_Stablemaster_Head_R5'];mesh=obj.data;rig=obj.parent
base=np.load(home/'StablemasterHeadR5/HeadSurface.npz')['pos']
fit=np.load(out/'facial_fit.npz')
positions=np.empty_like(base);mesh.vertices.foreach_get('co',positions.ravel())
if not np.allclose(base,positions,atol=.0001):raise ValueError('Mesh and saved projection do not agree')
loops=np.zeros(len(mesh.loops),dtype='i');mesh.loops.foreach_get('vertex_index',loops)
old=np.empty((len(loops),3),'f');mesh.corner_normals.foreach_get('vector',old.ravel())
dest=fit['normal'][loops];weight=fit['weight'][loops,None]
# Keep hard normals on hidden backfaces of the thin hair/eyelid sheets.
weight*=np.clip(((-old[:,1])+0.08)/.43,0,1)[:,None]
result=old*(1-weight)+dest*weight
for field in ('side','hair'):
    n=fit[field+'_normal'][loops]
    w=fit[field+'_weight'][loops][:,None]
    if field=='side':
        # Avoid mixing the ear's inner fold with its back surface.
        w=w*np.clip(((n*old).sum(1)+.10)/.62,0,1)[:,None]
    result=result*(1-w)+n*w
result/=np.maximum(1e-8,np.linalg.norm(result,axis=1,keepdims=True))
mesh.vertices.foreach_set('co',fit['pos'].ravel());mesh.update()
mesh.normals_split_custom_set(result.tolist())
obj.name='SK_Stablemaster_FaceR6'
mat=bpy.data.materials.new('M_Stablemaster_FaceR6');mat.use_nodes=True;mesh.materials[0]=mat
nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
def image_node(role,space,x,y):
    img=bpy.data.images.load(str(out/('T_Stablemaster_FaceR6_'+role+'.png')),check_existing=False)
    img.colorspace_settings.name=space;img.pack()
    node=nt.nodes.new('ShaderNodeTexImage');node.image=img;node.location=(x,y);return node
def wire(n,s,m,t):nt.links.new(n.outputs[s],m.inputs[t])
color=image_node('Color','sRGB',-840,500);normal=image_node('Normal','Non-Color',-840,-300);props=image_node('Surface','Non-Color',-840,150)
wire(color,'Color',bs,'Base Color')
nm=nt.nodes.new('ShaderNodeNormalMap');nm.location=(-340,-270);wire(normal,'Color',nm,'Color');wire(nm,'Normal',bs,'Normal')
sep=nt.nodes.new('ShaderNodeSeparateColor');sep.location=(-300,150);wire(props,'Color',sep,'Color')
wire(sep,'Red',bs,'Subsurface Weight');wire(sep,'Green',bs,'Roughness');wire(sep,'Blue',bs,'Specular IOR Level')
bs.inputs['Subsurface Radius'].default_value=(.38,.18,.085)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(out/(obj.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,
    use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='Y',axis_up='Z',use_mesh_modifiers=False,mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'StablemasterFaceR6.blend'),compress=True)
