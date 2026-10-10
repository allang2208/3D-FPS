"""Build the three user-directed replacements from the current V37 author."""
from pathlib import Path
root=Path(__file__).resolve().parent
text=(root.parent/'ElementHeadsV37/author_blender.py').read_text(encoding='utf-8')
text=text.replace('V37','V38').replace("'revision']=37","'revision']=38").replace("'revision':37","'revision':38")
text=text.replace("('jade_spirit_crystal', 'Jade'), ","")
text=text.replace('from mathutils import Vector','from mathutils import Vector, noise')
start=text.index("    if kind=='Ice':",text.index('def recipe('))
end=text.index("    elif kind=='Jade':",start)
text=text[:start]+'''    if kind=='Ice':
        # Explicitly opaque white ice, per the latest user direction.
        color=g.ramp(cloud,[(.18,(.53,.57,.59)),(.52,(.76,.79,.80)),(.82,(.92,.94,.95))])
        lines=g.ramp(strand,[(.55,(0,0,0)),(.69,(.20,.20,.20)),(.85,(.44,.44,.44))])
        color=g.mix(lines,color,(.90,.93,.95,1))
        rough=g.math('ADD',g.range(cloud,.18,.31),g.math('MULTIPLY',lines,.14))
        opacity=1.;glow=g.math('MULTIPLY',lines,.025)
        bump_height=g.math('ADD',g.math('MULTIPLY',grain,.025),g.math('MULTIPLY',strand,.035))
        transmission=0.
    elif kind=='Magma':
        # Warped, nonuniform molten channels, independent of the sphere topology.
        warp=g.node('ShaderNodeTexNoise');g.input(warp,'Vector',coord)
        warp.inputs['Scale'].default_value=3.1
        scale=g.node('ShaderNodeVectorMath');scale.operation='SCALE'
        g.input(scale,0,warp.outputs['Color']);scale.inputs['Scale'].default_value=.24
        add=g.node('ShaderNodeVectorMath');add.operation='ADD'
        g.input(add,0,coord);g.input(add,1,scale.outputs[0])
        vor=g.node('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE'
        g.input(vor,'Vector',add.outputs[0]);vor.inputs['Scale'].default_value=5.2
        molten=g.ramp(vor.outputs['Distance'],[(0,(1,1,1)),(.035,(.80,.80,.80)),(.085,(0,0,0))])
        heat=g.math('MULTIPLY',molten,g.range(cloud,.55,1.))
        crust=g.ramp(cloud,[(.20,(.008,.005,.004)),(.52,(.04,.017,.009)),(.82,(.14,.049,.013))])
        hot=g.ramp(heat,[(0,(.24,.010,.002)),(.5,(.85,.075,.004)),(1,(1.,.33,.025))])
        color=g.mix(molten,crust,hot)
        rough=g.mix(molten,g.range(grain,.40,.64),(.20,.20,.20,1))
        opacity=1.;glow=heat;transmission=0.
        bump_height=g.math('SUBTRACT',g.math('MULTIPLY',grain,.22),g.math('MULTIPLY',molten,.35))
''' +text[end:]
text=text.replace("'Ice':(.10,.55,.80,1)","'Ice':(.78,.88,1.,1)")
start=text.index('def inner_geometry(');end=text.index('\n\nmanifest=[]',start)
text=text[:start]+'''def magma_sphere():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1.)
    obj=bpy.context.object;obj.name='Magma_Irregular_Round_Sphere'
    for v in obj.data.vertices:
        d=v.co.normalized()
        broad=noise.noise_vector(d*2.2+Vector((8.2,3.7,9.1)))[0]
        middle=noise.noise_vector(d*7.3+Vector((4.6,1.8,7.4)))[1]
        fine=noise.noise_vector(d*21.0+Vector((2.1,5.2,3.7)))[2]
        r=4.88*(.98+.080*broad+.026*middle+.006*fine)
        p=d*r;p.y*=.98;p.z*=1.02
        # Melt the lowest cap into the existing seat without a floating ball.
        p.z-=.66*max(0.,(-d.z-.66)/.34)**2
        v.co=p+Vector((0,0,70.85))
    for p in obj.data.polygons:p.use_smooth=True
    unwrap(obj)
    obj['design']='irregular round molten sphere, no polygonal plate grid'
    return obj


def electric_tube(points,branch,mat,layer,parameters=None):
    pts=[Vector(p) for p in points];sides=6;verts=[]
    ts=parameters or [i/(len(pts)-1) for i in range(len(pts))]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        n=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(n)
        width=(.014 if layer else .046)*(0.78+.22*math.sin(i*2.7+branch))
        verts.extend([p+width*(math.cos(k*math.tau/sides)*n+math.sin(k*math.tau/sides)*other) for k in range(sides)])
    faces=[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)
           for j in range(len(pts)-1) for k in range(sides)]
    faces += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+k for k in range(sides))]
    data=bpy.data.meshes.new('Core_Bolt');data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new('Core_Bolt_'+str(branch)+'_'+str(layer),data)
    bpy.context.collection.objects.link(obj);data.materials.append(mat)
    uv=data.uv_layers.new(name='UVMap')
    for loop in data.loops:
        # UE FBX import flips V. The shader uses (1 - V) to recover branch ID.
        uv.data[loop.index].uv=(ts[loop.vertex_index//sides],branch/16.)
    vertex_signal(obj,float(layer),branch/8.)
    for p in data.polygons:p.use_smooth=True
    return obj


def inner_geometry(kind):
    # The solid seed is gone: every visible central piece belongs to the VFX.
    mat=core_material('Storm');objects=[]
    rng=random.Random(3809)
    for branch in range(8):
        a=branch*math.tau/8;z=-.70+1.4*((branch*3)%8)/7
        direction=Vector((math.cos(a)*math.sqrt(1-z*z),math.sin(a)*math.sqrt(1-z*z),z))
        side=direction.cross(Vector((0,0,1))).normalized()
        pts=[]
        for i in range(11):
            t=i/10.;r=2.25*(t*2-1)
            jitter=side*rng.uniform(-.15,.15)*math.sin(math.pi*t)
            pts.append(Vector((0,0,71))+direction*r+jitter)
        for layer in (0,1):objects.append(electric_tube(pts,branch,mat,layer))
        if branch%2==0:
            start=pts[5]
            fork=[start+side*(j*.30)+direction*(j*.20)+Vector((0,0,.09*j)) for j in range(5)]
            for layer in (0,1):objects.append(electric_tube(fork,branch,mat,layer,[.5+.1*j for j in range(5)]))
    return objects
''' +text[end:]
text=text.replace("gem=extract(old,False,kind+'_Faceted_Shell')\n    craft_mount(metal)\n    craft_facets(gem,kind)", "gem=magma_sphere() if kind=='Magma' else extract(old,False,kind+'_Faceted_Shell')\n    craft_mount(metal)\n    if kind!='Magma':craft_facets(gem,kind)")
text=text.replace("(inner_geometry(kind) if kind in ('Ice','Storm') else [])","(inner_geometry(kind) if kind=='Storm' else [])")
text=text.replace("'texture_maps':15","'texture_maps':12")
text=text.replace("polished ice facets; recessed obsidian plates; layered jade mineral; smoky quartz with phased forked lightning", "opaque white ice; irregular round molten sphere; continuously reshaped lightning core inside retained storm shell")
(root/'author_blender.py').write_text(text,encoding='utf-8')
print('V38_AUTHOR_WRITTEN')
