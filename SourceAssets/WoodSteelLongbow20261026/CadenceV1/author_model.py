"""Centimetre-native, skinned braid and serving for the approved Cadence string."""
from pathlib import Path
import bpy, math, json
from mathutils import Vector

P=Path(__file__).parent
(P/'Export').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
X=-17.36598;UP=88.33999;LOW=-77.95815;NOCK=9.3328
NAME='SK_Highland_CadenceString'
finishes={
 'M_Cadence_Fibre':dict(color=[.022,.105,.17],metallic=.10,roughness=.46),
 'M_Cadence_Graphite':dict(color=[.035,.043,.049],metallic=.05,roughness=.62),
 'M_Cadence_Silver':dict(color=[.60,.66,.69],metallic=.88,roughness=.26),
 'M_Cadence_Gold':dict(color=[.50,.42,.28],metallic=.82,roughness=.32),
 'M_Cadence_Serving':dict(color=[.022,.028,.032],metallic=0,roughness=.72),
 'M_Cadence_Resonance':dict(color=[.62,.66,.70],metallic=.80,roughness=.29),
}
materials=[]
for name,f in finishes.items():
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;links=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*f['color'],1)
    bs.inputs['Metallic'].default_value=f['metallic'];bs.inputs['Roughness'].default_value=f['roughness']
    tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=125
    links.new(tc.outputs['Generated'],noise.inputs['Vector']);bump=n.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.008
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    materials.append(m)

vertices=[];faces=[];uvs=[];weights=[];colors=[];slots=[];parts=[]
def skin(z,bone=None):
    if bone is not None:return {bone:1.}
    if z>=NOCK:
        t=max(0,min(1,(z-NOCK)/(UP-NOCK)));return {'string_nock':1-t,'string_upper':t}
    t=max(0,min(1,(NOCK-z)/(NOCK-LOW)));return {'string_nock':1-t,'string_lower':t}

def tube(label,points,r,slot,sides=6,closed=False,bone=None,mark=0):
    points=[Vector(p) for p in points];base=len(vertices);length=0
    for i,p in enumerate(points):
        tangent=(points[(i+1)%len(points)]-points[i-1 if i else (-1 if closed else 0)]).normalized()
        if not closed and i==len(points)-1:tangent=(p-points[i-1]).normalized()
        a=tangent.cross(Vector((0,1,0)))
        if a.length<.01:a=tangent.cross(Vector((1,0,0)))
        a.normalize();b=tangent.cross(a).normalized()
        if i:length+=(p-points[i-1]).length
        for j in range(sides):
            angle=j*math.tau/sides;v=p+r*(a*math.cos(angle)+b*math.sin(angle))
            vertices.append(tuple(v));uvs.append((j/sides,length/.4));weights.append(skin(p.z,bone));colors.append((mark,0,0,1))
    count=len(points) if closed else len(points)-1
    for i in range(count):
        for j in range(sides):
            faces.append((base+i*sides+j,base+i*sides+(j+1)%sides,base+((i+1)%len(points))*sides+(j+1)%sides,base+((i+1)%len(points))*sides+j));slots.append(slot)
    if not closed:
        for index,reverse in [(0,True),(len(points)-1,False)]:
            c=len(vertices);vertices.append(tuple(points[index]));uvs.append((.5,.5));weights.append(skin(points[index].z,bone));colors.append((mark,0,0,1))
            for j in range(sides):
                f=(c,base+index*sides+j,base+index*sides+(j+1)%sides)
                faces.append(tuple(reversed(f)) if reverse else f);slots.append(slot)
    parts.append({'name':label,'vertices':len(vertices)-base})

def helix(label,z0,z1,rad,wire,pitch,slot,phase=0,direction=1,bone=None):
    count=max(12,int(abs(z1-z0)/pitch*12))
    pts=[]
    for i in range(count+1):
        z=z0+(z1-z0)*i/count;a=(z-z0)/pitch*math.tau*direction+phase
        rr=rad+.005*math.cos(a*4)
        pts.append((X+rr*math.cos(a),rr*math.sin(a),z))
    tube(label,pts,wire,slot,5,bone=bone)

# Counter-woven fibre bundles; gold is a thin strand, never a rigid cable sleeve.
for side in [-1,1]:
    for j in range(3):
        helix('Counterwoven silver/graphite',LOW+1.2,UP-1.2,.058,.026,2.8,j%2,j*math.tau/3,side)
helix('Fine silver counterbraid',LOW+1.2,UP-1.2,.088,.010,3.8,2)
helix('Warm silver companion filament',LOW+1.2,UP-1.2,.089,.009,3.8,3,math.pi,-1)

