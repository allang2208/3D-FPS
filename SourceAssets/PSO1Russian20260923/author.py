"""Author three fitted PSO-1 assemblies and host-specific 4K surface bakes."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;E=O/'Exports';T=O/'Textures'
E.mkdir(exist_ok=True);T.mkdir(exist_ok=True)
sources=json.loads((O/'sources.json').read_text())
markers=json.loads((S/'SVDCompletion20260923/authoring.json').read_text())['markers_root_m']
placements={'AKM':(.010,-.035,.035),'A762':(.010,-.015,.035),'PKM':(.075,.035,.035)}
report={'hosts':{},'source':'SVD corrected UV0 PSO-1; CC BY 4.0 LeroyCake','tests_run':False}
bpy.context.preferences.filepaths.save_version=0

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]

def load_image(path,srgb=False):
    im=bpy.data.images.load(str(path),check_existing=True)
    im.colorspace_settings.name='sRGB' if srgb else 'Non-Color'
    return im

for host,delta in placements.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/(host+'_ReceiverReference.blend')))
    # Receiver-only contact surface excludes all mechanical motion groups.
    refs=list(bpy.context.scene.objects);vertices=[];faces=[]
    for ob in refs:
        if ob.type!='MESH':continue
        names={g.index:g.name for g in ob.vertex_groups}
        fixed={v.index for v in ob.data.vertices if any(names.get(g.group)=='WPN_root' and g.weight>.9 for g in v.groups)}
        offset=len(vertices);vertices.extend([tuple(v.co) for v in ob.data.vertices])
        faces.extend([tuple(offset+i for i in p.vertices) for p in ob.data.polygons if all(i in fixed for i in p.vertices)])
    receiver=BVHTree.FromPolygons(vertices,faces)
    reference=bpy.data.collections.new('HOST_RECEIVER_REFERENCE');bpy.context.scene.collection.children.link(reference)
    for ob in refs:
        for col in list(ob.users_collection):col.objects.unlink(ob)
        reference.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
    with bpy.data.libraries.load(str(O/'PSO_SourceRoot.blend'),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n.startswith('PSO_')]
    optic=list(dst.objects)
    for ob in optic:bpy.context.scene.collection.objects.link(ob);ob.data.transform(Matrix.Translation(delta))
    opaque=[o for o in optic if 'Lens' not in o.name]
    lens=next(o for o in optic if 'Lens' in o.name)

    # Source structural UV0 is untouched. UV1 projects just the host coating,
    # at the same physical scale as that host's accepted receiver/optic coating.
    tile=(.12,.025) if host=='AKM' else (.05,.05) if host=='A762' else (.024,.05)
    for ob in opaque:
        ob.data.uv_layers[0].name='SourceUV'
        uv=ob.data.uv_layers.new(name='HostCoatingUV')
        mask=ob.data.color_attributes.new(name='PSO_CoatingRegion',type='FLOAT_COLOR',domain='CORNER')
        for f in ob.data.polygons:
            axis=max(range(3),key=lambda k:abs(f.normal[k]));axes=[i for i in range(3) if i!=axis]
            radial=Vector((f.center.x-delta[0],0,f.center.z-delta[2]-.1023702845))
            inward=(f.center.z-delta[2]>.075 and radial.length<.026 and abs(f.normal.y)<.85 and f.normal.dot(radial)<-.0001)
            for li in f.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(p[axes[0]]/tile[0]+.5,p[axes[1]]/tile[1]+.5)
                mask.data[li].color=(0 if inward else 1,)*3+(1,)
        ob.data.uv_layers.active_index=0

    mat=bpy.data.materials.new('PSO1_'+host+'_Shell');mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    uv0=nodes.new('ShaderNodeUVMap');uv0.uv_map='SourceUV'
    uv1=nodes.new('ShaderNodeUVMap');uv1.uv_map='HostCoatingUV'
    def tex(image,uv):
        n=nodes.new('ShaderNodeTexImage');n.image=image;links.new(uv.outputs[0],n.inputs['Vector']);return n.outputs['Color']
    def mathnode(op,a,b):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for socket,val in zip(n.inputs,[a,b]):
            if hasattr(val,'node'):links.new(val,socket)
            else:socket.default_value=val
        return n.outputs[0]
    def mix(factor,a,b):
        n=nodes.new('ShaderNodeMixRGB');n.blend_type='MIX';links.new(factor,n.inputs[0])
        for socket,val in zip(list(n.inputs)[1:],[a,b]):
            if hasattr(val,'node'):links.new(val,socket)
            else:socket.default_value=val
        return n.outputs[0]
    base=tex(load_image(S/'SVDSurface20260923/Textures/T_SVD_Surface_pso_BaseColor.png',True),uv0)
    orm=tex(load_image(S/'SVDSurface20260923/Textures/T_SVD_Surface_pso_ORM.png'),uv0)
    sep=nodes.new('ShaderNodeSeparateColor');links.new(orm,sep.inputs[0])
    region=nodes.new('ShaderNodeVertexColor');region.layer_name='PSO_CoatingRegion'
    # The SVD surface ORM already separates lettering and rubber from metal.
    metalmask=mathnode('MINIMUM',1,mathnode('MAXIMUM',0,mathnode('MULTIPLY',mathnode('SUBTRACT',sep.outputs['Blue'],.15),5)))
    coating=mathnode('MULTIPLY',metalmask,region.outputs['Color'])
    if host=='A762':
        info=sources['a762_finish'];color=tuple(info['color'])+(1,)
        grain=tex(load_image(sources['textures']['A762_Grain']['source'][0]),uv1)
        rough=mathnode('ADD',info['roughness'],mathnode('MULTIPLY',mathnode('SUBTRACT',grain,.5),.018))
        metal=info['metallic']
    elif host=='AKM':
        color=tex(load_image(sources['textures']['AKM_BaseColor']['source'][0],True),uv1)
        rough=tex(load_image(sources['textures']['AKM_Roughness']['source'][0]),uv1)
        metal=tex(load_image(sources['textures']['AKM_Metallic']['source'][0]),uv1)
    else:
        color=tex(load_image(sources['textures']['PKM_BaseColor']['source'][0],True),uv1)
        packed=tex(load_image(sources['textures']['PKM_ORM']['source'][0]),uv1)
        hostorm=nodes.new('ShaderNodeSeparateColor');links.new(packed,hostorm.inputs[0])
        rough=hostorm.outputs['Green'];metal=hostorm.outputs['Blue']
    color=mix(coating,base,color)
    rough=mix(coating,sep.outputs['Green'],rough if hasattr(rough,'node') else (rough,)*3+(1,))
    metal=mix(coating,sep.outputs['Blue'],metal if hasattr(metal,'node') else (metal,)*3+(1,))
    packed=nodes.new('ShaderNodeCombineColor')
    for socket,value in zip(packed.inputs,[sep.outputs['Red'],rough,metal]):links.new(value,socket)
    bs=nodes.new('ShaderNodeBsdfPrincipled');links.new(color,bs.inputs['Base Color']);links.new(rough,bs.inputs['Roughness']);links.new(metal,bs.inputs['Metallic'])
    normalimage=load_image(S/'SVDDragunov20260922/Textures/T_SVD_pso_normal.png')
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='SourceUV';normal.inputs['Strength'].default_value=1
    links.new(tex(normalimage,uv0),normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
    out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs[0])
    for ob in opaque:ob.data.materials.clear();ob.data.materials.append(mat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
    scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=16
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except Exception:scene.cycles.device='CPU'
    baked={}
    for kind,value in [('BaseColor',color),('ORM',packed.outputs[0])]:
        image=bpy.data.images.new('T_PSO1_'+host+'_'+kind,width=4096,height=4096,alpha=False)
        image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        target=nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage');target.name='BAKE_TARGET';target.image=image;nodes.active=target
        emit=nodes.get('BAKE_EMISSION') or nodes.new('ShaderNodeEmission');emit.name='BAKE_EMISSION';links.new(value,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs[0])
        select(opaque);bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save();baked[kind]=image
    links.new(bs.outputs[0],out.inputs[0])
    # Keep the full author graph as a source; the visible/export material uses the bake.
    mat.name='AUTHOR_PSO1_'+host;mat.use_fake_user=True
    surface=bpy.data.materials.new('PSO1_'+host+'_Shell');surface.use_nodes=True
    n=surface.node_tree.nodes;l=surface.node_tree.links;p=n.get('Principled BSDF')
    uv=n.new('ShaderNodeUVMap');uv.uv_map='SourceUV'
    for kind in ['BaseColor','ORM','Normal']:
        t=n.new('ShaderNodeTexImage');t.image=normalimage if kind=='Normal' else baked[kind];l.new(uv.outputs[0],t.inputs['Vector'])
        if kind=='BaseColor':l.new(t.outputs['Color'],p.inputs['Base Color'])
        elif kind=='ORM':
            split=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],p.inputs['Roughness']);l.new(split.outputs['Blue'],p.inputs['Metallic'])
        else:
            nm=n.new('ShaderNodeNormalMap');nm.uv_map='SourceUV';l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
    for ob in opaque:ob.data.materials[0]=surface
    adaptermat=bpy.data.materials.new('PSO1_'+host+'_Adapter');adaptermat.use_nodes=True
    an=adaptermat.node_tree.nodes;al=adaptermat.node_tree.links;ab=an.get('Principled BSDF')
    if host=='A762':
        ab.inputs['Base Color'].default_value=tuple(sources['a762_finish']['color'])+(1,)
        ab.inputs['Metallic'].default_value=sources['a762_finish']['metallic'];ab.inputs['Roughness'].default_value=sources['a762_finish']['roughness']
    else:
        for role in ['BaseColor','ORM'] if host=='PKM' else ['BaseColor','Metallic','Roughness']:
            node=an.new('ShaderNodeTexImage');node.image=load_image(sources['textures'][host+'_'+role]['source'][0],role=='BaseColor')
            if role=='ORM':
                split=an.new('ShaderNodeSeparateColor');al.new(node.outputs['Color'],split.inputs[0]);al.new(split.outputs['Green'],ab.inputs['Roughness']);al.new(split.outputs['Blue'],ab.inputs['Metallic'])
            else:al.new(node.outputs['Color'],ab.inputs['Base Color' if role=='BaseColor' else role])

    # Contoured receiver pads support a shallow open bridge and dovetail shoe.
    # PKM's bridge extends laterally below the cover; no part is attached to the lid.
    pieces=[];contacts=[];cy=-.0613+delta[1];cz=.015+delta[2];outside=.0133+delta[0]
    def finish(ob):
        select([ob]);ob.data.materials.clear();ob.data.materials.append(adaptermat)
        bevel=ob.modifiers.new('Machined edges','BEVEL');bevel.width=.0004;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
        for p in ob.data.polygons:p.use_smooth=True
        weighted=ob.modifiers.new('Area normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=weighted.name)
        triangulate=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=triangulate.name)
        ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
        for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
        uv=ob.data.uv_layers.new(name='HostCoatingUV')
        for face in ob.data.polygons:
            axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
            for li in face.loop_indices:
                v=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(v[axes[0]]/tile[0]+.5,v[axes[1]]/tile[1]+.5)
        pieces.append(ob);return ob
    def cube(name,p,size):
        bpy.ops.mesh.primitive_cube_add(size=1,location=p);ob=bpy.context.object;ob.name=name;ob.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(ob)
    for j,y in enumerate([cy-.027,cy+.027]):
        pad=[]
        for yy,zz in [(y-.010,cz-.009),(y+.010,cz-.009),(y+.010,cz+.009),(y-.010,cz+.009)]:
            p,n,i,d=receiver.ray_cast(Vector((.2,yy,zz)),Vector((-1,0,0)),.4)
            if p is None:raise RuntimeError('Missing receiver contact '+host+str((yy,zz)))
            contacts.append(list(p));pad.append(tuple(p-Vector((.0001,0,0))))
        # A short overlap seats the bridge on a real receiver surface.
        top=max(p[0] for p in pad)+.004
        verts=pad+[(top,p[1],p[2]) for p in pad]
        me=bpy.data.meshes.new('ReceiverContact');me.from_pydata(verts,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);me.update()
        ob=bpy.data.objects.new(host+'_ContouredPad_'+str(j),me);scene.collection.objects.link(ob);finish(ob)
        # Tapered cross arm; smaller outboard height meets the original PSO clamp.
        end=outside+.002
        cube(host+'_BridgeArm_'+str(j),((top+end)/2,y,cz),(abs(end-top)+.001,.012,.009))
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.003,depth=.003,location=(end+.001,y,cz),rotation=(0,math.pi/2,0))
        bolt=bpy.context.object;bolt.name=host+'_ClampBolt_'+str(j);finish(bolt)
    cube(host+'_DovetailSpine',(outside,cy,cz),(.004,.078,.014))
    # Chamfered stop supports the longitudinal clamp without altering the source lever.
    cube(host+'_RecoilStop',(outside+.001,cy-.039,cz),(.006,.004,.019))
    optic.extend(pieces)
    # Glass remains a distinct surface. It is hidden with the viewmodel in full ADS.
    glass=bpy.data.materials.new('PSO1_OpticalGlass');glass.use_nodes=True
    gb=glass.node_tree.nodes.get('Principled BSDF');gb.inputs['Base Color'].default_value=(.018,.038,.045,1)
    gb.inputs['Roughness'].default_value=.1;gb.inputs['Metallic'].default_value=.05;gb.inputs['Transmission Weight'].default_value=.86
    lens.data.materials.clear();lens.data.materials.append(glass)

    # Asset +X is optical forward. Runtime yaw +90 maps it onto the host's +Y.
    canonical=Matrix.Rotation(math.pi/2,4,'Z')
    for ob in optic:ob.data.transform(canonical)
    def marker(key):
        p=canonical@(Vector(markers[key])+Vector(delta));return [p.x*100,-p.y*100,p.z*100]
    sockets={'AimCenter':marker('WPN_RearSight'),'AimFront':marker('WPN_FrontSight')}
    select(optic)
    name='SM_PSO1_'+host
    bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    # Match author assembly to the runtime mount, keeping reference geometry hidden.
    for ob in optic:ob.matrix_world=canonical.inverted()
    bpy.ops.wm.save_as_mainfile(filepath=str(O/('PSO1_'+host+'_Editable.blend')))
    report['hosts'][host]={'mesh':name,'translation_root_m':list(delta),'sockets_cm':sockets,
      'bone':'WPN_root','yaw_degrees':90,'relative_scale':.01,'coating_tile_m':list(tile),
      'contacts_root_m':contacts,'textures':{k:str(v.filepath_raw) for k,v in baked.items()},
      'slots':[surface.name,adaptermat.name,glass.name],
      'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in optic)}
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    print('PSO1_HOST_AUTHORED',host,flush=True)
print('PSO1_AUTHORING_COMPLETE',flush=True)
