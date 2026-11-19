"""Dimensioned oak fascia, forged strapwork and peened nails. All measurements in cm."""
from pathlib import Path
import math
import bpy

OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Sign'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
material = bpy.data.materials.new('PaintedOakAndIron')
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
bsdf = nodes.get('Principled BSDF')


def tex(filename, location, data=False):
    image = bpy.data.images.load(str(OUT/(filename+'.png')))
    image.filepath = '//'+filename+'.png'
    if data:
        image.colorspace_settings.name = 'Non-Color'
    image_node = nodes.new('ShaderNodeTexImage')
    image_node.image = image
    image_node.location = location
    return image_node


albedo = tex('T_TavernSign_Color',(-550,260))
orm = tex('T_TavernSign_ORM',(-550,0),True)
split = nodes.new('ShaderNodeSeparateColor')
split.location = (-210,0)
links.new(albedo.outputs['Color'],bsdf.inputs['Base Color'])
links.new(orm.outputs['Color'], split.inputs[0])
links.new(split.outputs[1], bsdf.inputs['Roughness'])
links.new(split.outputs[2], bsdf.inputs['Metallic'])
# UE uses DirectX normals. Flip the green channel in the editable Blender material.
normal = tex('T_TavernSign_Normal',(-760,-340),True)
invert = nodes.new('ShaderNodeVectorMath')
invert.operation = 'MULTIPLY_ADD'
invert.inputs[1].default_value=(1,-1,1)
invert.inputs[2].default_value=(0,1,0)
invert.location=(-450,-300)
links.new(normal.outputs['Color'],invert.inputs[0])
nmap=nodes.new('ShaderNodeNormalMap')
nmap.location=(-210,-270)
links.new(invert.outputs[0],nmap.inputs['Color'])
links.new(nmap.outputs[0],bsdf.inputs['Normal'])


def inset(outline, cut):
    """Offset each straight edge inward, clipping the miters at splinter tips."""
    result = []
    for i,(x,y) in enumerate(outline):
        px,py = outline[i-1]
        nx,ny = outline[(i+1)%len(outline)]
        a,b = x-px,y-py
        c,d = nx-x,ny-y
        u,v = math.hypot(a,b),math.hypot(c,d)
        n1,n2=(-b/u,a/u),(-d/v,c/v)
        div=max(.34,1+n1[0]*n2[0]+n1[1]*n2[1])
        result.append((x+cut*(n1[0]+n2[0])/div, y+cut*(n1[1]+n2[1])/div))
    return result


