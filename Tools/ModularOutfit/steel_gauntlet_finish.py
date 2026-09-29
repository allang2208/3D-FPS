"""Forged plate finishing, in centimetres; baked into the existing steel atlas."""
import math
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
import build_metal_gauntlet_sample as s
TRIM_PATH=Path(__file__).resolve().parents[2]/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1/ArticulationSolve20260928/contour-solution.json'
TRIMS=json.loads(TRIM_PATH.read_text()) if TRIM_PATH.exists() else {}


def sample(grid,u,v):
    h,w=grid.shape[:2];px=u*(w-1);py=v*(h-1)
    ix=min(w-2,int(px));iy=min(h-2,int(py));a=px-ix;b=py-iy
    return grid[iy,ix]*(1-a)*(1-b)+grid[iy,ix+1]*a*(1-b)+grid[iy+1,ix]*(1-a)*b+grid[iy+1,ix+1]*a*b


def surface_normal(grid,u,v,dorsal):
    dx=sample(grid,min(1,u+.012),v)-sample(grid,max(0,u-.012),v)
    dy=sample(grid,u,min(1,v+.012))-sample(grid,u,max(0,v-.012))
    normal=s.unit(np.cross(dx,dy))
    return normal if normal@dorsal>0 else -normal


def plate(name,grid,dorsal,bone,rig,mat,role):
    grid=np.asarray(grid)
    author_grid=grid.copy()
    if name in TRIMS:
        solved=TRIMS[name];h,w=grid.shape[:2];first,last=solved['row_range']
        trimmed=[]
        for y in np.linspace(first,last,h):
            low=float(np.interp(y,np.arange(h),solved['lo']))
            high=float(np.interp(y,np.arange(h),solved['hi']))
            trimmed.append([sample(author_grid,x/(w-1),y/(h-1)) for x in np.linspace(low,high,w)])
        grid=np.asarray(trimmed)
    if role=='main':
        edge=[0.,.008,.018,.032,.055]
        us=np.array(edge+list(np.linspace(.085,.915,19))+[1-t for t in edge[::-1]])
        vs=np.array(edge+list(np.linspace(.085,.915,17))+[1-t for t in edge[::-1]])
    else:
        us=np.linspace(0,1,grid.shape[1]);vs=np.linspace(0,1,grid.shape[0])
    width=np.linalg.norm(grid[len(grid)//2,-1]-grid[len(grid)//2,0])
    length=np.linalg.norm(grid[-1,len(grid[0])//2]-grid[0,len(grid[0])//2])
    finished=[]
    for v in vs:
        row=[]
        for u in us:
            pu=u
            if role=='finger':
                # Pull only the outside corners inward; do not widen contact.
                corner=.12*math.exp(-(min(v,1-v)/.12)**2)
                pu=.5+(u-.5)*(1-corner)
            p=sample(grid,pu,v)
            if role=='main':
                distance=min(u*width,(1-u)*width,v*length,(1-v)*length)
                rim=.055*math.exp(-((distance-.115)/.065)**2)
                ridge=.105*math.exp(-((u-.50)/.075)**2)*math.sin(math.pi*v)**2
                shoulders=.035*(math.exp(-((u-(.5-.18*v))/.037)**2)+math.exp(-((u-(.5+.18*v))/.037)**2))*math.sin(math.pi*v)**2
                p=p+surface_normal(grid,pu,v,dorsal)*(rim+ridge+shoulders)
            row.append(p)
        finished.append(row)
    finished=np.asarray(finished);rows,cols=finished.shape[:2]
    faces=[]
    for iy in range(rows-1):
        for ix in range(cols-1):
            a=iy*cols+ix;faces.append([a,a+1,a+cols+1,a+cols])
    points=finished.reshape((-1,3));q=[s.to_blender(points[i]) for i in faces[len(faces)//2]]
    if (q[1]-q[0]).cross(q[2]-q[0]).dot(s.to_blender(dorsal))<0:faces=[f[::-1] for f in faces]
    obj=s.mesh_object(name,points,faces,mat);s.activate(obj)
    panel=obj.data.uv_layers.new(name='SteelPanelUV')
    for face in obj.data.polygons:
        for li in face.loop_indices:
            vi=obj.data.loops[li].vertex_index;iy,ix=divmod(vi,cols)
            panel.data[li].uv=(us[ix],vs[iy])
    obj.color=(width*.01,length*.01,1. if role=='main' else .55 if role=='cuff' else 0.,1.)
    thickness=.05 if role=='shell' else .09
    solid=obj.modifiers.new('ForgedWall','SOLIDIFY');solid.thickness=thickness*.01;solid.offset=-1.;solid.use_even_offset=True
    bpy.ops.object.modifier_apply(modifier=solid.name)
    bevel=obj.modifiers.new('PolishedEdge_0p22mm','BEVEL');bevel.width=.00022;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.65
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for face in obj.data.polygons:face.use_smooth=True
    atlas=obj.data.uv_layers.new(name='SteelSampleUV');obj.data.uv_layers.active=atlas
    for layer in obj.data.uv_layers:layer.active_render=layer.name=='SteelSampleUV'
    s.attach_rigid(obj,rig,bone)
    obj['WallThicknessCM']=thickness;obj['Finish']='Satin forged steel; integral raised rim and crest; baked engraving'
    s.PARTS.append(dict(name=name,bone=bone,kind='steel_plate',object=obj,thickness_cm=thickness,vertices=len(obj.data.vertices),author_grid=author_grid.tolist()))
    return finished


def rivet(name,grid,u,v,dorsal,bone,rig,mat,radius=.18):
    center=sample(grid,u,v);normal=surface_normal(grid,u,v,dorsal)
    across=s.unit(np.cross(normal,[0,0,1]) if abs(normal[2])<.9 else np.cross(normal,[0,1,0]))
    up=np.cross(normal,across);sides=16
    # Recessed seat, short shank and domed cap are one closed lathed piece.
    profile=[(.42,.079),(.70,.065),(.84,.044),(.86,.025),(1.10,.020),(1.15,.006),(1.10,-.012),(.70,-.020)]
    points=[center+normal*.086]
    for r,h in profile:
        for i in range(sides):
            t=i*math.tau/sides;points.append(center+normal*h+radius*r*(across*math.cos(t)+up*math.sin(t)))
    points.append(center-normal*.020)
    faces=[[0,1+i,1+(i+1)%sides] for i in range(sides)]
    for j in range(len(profile)-1):
        for i in range(sides):
            a=1+j*sides+i;b=1+j*sides+(i+1)%sides;faces.append([a,a+sides,b+sides,b])
    faces.extend([[len(points)-1,1+(len(profile)-1)*sides+(i+1)%sides,1+(len(profile)-1)*sides+i] for i in range(sides)])
    obj=s.mesh_object(name,points,faces,mat);s.activate(obj)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    panel=obj.data.uv_layers.new(name='SteelPanelUV')
    for face in obj.data.polygons:
        for li in face.loop_indices:
            delta=np.asarray(points[obj.data.loops[li].vertex_index])-center
            panel.data[li].uv=(.5+(delta@across)/(radius*2.4),.5+(delta@up)/(radius*2.4))
    atlas=obj.data.uv_layers.new(name='SteelSampleUV');obj.data.uv_layers.active=atlas
    for layer in obj.data.uv_layers:layer.active_render=layer.name=='SteelSampleUV'
    obj.color=(radius*.024,radius*.024,.30,1.)
    s.attach_rigid(obj,rig,bone)
    s.PARTS.append(dict(name=name,bone=bone,kind='steel_rivet',object=obj,vertices=len(obj.data.vertices)))


def material():
    mat=bpy.data.materials.new('SteelGauntlet_Authored');mat.use_nodes=True
    nt=mat.node_tree;n=nt.nodes;l=nt.links;bs=n.get('Principled BSDF');out=n.get('Material Output')
    def connect(value,socket):
        if isinstance(value,(int,float,tuple,list)):socket.default_value=value
        else:l.new(value,socket)
    def mathnode(op,a,b=None):
        node=n.new('ShaderNodeMath');node.operation=op;connect(a,node.inputs[0])
        if b is not None:connect(b,node.inputs[1])
        return node.outputs[0]
    def mix(f,a,b):
        node=n.new('ShaderNodeMixRGB');connect(f,node.inputs[0]);connect(a,node.inputs[1]);connect(b,node.inputs[2]);return node.outputs[0]
    def gaussian(x,center,width):
        t=mathnode('DIVIDE',mathnode('SUBTRACT',x,center),width)
        return mathnode('EXPONENT',mathnode('MULTIPLY',mathnode('MULTIPLY',t,t),-1))
    def noise(vector,scale,detail=2):
        node=n.new('ShaderNodeTexNoise');connect(vector,node.inputs['Vector']);node.inputs['Scale'].default_value=scale;node.inputs['Detail'].default_value=detail;return node.outputs['Fac']
    panel=n.new('ShaderNodeUVMap');panel.uv_map='SteelPanelUV'
    uv=n.new('ShaderNodeSeparateXYZ');l.new(panel.outputs['UV'],uv.inputs[0])
    info=n.new('ShaderNodeObjectInfo');dimensions=n.new('ShaderNodeSeparateColor');l.new(info.outputs['Color'],dimensions.inputs[0])
    width,height,style=(dimensions.outputs[k] for k in ('Red','Green','Blue'))
    mx=mathnode('MULTIPLY',mathnode('MINIMUM',uv.outputs['X'],mathnode('SUBTRACT',1.,uv.outputs['X'])),width)
    my=mathnode('MULTIPLY',mathnode('MINIMUM',uv.outputs['Y'],mathnode('SUBTRACT',1.,uv.outputs['Y'])),height)
    edge=mathnode('MINIMUM',mx,my)
    main=mathnode('GREATER_THAN',style,.8)
    hardware=mathnode('MULTIPLY',mathnode('GREATER_THAN',style,.2),mathnode('LESS_THAN',style,.4))
    panel_mask=mathnode('SUBTRACT',1.,hardware)
    groove=mathnode('MULTIPLY',gaussian(edge,.00155,.00018),panel_mask)
    groove2=mathnode('MULTIPLY',gaussian(edge,.00225,.00010),main)
    engraving=mathnode('MAXIMUM',groove,groove2)
    polish=mathnode('MULTIPLY',gaussian(edge,.00042,.00044),panel_mask)
    metric=n.new('ShaderNodeCombineXYZ');connect(mathnode('MULTIPLY',uv.outputs['X'],width),metric.inputs['X']);connect(mathnode('MULTIPLY',uv.outputs['Y'],height),metric.inputs['Y'])
    broad=noise(metric.outputs[0],85.,2)
    stretched=n.new('ShaderNodeVectorMath');stretched.operation='MULTIPLY';l.new(metric.outputs[0],stretched.inputs[0]);stretched.inputs[1].default_value=(1900.,38.,1.)
    brush=noise(stretched.outputs[0],1.,2)
    micro=noise(metric.outputs[0],6500.,1)
    color=mix(broad,(.275,.30,.325,1),(.305,.325,.345,1))
    color=mix(polish,color,(.39,.415,.44,1))
    color=mix(mathnode('MULTIPLY',engraving,.62),color,(.10,.125,.15,1))
    color=mix(mathnode('MULTIPLY',hardware,.65),color,(.235,.26,.285,1))
    rough=mathnode('ADD',.42,mathnode('MULTIPLY',mathnode('SUBTRACT',brush,.5),.095))
    rough=mathnode('ADD',rough,mathnode('MULTIPLY',mathnode('SUBTRACT',broad,.5),.035))
    rough=mathnode('ADD',rough,mathnode('MULTIPLY',engraving,.10))
    rough=mathnode('SUBTRACT',rough,mathnode('MULTIPLY',polish,.15))
    rough=mathnode('SUBTRACT',rough,mathnode('MULTIPLY',hardware,.055))
    h=mathnode('ADD',mathnode('MULTIPLY',brush,.15),mathnode('MULTIPLY',micro,.04))
    h=mathnode('SUBTRACT',h,mathnode('MULTIPLY',engraving,1.))
    mail=mathnode('MULTIPLY',mathnode('GREATER_THAN',style,.65),mathnode('LESS_THAN',style,.75))
    row=mathnode('DIVIDE',mathnode('MULTIPLY',uv.outputs['Y'],height),.0006)
    col=mathnode('DIVIDE',mathnode('MULTIPLY',uv.outputs['X'],width),.0007)
    stagger=mathnode('MULTIPLY',mathnode('PINGPONG',mathnode('FLOOR',row),1.),.5)
    rx=mathnode('DIVIDE',mathnode('SUBTRACT',mathnode('FRACT',mathnode('ADD',col,stagger)),.5),.43)
    ry=mathnode('DIVIDE',mathnode('SUBTRACT',mathnode('FRACT',row),.5),.39)
    ring=mathnode('SQRT',mathnode('ADD',mathnode('MULTIPLY',rx,rx),mathnode('MULTIPLY',ry,ry)))
    wire=gaussian(ring,.84,.19)
    mail_color=mix(wire,(.025,.033,.043,1),(.26,.29,.325,1))
    color=mix(mail,color,mail_color)
    rough=mathnode('ADD',mathnode('MULTIPLY',rough,mathnode('SUBTRACT',1.,mail)),mathnode('MULTIPLY',mail,mathnode('SUBTRACT',.64,mathnode('MULTIPLY',wire,.29))))
    metallic=mathnode('SUBTRACT',1.,mathnode('MULTIPLY',mail,mathnode('MULTIPLY',mathnode('SUBTRACT',1.,wire),.82)))
    h=mathnode('ADD',mathnode('MULTIPLY',h,mathnode('SUBTRACT',1.,mail)),mathnode('MULTIPLY',mail,mathnode('MULTIPLY',wire,3.)))
    connect(metallic,bs.inputs['Metallic']);connect(color,bs.inputs['Base Color']);connect(rough,bs.inputs['Roughness'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.48;bump.inputs['Distance'].default_value=.00007;connect(h,bump.inputs['Height'])
    bevel=n.new('ShaderNodeBevel');bevel.inputs['Radius'].default_value=.00022;bevel.samples=4;l.new(bump.outputs[0],bevel.inputs['Normal']);l.new(bevel.outputs[0],bs.inputs['Normal'])
    ao=n.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.002;ao.samples=8
    pack=n.new('ShaderNodeCombineColor');pack.mode='RGB';connect(ao.outputs['AO'],pack.inputs['Red']);connect(rough,pack.inputs['Green']);connect(metallic,pack.inputs['Blue'])
    mat['Finish']='Satin cold steel; local directional brushing; polished perimeter; inset engraving; subtle microtexture'
    return mat,color,pack.outputs[0],bs,out
