"""Precisely authored replacement cargo stack and switchgear. No renders or simulation."""
import json,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix,Euler

ROOT=Path(__file__).resolve().parents[1]
ATLAS=json.loads((ROOT/'Authored/atlas.json').read_text(encoding='utf-8'))
MATERIAL='/Game/Dungeons/FacilityPropPolish20260928/Materials/M_FacilityProp_Atlas'
SLOT='FacilityProp_Atlas'
V=[];F=[];UV=[];SMOOTH=[]

def tex(surface,u,v):
    x0,y0,x1,y1=ATLAS['rects'][surface]
    return ((x0+u*(x1-x0))/4096,1-(y0+v*(y1-y0))/2048)

def face(vertices,surface,uv=None,smooth=False):
    offset=len(V);V.extend(tuple(p) for p in vertices);F.append(tuple(range(offset,offset+len(vertices))))
    UV.append([tex(surface,*p) for p in (uv or [(0,1),(1,1),(1,0),(0,0)])]);SMOOTH.append(smooth)

def box(c,size,surface='enamel',bevel=.003,rotation=(0,0,0)):
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for vert in bm.verts:vert.co=Vector(tuple(vert.co[i]*size[i] for i in range(3)))
    if bevel:
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(size)*.23),segments=3,affect='EDGES')
    bm.normal_update();rot=Euler(rotation).to_matrix();center=Vector(c)
    for p in bm.faces:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));dims=[i for i in range(3) if i!=axis]
        if surface in ('wood','red'):dims.sort(key=lambda i:size[i])
        coords=[]
        for vert in p.verts:
            uv=[]
            for dim in dims:
                den=max(size[dims[0]],size[dims[1]]) if surface=='wood' else size[dim]
                uv.append(.5+vert.co[dim]/max(den,.001)*.97)
            coords.append((uv[0],1-uv[1]))
        face([center+rot@v.co for v in p.verts],surface,coords,max(abs(p.normal[i]) for i in range(3))<.999)
    bm.free()

def basis(axis):
    n=Vector(axis).normalized();u=Vector((1,0,0)) if abs(n.x)<.9 else Vector((0,1,0))
    u=(u-n*u.dot(n)).normalized();return n,u,n.cross(u).normalized()

def lathe(c,axis,profile,surface='steel',segments=32,smooth=True):
    n,u,v=basis(axis);c=Vector(c)
    rings=[[c+n*z+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*radius for i in range(segments)] for z,radius in profile]
    for k in range(len(rings)-1):
        for i in range(segments):
            j=(i+1)%segments
            face([rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]],surface,
                 [(i/segments,k/(len(rings)-1)),((i+1)/segments,k/(len(rings)-1)),((i+1)/segments,(k+1)/(len(rings)-1)),(i/segments,(k+1)/(len(rings)-1))],smooth)
    for k,reverse in [(0,True),(-1,False)]:
        ids=list(range(segments));ids=ids[::-1] if reverse else ids
        face([rings[k][i] for i in ids],surface,[(.5+.48*math.cos(i*math.tau/segments),.5-.48*math.sin(i*math.tau/segments)) for i in ids])

def rod(a,b,r,surface='steel',segments=16):
    a=Vector(a);b=Vector(b);lathe(a,b-a,[(0,r),((b-a).length,r)],surface,segments)

def tube(points,r,surface='steel',segments=12):
    points=[Vector(p) for p in points];rings=[]
    for i,p in enumerate(points):
        direction=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        n,u,v=basis(direction)
        rings.append([p+r*(u*math.cos(j*math.tau/segments)+v*math.sin(j*math.tau/segments)) for j in range(segments)])
    for k in range(len(rings)-1):
        for i in range(segments):
            j=(i+1)%segments
            face([rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]],surface,[(i/segments,0),((i+1)/segments,0),((i+1)/segments,1),(i/segments,1)],True)
    face(list(reversed(rings[0])),surface,[(.5+.4*math.cos(i*math.tau/segments),.5+.4*math.sin(i*math.tau/segments)) for i in reversed(range(segments))])
    face(rings[-1],surface,[(.5+.4*math.cos(i*math.tau/segments),.5+.4*math.sin(i*math.tau/segments)) for i in range(segments)])