class Sign:
    def __init__(self, damaged, level):
        self.damaged, self.level = damaged, level
        self.vertices, self.polys, self.uvs = [], [], []

    def vertex(self,d,h,z,hang):
        if hang and self.damaged:
            # The panel sags from its left fixing. Keep both models on the same rear datum.
            angle=math.radians(-2.5)
            t=h+35
            v=z-36
            h=-35+t*math.cos(angle)-v*math.sin(angle)
            z=36+t*math.sin(angle)+v*math.cos(angle)
        self.vertices.append((d/100,h/100,z/100))
        return len(self.vertices)-1

    def face(self,ids,coords):
        self.polys.append(ids)
        self.uvs.append(coords)

    def face_uv(self,h,z):
        top=896 if self.damaged else 0
        return ((4+(h+42.5)/85*2040)/2048,1-(top+4+(44-z)/44*888)/2048)

    @staticmethod
    def plain_uv(h,z,iron):
        u=(h+48)/96
        if iron:
            return u,1-(1973+(45-z)/49*70)/2048
        return u,1-(1796+(45-z)/49*165)/2048

    def profile(self,outline,back,front,cut=.22,face='wood',hang=True):
        # Polygon coordinates start at bottom left and wind counter-clockwise seen from outside.
        is_iron=face=='iron'
        rim=inset(outline,cut)
        loops=[(back,rim),(back+cut,outline),(front-cut,outline),(front,rim)]
        if self.level==1:
            loops=[(back,outline),(front-cut,outline),(front,rim)]
        elif self.level==2:
            loops=[(back,outline),(front,outline)]
        rings=[[self.vertex(d,h,z,hang) for h,z in shape] for d,shape in loops]
        self.face(rings[0][::-1],[self.plain_uv(h,z,is_iron) for h,z in loops[0][1][::-1]])
        front_uv=self.face_uv if face=='paint' else lambda h,z:self.plain_uv(h,z,is_iron)
        self.face(rings[-1],[front_uv(h,z) for h,z in loops[-1][1]])
        distance=0
        for i,(h,z) in enumerate(outline):
            j=(i+1)%len(outline)
            length=math.dist(outline[i],outline[j])
            for k in range(len(loops)-1):
                band=1973 if is_iron else 1797
                spread=68 if is_iron else 163
                def edge_uv(t,d):
                    return t/100+.017,1-(band+spread*(.18+.55*(d-back)/(front-back)))/2048
                self.face([rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]],
                          [edge_uv(distance,loops[k][0]),edge_uv(distance+length,loops[k][0]),
                           edge_uv(distance+length,loops[k+1][0]),edge_uv(distance,loops[k+1][0])])
            distance+=length

    def spike(self,h,z,phase,lost=False):
        # A square shank swells into an uneven rose-head. Lost nail leaves a dark hollow.
        count=(8,6,4)[self.level]
        if lost:
            size_depth=[(.69,6.17),(.62,6.21),(.36,6.22),(.26,6.145)]
        else:
            size_depth=[(.64,6.12),(.94,6.28),(1.04,6.46),(.64,6.78),(.24,6.87)]
        rings=[]
        for r,d in size_depth:
            ring=[]
            for j in range(count):
                a=j*math.tau/count+phase
                rr=r*(1+.055*math.cos(3*a+phase))
                ring.append(self.vertex(d,h+rr*math.cos(a),z+rr*math.sin(a)*.90,True))
            rings.append(ring)
        def disk_uv(j,r):
            a=j*math.tau/count+phase
            return .43+.08*r*math.cos(a),1-(2006+26*r*math.sin(a))/2048
        for k in range(len(rings)-1):
            for j in range(count):
                n=(j+1)%count
                self.face([rings[k][j],rings[k][n],rings[k+1][n],rings[k+1][j]],
                          [disk_uv(j,size_depth[k][0]),disk_uv(n,size_depth[k][0]),
                           disk_uv(n,size_depth[k+1][0]),disk_uv(j,size_depth[k+1][0])])
        self.face(rings[-1],[disk_uv(j,size_depth[-1][0]) for j in range(count)])

    def build(self):
        # The rough stone pier recedes under the plaque. These two short squared oak
        # grounds enter the masonry and leave the painted board clear of the door quoins.
        for h in (-34.4,34.4):
            self.profile([(h-3.7,6.4),(h+3.7,6.4),(h+3.7,36.7),(h-3.7,36.7)],-34.,2.08,.24,hang=False)
        if self.damaged:
            lower=[(-41.5,2.2),(-28.1,2.45),(-9,2.1),(17.1,2.25),(23.0,3.0),
                   (17.5,3.75),(28.4,4.4),(25.1,5.1),(34.2,6.0),(32.5,6.7),(39.9,8.1),
                   (41.7,10.2),(41.5,15.2),(37,16.0),(41.5,16.8),(41.9,21.8),
                   (15,21.93),(-7,21.85),(-24,22.08),(-41.8,21.81),(-42.15,6.1)]
            upper=[(-41.8,22.29),(-24,22.53),(-7,22.25),(15,22.34),(41.9,22.2),
                   (41.5,37.8),(40,41.7),(34.7,41.72),(32.5,40.9),(30.6,41.89),
                   (7,42.2),(-12,42.09),(-38.6,42.1),(-41.4,40.7),(-42.15,38.7)]
        else:
            lower=[(-41.1,.45),(-34,.12),(-16,.0),(4,.15),(30,.06),(40.9,.28),
                   (42.32,1.6),(42.5,11.7),(42.31,21.87),(25,21.96),(6,22.01),
                   (-15,21.92),(-30,22.05),(-42.28,21.93),(-42.42,2.23)]
            upper=[(-42.28,22.11),(-30,22.23),(-15,22.10),(6,22.19),(25,22.14),
                   (42.31,22.05),(42.47,40.43),(41.38,42.71),(39.40,43.79),
                   (22,43.94),(-2,43.87),(-27,44),(-39.2,43.83),(-41.3,42.6),(-42.37,40.8)]
        self.profile(lower,2.02,5.54,.27,'paint')
        self.profile(upper,2.02,5.65,.31,'paint')
        # Forged fish-tail straps bridge the seam and hold both pieces to the rear grounds.
        for side in (-1,1):
            h=side*36.8
            bend=.95 if self.damaged and side==1 else 0.
            bottom=9.4 if self.damaged and side==1 else 4.3
            strap=[(h-1.2+bend,bottom+2.4),(h+bend,bottom),(h+1.24+bend,bottom+2.3),
                   (h+.81+bend,14.3),(h+1.03,22),(h+.82,31.6),(h+1.51,36.5),
                   (h+1.0,38.27),(h,40.16),(h-.95,38.31),(h-1.46,36.4),
                   (h-.82,31.5),(h-1.08,22.1),(h-.82+bend,14.4)]
            self.profile(strap,5.51,6.18,.13,'iron')
            self.spike(h,36.65,side*.37)
            self.spike(h+bend, bottom+3.2, side*.61,self.damaged and side==1)

    def object(self,name):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices,[],self.polys)
        mesh.update()
        uv=mesh.uv_layers.new(name='Atlas')
        for p,coords in zip(mesh.polygons,self.uvs):
            for index,coord in zip(p.loop_indices,coords):
                uv.data[index].uv=coord
        mesh.materials.append(material)
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new('Triangulate game faces','TRIANGULATE')
        return obj


for name,damaged in (('SM_TavernSign',False),('SM_TavernSignRuined',True)):
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    for level in range(3):
        model=Sign(damaged,level)
        model.build()
        obj=model.object(name+'_LOD'+str(level))
        obj.parent=group
        obj.hide_set(level>0)
    bpy.ops.object.select_all(action='DESELECT')
    group.select_set(True)
    for obj in group.children:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
                             object_types={'EMPTY','MESH'},axis_forward='-Y',axis_up='Z',
                             mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
                             use_custom_props=True,add_leaf_bones=False,path_mode='STRIP')
    for i,obj in enumerate(sorted(group.children,key=lambda child:child.name)):
        obj.hide_set(i>0)
    if damaged:
        group.location.y=1.0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TavernSign.blend'),relative_remap=False)
