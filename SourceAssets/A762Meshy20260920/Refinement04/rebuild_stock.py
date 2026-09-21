"""Rebuild the A762 butt-end joint in the existing fitted game frame.

Complete connected rod shoulders and a clean metal/rubber tail assembly replace
the remaining generated end geometry. No renders or game tests are run.
"""
import ast,bpy,bmesh,json,math,shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;D=O/'Exports';D.mkdir(exist_ok=True)
previous=O.parent/'Refinement03';meta=json.loads((O.parent/'Integration/authoring.json').read_text(encoding='utf-8'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(previous/'A762_ADS_Surfaces_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
cx=.00056;new=[];body=[];magazines=[];sights={'RearSight':[],'FrontSight':[]}
archive=bpy.data.collections.new('A762_BEFORE_STOCK_JOINT_04');s.collection.children.link(archive)
made=bpy.data.collections.new('A762_STOCK_JOINT_04');s.collection.children.link(made)
report={'source':'Refinement03/A762_ADS_Surfaces_Editable.blend','new_parts':{},'materials':{},'changes':{},'tests_run':False,'renders_run':False}
funcs={'select','regions','bind','primitive','extrude','box','lathe','tube','pin','rounded_rect','loop_prism'}
tree=ast.parse((O.parent/'Refinement02/rebuild.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in funcs],type_ignores=[]),str(O.parent/'Refinement02/rebuild.py'),'exec'),globals())
mats={'SightInner':bpy.data.materials['M_A762_SightInner']}
(O/'Textures').mkdir(exist_ok=True);shutil.copy2(previous/'Textures/T_A762_RebuiltFinish.png',O/'Textures/T_A762_RebuiltFinish.png')
image=bpy.data.images['T_A762_RebuiltFinish']
recipes={
 'FactoryStock_Metal04':((.021,.028,.039),.86,.33,.018),
 'FactoryStock_Rubber04':((.006,.008,.010),0,.72,.025),
 'FactoryStock_Seam04':((.004,.006,.008),0,.64,.012),
}
for key,(col,metal,rough,variation) in recipes.items():
    mat=bpy.data.materials.new('M_A762_'+key);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal
    uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap';tx=n.new('ShaderNodeTexImage');tx.image=image;l.new(uv.outputs[0],tx.inputs[0])
    scale=n.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=variation;l.new(tx.outputs['Color'],scale.inputs[0])
    add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=rough-variation/2;l.new(scale.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs['Roughness'])
    mats[key]=mat;report['materials'][mat.name]={'base_color_linear':col,'metallic':metal,'roughness_center':rough,'roughness_variation':variation,'finish_texture':'Textures/T_A762_RebuiltFinish.png'}
mats['SightInner']=mats['FactoryStock_Seam04']

def hide_old(ob):
    ob.name+='_Before04'
    for c in list(ob.users_collection):c.objects.unlink(ob)
    archive.objects.link(ob);ob.hide_set(True);ob.hide_render=True
for collection in ['A762_REFINED_GEOMETRY','A762_RECONSTRUCTED_02','A762_CLOSED_SURFACES_03']:
    for ob in list(bpy.data.collections[collection].objects):
        if ob.type!='MESH':continue
        if ob.name in ['A762_FactoryStock','A762_Stock_UpperTube','A762_Stock_LowerTube']:
            hide_old(ob)
        elif not ob.name.startswith('SM_A762_'):body.append(ob)

metal='FactoryStock_Metal04';rubber='FactoryStock_Rubber04';seam='FactoryStock_Seam04'

def solid_round_profile(name,z,profile):
    """One continuous wall from the original rod to its flared tail shoulder."""
    n=96;v=[];f=[]
    for y,radius in profile:
        for i in range(n):
            a=math.tau*i/n;v.append((cx+radius*math.cos(a),y,z+radius*math.sin(a)))
    for j in range(len(profile)-1):f.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
    f.extend([tuple(range(n-1,-1,-1)),tuple(range((len(profile)-1)*n,len(profile)*n))])
    return primitive(name,v,f,metal,0)

# Original tube centers/radii and receiver-side seats are preserved. The tail
# shoulders are part of the same mesh wall, not floating collars on open rods.
solid_round_profile('A762_R04_StockUpperRod_Joined',.074,[
    (.113,.00445),(.114,.00460),(.273,.00460),(.277,.00460),
    (.279,.00475),(.280,.00520),(.281,.00610),(.2822,.00665),
    (.284,.0069),(.293,.0069),(.295,.00710),(.299,.00735),(.314,.00735)])
solid_round_profile('A762_R04_StockLowerRod_Joined',.042,[
    (.113,.00405),(.114,.00420),(.272,.00420),(.276,.00420),
    (.278,.00440),(.279,.00490),(.2805,.00590),(.282,.00660),
    (.285,.00690),(.293,.00740),(.298,.00830),(.314,.00830)])

def cubic_samples(knots,x):
    """Monotone cubic profiles keep smooth tails without overshooting the outline."""
    a=np.asarray(knots,dtype=float);t=a[:,0];q=a[:,1:];h=np.diff(t);d=np.diff(q,axis=0)/h[:,None]
    m=np.zeros_like(q);m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(t)-1):
        same=d[i-1]*d[i]>0
        w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
        m[i,same]=(w1+w2)/(w1/d[i-1,same]+w2/d[i,same])
    i=min(max(int(np.searchsorted(t,x))-1,0),len(t)-2);u=(x-t[i])/h[i]
    return (2*u**3-3*u*u+1)*q[i]+(u**3-2*u*u+u)*h[i]*m[i]+(-2*u**3+3*u*u)*q[i+1]+(u**3-u*u)*h[i]*m[i+1]

# Profiles are taken from the existing tail: broad rounded heel at the top,
# narrow lower toe, shallow curved rear face. They remain inside its envelope.
knots=[
 (-.0460,.0016,.0020,.3180),(-.0440,.0070,.0038,.3186),
 (-.0400,.0102,.0046,.3188),(-.0320,.0112,.0046,.3191),
 (-.0150,.0115,.0046,.3168),(.0040,.0115,.0046,.3161),
 (.0240,.0117,.0046,.3167),(.0440,.0133,.0046,.3191),
 (.0610,.0147,.0046,.3205),(.0700,.0139,.0046,.3206),
 (.0770,.0109,.0040,.3204),(.0805,.0061,.0030,.3198),
 (.0820,.0015,.0016,.3190)]

def contour(hw,hd):
    base=rounded_rect(hw,hd,min(.0018,hw*.45,hd*.55),8);out=[]
    for i,(a,b) in enumerate(zip(base,base[1:]+base[:1])):
        # Fixed subdivision of every segment keeps all rings compatible.
        for t in ([0,.25,.5,.75] if i%8==7 else [0]):out.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
    return out

def pad_layer(name,key,yoffset=0,width_offset=0,depth_scale=1,ribbed=False):
    zs=np.unique(np.r_[np.linspace(-.046,.082,321 if ribbed else 81),[a[0] for a in knots]])
    v=[];f=[];n=len(contour(.01,.004))
    for z in zs:
        hw,hd,y=cubic_samples(knots,float(z));hw=max(.0008,hw+width_offset);hd=max(.0006,hd*depth_scale)
        for x,dy in contour(hw,hd):
            if ribbed:
                # Actual low rubber ribs on a fully backed, continuous surface.
                phase=(float(z)+.041)/.0062
                rib=(.5+.5*math.cos(math.tau*phase))**4
                edge=max(0,min(1,(1-abs(x)/hw)/.18))
                face=max(0,min(1,(dy/hd-.72)/.28))
                ends=max(0,min(1,(float(z)+.043)/.007,(.078-float(z))/.007))
                dy+=.00065*rib*edge*face*ends
            v.append((cx+x,float(y+yoffset+dy),float(z)))
    for j in range(len(zs)-1):f.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
    f.extend([tuple(range(n-1,-1,-1)),tuple(range((len(zs)-1)*n,len(zs)*n))])
    return primitive(name,v,f,key,0)

pad_layer('A762_R04_Buttpad_ContinuousRubber',rubber,ribbed=True)
pad_layer('A762_R04_Buttplate_MetalBacking',metal,yoffset=-.0064,width_offset=-.0010,depth_scale=.57)
# This narrow, backed interface is a material seam, never an open slot.
pad_layer('A762_R04_Buttpad_SeatedGasket',seam,yoffset=-.0049,width_offset=-.00035,depth_scale=.17)

# Closed metal web joins both cylinder shoulders directly to the curved plate.
# Its triangular lower silhouette and original width are preserved.
outline=[(.3110,.0790),(.2990,.0788),(.2910,.0765),(.2860,.0710),
         (.2860,.0500),(.2825,.0320),(.2730,.0030),(.2700,-.0100),
         (.2725,-.0170),(.2950,-.0380),(.3090,-.0430),(.3140,-.0390),
         (.3133,-.0150),(.3105,.0080),(.3130,.0430),(.3160,.0690)]
extrude('A762_R04_StockTail_ClosedSupport',outline,cx-.0097,cx+.0097,axis=0,key=metal,bevel=.00070)
# Rounded shoulder pads fill the rod-to-web intersections on both sides.
for z,y,rad in [(.074,.296,.0072),(.042,.294,.0082)]:
    for side in [-1,1]:
        pin('A762_R04_StockTail_Fastener_'+str(z)+'_'+str(side),(cx+side*.00965,y,z),.0021,metal)
for side in [-1,1]:
    pin('A762_R04_StockTail_WebPin_'+str(side),(cx+side*.0098,.286,-.008),.0027,metal)

for ob in new:bind(ob)
body.extend(new)
report['changes']={
 'tail_geometry':'Replace the remaining generated butt-end mesh; continuous rods include the chamfered flare/shoulder, complete support web, curved backing plate and seated rubber pad.',
 'outline':'Retain fitted rod centers (.074/.042), shaft radii, stock length and the broad upper/narrow lower tail outline.',
 'materials':'Dedicated factory-stock metal/rubber/seam finishes with independent UVs and geometric normals; no source atlas on new shapes.',
 'preserved':'Receiver-side sockets, rest skeleton, mechanical groups, all 11 A762 animations, both sights, magazine and AKM audio.'}
report['expected_materials']=sorted({mat.name for ob in body+[hands] for mat in ob.data.materials if mat})
paths={}
for rev in ['Refinement01','Refinement02','Refinement03']:
    auth=json.loads((O.parent/rev/'authoring.json').read_text(encoding='utf-8'))
    for name in auth['materials']:paths[name]='/Game/Weapons/A762/'+rev+'/Materials/'+name
report['inherited_material_paths']={name:paths[name] for name in report['expected_materials'] if name in paths}
r.data.pose_position='REST';bpy.context.view_layer.update()
select(body+[hands,r]);bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update();archive.hide_viewport=True;archive.hide_render=True
for name in ['SM_A762_FrontSight.fbx','SM_A762_RearSight.fbx']:shutil.copy2(previous/'Exports'/name,D/name)
report['editable']='A762_StockJoint_Editable.blend'
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_StockJoint_Editable.blend'))
print('A762_STOCKJOINT04_AUTHORED',flush=True)