def bolt(c,axis=(0,-1,0),scale=1):
    n=Vector(axis).normalized();lathe(c,n,[(0,.009*scale),(.0016*scale,.009*scale)],'steel',24)
    center=Vector(c)+n*.0016*scale
    lathe(center,n,[(0,.0065*scale),(.004*scale,.0065*scale),(.005*scale,.0056*scale),(.005*scale,.0028*scale),(.0025*scale,.0028*scale)],'steel',6,False)
    lathe(center+n*.00255*scale,n,[(0,.0026*scale),(.0001*scale,.0026*scale)],'dark',6,False)

def plaque(c,width,height,surface,axis=(0,-1,0),thickness=.0015,backing='steel',single_surface=False):
    n,u,v=basis(axis);c=Vector(c)
    first_face=len(F)
    # Backing dimensions and rotation are derived from the printed face basis.
    if abs(n.y)>.9:box(c-n*thickness*.5,(width,thickness,height),backing,.0006)
    elif abs(n.x)>.9:box(c-n*thickness*.5,(thickness,width,height),backing,.0006)
    else:box(c-n*thickness*.5,(width,height,thickness),backing,.0006)
    if single_surface:
        # Print into the actual front cap. No duplicate face or sub-mm depth gap.
        for fi in range(first_face,len(F)):
            points=[Vector(V[i]) for i in F[fi]]
            if all(abs((p-c).dot(n))<1.e-7 for p in points):
                UV[fi]=[tex(surface,.5+(p-c).dot(u)/width,.5-(p-c).dot(v)/height) for p in points]
        return
    c+=n*.0004
    face([c-u*width*.5-v*height*.5,c+u*width*.5-v*height*.5,c+u*width*.5+v*height*.5,c-u*width*.5+v*height*.5],surface)

def dial(x,z,unit):
    # Gasket, flange, stepped bezel and recessed printed face.
    c=Vector((x,-.288,z));n=Vector((0,-1,0))
    lathe(c,n,[(0,.076),(.006,.076)],'dark',64)
    lathe(c+n*.006,n,[(0,.074),(.010,.074),(.016,.069),(.033,.069),(.037,.066),(.037,.060),(.031,.058)],'steel',64)
    center=c+n*.040
    verts=[center]+[center+Vector((math.cos(i*math.tau/96)*.058,0,math.sin(i*math.tau/96)*.058)) for i in range(96)]
    for i in range(96):
        a=i*math.tau/96;b=(i+1)*math.tau/96
        face([verts[0],verts[i+1],verts[(i+1)%96+1]],'dial_'+unit,[(.5,.5),(.5+math.cos(a)*.5,.5-math.sin(a)*.5),(.5+math.cos(b)*.5,.5-math.sin(b)*.5)])
    angle=math.radians(135 if unit=='V' else 129);pointer=Vector((math.cos(angle),0,math.sin(angle)));side=Vector((-pointer.z,0,pointer.x))
    p=center+n*.0018
    face([p-pointer*.011-side*.0018,p+pointer*.044,p-pointer*.011+side*.0018],'dark',[(.4,.4),(.6,.4),(.5,.6)])
    lathe(p+n*.0003,n,[(0,.0048),(.0015,.0048)],'steel',24)
    for a in (45,135,225,315):
        q=math.radians(a);bolt((x+math.cos(q)*.064,-.331,z+math.sin(q)*.064),scale=.31)

