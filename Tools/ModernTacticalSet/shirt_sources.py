"""Editable shirt sources and standard empty-garment inventory artwork."""
import bpy,sys,ast,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import *
OUT=R/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/01_KevlarVest.blend'))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
def cloth(name,base,color=None):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials[base].copy();m.name=name
    if color:
        bs=m.node_tree.nodes.get('Principled BSDF')
        for link in list(bs.inputs['Base Color'].links):m.node_tree.links.remove(link)
        bs.inputs['Base Color'].default_value=(*color,1)
    return m
cloth('M_CombatFabric','TS01_RangerRipstop')
for rig in ['Jason','Kaitlin','Body']:cloth('MI_CombatTorso_'+rig,'TS01_CharcoalStretch',(.075,.043,.022))
def material(path):
    name=path.split('/')[-1].split('.')[0]
    return bpy.data.materials.get(name) or bpy.data.materials.get('TS01_'+name.removeprefix('M_'))
def mesh(d,name):
    me=bpy.data.meshes.new(name);me.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']],[],d['triangles']);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for path in d['materials']:
        mat=material(path)
        if not mat:raise RuntimeError('Missing Blender material '+path)
        me.materials.append(mat)
    uv=me.uv_layers.new()
    for face,mi,tex in zip(me.polygons,d['triangle_materials'],d['uv']):
        face.material_index=mi;face.use_smooth=True
        for li,t in zip(face.loop_indices,tex):uv.data[li].uv=(t[0],1-t[1])
    me.normals_split_custom_set([(n[0],-n[1],n[2]) for f in d['normals'] for n in f]);groups={b['index']:ob.vertex_groups.new(name=b['name']) for b in d['bones']}
    for vi,ws in enumerate(d['weights']):
        for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
    return ob
def rig(d):
    ad=bpy.data.armatures.new('NativeBody');ob=bpy.data.objects.new('NativeBody',ad);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT');byid={}
    for row in d['bones']:
        b=ad.edit_bones.new(row['name']);p=Vector((row['position'][0],-row['position'][1],row['position'][2]))*.01;b.head=p;b.tail=p+Vector((0,0,.025));byid[row['index']]=b
        if row.get('axes'):
            reflection=Matrix.Diagonal(Vector((1,-1,1)));basis=reflection@Matrix(row['axes']).transposed()@reflection;matrix=basis.to_4x4();matrix.translation=p;b.matrix=matrix;b.length=.025
    for row in d['bones']:
        if row['parent'] in byid:byid[row['index']].parent=byid[row['parent']]
    bpy.ops.object.mode_set(mode='OBJECT');return ob
requested=sys.argv[sys.argv.index('--rigs')+1].split(',') if '--rigs' in sys.argv else ['Jason','Kaitlin']
for rig_name in requested:
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    standalone=read(R/'Authored'/f'shirt_standalone_{rig_name}.json');ob=mesh(standalone,'TS01_CombatShirt_'+rig_name);arm=rig(standalone);ob.modifiers.new('NativeSkeleton','ARMATURE').object=arm;ob.parent=arm
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'Models'/f'TS01_CombatShirt_{rig_name}.blend'))
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/f'TS01_CombatShirt_{rig_name}.fbx'),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
    bpy.ops.export_scene.gltf(filepath=str(R/'Exports'/f'TS01_CombatShirt_{rig_name}.glb'),export_format='GLB',use_selection=True,export_all_influences=True)
    print('TS01_SHIRT_SOURCES',rig_name,flush=True)
if '--sources-only' in sys.argv:raise SystemExit(0)
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
d=read(R/'Authored/outfit_display_Jason.json');ob=mesh(d,'TS01_CarrierAndCombatShirt')
# Full-scale source is retained separately from the camera-aligned icon geometry.
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Models/TS01_CarrierAndCombatShirt.blend'))
tree=ast.parse((P/'Tools/ModernTacticalSet/prepare_delivery.py').read_text(encoding='utf-8'));ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,OUT=OUT,P=P,read=read,write=write)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='icon'],type_ignores=[]),'standard_inventory_icon','exec'),ns)
result=ns['icon'](ob,'ue_modern_kevlar_vest',3,3,'vest')
display=read(result['display']);display['materials']=[next(path for path in d['materials'] if material(path).name==name) for name in display['material_slots']];write(result['display'],display)
pickup=read(R/'Authored/outfit_display_Jason.json')
center=(np.array(pickup['positions']).min(0)+np.array(pickup['positions']).max(0))*.5
pickup['positions']=(np.array(pickup['positions'])-center).tolist();write(R/'Authored/pickup.json',pickup)
# Native rest-space torso material uses correspondingly translated origin on drop meshes.
write(R/'artwork.json',dict(completed=True,icon=result,pickup=str(R/'Authored/pickup.json'),pickup_origin_offset=center.tolist(),design=str(S/'Design/TS01_CombatShirt_EarthBrown_R1.png')))
