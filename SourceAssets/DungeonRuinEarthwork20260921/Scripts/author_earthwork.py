"""Fit existing scanned earthwork to the ruin. Export assets only; no render/test."""
import bpy,bmesh,json,math,random
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
ROOM=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRoomInteriors20260921')
source=json.loads((ROOT/'Sources/source-manifest.json').read_text())
maps=json.loads((ROOT/'Sources/surface-maps.json').read_text())
R=random.Random(921371)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
sources={};materials={};objects=[]

recipes={
 'Ridge':{'source':'ridge_a','tint':[.31,.82,1.20],'roughness_channel':'base_alpha','roughness_min':.69,'roughness_max':.98},
 'Gravel':{'source':'gravel','tint':[.89,.86,.78],'roughness_channel':'orm_green','roughness_min':.72,'roughness_max':.98},
 'Pebbles':{'source':'stone_scatter','tint':[.65,.84,1.08],'roughness_channel':'orm_green','roughness_min':.72,'roughness_max':.98},
 'PebblePatch':{'source':'stone_patch','tint':[.48,.60,.76],'roughness_channel':'orm_green','roughness_min':.72,'roughness_max':.98},
 'Soil':{'tint':[.68,.93,1.42],'roughness_channel':'mask_red','roughness_min':.78,'roughness_max':.98,
  'textures':{'base':'/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Albedo',
              'normal':'/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Normal',
              'mask':'/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_RHAOM'}},
 'RubbleStone':{'native_parent':source['source_assets']['rubble_a']['materials'][1]['path'],
  'vector_overrides':{'TS00_BaseColor_Tint':[.37,.34,.29,1],'TS01_BaseColor_Tint':[.50,.46,.39,1],
                     'TS02_BaseColor_Tint':[.62,.58,.50,1],'GBC_Variation_00A_BaseColorTint':[1,1,1,1]},
  'scalar_overrides':{'GBC_Variation_00A_Intensity':.05,'GBC_Variation_01A_Intensity':.10,
                      'TS00_Specular':.25,'TS01_Specular':.25}},
}
for name,recipe in recipes.items():
    if recipe.get('source'):
        matpath=source['source_assets'][recipe['source']]['materials'][0]['path']
        t=source['materials'][matpath]['textures']
        recipe['textures']={'base':t.get('BaseColour') or t.get('BaseColorTexture'),
                           'normal':t.get('Normals') or t.get('NormalTexture')}
        if 'MetallicRoughnessTexture' in t:recipe['textures']['mask']=t['MetallicRoughnessTexture']
    m=bpy.data.materials.new('Earth_'+name);m.use_nodes=True;materials[name]=m
    shader=m.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.87
    for channel,path in recipe.get('textures',{}).items():
        info=maps.get(path) or maps.get(path+'.'+path.rsplit('/',1)[-1])
        if not info:continue
        image=bpy.data.images.load(info['file'],check_existing=True)
        image.colorspace_settings.name='sRGB' if channel=='base' else 'Non-Color'
        node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
        if channel=='base':
            mul=m.node_tree.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
            mul.inputs[2].default_value=(*recipe['tint'],1);m.node_tree.links.new(node.outputs['Color'],mul.inputs[1])
            m.node_tree.links.new(mul.outputs[0],shader.inputs['Base Color'])
        elif channel=='normal':
            split=m.node_tree.nodes.new('ShaderNodeSeparateXYZ');comb=m.node_tree.nodes.new('ShaderNodeCombineXYZ')
            inv=m.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
            m.node_tree.links.new(node.outputs['Color'],split.inputs[0]);m.node_tree.links.new(split.outputs[0],comb.inputs[0])
            m.node_tree.links.new(split.outputs[1],inv.inputs[1]);m.node_tree.links.new(inv.outputs[0],comb.inputs[1])
            m.node_tree.links.new(split.outputs[2],comb.inputs[2])
            normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(comb.outputs[0],normal.inputs['Color'])
            m.node_tree.links.new(normal.outputs[0],shader.inputs['Normal'])

def import_source(ident):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=source['source_assets'][ident]['fbx'])
    added=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
    obj=added[0]
    obj.data.transform(obj.matrix_world);obj.matrix_world.identity()
    obj.name='SOURCE_'+ident;obj.hide_render=True;obj.hide_set(True);sources[ident]=obj
    return obj
for ident in ('ridge_a','ridge_b','gravel','stone_scatter','stone_patch','rubble_a'):import_source(ident)

def clone(ident,name,mat):
    obj=sources[ident].copy();obj.data=sources[ident].data.copy();scene.collection.objects.link(obj)
    obj.name='SM_Earth_'+name;obj.hide_render=False;obj.hide_set(False)
    obj.data.materials.clear();obj.data.materials.append(materials[mat])
    for f in obj.data.polygons:f.material_index=0
    return obj

def trim(obj,planes):
    bm=bmesh.new();bm.from_mesh(obj.data)
    for point,normal in planes:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,
           plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
    bm.to_mesh(obj.data);bm.free();obj.data.update()

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