def ring(label,z,rad,wire,slot,bone,mark=0):
    tube(label,[(X+rad*math.cos(t),rad*math.sin(t),z) for t in [i*math.tau/40 for i in range(40)]],wire,slot,6,True,bone,mark)

for end,sign,bone in [(UP,1,'string_upper'),(LOW,-1,'string_lower')]:
    # Loop bears on the existing tip anchor, with an open woven eye and bound neck.
    for j in range(4):
        pts=[]
        for i in range(96):
            a=i*math.tau/96;tw=a*12+j*math.pi/2
            pts.append((X+.42*math.sin(a)+.026*math.cos(tw),.026*math.sin(tw),end+sign*(.64*math.cos(a)-.20)))
        tube('Flexible tip eye',pts,.023,j%2,5,True,bone)
    z=end-sign*1.05
    helix('Flexible close-wound loop neck',z-.25,z+.25,.108,.020,.047,1,bone=bone)
    for dz in [-.23,.23]:ring('Gold sleeve rim',z+dz,.116,.018,3,bone)
    for dz in [-.13,-.07,0,.07,.13]:ring('Shallow sleeve machining',z+dz,.116,.004,1,bone)

tube('Soft serving body',[(X,0,NOCK-4),(X,0,NOCK+2)],.117,4,16,bone='string_nock')
helix('Close wound serving',NOCK-4,NOCK+2,.120,.016,.070,4,bone='string_nock')
for z in [NOCK-4,NOCK+2]:ring('Bound serving edge',z,.120,.020,1,'string_nock')
for z in [NOCK+.32,NOCK+.43]:ring('Nocking locator',z,.130,.021,3,'string_nock')
# Five soft rhythmic bands, spread along the loaded string, clear of nock/fingers.
for k,z in enumerate([LOW+22,LOW+51,NOCK+8,NOCK+32,UP-17]):
    for j in range(7):
        ring('Cadence fine winding '+str(k+1),z+(j-3)*.053,.099,.017,5,None,(k+1)/5)
    for dz in [-.24,.24]:ring('Champagne bound edge',z+dz,.102,.012,3,None)
    for face in [-1,1]:
        for offset in [-.065,.065]:
            tube('Fine cadence chevron '+str(k+1),[(X-.058,face*.078,z+.10+offset),(X,face*.105,z-.015+offset),(X+.058,face*.078,z+.10+offset)],.009,5,5,False,None,(k+1)/5)

mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(vertices,[],faces);mesh.update()
obj=bpy.data.objects.new(NAME,mesh);scene.collection.objects.link(obj)
for m in materials:mesh.materials.append(m)
uv=mesh.uv_layers.new(name='UVMap');color=mesh.color_attributes.new(name='ResonanceID',type='FLOAT_COLOR',domain='POINT')
for i,c in enumerate(colors):color.data[i].color=c
for poly,slot in zip(mesh.polygons,slots):
    poly.material_index=slot;poly.use_smooth=True
    us=[uvs[mesh.loops[i].vertex_index][0] for i in poly.loop_indices]
    wrap=max(us)-min(us)>.65
    for li in poly.loop_indices:
        u,v=uvs[mesh.loops[li].vertex_index];uv.data[li].uv=(u+1 if wrap and u<.1 else u,v)

armdata=bpy.data.armatures.new('Cadence_StringRig');arm=bpy.data.objects.new('Cadence_StringRig',armdata);scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
root=armdata.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,1,0)
for name,z in [('string_upper',UP),('string_nock',NOCK),('string_lower',LOW)]:
    bone=armdata.edit_bones.new(name);bone.head=(X,0,z);bone.tail=(X,1,z);bone.parent=root
bpy.ops.object.mode_set(mode='OBJECT')
for name in ['string_upper','string_nock','string_lower']:
    group=obj.vertex_groups.new(name=name)
    for i,w in enumerate(weights):
        if w.get(name,0)>0:group.add([i],w[name],'REPLACE')
obj.parent=arm;mod=obj.modifiers.new('String attachment skin','ARMATURE');mod.object=arm
# Source units are centimetres, matching the existing bow tip and hand contracts.
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Cadence_String.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(NAME+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},
    global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR')
(P/'authoring.json').write_text(json.dumps({'mesh':NAME,'finishes':finishes,'parts':parts,
    'vertices':len(vertices),'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),
    'anchors_cm':{'upper':[X,0,UP],'nock':[X,0,NOCK],'lower':[X,0,LOW]},
    'skeleton':'root with independent string_upper/string_nock/string_lower',
    'source_license':'original procedural geometry; shared project material textures keep their source provenance',
    'concept':'../CadenceStringConcept20261028/concept-v1.png',
    'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CADENCE_MODEL_EXPORTED',flush=True)