def cabinet():
    box((0,0,.096),(1.60,.68,.192),'dark',.007)
    box((0,-.337,.118),(1.53,.008,.107),'steel',.002)
    for x in (-.73,.73):
        for z in (.067,.159):bolt((x,-.341,z),scale=.72)
    # Folded enclosure and returned roof lip; visible side stiffening rails.
    box((0,.057,1.033),(1.582,.575,1.70),'enamel',.006)
    box((0,.018,1.889),(1.60,.620,.032),'enamel',.004)
    box((0,-.291,1.875),(1.60,.026,.018),'steel',.002)
    for x in (-.780,.780):
        box((x,-.272,1.044),(.034,.060,1.654),'enamel',.003)
        box((x,.248,1.02),(.023,.026,1.52),'enamel',.002)
    box((0,-.273,1.040),(.034,.055,1.640),'dark',.002)
    box((0,-.274,.235),(1.532,.052,.044),'enamel',.003)
    box((0,-.274,1.851),(1.532,.052,.035),'enamel',.003)
    for side,x in enumerate((-.400,.400)):
        # Seal around each door, real four-sided folded edge and raised skin.
        box((x,-.282,1.05),(.774,.018,1.582),'dark',.004)
        front=-.297;thick=.006;lo=.271;hi=1.829;vent_lo=.38;vent_hi=.665;half=.255
        box((x,front,(.681+hi)*.5),(.756,thick,hi-.681),'enamel',.002)
        box((x,front,(lo+.362)*.5),(.756,thick,.362-lo),'enamel',.002)
        for sign in (-1,1):
            box((x+sign*.323,front,.520),(.110,thick,.318),'enamel',.002)
            box((x+sign*.373,-.286,1.05),(.010,.027,1.556),'enamel',.002)
        for z in (.276,1.824):box((x,-.286,z),(.738,.027,.010),'enamel',.002)
        # Deep cavity and individually folded louver hoods, not black decals.
        box((x,-.248,.518),(.524,.018,.310),'dark',.003)
        for i in range(5):
            z=.389+i*.057
            box((x,front,z),(.520,.006,.014),'enamel',.001)
            box((x,-.305,z+.020),(.510,.021,.027),'enamel',.0015,(math.radians(-32),0,0))
        for vx in (x-.240,x+.240):
            for z in (.373,.663):bolt((vx,-.301,z),scale=.45)
        # Outer hinges have two leaves and alternating knuckles.
        outer=x+(-.373 if side==0 else .373)
        for z in (.515,1.035,1.55):
            for dx in (-.013,.013):box((outer+dx,-.309,z),(.020,.014,.105),'steel',.0015)
            for i in range(5):lathe((outer,-.317,z-.050+i*.020),(0,0,1),[(0,.010),(.0185,.010)],'steel',20)
            for zz in (z-.033,z+.033):bolt((outer+(-.018 if side==0 else .018),-.319,zz),scale=.40)
        # Recessed locking escutcheon with a bowed handle and cylinder lock.
        handle=x+(.305 if side==0 else -.305)
        box((handle,-.304,1.032),(.056,.010,.239),'dark',.006)
        box((handle,-.312,1.032),(.046,.010,.222),'steel',.004)
        points=[(handle,-.317,.964),(handle,-.331,.970),(handle,-.343,.986),(handle,-.344,1.09),(handle,-.331,1.107),(handle,-.317,1.113)]
        tube(points,.009,'steel',12)
        lathe((handle,-.320,.943),(0,-1,0),[(0,.010),(.004,.010)],'steel',24)
        box((handle,-.325,.943),(.003,.001,.012),'dark',.0004)
        dial(x,1.503,'V' if side==0 else 'A')
        plaque((x,-.302,1.716),.320,.083,'cabinet_left' if side==0 else 'cabinet_right')
        for bx in (x-.147,x+.147):bolt((bx,-.3024,1.716),scale=.34)
        for index,bx in enumerate((x-.141,x+.141)):
            lathe((bx,-.301,1.275),(0,-1,0),[(0,.029),(.007,.029),(.010,.026)],'steel',40)
            lathe((bx,-.311,1.275),(0,-1,0),[(0,.022),(.004,.022)],'dark',32)
            lathe((bx,-.315,1.275),(0,-1,0),[(0,.019),(.009,.019),(.014,.016)],'green_cap' if index==0 else 'red_cap',40)
        plaque((x,-.302,1.205),.335,.054,'buttons',backing='dark')
        plaque((x,-.302,.811),.273,.113,'warning' if side else 'rating')
    plaque((.7925,-.003,1.27),.230,.079,'service',(1,0,0))
    # Cable glands are attached to the lower enclosure, with short capped tails.
    for x in (-.51,-.39,.42):
        lathe((x,.305,.35),(0,1,0),[(0,.030),(.011,.030),(.012,.024),(.029,.024)],'dark',24)