bank=clone('ridge_a','BankLeft','Ridge')
trim(bank,[((-1.65,0,0),(-1,0,0)),((0,-2.75,0),(0,-1,0)),((0,2.75,0),(0,1,0))])
for v in bank.data.vertices:
    p=v.co.copy();y=8.46+p.y
    toe=smooth((2.05-p.x)/.42)
    end=smooth((y-5.71)/.62)
    v.co=(15.15+(p.x+1.65)*.52,y,-.197+max(0,p.z+.038)*.67*end*toe)
objects.append(bank)

right=clone('ridge_b','BankRight','Ridge')
trim(right,[((-.85,0,0),(-1,0,0)),((0,-1.05,0),(0,-1,0)),((0,1.05,0),(0,1,0))])
for v in right.data.vertices:
    p=v.co.copy();y=9.40-p.y
    end=smooth((y-8.35)/.43)*smooth((10.45-y)/.43)
    v.co=(21.36-(p.x+.85)*.42,y,-.197+max(0,p.z+.048)*.44*end)
# The X/Y reversal above is a proper half-turn; winding remains outward.
objects.append(right)

def mesh_object(name,verts,faces,mat):
    mesh=bpy.data.meshes.new('Earth_'+name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('SM_Earth_'+name,mesh);scene.collection.objects.link(obj)
    mesh.materials.append(materials[mat]);return obj

# Fine substrate sits immediately under exposed flagstone gaps, not over the route.
verts=[];faces=[];nx=56;ny=54
for j in range(ny+1):
    for i in range(nx+1):
        x=15.1+6.3*i/nx;y=5.44+5.78*j/ny
        z=-.201+.003*math.sin(x*8.7+y*5.3)
        verts.append((x,y,z))
for j in range(ny):
    for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
fill=mesh_object('FineFill',verts,faces,'Soil');objects.append(fill)

threshold_points=[(0,1.46),(.98,1.29),(1.77,1.49),(2.40,1.28),(3.02,1.60),(3.73,1.44),
                  (4.32,1.62),(5.10,1.29),(5.66,1.56),(6.5,1.40)]
def threshold_edge(x):
    for (a,b),(c,d) in zip(threshold_points,threshold_points[1:]):
        if a<=x<=c:return b+(d-b)*(x-a)/(c-a)
    return 1.4
verts=[];faces=[];nx=108;ny=16
for i in range(nx+1):
    x=6.5*i/nx;edge=4+threshold_edge(x)
    for j in range(ny+1):
        t=j/ny;length=.62+.07*math.sin(x*2.4)
        y=edge-.035+length*t;z=-.008-.190*smooth(t)+.007*math.sin(x*6.2+y*4.3)*math.sin(t*math.pi)
        verts.append((15+x,y,z))
for i in range(nx):
    for j in range(ny):a=i*(ny+1)+j;faces.append((a,a+ny+1,a+ny+2,a+1))
ramp=mesh_object('ThresholdRamp',verts,faces,'Soil');objects.append(ramp)

# Read the actual existing floor/threshold surfaces to drape contacts to them.
with bpy.data.libraries.load(str(ROOM/'Authored/DungeonRooms_Authored.blend'),link=False) as (src,dst):
    dst.objects=['SM_Room_RU_OldFlagstones','SM_Room_RU_Threshold']
support_objs=[o for o in dst.objects if o]+[bank,right,fill,ramp]
for o in dst.objects:
    if o:scene.collection.objects.link(o);o.hide_render=True;o.hide_set(True)
def bvh_for(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(f.vertices) for f in obj.data.polygons])
support=[bvh_for(o) for o in support_objs]
def ground(x,y):
    z=-.20
    for tree in support:
        hit=tree.ray_cast(Vector((x,y,4.9)),Vector((0,0,-1)),6)[0]
        if hit:z=max(z,hit.z)
    return z

def drape(ident,name,mat,center,scale,angle,embed=.016,subdivide=False):
    obj=clone(ident,name,mat)
    if subdivide:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
        bm.to_mesh(obj.data);bm.free()
    coords=[v.co.copy() for v in obj.data.vertices]
    lo=[min(p[i] for p in coords) for i in range(3)];hi=[max(p[i] for p in coords) for i in range(3)]
    cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2;co=math.cos(angle);si=math.sin(angle)
    for v,p in zip(obj.data.vertices,coords):
        x=(p.x-cx)*scale[0];y=(p.y-cy)*scale[1]
        wx=center[0]+x*co-y*si;wy=center[1]+x*si+y*co
        v.co=(wx,wy,ground(wx,wy)+(p.z-lo[2])*scale[2]-embed)
    return obj

aprons=[]
for i,(x,y,sx,sy,sz,angle) in enumerate([
 (16.38,6.36,.78,.57,.64,.17),(16.65,7.65,.73,.77,.68,-.31),
 (16.78,9.12,.76,.64,.67,.43),(16.47,10.47,.70,.68,.73,-.21),
 (20.76,9.16,.43,.75,.40,1.10),(20.66,10.46,.49,.42,.38,-.44),
 (18.03,5.62,.68,.34,.20,.11)]):
    aprons.append(drape('gravel','Apron_'+str(i),'Gravel',(x,y),(sx,sy,sz),angle,.016,True))
