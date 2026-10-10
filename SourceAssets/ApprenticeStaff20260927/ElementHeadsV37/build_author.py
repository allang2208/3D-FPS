"""Produce a standalone V37 author from the established centimetre/FBX baker."""
from pathlib import Path
root=Path(__file__).resolve().parent
text=(root.parent/'CrystalCraftV33/author_blender.py').read_text(encoding='utf-8')
text=text.replace('V33','V37').replace("scene['revision']=33","scene['revision']=37").replace("'revision':33","'revision':37")
start=text.index('def craft_facets(')
end=text.index('\n\nclass Graph:',start)
text=text[:start]+'''def weighted_finish(obj):
    # Keep broad optical faces and round only the small edge bevels.
    activate(obj)
    mod=obj.modifiers.new('Area weighted polish normals','WEIGHTED_NORMAL')
    mod.keep_sharp=True
    mod.weight=40
    bpy.ops.object.modifier_apply(modifier=mod.name)


def craft_mount(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[e for e in bm.edges if e.is_manifold and
           min(v.co.z for v in e.verts)>62.25 and e.calc_face_angle()>.40]
    result=bmesh.ops.bevel(bm,geom=edges,offset=.028,segments=2,
                           affect='EDGES',clamp_overlap=True)
    for f in result['faces']:f.smooth=True
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    weighted_finish(obj)


def craft_facets(obj, kind):
    # Inherit V33's inward envelope, without repeatedly beveling the V33 mesh.
    for v in obj.data.vertices:
        a=math.atan2(v.co.y,v.co.x);z=v.co.z
        if z>65.3:
            inward=.975-.020*(.5+.5*math.sin(a*3.+z*.47))
            v.co.x*=inward;v.co.y*=inward
    bm=bmesh.new();bm.from_mesh(obj.data)
    seam=bm.faces.layers.int.new('MoltenSeam')
    if kind=='Magma':
        bm.normal_update()
        # Sink the shared edges first, then raise inset faces to the old shell.
        # The fissures therefore have depth and remain inside the old envelope.
        for v in bm.verts:v.co-=v.normal*.105
        result=bmesh.ops.inset_individual(bm,faces=list(bm.faces),
            thickness=.075,depth=.10,use_even_offset=True,use_relative_offset=False)
        for f in result['faces']:f[seam]=1
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>.34]
        bevel=bmesh.ops.bevel(bm,geom=edges,offset=.013,segments=1,
                             affect='EDGES',clamp_overlap=True)
    else:
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>.15]
        bevel=bmesh.ops.bevel(bm,geom=edges,
            offset={'Ice':.060,'Jade':.125,'Storm':.065}[kind],
            segments=3 if kind=='Jade' else 2,affect='EDGES',clamp_overlap=True)
    for f in bm.faces:f.smooth=False
    for f in bevel['faces']:f.smooth=True
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    color=bm.loops.layers.color.new('MineralData')
    for f in bm.faces:
        for loop in f.loops:loop[color]=(float(f[seam]),0,0,1)
    bm.to_mesh(obj.data);bm.free()
    weighted_finish(obj)
    unwrap(obj)
''' +text[end:]
start=text.index('def recipe(');end=text.index('\n\ndef bake(',start)
text=text[:start]+'''def recipe(kind):
    g=Graph('M_StaffCraft_'+kind+'_V37')
    coord=g.coord
    stretch=g.node('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    g.input(stretch,0,coord)
    g.input(stretch,1,{'Ice':(12.,12.,.8),'Jade':(2.8,2.8,.55),
                      'Storm':(1.4,1.4,2.0),'Mount':(3.,3.,42.)}.get(kind,(1.,1.,1.)))
    g.coord=stretch.outputs[0]
    strand=g.noise(5.2,3)
    g.coord=coord
    cloud=g.noise(3.8,4,.60);grain=g.noise(155,2,.60)
    z=g.node('ShaderNodeSeparateXYZ');g.input(z,'Vector',coord)
    root=g.ramp(z.outputs['Z'],[(0,(1,1,1)),(.22,(0,0,0))])
    if kind=='Ice':
        color=g.ramp(cloud,[(.20,(.028,.105,.16)),(.53,(.085,.27,.36)),(.82,(.29,.52,.58))])
        lines=g.ramp(strand,[(.55,(0,0,0)),(.69,(.23,.23,.23)),(.85,(.48,.48,.48))])
        color=g.mix(lines,color,(.25,.52,.60,1))
        rough=g.math('ADD',g.range(cloud,.065,.145),g.math('MULTIPLY',lines,.10))
        opacity=g.math('ADD',g.range(cloud,.23,.36),g.math('MULTIPLY',root,.07))
        glow=g.math('MULTIPLY',lines,.16)
        bump_height=g.math('ADD',g.math('MULTIPLY',grain,.008),g.math('MULTIPLY',strand,.025))
        transmission=.72
    elif kind=='Magma':
        attr=g.node('ShaderNodeVertexColor');attr.layer_name='MineralData'
        sep=g.node('ShaderNodeSeparateColor');g.input(sep,'Color',attr.outputs['Color'])
        heat=g.math('MULTIPLY',sep.outputs['Red'],g.range(cloud,.45,1.))
        color=g.ramp(cloud,[(.20,(.006,.008,.009)),(.53,(.024,.020,.016)),(.82,(.070,.042,.024))])
        color=g.mix(heat,color,(.49,.043,.003,1))
        rough=g.mix(heat,g.range(grain,.32,.61),(.21,.21,.21,1))
        opacity=1.;glow=heat
        pits=g.ramp(grain,[(.36,(0,0,0)),(.60,(.32,.32,.32)),(.74,(1,1,1))])
        bump_height=g.math('MULTIPLY',pits,.19)
        transmission=0.
    elif kind=='Jade':
        mineral=g.math('ADD',g.math('MULTIPLY',cloud,.62),g.math('MULTIPLY',strand,.38))
        color=g.ramp(mineral,[(.20,(.007,.034,.018)),(.43,(.015,.10,.050)),
            (.60,(.072,.25,.128)),(.80,(.26,.45,.25))])
        vein=g.ramp(strand,[(.53,(0,0,0)),(.66,(.12,.12,.12)),(.80,(.30,.30,.30))])
        color=g.mix(vein,color,(.32,.44,.24,1))
        rough=g.range(mineral,.125,.245);opacity=1.
        glow=g.math('MULTIPLY',vein,.18)
        bump_height=g.math('MULTIPLY',grain,.012)
        transmission=.08
        g.bs.inputs['Subsurface Weight'].default_value=.24
        g.bs.inputs['Subsurface Radius'].default_value=(.18,.45,.22)
    elif kind=='Storm':
        color=g.ramp(cloud,[(.20,(.018,.012,.048)),(.54,(.060,.037,.16)),(.82,(.20,.13,.32))])
        rough=g.range(cloud,.075,.17)
        opacity=g.math('ADD',g.range(cloud,.21,.32),g.math('MULTIPLY',root,.065))
        glow=g.math('MULTIPLY',g.math('POWER',strand,6.),.08)
        bump_height=g.math('MULTIPLY',grain,.009)
        transmission=.78
    else:
        color=g.ramp(cloud,[(.20,(.042,.031,.018)),(.53,(.19,.135,.062)),(.82,(.34,.255,.135))])
        rough=g.math('ADD',g.range(cloud,.26,.38),g.math('MULTIPLY',strand,.085))
        opacity=1.;glow=0.;transmission=0.
        bump_height=g.math('ADD',g.math('MULTIPLY',strand,.025),g.math('MULTIPLY',grain,.010))
        g.bs.inputs['Metallic'].default_value=.82
    g.input(g.bs,'Base Color',color);g.input(g.bs,'Roughness',rough)
    g.bs.inputs['IOR'].default_value=1.31 if kind=='Ice' else 1.54
    g.bs.inputs['Transmission Weight'].default_value=transmission
    bump=g.node('ShaderNodeBump');g.input(bump,'Height',bump_height)
    bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.045
    g.input(g.bs,'Normal',bump.outputs['Normal'])
    palette={'Ice':(.10,.55,.80,1),'Magma':(1.,.105,.004,1),'Jade':(.08,.52,.19,1),
             'Storm':(.28,.12,.85,1),'Mount':(0,0,0,1)}
    g.bs.inputs['Emission Color'].default_value=palette[kind]
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',glow,3.2 if kind=='Magma' else .25))
    combine=g.node('ShaderNodeCombineColor');combine.mode='RGB'
    for pin,value in [('Red',rough),('Green',opacity),('Blue',glow)]:g.input(combine,pin,value)
    g.mat['packed_channels']='R roughness; G opacity; B localized emission/illumination mask'
    return g,color,combine.outputs['Color']
''' +text[end:]
start=text.index('def vertex_signal(');end=text.index('\n\nmanifest=[]',start)
text=text[:start]+'''def vertex_signal(obj,value,phase=0.):
    attr=obj.data.color_attributes.get('CoreSignal') or obj.data.color_attributes.new(name='CoreSignal',type='BYTE_COLOR',domain='CORNER')
    for c in attr.data:c.color=(value,phase,0,1)
    obj.data.color_attributes.active_color=attr
    obj.data.color_attributes.render_color_index=list(obj.data.color_attributes).index(attr)


def core_material(kind):
    g=Graph('M_StaffCraft_'+kind+'Inner_V37')
    signal=g.node('ShaderNodeVertexColor');signal.layer_name='CoreSignal'
    sep=g.node('ShaderNodeSeparateColor');g.input(sep,'Color',signal.outputs['Color'])
    if kind=='Ice':
        g.bs.inputs['Base Color'].default_value=(.075,.20,.26,1)
        g.bs.inputs['Roughness'].default_value=.25
        tint=(.12,.60,.72,1);strength=.10
    else:
        g.input(g.bs,'Base Color',g.mix(sep.outputs['Red'],(.010,.006,.024,1),(.23,.15,.46,1)))
        g.bs.inputs['Roughness'].default_value=.20
        tint=(.38,.22,1.,1);strength=4.2
    g.bs.inputs['Emission Color'].default_value=tint
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',sep.outputs['Red'],strength))
    return g.mat


def arc_tube(points,name,mat,phase,width=.032):
    pts=[Vector(p) for p in points];sides=6;verts=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        n=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(n)
        radius=width*(.34+.66*math.sin(math.pi*i/(len(pts)-1)))
        verts.extend([p+radius*(math.cos(k*math.tau/sides)*n+math.sin(k*math.tau/sides)*other) for k in range(sides)])
    faces=[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)
           for j in range(len(pts)-1) for k in range(sides)]
    faces += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+k for k in range(sides))]
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat);vertex_signal(obj,1.,phase)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def inner_geometry(kind):
    mat=core_material(kind);objects=[]
    if kind=='Ice':
        for i,(pos,scale) in enumerate([((.1,.15,70.5),(.35,.25,2.55)),((-.75,.25,69),(.19,.14,1.35)),((.45,-.5,72),(.16,.12,1.1))]):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=pos)
            obj=bpy.context.object;obj.name='Ice_Mineral_Needle_'+str(i);obj.scale=scale
            obj.rotation_euler=(.13*i,.16*(i-1),.4*i)
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            obj.data.materials.append(mat);vertex_signal(obj,.35);objects.append(obj)
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(0,0,71))
        obj=bpy.context.object;obj.name='Storm_Faceted_Seed';obj.scale=(1.02,.90,1.32)
        for v in obj.data.vertices:v.co*=.93+.07*math.sin(v.co.x*13.+v.co.y*7.+v.co.z*11.)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(mat);vertex_signal(obj,0);objects.append(obj)
        rng=random.Random(3704)
        for branch in range(6):
            a=branch*math.tau/6;pts=[]
            for step in range(11):
                t=step/10.;radius=.55+1.75*math.sin(math.pi*t)
                pts.append(Vector((math.cos(a+t*.7)*radius+rng.uniform(-.22,.22),
                                   math.sin(a+t*.7)*radius+rng.uniform(-.22,.22),67.8+t*6.6)))
            objects.append(arc_tube(pts,'Storm_Bound_Arc_'+str(branch),mat,branch/6.,.037))
            p=pts[5];fork=[p,p+Vector((.30*math.cos(a+1),.30*math.sin(a+1),.45)),
                p+Vector((.65*math.cos(a+1),.65*math.sin(a+1),.70)),
                p+Vector((.72*math.cos(a+1),.72*math.sin(a+1),1.2))]
            objects.append(arc_tube(fork,'Storm_Arc_Fork_'+str(branch),mat,branch/6.,.020))
    return objects
''' +text[end:]
text=text.replace("gem=extract(old,False,kind+'_Faceted_Shell')\n    craft_facets", "gem=extract(old,False,kind+'_Faceted_Shell')\n    craft_mount(metal)\n    craft_facets")
text=text.replace("if not obj.data.color_attributes:vertex_signal(obj,0)","if not obj.data.color_attributes.get('CoreSignal'):vertex_signal(obj,0)")
text=text.replace("ice fractures; obsidian magma fissures; cloudy jade; smoke-purple shell with contained lightning", "polished ice facets; recessed obsidian plates; layered jade mineral; smoky quartz with phased forked lightning")
text=text.replace("pivot and dimensions unchanged","pivot and lower mating surface retained; changes stay inside the previous silhouette")
(root/'author_blender.py').write_text(text,encoding='utf-8')
print('V37_STANDALONE_AUTHOR_WRITTEN')
