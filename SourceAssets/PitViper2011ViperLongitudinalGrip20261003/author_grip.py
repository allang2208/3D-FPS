"""Author full-height Viper side skins in the unchanged native weapon frame."""
import json,math,sys,subprocess,shutil
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[1];SOURCE=O.parent/'PitViper2011Integration20261002'
OLD=O.parent/'PitViper2011VipGrip20261002';PRIOR=O.parent/'PitViper2011GripRebuild20261003'
NAME='SM_PitViper2011_VipViperGrip';D='/Game/Weapons/PitViper2011/VipGrip20261002'
sys.path.insert(0,str(P/'Tools/Weapons'));sys.path.insert(0,str(O))
from pit_viper_longitudinal_grip import LongitudinalPalmPanel,palm_limits,palm_lower_boundary
from surface_recipe import scale_fields
for folder in ('Exports','Textures','Icons'):(O/folder).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Single/PitViper2011_single_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
root=bpy.data.objects['SK_PitViper2011_Manny'].data.bones['WPN_root'].matrix_local.copy()
alignment=Matrix(json.loads((SOURCE/'Single/authoring.json').read_text(encoding='utf8'))['alignment'])
parts=json.loads((SOURCE/'canonical_parts.json').read_text(encoding='utf8'));vertices=[];faces=[]
for part in parts:
    if part['identity']=='2011pv frame_12' and part['material']=='polymer':
        start=len(vertices);vertices.extend(alignment@Vector(v) for v in part['verts'])
        faces.extend(tuple(start+i for i in f) for f in part['faces'])
bvh=BVHTree.FromPolygons(vertices,faces);limits=palm_limits(parts)
lower_line=palm_lower_boundary(parts)
panels=[LongitudinalPalmPanel(bvh,alignment,root,side,limits,lower_line) for side in (-1,1)]
width=sum(p.atlas_width for p in panels)/2;height=sum(p.atlas_height for p in panels)/2
print('VIP_LONGITUDINAL_NATIVE_SPAN',limits,'atlas_width_height_m',width,height,flush=True)
subprocess.run(['py','-3.11',str(O/'produce_textures.py'),'--width',str(width),'--height',str(height)],check=True)
recipe=json.loads((O/'texture_recipe.json').read_text(encoding='utf8'))
for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
surface=bpy.data.materials.new('M_PitViper2011_VipViperGrip');surface.use_nodes=True
bs=next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for kind in ('BaseColor','Normal','ORM'):
    im=bpy.data.images.load(recipe['private'][kind]);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    tx=surface.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im
    if kind=='BaseColor':surface.node_tree.links.new(tx.outputs[0],bs.inputs['Base Color'])
    elif kind=='Normal':
        nm=surface.node_tree.nodes.new('ShaderNodeNormalMap');nm.uv_map='UV0'
        surface.node_tree.links.new(tx.outputs[0],nm.inputs['Color']);surface.node_tree.links.new(nm.outputs[0],bs.inputs['Normal'])
    else:
        sep=surface.node_tree.nodes.new('ShaderNodeSeparateColor');surface.node_tree.links.new(tx.outputs[0],sep.inputs[0])
        surface.node_tree.links.new(sep.outputs[1],bs.inputs['Roughness']);surface.node_tree.links.new(sep.outputs[2],bs.inputs['Metallic'])