objects.extend(aprons)

# Local clusters follow the fall line and taper away from each slope toe.
clusters=[]
for i in range(26):
    y=R.uniform(5.93,10.90);x=R.uniform(16.34,17.38)
    if i<5:x=R.uniform(20.53,20.95);y=R.uniform(8.51,10.65)
    ident='stone_scatter' if i%3 else 'stone_patch';mat='Pebbles' if ident=='stone_scatter' else 'PebblePatch'
    scale=R.uniform(.78,1.27)
    obj=drape(ident,'Pebbles_'+str(i),mat,(x,y),(scale,scale,R.uniform(.95,1.3)),R.uniform(-math.pi,math.pi),.009)
    clusters.append(obj)
objects.extend(clusters)

# Reuse irregular broken masonry around the toe; retain the source stone material.
rubbles=[]
for i,(x,y,scale,angle) in enumerate([(16.64,6.98,.61,.29),(16.32,9.84,.69,-.48),(20.75,10.70,.43,1.1)]):
    obj=drape('rubble_a','Rubble_'+str(i),'Soil',(x,y),(scale,scale,scale),angle,.025)
    obj.data.materials.append(materials['RubbleStone'])
    for face,original in zip(obj.data.polygons,sources['rubble_a'].data.polygons):face.material_index=original.material_index
    rubbles.append(obj)
objects.extend(rubbles)

def finish_surface(obj,category):
    mesh=obj.data
    uv=mesh.uv_layers.get('UVMap') or (mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name='UVMap'))
    for layer in list(mesh.uv_layers):
        if layer!=uv:mesh.uv_layers.remove(layer)
    uv1=mesh.uv_layers.new(name='EarthWorldUV')
    # Existing scan UVs remain the first channel. Newly made soil uses metre-scaled UVs.
    custom=category in ('FineFill','ThresholdRamp')
    color=mesh.color_attributes.get('EarthBlend') or mesh.color_attributes.new(name='EarthBlend',type='FLOAT_COLOR',domain='CORNER')
    mesh.color_attributes.active_color=color
    for f in mesh.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            if custom:uv.data[li].uv=(p.x/2,p.y/2)
            uv1.data[li].uv=(p.x/2,p.y/2)
            if category.startswith('Bank'):
                mask=.42*smooth((.22-p.z)/.35)
            elif category.startswith('Apron'):
                mask=.22
            else:mask=0
            color.data[li].color=(mask,0,0,1)
    mesh.set_sharp_from_angle(angle=math.radians(57))
    if mesh.has_custom_normals:
        mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops))
    mesh.update()

manifest=[]
for obj in objects:
    category=obj.name.removeprefix('SM_Earth_');finish_surface(obj,category)
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    target=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    manifest.append({'name':obj.name,'actor':'DGN_RuinEarth_'+category,'fbx':str(target),
       'collision':category in ('BankLeft','BankRight','ThresholdRamp'),
       'materials':[s.material.name for s in obj.material_slots]})

# Preserve editable copies of source scans and the authoring support surfaces.
for ident,obj in sources.items():
    obj.hide_render=True;obj.hide_set(True)
    keys={'ridge_a':['Ridge'],'ridge_b':['Ridge'],'gravel':['Gravel'],'stone_scatter':['Pebbles'],
          'stone_patch':['PebblePatch'],'rubble_a':['Soil','RubbleStone']}[ident]
    indices=[p.material_index for p in obj.data.polygons]
    obj.data.materials.clear()
    for key in keys:obj.data.materials.append(materials[key])
    for face,index in zip(obj.data.polygons,indices):face.material_index=min(index,len(keys)-1)
for obj in dst.objects:
    if obj:obj.hide_render=True;obj.hide_set(True)
for mat in list(bpy.data.materials):
    if mat.users==0:bpy.data.materials.remove(mat)
for image in list(bpy.data.images):
    if image.source=='FILE' and image.filepath:
        if Path(bpy.path.abspath(image.filepath)).exists():image.pack()
        elif image.users==0:bpy.data.images.remove(image)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonRuinEarthwork.blend'))
(OUT/'manifest.json').write_text(json.dumps({'objects':manifest,'materials':recipes,'seed':921371,
 'hidden_previous':['DGN_Room_RU_EarthBank','DGN_Room_RU_ThresholdEarth','DGN_Room_RU_BankFragments',
                    'DGN_Room_RU_MasonryBank_A','DGN_Room_RU_MasonryBank_B'],
 'source_blend':str(OUT/'DungeonRuinEarthwork.blend'),'coordinate_system':'Blender metres baked world; UE mirrors Y',
 'tests_run':False,'renders_run':False},indent=2),encoding='utf-8')
print('EARTHWORK_AUTHORED',len(manifest),'NO_RENDER')