def cargo():
    # Three runners, nine bearing blocks, five deck boards. All load bottoms stay at 25 cm.
    for x in (-.75,0,.75):
        box((x,0,.023),(.15,1.12,.046),'wood',.003)
        for y in (-.438,0,.438):box((x,y,.128),(.15,.218,.160),'wood',.003)
    for j,y in enumerate((-.49,-.245,0,.245,.49)):
        box((0,y,.225),(1.9,.180,.050),'wood',.0025)
        for x in (-.75,0,.75):
            for dx in (-.038,.038):lathe((x+dx,y,.250),(0,0,1),[(0,.0045),(.0007,.0045)],'steel',12)
    for number,(x,y,z,sx,sy,sz) in enumerate([(-.48,0,.70,.85,.99,.90),(.48,0,.61,.83,.99,.72),(-.40,.03,1.32,.70,.79,.34)]):
        bottom=z-sz*.5;top=z+sz*.5;seam=top-.085;depth=.018
        box((x,y,(bottom+seam)*.5),(sx-.006,sy-.006,seam-bottom),'red',.004)
        box((x,y,seam+.003),(sx-.010,sy-.010,.006),'dark',.001)
        box((x,y,(seam+.010+top)*.5),(sx,sy,top-seam-.010),'red',.004)
        # Recessed plywood infills, framed along the base and lid rather than featureless cubes.
        for sign in (-1,1):
            fy=y+sign*(sy*.5+.0005)
            box((x,fy,(bottom+seam)*.5),(sx-.125,.010,seam-bottom-.092),'red',.004)
            for zz in (bottom+.025,seam-.025):box((x,fy+sign*.004,zz),(sx-.028,.018,.037),'red',.002)
        # Steel straps form continuous front/top/back bands. Corner guards cover the joints.
        for xx in (x-sx*.36,x+sx*.36):
            box((xx,y,top+.0008),(.050,sy+.004,.0025),'steel',.0006)
            for sign in (-1,1):
                fy=y+sign*(sy*.5+.006)
                box((xx,fy,z),(.050,.0045,sz-.007),'steel',.001)
                for zz in (bottom+.040,seam-.045,top-.024):bolt((xx,fy+sign*.003,zz),(0,sign,0),.60)
        for signx in (-1,1):
            for signy in (-1,1):
                for zz in (bottom+.040,top-.039):
                    cx=x+signx*(sx*.5-.025);cy=y+signy*(sy*.5+.005)
                    box((cx,cy,zz),(.049,.006,.067),'steel',.002)
                    box((x+signx*(sx*.5+.003),y+signy*(sy*.5-.026),zz),(.006,.053,.067),'steel',.002)
                    bolt((cx,cy+signy*.004,zz),(0,signy,0),.45)
        # Functional latch geometry on the two front strap lines.
        for xx in (x-sx*.36,x+sx*.36):
            fy=y-sy*.5-.013
            box((xx,fy,seam-.015),(.040,.011,.090),'steel',.003)
            box((xx,fy-.007,seam-.015),(.018,.007,.051),'dark',.002)
            tube([(xx-.012,fy-.012,seam-.039),(xx-.012,fy-.025,seam+.012),(xx+.012,fy-.025,seam+.012),(xx+.012,fy-.012,seam-.039)],.0033,'steel',10)
            rod((xx-.023,fy-.014,seam-.036),(xx+.023,fy-.014,seam-.036),.004,'steel',16)
        # Back hinge leaves and barrels, set below the bearing surface of the lid.
        for xx in (x-sx*.30,x+sx*.30):
            fy=y+sy*.5+.006
            box((xx,fy,seam),(.082,.006,.096),'steel',.002)
            rod((xx-.040,fy+.010,seam),(xx+.040,fy+.010,seam),.009,'steel',20)
            for dx in (-.025,.025):
                for zz in (seam-.031,seam+.031):bolt((xx+dx,fy+.004,zz),(0,1,0),.40)
        # Side bail handles hang against an actual mounting plate.
        for sign in (-1,1):
            cx=x+sign*(sx*.5+.006);hz=z+sz*.09
            box((cx,y,hz),(.009,.198,.094),'steel',.004)
            for dy in (-.074,.074):bolt((cx+sign*.006,y+dy,hz),(sign,0,0),.55)
            tube([(cx+sign*.012,y-.063,hz+.005),(cx+sign*.030,y-.063,hz-.013),(cx+sign*.032,y-.054,hz-.060),(cx+sign*.032,y+.054,hz-.060),(cx+sign*.030,y+.063,hz-.013),(cx+sign*.012,y+.063,hz+.005)],.006,'steel',12)
        plaque((x,y-sy*.5-.0085,z-.045 if number<2 else z-.025),min(.292,sx*.48),.129,'cargo_0'+str(number+1),thickness=.003,backing='dark',single_surface=True)
        if number<2:
            plaque((x+sx*.5,y+.280,z-.102),.107,.125,'arrows',(1,0,0),thickness=.003,backing='red',single_surface=True)
        else:
            plaque((x+sx*.5,y+.215,z-.035),.090,.107,'fragile',(1,0,0),thickness=.003,backing='red',single_surface=True)

