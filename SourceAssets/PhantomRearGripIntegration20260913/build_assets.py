"""Prepare the accepted model and removable factory sections for three game rifles."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;S=P.parent
bpy.context.preferences.filepaths.save_version=0
geo=json.loads((P/'geometry_sources.json').read_text())
targets={key:next(ob for ob in geo[key]['objects'] if ob['name']==name) for key,name in [('M4','M4_Grip Default Unreal_Export'),('QBZ191','QBZ_PistolGrip')]}
targets['AKM']=geo['AKM']['objects'][0]['components'][7]
bindings={}
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

# Factory geometry stays unchanged; only a material section is added for visibility.
for key in ['AKM','QBZ191']:
    out=P/key;out.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=geo[key]['source'])
    rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';bpy.context.view_layer.update()
    if key=='AKM':
        gun=bpy.data.objects['AKM_Soviet_Native'];adj=[[] for v in gun.data.vertices]
        for e in gun.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
        seen=set();groups=[]
        for idx in range(len(adj)):
            if idx in seen:continue
            stack=[idx];seen.add(idx);ids=set()
            while stack:
                v=stack.pop();ids.add(v)
                for n in adj[v]:
                    if n not in seen:seen.add(n);stack.append(n)
            groups.append(ids)
        ids=groups[7];original=gun.data.materials[0]
        material=original.copy();material.name='M_AKM_FactoryRearGrip';gun.data.materials.append(material);slot=len(gun.data.materials)-1
        for face in gun.data.polygons:
            if all(i in ids for i in face.vertices):face.material_index=slot
        bindings[key]={material.name:original.name}
        select([gun,bpy.data.objects['AKM_FactoryMagazine_Preview'],bpy.data.objects['SK_Manny_Arms_Export'],rig])
        bpy.ops.export_scene.fbx(filepath=str(out/'SK_AKM_MannyNative.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    else:
        gun=bpy.data.objects['QBZ_PistolGrip'];original=gun.data.materials[0];material=original.copy();material.name='M_QBZ191_FactoryRearGrip';gun.data.materials[0]=material
        bindings[key]={material.name:original.name}
        sys.path.insert(0,str(S/'QBZ191Hero20260913'));from export_mesh import export_joined
        objects=[ob for ob in bpy.data.collections['QBZ_LOW'].objects if ob.type=='MESH' and not ob.get('is_static_head')]
        export_joined(rig,bpy.data.objects['SK_Manny_Arms_Export'],objects,out)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(key+'_RearGripSections_Editable.blend')))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(S/'PhantomRearGripMultiview_20260913/seed_91627/textured_master_00001_.glb'))
high=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH')
high.data.transform(high.matrix_world);high.parent=None;high.matrix_world=Matrix.Identity(4)
rot=Matrix.Rotation(-math.pi/2,4,'Z');high.data.transform(rot)
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);select([low])
low.data.calc_loop_triangles();dec=low.modifiers.new('Game mesh silhouette reduction','DECIMATE');dec.ratio=min(1,50000/len(low.data.loop_triangles));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
mat=low.data.materials[0];mat.name='M_PhantomRearGrip';nt=mat.node_tree
bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
base=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
packed=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and n.image!=base)
for name,img in [('BaseColor',base),('MetalRough',packed)]:
    img.filepath_raw=str(P/('T_PhantomRearGrip_'+name+'.png'));img.file_format='PNG';img.save()
points=[v.co.copy() for v in low.data.vertices]
lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
canonical=low.data.copy();high.hide_set(True);high.hide_render=True
auth={'source':'PhantomRearGripMultiview_20260913/seed_91627','factory_bindings':bindings,'fits':{}}
for key in ['M4','AKM','QBZ191']:
    out=P/key;out.mkdir(exist_ok=True);target=targets[key];tl=Vector(target['lo']);th=Vector(target['hi'])
    # Retain the side silhouette at uniform scale; match transverse hand width.
    scale=(th.z-tl.z)/(hi.z-lo.z);width=(th.x-tl.x)/(hi.x-lo.x)
    transform=Matrix.Translation(Vector(((tl.x+th.x)/2,(tl.y+th.y)/2,th.z)))@Matrix.Diagonal((width,scale,scale,1))@Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-hi.z)))
    low.data=canonical.copy();low.data.transform(transform);low.name='SM_PhantomRearGrip';select([low])
    bpy.ops.export_scene.fbx(filepath=str(out/'SM_PhantomRearGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'PhantomRearGrip_Fitted_Editable.blend'))
    auth['fits'][key]={'root_space_metres':[list(row) for row in transform],'factory_bounds':target,'mount':'WPN_root, identity rotation/translation, component scale 0.01'}
(P/'authoring.json').write_text(json.dumps(auth,indent=2))
print('PHANTOM_ASSETS_AUTHORED',flush=True)
