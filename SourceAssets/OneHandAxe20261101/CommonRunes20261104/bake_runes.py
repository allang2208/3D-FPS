"""Fit a uniform-scale physical glyph window on each real head, then bake its own UV0."""
import bpy,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'KukriComponentVariants20261026'))
from asset_tools import activate,make_mat,node,op,tex
source=json.loads((P/'sources.json').read_text('utf-8'))
kind=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else None
heads=[h for h in source['heads'] if kind is None or h['kind']==kind]
for head in heads:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
    scene.render.bake.margin=4;scene.render.bake.use_clear=True
    scene.render.bake.use_selected_to_active=False
    with bpy.data.libraries.load(head['blend'],link=False) as (available,loaded):
        loaded.objects=[head['object']]
    blade=loaded.objects[0];scene.collection.objects.link(blade)
    mesh=blade.data;mesh.calc_loop_triangles()
    triangles=list(mesh.loop_triangles)
    positions=[v.co.copy() for v in mesh.vertices]
    bvh=BVHTree.FromPolygons(positions,[tuple(t.vertices) for t in triangles],all_triangles=True)
    base=bpy.data.images.load(head['basecolor_file'],check_existing=True)
    pixels=np.empty(len(base.pixels),np.float32);base.pixels.foreach_get(pixels)
    iw,ih=base.size;pixels=pixels.reshape(ih,iw,4)
    uv=mesh.uv_layers[0]
    fitting_counts={'miss':0,'normal':0,'basecolor':0,'accepted':0}
    def body_surface(x,z,side):
        hit,normal,ti,distance=bvh.ray_cast(Vector((x,side*.05,z)),Vector((0,-side,0)),.10)
        if hit is None:fitting_counts['miss']+=1;return False
        tri=triangles[ti];a,b,c=[positions[v] for v in tri.vertices]
        v0=b-a;v1=c-a;v2=hit-a
        d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1)
        d20=v2.dot(v0);d21=v2.dot(v1);den=d00*d11-d01*d01
        if abs(den)<1e-20:return False
        b1=(d11*d20-d01*d21)/den;b2=(d00*d21-d01*d20)/den
        smooth_normal=sum((mesh.corner_normals[li].vector*w for li,w in zip(tri.loops,(1-b1-b2,b1,b2))),Vector()).normalized()
        if smooth_normal.y*side<.97:fitting_counts['normal']+=1;return False
        coord=sum((uv.data[li].uv*w for li,w in zip(tri.loops,(1-b1-b2,b1,b2))),Vector((0.,0.)))
        ix=min(iw-1,max(0,int(coord.x*iw)));iy=min(ih-1,max(0,int(coord.y*ih)))
        # Keep the light ground edge out of the body-only placement domain.
        accepted=float(np.mean(pixels[max(0,iy-5):min(ih,iy+6),max(0,ix-5):min(iw,ix+6),:3]))<.40
        fitting_counts['accepted' if accepted else 'basecolor']+=1
        return accepted
    step=.001
    xs=np.arange(.018,.181,step);zs=np.arange(.185,.311,step)
    usable=np.array([[body_surface(float(x),float(z),1) and body_surface(float(x),float(z),-1)
                      for x in xs] for z in zs],dtype=bool)
    # Both faces must carry the entire glyph rectangle plus 3 mm of clear body.
    integral=np.pad(usable.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
    print('FIT_DOMAIN '+head['kind']+' '+str(fitting_counts)+' bounds='+str([[min(v[i] for v in positions),max(v[i] for v in positions)] for i in range(3)]),flush=True)
    preferred=np.array([.085,.245]) if head['kind']!='SwiftCrescent' else np.array([.070,.255])
    plans=[]
    for rune in source['runes']:
        glyph=bpy.data.images.load(rune['glyph'],check_existing=True)
        aspect=glyph.size[0]/glyph.size[1]
        chosen=None
        for mm in range(50,17,-1):
            h=mm*.001;w=h*aspect
            nx=math.ceil((w+.006)/step)+1;nz=math.ceil((h+.006)/step)+1
            if nx>len(xs) or nz>len(zs):continue
            sums=integral[nz:,nx:]-integral[:-nz,nx:]-integral[nz:,:-nx]+integral[:-nz,:-nx]
            iz,ix=np.where(sums==nx*nz)
            if len(ix):
                centers=np.column_stack((xs[ix]+(nx-1)*step*.5,zs[iz]+(nz-1)*step*.5))
                choice=int(np.argmin(np.sum((centers-preferred)**2,axis=1)))
                chosen=(*centers[choice],w,h);break
        if chosen is None:raise RuntimeError('No body-only uniform window for '+head['kind'])
        x0,z0,width,height=[float(v) for v in chosen]
        mat,nt,bs,out=make_mat('BakeHatchet_'+head['kind']+'_'+rune['kind'])
        mesh.materials.clear();mesh.materials.append(mat)
        for poly in mesh.polygons:poly.material_index=0
        coords=node(nt,'ShaderNodeTexCoord');xyz=node(nt,'ShaderNodeSeparateXYZ')
        nt.links.new(coords.outputs['Object'],xyz.inputs[0])
        geometry=node(nt,'ShaderNodeNewGeometry')
        to_local=node(nt,'ShaderNodeVectorTransform',vector_type='NORMAL',convert_from='WORLD',convert_to='OBJECT')
        nt.links.new(geometry.outputs['Normal'],to_local.inputs['Vector'])
        normal=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(to_local.outputs[0],normal.inputs[0])
        # Each outward-facing side reads the same glyph, with an orthogonal basis and no shear.
        orientation=op(nt,'MULTIPLY',op(nt,'SIGN',normal.outputs['Y']),-1)
        U=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'MULTIPLY',op(nt,'SUBTRACT',xyz.outputs['X'],x0),orientation),width),.5)
        V=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'SUBTRACT',xyz.outputs['Z'],z0),height),.5)
        coords2=node(nt,'ShaderNodeCombineXYZ')
        nt.links.new(U,coords2.inputs[0]);nt.links.new(V,coords2.inputs[1])
        texture=tex(nt,rune['glyph']);texture.extension='CLIP'
        nt.links.new(coords2.outputs[0],texture.inputs['Vector'])
        gray=node(nt,'ShaderNodeRGBToBW');nt.links.new(texture.outputs['Color'],gray.inputs[0])
        ink=op(nt,'GREATER_THAN',op(nt,'MULTIPLY',gray.outputs[0],texture.outputs['Alpha']),.92)
        ink=op(nt,'MULTIPLY',ink,op(nt,'GREATER_THAN',op(nt,'ABSOLUTE',normal.outputs['Y']),.97))
        emission=node(nt,'ShaderNodeEmission');nt.links.new(ink,emission.inputs['Color'])
        nt.links.new(emission.outputs[0],out.inputs['Surface'])
        name='T_HatchetRune_'+head['kind']+'_'+rune['kind']
        image=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
        image.colorspace_settings.name='Non-Color'
        target=node(nt,'ShaderNodeTexImage');target.image=image;nt.nodes.active=target
        activate(blade);bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(P/'Textures'/(name+'.png'));image.file_format='PNG';image.save();image.pack()
        plans.append(dict(id=rune['id'],kind=rune['kind'],mask=image.filepath_raw,
            center_m=[x0,z0],width_m=width,height_m=height,source_aspect=aspect,
            centimetres_per_pixel=[width*100/glyph.size[0],height*100/glyph.size[1]],
            face_normal_y_min=.97,body_margin_mm=3,projection='head local isometric XZ; outward-readable two sides; baked UV0'))
        glyph.pack()
        print('HATCHET_RUNE_BAKED '+head['kind']+' '+rune['id']+' size_mm='+str(round(width*1000,2)),flush=True)
    head['placements']=plans
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'Editable'/(head['kind']+'_RunePlacement_Editable.blend')))
    (P/(head['kind']+'.json')).write_text(json.dumps(head,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HATCHET_RUNE_BAKING_FINISHED',flush=True)