def material():
    mat=bpy.data.materials.get(SLOT) or bpy.data.materials.new(SLOT);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    out=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled');links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    maps={}
    for suffix in ('BaseColor','NormalGL','ORM'):
        image=bpy.data.images.load(str(ROOT/'Authored/Textures'/('T_FacilityProp_'+suffix+'.png')),check_existing=True)
        if suffix!='BaseColor':image.colorspace_settings.name='Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=image;maps[suffix]=node
    links.new(maps['BaseColor'].outputs['Color'],bsdf.inputs['Base Color'])
    separate=nodes.new('ShaderNodeSeparateColor');links.new(maps['ORM'].outputs['Color'],separate.inputs['Color'])
    links.new(separate.outputs['Green'],bsdf.inputs['Roughness']);links.new(separate.outputs['Blue'],bsdf.inputs['Metallic'])
    norm=nodes.new('ShaderNodeNormalMap');links.new(maps['NormalGL'].outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bsdf.inputs['Normal'])
    return mat

def build_all(output_dir=None,reset=True,save=True,layout_start=0,only=None):
    if reset:bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    dest=Path(output_dir or ROOT/'Authored');dest.mkdir(parents=True,exist_ok=True)
    mat=material();records=[]
    specs=[('PowerCabinet',cabinet,[((0,0,.96),(1.6,.68,1.92))]),
           ('CargoStack',cargo,[((0,0,.64),(1.9,1.12,1.28)),((-.4,.03,1.32),(.7,.79,.34))])]
    for index,(key,build,colliders) in enumerate(specs):
        if only and key not in only:continue
        V.clear();F.clear();UV.clear();SMOOTH.clear();build()
        name='SM_Facility_'+key;mesh=bpy.data.meshes.new(name);mesh.from_pydata(V,[],F);mesh.update();mesh.materials.append(mat)
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
        uv=mesh.uv_layers.new(name='UVMap')
        for polygon,coords,smooth in zip(mesh.polygons,UV,SMOOTH):
            polygon.use_smooth=smooth
            for li,at in zip(polygon.loop_indices,coords):uv.data[li].uv=at
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        # Merge only coincident geometry within this assembly. UVs live per-corner.
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bm.to_mesh(mesh);bm.free()
        weighted=obj.modifiers.new('Manufactured weighted normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=40
        bpy.ops.object.modifier_apply(modifier=weighted.name)
        tri=obj.modifiers.new('Final export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
        # Author a noncollapsed UV basis for bevel/cap triangles after triangulation.
        mesh=obj.data;uv=mesh.uv_layers.active.data
        for polygon in mesh.polygons:
            ids=list(polygon.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-12:continue
            coords=[mesh.vertices[mesh.loops[i].vertex_index].co for i in ids]
            normal=polygon.normal;axis=max(range(3),key=lambda k:abs(normal[k]));dims=[k for k in range(3) if k!=axis]
            center=sum(coords,Vector())/3
            for li,p in zip(ids,coords):uv[li].uv=tex('steel',.5+(p[dims[0]]-center[dims[0]])*.25,.5-(p[dims[1]]-center[dims[1]])*.25)
        collision_objects=[]
        for number,(center,size) in enumerate(colliders):
            bpy.ops.mesh.primitive_cube_add(size=1,location=center);collision=bpy.context.object
            collision.name=f'UCX_{name}_{number:02d}';collision.dimensions=size
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collision_objects.append(collision)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        for collision in collision_objects:collision.select_set(True)
        bpy.context.view_layer.objects.active=obj
        fbx=dest/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        records.append(dict(name=name,key=key,fbx=str(fbx),materials={SLOT:MATERIAL},triangles=len(mesh.polygons),collision=True,collision_boxes=len(colliders),revision='precision_prop_polish_20260928'))
        offset=Vector((((index+layout_start)%3)*3.2,((index+layout_start)//3)*3.2,0));obj.location+=offset
        for collision in collision_objects:collision.location+=offset;collision.hide_viewport=True;collision.hide_render=True
        print('FACILITY_PROP_AUTHORED',name,len(mesh.polygons),flush=True)
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=str(dest/'FacilityProps_Polished.blend'))
        (dest/'manifest.json').write_text(json.dumps({'objects':records,'units':'metres; imported as UE centimetres','tests_run':False,'source':'Original precise geometry and original PBR atlas; same production mesh paths and collision volumes'},indent=2),encoding='utf-8')
    return records

if __name__=='__main__':build_all()
