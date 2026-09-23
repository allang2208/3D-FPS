"""Retain the structural grid; relocate/rebuild its service pipe bank precisely."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
CFG=json.loads((ROOT/'Config/services.json').read_text())
BEFORE=json.loads((ROOT/'Sources/scene-before.json').read_text())
SRC=ROOT.parent/'DungeonAtmosphereV2_20260921/Authored/DungeonAtmosphereV2_Structure.blend'
BASE='/Game/Dungeons/AtmosphereV2/Services'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.0
names=['SM_V2_'+x+'_Ceiling' for x in ('MainCorridor','Dogleg','EndLanding','Workshop','MachineBay','ServiceRecess','RuinNiche')]+['SM_V2_CableTrays','SM_V2_HangingCables']
with bpy.data.libraries.load(str(SRC),link=False) as (src,dst):dst.objects=names
objects=[]
for ob in dst.objects:
    bpy.context.scene.collection.objects.link(ob)
    if ob.name.endswith('_Ceiling'):
        # Derive the intended underside from the captured level; idempotent even
        # after the base structure author has regenerated its corrected ceilings.
        row=next(a for a in BEFORE['actors'] if a['label']==ob.name.replace('SM_V2_','DGN_AV2_'))
        expected=row['components'][0]['local_max'][2]/100
        delta=expected-min(v.co.z for v in ob.data.vertices)
    else:delta=-CFG['tray_lowering_m']
    for v in ob.data.vertices:
        v.co.z+=delta
        if ob.name.endswith('HangingCables') and v.co.x<6:
            v.co.y+=.86 # attach to the tray side, clear of the relocated pipe bank
        if not ob.name.endswith('_Ceiling') and v.co.y>3:
            v.co.y-=.06 # north tray outer lip must clear the north pier's 3.71 m face
    old=ob.name;ob.name=old.replace('SM_V2_','SM_Services_')
    objects.append((ob,old))

def material(name,color,metallic=0,rough=.65):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metallic
    return mat
paint=material('Service_Paint',(.075,.085,.051));steel=material('Service_Hardware',(.12,.135,.14),.78,.48)
rubber=material('Service_Gasket',(.012,.015,.013),0,.91)
# The source uses the same texture and vertex-age blend as its Unreal counterpart.
nt=paint.node_tree;p=nt.nodes.get('Principled BSDF')
tex={}
for key in ('BaseColor','RustColor','AgeMask','Roughness','Metallic','Normal'):
    n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(OUT/'Textures'/('ServicePaint_'+key+'.png')))
    n.image.colorspace_settings.name='sRGB' if key in ('BaseColor','RustColor') else 'Non-Color';tex[key]=n
vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='ServiceAge'
sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(vc.outputs['Color'],sep.inputs['Color'])
mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';nt.links.new(tex['AgeMask'].outputs['Color'],mul.inputs[0]);nt.links.new(sep.outputs[0],mul.inputs[1])
mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mul.outputs[0],mix.inputs[0]);nt.links.new(tex['BaseColor'].outputs['Color'],mix.inputs[1]);nt.links.new(tex['RustColor'].outputs['Color'],mix.inputs[2]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
nr=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex['Normal'].outputs['Color'],nr.inputs['Color']);nt.links.new(nr.outputs[0],p.inputs['Normal'])
nt.links.new(tex['Roughness'].outputs['Color'],p.inputs['Roughness']);nt.links.new(tex['Metallic'].outputs['Color'],p.inputs['Metallic'])

V=[];F=[];MI=[];UV=[];AGE=[];SM=[]
def face(points,uvs,mat=0,ages=None,smooth=False):
    first=len(V);V.extend(points);F.append(tuple(range(first,first+len(points))))
    MI.append(mat);UV.append(uvs);AGE.append(ages or [0]*len(points));SM.append(smooth)
def box(center,size,mat=1):
    x,y,z=center;a,b,c=[v/2 for v in size]
    vs=[(x+px,y+py,z+pz) for px,py,pz in [(-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]]
    for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        ps=[vs[i] for i in ids];normal=(Vector(ps[1])-Vector(ps[0])).cross(Vector(ps[2])-Vector(ps[0]))
        axis=max(range(3),key=lambda i:abs(normal[i]));dims=[i for i in range(3) if i!=axis]
        face(ps,[(p[dims[0]]/.8,p[dims[1]]/.8) for p in ps],mat)
couplings=[1.25+3*i for i in range(7)]
def age(x,theta):
    contact=max([math.exp(-((x-c)/.065)**2) for c in couplings+CFG['pier_x_m']])
    underside=max(0,-math.sin(theta))
    return min(1,.12+.70*contact+.20*underside)
def tube_x(profile,y,z,mat=0,sides=64,closed=False):
    # Profile (x,r) may return to its starting point to create a hollow clamp.
    for (x0,r0),(x1,r1) in zip(profile,profile[1:]):
        for j in range(sides):
            a=j*math.tau/sides;b=(j+1)*math.tau/sides
            ps=[(x0,y+r0*math.cos(a),z+r0*math.sin(a)),(x0,y+r0*math.cos(b),z+r0*math.sin(b)),
                (x1,y+r1*math.cos(b),z+r1*math.sin(b)),(x1,y+r1*math.cos(a),z+r1*math.sin(a))]
            face(ps,[(x0/.8,a*r0/.8),(x0/.8,b*r0/.8),(x1/.8,b*r1/.8),(x1/.8,a*r1/.8)],mat,
                 [age(x0,a),age(x0,b),age(x1,b),age(x1,a)],smooth=abs(x1-x0)>.00001 and sides>8)
    if closed:
        for i,reverse in [(0,True),(-1,False)]:
            x,r=profile[i];ps=[(x,y+r*math.cos(j*math.tau/sides),z+r*math.sin(j*math.tau/sides)) for j in range(sides)]
            if reverse:ps.reverse()
            face(ps,[(p[1]/.8,p[2]/.8) for p in ps],mat)
for run in CFG['pipe_runs']:
    z,r=run['z'],run['radius'];y=CFG['pipe_center_y_m']
    stations=sorted(set([0,22]+[i*.25 for i in range(89)]+[round(c+d,5) for c in couplings+CFG['pier_x_m'] for d in (-.14,-.06,0,.06,.14)]))
    tube_x([(x,r) for x in stations],y,z,0,closed=True)
    for x in couplings:
        # Paired cast lips, recessed gasket, independent six-bolt fasteners.
        for s in (-1,1):
            a=x+s*.021
            profile=[(a-.018,r+.001),(a-.018,r*1.25),(a-.013,r*1.29),(a+.013,r*1.29),(a+.018,r*1.25),(a+.018,r+.001)]
            tube_x(profile,y,z,0)
            for j in range(6):
                t=j*math.tau/6+.12
                tube_x([(a-.025,.008),(a+.025,.008)],y+(r+.020)*math.cos(t),z+(r+.020)*math.sin(t),1,6,True)
        tube_x([(x-.004,r*1.245),(x+.004,r*1.245)],y,z,2)
    for x in CFG['pier_x_m']:
        tube_x([(x-.024,r+.001),(x-.024,r+.010),(x-.020,r+.013),(x+.020,r+.013),(x+.024,r+.010),(x+.024,r+.001),(x-.024,r+.001)],y,z,1)
        start=CFG['pier_front_y_m'];end=y-r-.007
        box((x,start+.008,z),(.12,.016,.235))
        box((x,(start+.016+end)/2,z),(.055,end-start-.016,.045))
        for dz in (-.087,.087):box((x,start+.021,z+dz),(.022,.012,.022))
mesh=bpy.data.meshes.new('ServiceBank');mesh.from_pydata(V,[],F);mesh.update()
for m in (paint,steel,rubber):mesh.materials.append(m)
uv=mesh.uv_layers.new(name='UVMap');col=mesh.color_attributes.new(name='ServiceAge',type='BYTE_COLOR',domain='CORNER')
for poly,mi,uvs,ages,sm in zip(mesh.polygons,MI,UV,AGE,SM):
    poly.material_index=mi;poly.use_smooth=sm
    for li,co,av in zip(poly.loop_indices,uvs,ages):uv.data[li].uv=co;col.data[li].color=(av,0,0,1)
ob=bpy.data.objects.new('SM_Services_ServicePipes',mesh);bpy.context.scene.collection.objects.link(ob)
# Coincident rings share side normals; caps/profile steps retain sharp split normals.
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
mod=ob.modifiers.new('Weld pipe surfaces','WELD');mod.merge_threshold=.000001;bpy.ops.object.modifier_apply(modifier=mod.name)
objects.append((ob,'SM_V2_ServicePipes'))
manifest=dict(objects=[],source_blend=str(OUT/'DungeonServices_Source.blend'),config=CFG)
for ob,old in objects:
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    # Explicit triangulation is part of FBX authoring, not an application test.
    mod=ob.modifiers.new('Export triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    path=OUT/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,colors_type='LINEAR')
    label=old.replace('SM_V2_','DGN_AV2_');before=next(a for a in BEFORE['actors'] if a['label']==label)['components'][0]
    materials={}
    for m in ob.data.materials:
        if m.name.startswith('Service_'):
            materials[m.name]=BASE+'/Materials/M_'+m.name
        else:materials[m.name]='/Game/Dungeons/AtmosphereV2/Materials/M_'+m.name.replace('V2_','').split('.')[0]
    manifest['objects'].append(dict(name=ob.name,source_object=old,actor=label,previous_mesh=before['mesh'],fbx=str(path),materials=materials))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonServices_Source.blend'))
(OUT/'geometry-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('DUNGEON_SERVICES_AUTHORED',len(objects))
