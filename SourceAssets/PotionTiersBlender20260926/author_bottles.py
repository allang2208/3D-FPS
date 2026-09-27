"""Original dimensioned Blender bottle construction; no image-to-mesh or renders.

Profiles and units live in design.json. All parts retain a shared bottom pivot.
Authoring meshes, game meshes, explicit UVs, collision and LODs are made together.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np

OUT = Path(__file__).resolve().parent
SPEC = json.loads((OUT / 'design.json').read_text(encoding='utf-8'))
EXPORT = OUT / 'Export'
TEXTURES = OUT / 'Textures'
EXPORT.mkdir(exist_ok=True)
TEXTURES.mkdir(exist_ok=True)
MM = 0.001
MATERIALS = {}


def image_file(name, rgb, color=False):
    h, w = rgb.shape[:2]
    image = bpy.data.images.new(name, width=w, height=h, alpha=False)
    image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    pixels = np.ones((h,w,4), dtype=np.float32)
    pixels[:,:,:3] = rgb
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(TEXTURES / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
    return image


def cork_maps():
    # Original deterministic PBR maps, not pixels sampled from the concept art.
    n = 1024
    rng = np.random.default_rng(260926)
    yy, xx = np.mgrid[0:n,0:n].astype(np.float32)
    grain = rng.random((n,n), dtype=np.float32)
    cloud = np.zeros_like(grain)
    for cells, amp in [(12,.50),(37,.27),(93,.14),(231,.09)]:
        grid = rng.random((cells+1,cells+1), dtype=np.float32)
        grid[-1,:]=grid[0,:];grid[:,-1]=grid[:,0]
        ux=xx*cells/n;uy=yy*cells/n
        ix=ux.astype(int);iy=uy.astype(int)
        tx=ux-ix;ty=uy-iy
        tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
        cloud+=amp*((1-ty)*((1-tx)*grid[iy,ix]+tx*grid[iy,ix+1])+ty*((1-tx)*grid[iy+1,ix]+tx*grid[iy+1,ix+1]))
    pores=np.zeros_like(cloud)
    for _ in range(1050):
        cx,cy=rng.integers(0,n,2);rx=rng.uniform(1.5,9);ry=rng.uniform(.6,3)
        lx=int(math.ceil(rx*2));ly=int(math.ceil(ry*2))
        py,px=np.mgrid[-ly:ly+1,-lx:lx+1]
        stamp=np.exp(-2*((px/rx)**2+(py/ry)**2))*rng.uniform(.2,.85)
        iy=(cy+py)%n;ix=(cx+px)%n
        pores[iy,ix]=np.maximum(pores[iy,ix],stamp)
    shade=np.clip(.65+.64*cloud+.08*(grain-.5)-.58*pores,.15,1.4)
    color=np.clip(shade[:,:,None]*np.array([.44,.245,.095]),0,1)
    rough=np.clip(.77+.13*cloud+.08*pores,0,1)
    height=.60*cloud+.09*grain-.62*pores
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.42
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.42
    norm=np.stack((-dx,-dy,np.ones_like(dx)),axis=2)
    norm/=np.linalg.norm(norm,axis=2,keepdims=True)
    return {'BaseColor':image_file('T_PotionCork_BaseColor',color,True),
            'Roughness':image_file('T_PotionCork_Roughness',np.repeat(rough[:,:,None],3,axis=2)),
            'Normal':image_file('T_PotionCork_Normal',norm*.5+.5)}


def material(name, color, rough, metal=0, transmission=0, ior=1.45):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True;mat.use_fake_user=True;mat.diffuse_color=(*color,1)
    node=mat.node_tree.nodes.get('Principled BSDF')
    for key,value in [('Base Color',(*color,1)),('Roughness',rough),('Metallic',metal),('Transmission Weight',transmission),('IOR',ior)]:
        node.inputs[key].default_value=value
    mat['linear_base_color']=list(color)
    return mat


def make_materials():
    global MATERIALS
    maps=cork_maps()
    MATERIALS={
        'Glass':material('Glass',(.965,.985,.99),.075,transmission=1,ior=1.46),
        'Liquid':material('Liquid',SPEC['liquids']['health'],.09,transmission=.78,ior=1.333),
        'ManaLiquid':material('ManaLiquid',SPEC['liquids']['mana'],.09,transmission=.78,ior=1.333),
        'Cork':material('Cork',(.44,.245,.095),.82),
        'Pewter':material('Pewter',(.46,.48,.50),.29,metal=1),
        'Silver':material('Silver',(.67,.70,.74),.22,metal=1),
        'Brass':material('Brass',(.63,.43,.17),.24,metal=1)
    }
    cork=MATERIALS['Cork'];nodes=cork.node_tree.nodes;links=cork.node_tree.links
    shader=nodes.get('Principled BSDF')
    for kind,img in maps.items():
        tex=nodes.new('ShaderNodeTexImage');tex.image=img;tex.label=kind
        if kind=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.5
            links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:links.new(tex.outputs['Color'],shader.inputs['Base Color' if kind=='BaseColor' else 'Roughness'])
    for key in ('Pewter','Silver','Brass'):
        mat=MATERIALS[key];nodes=mat.node_tree.nodes;links=mat.node_tree.links
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=240
        noise.inputs['Detail'].default_value=2
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.035;bump.inputs['Distance'].default_value=.000015
        links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])


def monotone(points, step):
    # Shape-preserving cubic Hermite interpolation: no overshoot at the neck.
    p=np.array(points,dtype=float);z=p[:,0];h=np.diff(z);d=np.diff(p[:,1:],axis=0)/h[:,None]
    m=np.zeros_like(p[:,1:]);m[0]=d[0];m[-1]=d[-1]
    for k in range(1,len(p)-1):
        for a in range(2):
            if d[k-1,a]*d[k,a]>0:
                w1=2*h[k]+h[k-1];w2=h[k]+2*h[k-1]
                m[k,a]=(w1+w2)/(w1/d[k-1,a]+w2/d[k,a])
    result=[]
    for k in range(len(p)-1):
        count=max(1,int(math.ceil(h[k]/step)))
        for i in range(count):
            t=i/count;t2=t*t;t3=t2*t
            r=(2*t3-3*t2+1)*p[k,1:]+(t3-2*t2+t)*h[k]*m[k]+(-2*t3+3*t2)*p[k+1,1:]+(t3-t2)*h[k]*m[k+1]
            result.append((z[k]+h[k]*t,float(r[0]),float(r[1])))
    return result+[tuple(p[-1])]


def profile_at(profile,z):
    for a,b in zip(profile,profile[1:]):
        if a[0]<=z<=b[0]:
            t=(z-a[0])/(b[0]-a[0]);return (z,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t)
    return profile[-1]


def section_xy(theta,rx,ry,shape,z):
    # High bottle has a six-sided plan with gently rounded manufactured corners.
    # Special has a broad face and polished perimeter with an elliptical side.
    c,s=math.cos(theta),math.sin(theta)
    if shape=='hex' and z<149:
        polygon=[(.76,-1),(1,0),(.76,1),(-.76,1),(-1,0),(-.76,-1)]
        ray=(c,s);distance=1e9
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            ex,ey=b[0]-a[0],b[1]-a[1]
            den=ray[0]*ey-ray[1]*ex
            if abs(den)<1e-8:continue
            t=(a[0]*ey-a[1]*ex)/den
            u=(a[0]*ray[1]-a[1]*ray[0])/den
            if t>0 and 0<=u<=1:distance=min(distance,t)
        w=min(1,max(0,(149-z)/14))
        radius=1+(distance-1)*w
        return rx*c*radius,ry*s*radius
    if shape=='crystal' and z<149:
        # Superellipse gives a clear central viewing face, rounded gripping edges.
        power=2.8;w=min(1,max(0,(149-z)/18))
        sx=math.copysign(abs(c)**(2/power),c);sy=math.copysign(abs(s)**(2/power),s)
        return rx*(c+(sx-c)*w),ry*(s+(sy-s)*w)
    return rx*c,ry*s


def loft(name,profile,n,mat,collection,shape='round',cap=True):
    vertices=[];faces=[];uvs=[]
    zs=[p[0] for p in profile];lo=min(zs);height=max(max(zs)-lo,1)
    for z,rx,ry in profile:
        for i in range(n):
            x,y=section_xy(2*math.pi*i/n,rx,ry,shape,z)
            vertices.append((x*MM,y*MM,z*MM))
    for j in range(len(profile)-1):
        for i in range(n):
            ni=(i+1)%n
            faces.append((j*n+i,j*n+ni,(j+1)*n+ni,(j+1)*n+i))
            v0=(profile[j][0]-lo)/height;v1=(profile[j+1][0]-lo)/height
            uvs.append(((i/n,v0),((i+1)/n,v0),((i+1)/n,v1),(i/n,v1)))
    if cap:
        for row,reverse in [(0,True),(len(profile)-1,False)]:
            center=len(vertices);vertices.append((0,0,profile[row][0]*MM))
            for i in range(n):
                face=(center,row*n+(i+1)%n,row*n+i) if reverse else (center,row*n+i,row*n+(i+1)%n)
                faces.append(face)
                uvs.append(tuple((.5+vertices[v][0]/(2*max(profile[row][1]*MM,.001)),.5+vertices[v][1]/(2*max(profile[row][2]*MM,.001))) for v in face))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);mesh.materials.append(MATERIALS[mat])
    uv=mesh.uv_layers.new(name='UVMap')
    for face,coords in zip(mesh.polygons,uvs):
        face.use_smooth=len(face.vertices)==4
        for li,coord in zip(face.loop_indices,coords):uv.data[li].uv=coord
    # Real bevels soften the high-grade plane intersections without rounding away facets.
    if shape=='hex':
        mod=obj.modifiers.new('Polished facet edges 0.35mm','BEVEL');mod.width=.00035;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(22)
    return obj


def ring(name,z,height,rx,ry,thickness,mat,n,col,shape='round'):
    b=min(.55,height*.2)
    p=[(z,rx-b,ry-b),(z+b,rx,ry),(z+height-b,rx,ry),(z+height,rx-b,ry-b),
       (z+height,rx-thickness,ry-thickness),(z,rx-thickness,ry-thickness),(z,rx-b,ry-b)]
    return loft(name,p,n,mat,col,shape,cap=False)


def build(tier,n,step,label):
    col=bpy.data.collections.new(label);bpy.context.scene.collection.children.link(col)
    h=tier['size'][2];lip=h-16;shape=tier['shape']
    outer=monotone(tier['body'],step)
    # Mouth is genuinely open. The profile crosses the rim and returns down the interior.
    neck=[(lip-8,14.4,14.4),(lip-5.6,14.4,14.4),(lip-4.6,16,16),(lip-1,16,16),(lip,15.2,15.2)]
    for p in neck:
        if p[0]>outer[-1][0]:outer.append(p)
    inner=[(lip,12.0,12.0),(lip-8,12.0,12.0)]
    inside=[(z,max(rx-2,12),max(ry-2,12)) for z,rx,ry in outer if 4.5<=z<lip-8]
    inside.insert(0,(4.5,max(profile_at(outer,4.5)[1]-3,12),max(profile_at(outer,4.5)[2]-3,12)))
    inner+=list(reversed(inside))
    shell=[loft('Bottle_Glass',outer+inner,n,'Glass',col,shape)]
    if tier['metal']:
        shell.append(ring('Neck_Collar',lip-12,7,14.8,14.8,1.2,tier['metal'],n,col))
        shell.append(ring('Collar_Lower_Bead',lip-13,1.5,15.2,15.2,1.0,tier['metal'],n,col))
    if tier['id']=='medium':
        shell.extend([ring('Glass_Heel_Lower',1.5,2.5,30,23.8,1.4,'Glass',n,col),ring('Glass_Heel_Upper',6,2,30.3,23.8,1.4,'Glass',n,col)])
    elif tier['id'] in ('high','special'):
        z=2.0;_,rx,ry=profile_at(outer,5)
        shell.append(ring('Metal_Heel',z,4.6,rx+.65,ry+.65,1.5,tier['metal'],n,col,shape))
    fill=tier['fill_z'];low=6.2
    liquid_profile=[(z,rx-2.6,ry-2.6) for z,rx,ry in outer if low<z<fill]
    for z,insert in [(low,True),(fill,False)]:
        _,rx,ry=profile_at(outer,z);p=(z,rx-2.6,ry-2.6)
        if insert:liquid_profile.insert(0,p)
        else:liquid_profile.append(p)
    z,rx,ry=liquid_profile[-1]
    liquid_profile.extend([(z+.45,rx-.12,ry-.12),(z,rx-.7,ry-.7)])
    liquid=[loft('Liquid_Volume',liquid_profile,n,'Liquid',col,shape)]
    stopper=[loft('Natural_Cork',[(lip-10,11.6,11.6),(lip-8,11.9,11.9),(lip-1,12.25,12.25),(lip+1.5,13.1,13.1),(h-1 if not tier['metal'] else h-4,13.5,13.5),(h if not tier['metal'] else h-3,13.0,13.0)],n,'Cork',col)]
    if tier['metal']:
        stopper.append(loft('Stopper_Metal_Cap',[(h-4.2,13.3,13.3),(h-3.8,14.2,14.2),(h-1,14.2,14.2),(h-.4,13.8,13.8),(h,12.5,12.5)],n,tier['metal'],col))
    return col,{'Shell':shell,'Liquid':liquid,'Stopper':stopper}


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]


def evaluated_copy_join(objects,name):
    copies=[];deps=bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),depsgraph=deps)
        copy=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(copy);copies.append(copy)
    select(copies)
    if len(copies)>1:bpy.ops.object.join()
    result=bpy.context.object;result.name=name
    return result


def collision_for(obj):
    mesh=bpy.data.meshes.new('CollisionHull');bm=bmesh.new()
    # Sparse sample rings keep convex physics inexpensive; independent of render tessellation.
    verts=[v.co.copy() for v in obj.data.vertices]
    zlo=min(v.z for v in verts);zhi=max(v.z for v in verts)
    for z in np.linspace(zlo,zhi,8):
        nearby=[v for v in verts if abs(v.z-z)<max((zhi-zlo)/12,.002)]
        if not nearby:continue
        rx=max(abs(v.x) for v in nearby);ry=max(abs(v.y) for v in nearby)
        for i in range(12):
            a=i*math.tau/12;bm.verts.new((rx*math.cos(a),ry*math.sin(a),z))
    result=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    unused=[v for v in result.get('geom_interior',[])+result.get('geom_unused',[]) if isinstance(v,bmesh.types.BMVert) and v.is_valid]
    if unused:bmesh.ops.delete(bm,geom=list(set(unused)),context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    hull=bpy.data.objects.new('UCX_'+obj.name+'_00',mesh);bpy.context.scene.collection.objects.link(hull);hull.hide_render=True
    return hull


def export_fbx(objects,name,with_collision):
    obj=evaluated_copy_join(objects,name);hull=collision_for(obj) if with_collision else None
    select([obj]+([hull] if hull else []))
    path=EXPORT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',axis_forward='-Y',axis_up='Z',use_tspace=True)
    obj.data.calc_loop_triangles()
    info={'file':str(path),'triangles':len(obj.data.loop_triangles),'materials':[m.name for m in obj.data.materials],'collision':bool(hull)}
    for o in [obj]+([hull] if hull else []):bpy.data.objects.remove(o,do_unlink=True)
    return info


def main():
    report={'origin':'Original Blender profile/loft modeling from approved concept V01','units':'meters in Blender and FBX source; centimeters in UE','rendered':False,'tiers':{}}
    for tier in SPEC['tiers']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version=0
        scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
        make_materials()
        author,author_parts=build(tier,192,2.0,'Authoring_High')
        author.hide_viewport=True;author.hide_render=True
        entry={'size_mm':tier['size'],'parts':{},'lods':{},'liquid_bottom_cm':.62,'grip_height_cm':tier['size'][2]/10-4.8}
        lod_objects={part:[] for part in ['Shell','Liquid','Stopper','Closed']}
        for lod,n,step in [(0,96,4.0),(1,48,7.0),(2,24,12.0)]:
            col,parts=build(tier,n,step,'Game_LOD'+str(lod))
            for part,objects in dict(parts,Closed=sum(parts.values(),[])).items():
                base='SM_Potion_'+tier['name']+'_'+part
                name=base if lod==0 else base+'_LOD'+str(lod)
                info=export_fbx(objects,name,lod==0 and part!='Liquid')
                if lod==0:entry['parts'][part]=info
                else:entry['lods'].setdefault(part,[]).append(info)
                lod_objects[part].append(evaluated_copy_join(objects,base+'_LOD'+str(lod)))
            if lod==0:
                select(sum(parts.values(),[]))
                for family in ['health','mana']:
                    for obj in parts['Liquid']:obj.data.materials[0]=MATERIALS['Liquid' if family=='health' else 'ManaLiquid']
                    bpy.ops.export_scene.gltf(filepath=str(EXPORT/('Potion_'+tier['name']+'_'+family+'.glb')),export_format='GLB',use_selection=True,export_apply=True)
                for obj in parts['Liquid']:obj.data.materials[0]=MATERIALS['Liquid']
            col.hide_viewport=True;col.hide_render=True
        # Native FBX LOD groups import during the initial commandlet task, without
        # the interactive StaticMeshEditorSubsystem or a subsequent reimport.
        for part,objects in lod_objects.items():
            base='SM_Potion_'+tier['name']+'_'+part
            group=bpy.data.objects.new(base,None);scene.collection.objects.link(group);group['fbx_type']='LodGroup'
            for obj in objects:obj.parent=group
            hull=collision_for(objects[0]) if part!='Liquid' else None
            select(objects+[group]+([hull] if hull else []))
            path=EXPORT/(base+'_LODs.fbx')
            bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',axis_forward='-Y',axis_up='Z',use_tspace=True)
            entry['parts'][part]['file']=str(path)
            entry['parts'][part]['name']=base
            for obj in objects+[group]+([hull] if hull else []):bpy.data.objects.remove(obj,do_unlink=True)
        author.hide_viewport=False;author.hide_render=False
        anchors=bpy.data.collections.new('Animation_Anchors');scene.collection.children.link(anchors)
        for name,z in [('BottleBottom',0),('BottleMouth',tier['size'][2]-16),('GripReference',entry['grip_height_cm']*10),('LiquidBottom',6.2)]:
            obj=bpy.data.objects.new(name,None);anchors.objects.link(obj);obj.location.z=z*MM;obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.012
        for obj in sum(author_parts.values(),[]):obj['part']='Shell' if obj in author_parts['Shell'] else 'Liquid' if obj in author_parts['Liquid'] else 'Stopper'
        scene['design_source']=SPEC['reference'];scene['tier']=tier['id'];scene['authored_by']='Codex / original Blender construction'
        scene['liquid_variants']='Liquid=health, ManaLiquid=mana; identical geometry'
        scene['nominal_size_mm']=tier['size'];scene['runtime_grip_height_cm']=entry['grip_height_cm']
        scene.world=bpy.data.worlds.new('NeutralWorld');scene.world.color=(.12,.12,.12)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    area.spaces.active.region_3d.view_distance=.36
                    area.spaces.active.region_3d.view_location=(0,0,tier['size'][2]*MM*.5)
                    area.spaces.active.shading.color_type='MATERIAL'
        blend=OUT/('Potion_'+tier['name']+'_editable.blend')
        bpy.ops.wm.save_as_mainfile(filepath=str(blend));entry['blend']=str(blend)
        report['tiers'][tier['id']]=entry
        (OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('POTION_TIER_AUTHORED',tier['id'],flush=True)
    print('POTION_FOUR_TIERS_EXPORTED',flush=True)


if __name__=='__main__':main()