gold=bpy.data.materials.new('MI_PitViper2011_VipChampagne');gold.use_nodes=True
gbs=next(n for n in gold.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
gbs.inputs['Base Color'].default_value=(.19,.145,.090,1);gbs.inputs['Metallic'].default_value=1;gbs.inputs['Roughness'].default_value=.38
V=[];F=[];UV=[];M=[]
for panel in panels:
    side=panel.side
    def relief(u,v):
        b,l,_,_=scale_fields(u,v,width,height);return b*.000025+l*.000015
    vs,fs,uv=panel.geometry(atlas=True,relief=relief)
    base=len(V);V.extend(vs);F.extend(tuple(base+i for i in f) for f in fs);UV.extend(uv);M.extend([0]*len(fs))
    def polygon(points,offset=.00039):
        base=len(V)
        for u,v in points:V.append(panel.location(u,v,offset));UV.append((u,1-v))
        face=tuple(base+i for i in range(len(points)));F.append(face[::-1] if side>0 else face);M.append(1)
    def ribbon(path,line_width=.00014):
        for (u0,v0),(u1,v1) in zip(path,path[1:]):
            du,dv=(u1-u0)*width,(v1-v0)*height;length=math.hypot(du,dv)
            if length<1e-7:continue
            su,sv=-dv/length*line_width/width/2,du/length*line_width/height/2
            steps=max(2,int(length/.00040))
            for j in range(steps):
                a,b=j/steps,(j+1)/steps;ua,va=u0+(u1-u0)*a,v0+(v1-v0)*a;ub,vb=u0+(u1-u0)*b,v0+(v1-v0)*b
                polygon([(ua-su,va-sv),(ub-su,vb-sv),(ub+su,vb+sv),(ua+su,va+sv)])
    # These paths use the fitted skin coordinates: their lower edge follows
    # the native magwell shoulder, not a short rectangular sticker boundary.
    ribbon([(.028,.023),(.972,.023),(.972,.977),(.028,.977),(.028,.023)])
    cx,cy=.78,.82;sx=.046/width;sy=.042/height
    shield=[(-.054,-.071),(.054,-.071),(.045,-.022),(0,.075),(-.045,-.022),(-.054,-.071)]
    ribbon([(cx+a*sx,cy+b*sy) for a,b in shield],line_width=.00016)
    glyph=[
        [(-.034,-.048),(.034,-.048),(.027,-.023),(0,-.014),(-.027,-.023)],
        [(-.034,-.035),(-.030,-.006),(-.010,.018),(-.016,-.014),(-.027,-.025)],
        [(.034,-.035),(.027,-.025),(.016,-.014),(.010,.018),(.030,-.006)],
        [(-.010,-.002),(0,.009),(.010,-.002),(0,.026)],
        [(-.012,.001),(-.010,.042),(-.003,.018)],[(.012,.001),(.003,.018),(.010,.042)]]
    for points in glyph:polygon([(cx+a*sx,cy+b*sy) for a,b in points],offset=.00040)
data=bpy.data.meshes.new(NAME);data.from_pydata(V,[],F);data.update();data.materials.append(surface);data.materials.append(gold)
for face,index in zip(data.polygons,M):face.material_index=index;face.use_smooth=True
inv=root.inverted()
for face in data.polygons:
    if face.material_index==1 and (inv.to_3x3()@face.normal).x*(inv@face.center).x<0:face.flip()
layer=data.uv_layers.new(name='UV0')
for face in data.polygons:
    for li in face.loop_indices:layer.data[li].uv=UV[data.loops[li].vertex_index]
for channel in (1,2,3):
    layer=data.uv_layers.new(name='UV'+str(channel))
    for face in data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in face.loop_indices:
            point=data.vertices[data.loops[li].vertex_index].co;layer.data[li].uv=(point[axes[0]]/.1,point[axes[1]]/.1)
ob=bpy.data.objects.new(NAME,data);bpy.context.collection.objects.link(ob)
ob['design']='Left and right longitudinal grip-body skins; stop above lower flare and magazine interface'
ob['part']='pit_viper_vip_scales';ob['native_frame']='WPN_root component reference; unchanged from existing integration'
refs=bpy.data.collections.new('REFERENCE_NativeGrip');bpy.context.scene.collection.children.link(refs)
for part in parts:
    if part['identity']!='2011pv frame_12':continue
    reference=bpy.data.meshes.new('Reference_'+part['material'])
    reference.from_pydata([root@(alignment@Vector(v)) for v in part['verts']],[],part['faces']);reference.update()
    ref=bpy.data.objects.new(reference.name,reference);refs.objects.link(ref);ref.hide_render=True;ref.hide_set(True)
    ref['reference_only']=True
bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
fbx=O/'Exports'/(NAME+'.fbx');blend=O/'Exports'/(NAME+'_Editable.blend')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(blend))
auth={'name':NAME,'fbx':str(fbx),'blend':str(blend),'fits':[p.record() for p in panels],
    'triangles':sum(len(f.vertices)-2 for f in data.polygons),'frame':'native skeletal component reference; inverse WPN_root bind chain at runtime',
    'bone':'WPN_root','mesh':D+'/'+NAME,'textures':recipe['legacy'],'quiet_textures':recipe['private'],
    'materials':{'surface':D+'/Materials/M_PitViper2011_VipViperGrip','metal':D+'/Materials/MI_PitViper2011_VipChampagne'},
    'active_surface':'/Game/Weapons/PitViper2011/SurfaceRefine20261003/Materials/M_PV2011_ViperQuiet',
    'texture_resolution':2048,'reference':str(O/'Reference/viper-vip-grip-concept.png'),'source':str(SOURCE/'canonical_parts.json'),
    'revision':'longitudinal_grip_20261003','atlas_width_m':width,'atlas_height_m':height,
    'design':'Two native-shaped lateral grip-body skins. Longitudinal, downward scale flow. Stop above the lower flare and magazine interface; magazine, magwell, upper frame and raised latch remain separate and exposed.',
    'provenance':'Original longitudinal snake-scale surface and small bronze inlay; native grip interface derived from Low Poly TTI JW4 Pit Viper 2011 by D_U, original integration records CC BY 4.0; https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153',
    'game_tested':False,'acceptance_rendered':False}
(O/'authoring.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
(OLD/'authoring.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
record=json.loads((PRIOR/'authoring.json').read_text(encoding='utf8'));record['vip']=auth
(PRIOR/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_GRIP_AUTHORED_AND_EXPORTED',auth['triangles'],flush=True)
