"""Background source production. Export changed third-room groups and glazing."""
import bpy,bmesh,json,math,sys,hashlib,random
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent;PROJECT=SOURCE.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(SOURCE/'Scripts'));sys.path.insert(0,str(ROOT))
import geometry as g
from round_hall import build_round_hall
from layout import BASE
scene=json.loads((SOURCE/'Config/scene.json').read_text('utf8'))
room=next(r for r in scene['rooms'] if r['id']=='AccumulatorControl')
roles=json.loads((SOURCE/'Config/materials.json').read_text('utf8'))
cards=json.loads((SOURCE/'TextCards20261005/cards.json').read_text('utf8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
materials={};paths={}
for role,raw in roles.items():
    name='PW_'+role;mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*raw['basecolor_linear'],1)
    bs.inputs['Roughness'].default_value=raw['roughness'];bs.inputs['Metallic'].default_value=raw['metallic']
    paths[name]=raw.get('existing_ue_path') or scene['ue_base']+'/Materials/M_Power_'+role
    if role=='Labels':
        paths[name]='/Game/Dungeons/PowerTheme20261004/TextCards20261005/Materials/M_Power_TextCards'
        image=bpy.data.images.load(str(SOURCE/'TextCards20261005/Authored/T_Power_TextCards.png'))
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    materials[role]=mat;mat['ue_material_path']=paths[name]
original_plate=g.plate
def plate(center,w,h,key,normal=(0,-1,0),atlas=None):
    card=next(c for c in cards if c['family']=='power' and c['key']==key and abs(c['width']-w)<.00001 and abs(c['height']-h)<.00001)
    original_plate(center,w,h,key,normal,dict(size=[4096,4096],rects={key:card['rect']}))
g.plate=plate
build_round_hall(g,scene,None)
for p in room['reused_parts']:
    if p.get('source_asset_id')!='SM_Staff_LampFixture':continue
    x,y,z=p['position_m'];ceiling=p.get('ceiling_m',room['dimensions_m'][2])
    for dx in (-.48,.48):
        if ceiling>z+.045:g.cylinder('Hangers',(x+dx,y,z+.045),(x+dx,y,ceiling-.015),.012,'Steel',10)
        g.box('Hangers',(x+dx,y,ceiling-.017),(.09,.12,.018),'Steel')
changed={'Structure','GalleryDeck','Rails','Trim','RoofFrame','ControlRoom','Cablework','Hardware','Signs','Hangers','Markings'}
records=[]
def finalize(obj,kind,hulls,mapping,previous=None,shards=0):
    name=obj.name
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    if kind in ('Structure','GalleryDeck','Trim','RoofFrame','ControlRoom'):
        mod=obj.modifiers.new('Fabricated edge radii','BEVEL');mod.width=.006 if kind=='Structure' else .003
        mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(35);mod.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Export triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    collisions=[]
    for i,(vs,fs) in enumerate(hulls):
        mesh=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);mesh.from_pydata(vs,[],fs);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        co=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(co);co.select_set(True);collisions.append(co)
    fbx=OUT/(name+'.fbx');obj.data.update()
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in collisions:co.hide_set(True);co.hide_render=True
    records.append(dict(name=name,kind=kind,mesh=BASE+'/Meshes/'+name,previous_mesh=previous,fbx=str(fbx),
        sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials=mapping,triangles=len(obj.data.polygons),
        collision=bool(hulls),collision_hulls=len(hulls),nanite=kind in ('Structure','GalleryDeck','Rails','Trim','RoofFrame','ControlRoom'),
        cast_shadow=kind not in ('Signs','Markings','Hardware','Hangers','Glass','Fracture'),fracture_shards=shards))
    print('POWER_UPPER_AUTHORED',name,len(obj.data.polygons),len(hulls),flush=True)
for (rid,kind),data in g.G.items():
    if kind not in changed:continue
    name='SM_Power_AccumulatorControl_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for role in order:mesh.materials.append(materials[role])
    mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER');uv=mesh.uv_layers['UVMap']
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))]
        scale=roles[role].get('uv_meters_override',roles[role].get('uv_meters',1))
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
            age.data[li].color=(.035+.14*math.exp(-max(0,p.z)/.23),0,0,1)
    previous=('/Game/Dungeons/PowerTheme20261004/TextCards20261005' if kind=='Signs' else scene['ue_base'])+'/Meshes/'+name
    finalize(obj,kind,g.C.get((rid,kind),[]),{materials[r].name:paths[materials[r].name] for r in order},previous)
    obj['room_origin_m']=room['origin_m'];obj['upper_control_revision']='20261005'

# Reuse the accepted physical glass / shard shader and the native UV contract.
stock=json.loads((PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/manifest.json').read_text('utf8'))
glass_path=next(iter(next(x for x in stock['objects'] if x['name']=='SM_SW_WindowPaneV5')['materials'].values()))
glass=bpy.data.materials.new('RS_Glass');glass['ue_material_path']=glass_path
def cube(name,center,size,material=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);obj=bpy.context.object;obj.name=name;obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:obj.data.materials.append(material)
    return obj
def export_glass(obj,kind,boxes=(),shards=0):
    obj.name='SM_Power_UpperControl'+kind;hulls=[]
    for center,size in boxes:
        co=cube('CollisionTemporary',center,size)
        hulls.append(([tuple(v.co) for v in co.data.vertices],[tuple(p.vertices) for p in co.data.polygons]))
        bpy.data.objects.remove(co,do_unlink=True)
    finalize(obj,'Fracture' if shards else 'Glass',hulls,{'RS_Glass':glass_path},shards=shards)
    obj.hide_set(True)
text=(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8')
text=text[text.index('def clipped('):text.index("panes('Door'")]
# Creating a corner color attribute reallocates UV buffers in Blender 5.1.
text=text.replace(' for face,attr in zip(mesh.polygons,attributes):'," uv0=mesh.uv_layers['UVMap'];uv1=mesh.uv_layers['ShardCenter'];uv2=mesh.uv_layers['ShardSeed']\n for face,attr in zip(mesh.polygons,attributes):")
context=dict(bpy=bpy,math=math,random=random,cube=cube,export=export_glass,glass=glass)
exec(compile(text,'power_upper_native_glass','exec'),context)
for kind,width,nx in [('Front',3.92,18),('Side',2.735,14)]:context['panes'](kind,width,2.0,.008,nx,12,61005+nx)
for image in bpy.data.images:
    if image.source=='FILE' and image.has_data:image.pack()
bpy.context.scene['tests_run']=False;bpy.context.scene['rendered']=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PowerUpperControlRoom.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,tests_run=False,rendered=False),indent=2),encoding='utf8')
print('POWER_UPPER_SOURCE_COMPLETE',len(records),flush=True)
