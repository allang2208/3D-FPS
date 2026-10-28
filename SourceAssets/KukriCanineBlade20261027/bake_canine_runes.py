"""Bake aspect-preserving glyphs onto each production blade's own UV0."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
OLD=P.parent/'KukriComponentVariants20261026'
sys.path.insert(0,str(OLD))
from asset_tools import activate, make_mat, node, op, tex

(P/'Textures').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=1
scene.render.bake.margin=4
scene.render.bake.use_clear=True
scene.render.bake.use_selected_to_active=False
plans=[p for p in json.loads((OLD/'design-prompts.json').read_text(encoding='utf-8'))['plans'] if p['slot']=='blade_2']
sources=json.loads((P/'blade-layout-source.json').read_text(encoding='utf-8'))
receipt=json.loads((OLD/'runes.json').read_text(encoding='utf-8'))
entries={v['id']:v for v in receipt['runes']}
layouts=[]
for source in sources:
    with bpy.data.libraries.load(source['blend'],link=False) as (available,loaded):
        loaded.objects=[source['object']]
    blade=loaded.objects[0]
    scene.collection.objects.link(blade)
    mesh=blade.data
    bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(f.vertices) for f in mesh.polygons])
    xmin,xmax=source['bounds'][0]
    def on_face(x,z):
        hit,normal,face,distance=bvh.ray_cast(Vector((x,.03,z)),Vector((0,-1,0)),.06)
        return hit is not None and abs(normal.y)>.88
    def face_center(z):
        xs=[xmin+(xmax-xmin)*i/400 for i in range(401)]
        valid=[x for x in xs if on_face(x,z)]
        if not valid:raise RuntimeError('No usable blade face: '+source['kind'])
        return (min(valid)+max(valid))*.5
    z0=.150
    x0=face_center(z0)
    slope=(face_center(z0+.012)-face_center(z0-.012))/.024
    angle=math.atan(slope)
    c,s=math.cos(angle),math.sin(angle)
    for plan in plans:
        glyph=bpy.data.images.load(str(OLD/'Concepts'/(plan['id']+'.png')),check_existing=True)
        w,h=glyph.size
        pixels=list(glyph.pixels)
        aspect=w/h
        samples=[]
        for iy in range(0,h,max(1,h//64)):
            for ix in range(0,w,max(1,w//64)):
                offset=4*(iy*w+ix)
                if min(pixels[offset:offset+3])*pixels[offset+3]>.92:
                    samples.append(((ix+.5)/w-.5,(iy+.5)/h-.5))
        def fits(height):
            for u,v in samples:
                dx=u*height*aspect
                dz=v*height
                x=x0+dx*c+dz*s
                z=z0-dx*s+dz*c
                if not all(on_face(x+mx,z+mz) for mx,mz in ((0,0),(.001,0),(-.001,0),(0,.001),(0,-.001))):
                    return False
            return True
        lo,hi=.012,.040
        if not fits(lo):raise RuntimeError('Glyph cannot fit blade face: '+source['kind'])
        for iteration in range(12):
            mid=(lo+hi)*.5
            if fits(mid):lo=mid
            else:hi=mid
        height=lo*.95
        width=height*aspect
        mat,nt,bs,out=make_mat('BakeNatural_'+source['kind']+'_'+plan['kind'])
        mesh.materials.clear()
        mesh.materials.append(mat)
        for polygon in mesh.polygons:polygon.material_index=0
        coords=node(nt,'ShaderNodeTexCoord')
        xyz=node(nt,'ShaderNodeSeparateXYZ')
        nt.links.new(coords.outputs['Object'],xyz.inputs[0])
        x,y,z=xyz.outputs
        dx=op(nt,'SUBTRACT',x,x0)
        dz=op(nt,'SUBTRACT',z,z0)
        # Orthonormal rotation and a common centimetres-per-pixel scale; no shear.
        u=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'SUBTRACT',op(nt,'MULTIPLY',dx,c),op(nt,'MULTIPLY',dz,s)),width),.5)
        v=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'ADD',op(nt,'MULTIPLY',dx,s),op(nt,'MULTIPLY',dz,c)),height),.5)
        uv=node(nt,'ShaderNodeCombineXYZ')
        nt.links.new(u,uv.inputs[0]);nt.links.new(v,uv.inputs[1])
        texture=tex(nt,OLD/'Concepts'/(plan['id']+'.png'))
        texture.extension='CLIP'
        nt.links.new(uv.outputs[0],texture.inputs['Vector'])
        gray=node(nt,'ShaderNodeRGBToBW')
        nt.links.new(texture.outputs['Color'],gray.inputs[0])
        ink=op(nt,'GREATER_THAN',op(nt,'MULTIPLY',gray.outputs[0],texture.outputs['Alpha']),.92)
        geometry=node(nt,'ShaderNodeNewGeometry')
        normal=node(nt,'ShaderNodeSeparateXYZ')
        nt.links.new(geometry.outputs['True Normal'],normal.inputs[0])
        side=op(nt,'GREATER_THAN',op(nt,'ABSOLUTE',normal.outputs['Y']),.88)
        ink=op(nt,'MULTIPLY',ink,side)
        emission=node(nt,'ShaderNodeEmission')
        nt.links.new(ink,emission.inputs['Color']);nt.links.new(emission.outputs[0],out.inputs['Surface'])
        name='T_KukriMask_'+source['kind']+'_'+plan['kind']
        image=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
        image.colorspace_settings.name='Non-Color'
        target=node(nt,'ShaderNodeTexImage');target.image=image;nt.nodes.active=target
        activate(blade)
        bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(P/'Textures'/(name+'.png'))
        image.file_format='PNG';image.save()
        entry=entries[plan['id']]
        entry.setdefault('blade_masks',{})[source['kind']]=image.filepath_raw
        if source['kind']=='Factory':entry['mask']=image.filepath_raw
        layouts.append({'blade':source['kind'],'id':plan['id'],'center':[x0,z0],
                        'angle_degrees':math.degrees(angle),'width_m':width,'height_m':height,
                        'source_aspect':aspect,'projection_aspect':width/height,'mask':image.filepath_raw})
        print('RUNE_BAKED '+source['kind']+' '+plan['id'],flush=True)
    blade.hide_render=True;blade.hide_set(True)
receipt['surface_revision']='canine-isometric-per-blade-20261027'
receipt['runes']=list(entries.values())
(P/'runes.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')

(P/'placements.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Canine_Runes_Editable.blend'))
