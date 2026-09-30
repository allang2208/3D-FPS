"""Art-only openable lid, native-arm rig extension and adapted box/belt surfaces."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O))
from feed_lib import *
bpy.context.preferences.filepaths.save_version=0
d,db,di=load_donor();dr=di['WPN_root'];dl={n:dr.inverted()@m for n,m in di.items()};origin=dl['PKM_Belt_00'].translation
names=[n for n in db if mechanical(n)]
# The exported installed PKM is the donor, including its current mechanical UVs.
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Installed_Donor.blend'),use_scripts=False)
src=next(o for o in bpy.data.objects if o.type=='MESH');me=src.data
groups={g.index:g.name for g in src.vertex_groups};dom={v.index:max(v.groups,key=lambda g:g.weight) for v in me.vertices if v.groups}
selected=[p for p in me.polygons if all(groups[dom[v].group] in names for v in p.vertices)]
used=sorted({v for p in selected for v in p.vertices});remap={v:i for i,v in enumerate(used)}
vs=[];ws=[]
for i in used:
 v=me.vertices[i];world=src.matrix_world@v.co;point=Vector();weights={}
 for g in v.groups:
  n=groups[g.group]
  if n not in names:continue
  # Old/new props share the seated rest layout; parked duplicates are animation.
  point+=(di[canonical(n)]@db[n].inverted()@world)*g.weight
  weights[mapped_name(n)]=g.weight
 vs.append(list(map_point(dr.inverted()@point,origin)));ws.append(weights)
faces=[];uvs=[];material_keys=[];normal_rows=[]
for p in selected:
 n=groups[dom[p.vertices[0]].group];new=n.startswith('New_');box=canonical(n) in ('PKM_Box','PKM_BoxLid')
 oldmat=me.materials[p.material_index].name
 kind='Paint' if box else 'Copper' if 'Copper' in oldmat else 'Case' if 'Case' in oldmat else 'Link'
 material_keys.append('M_LMG201_Feed__'+('New' if new else 'Old')+('Box' if box else 'Belt')+'_'+kind)
 faces.append([remap[v] for v in p.vertices]);uvs.append([list(me.uv_layers.active.data[l].uv) for l in p.loop_indices])
 row=[]
 for l in p.loop_indices:
  n=groups[dom[me.loops[l].vertex_index].group]
  xf=dr.inverted()@di[canonical(n)]@db[n].inverted()@src.matrix_world
  row.append(list((xf.to_3x3().inverted().transposed()@me.corner_normals[l].vector).normalized()))
 normal_rows.append(row)
packet={'positions':vs,'faces':faces,'uv':uvs,'weights':ws,'materials':material_keys,'normals':normal_rows}
(O/'feed_surface_source.json').write_text(json.dumps(packet,separators=(',',':')),encoding='utf8')
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Skin07/LMG201_SkinProfile_Editable.blend'),use_scripts=False)
sc=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];sc.frame_set(0);bpy.context.view_layer.update();rr=r.data.bones['WPN_root'].matrix_local.copy()
new_rest={mapped_name(n):rr@map_frame(dl[canonical(n)],origin) for n in names}
new_rest['LMG201_Cover']=rr@Matrix.Translation(HINGE)
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='EDIT')
for n,m in new_rest.items():
 b=r.data.edit_bones.new(n);b.matrix=m;b.length=.012;b.parent=r.data.edit_bones['WPN_root'];b.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT')
cover=['LMG201_ReferenceTopCover','LMG201_ReferenceCoverCrown','LMG201_ReferenceCoverSideReturn_-1','LMG201_ReferenceCoverSideReturn_1','LMG201_ReferenceCoverLatch_-1','LMG201_ReferenceCoverLatch_1']
for name in cover:
 ob=bpy.data.objects[name];ob.vertex_groups.clear();ob.vertex_groups.new(name='LMG201_Cover').add(list(range(len(ob.data.vertices))),1.,'REPLACE')
# Give the magazine's interior its own visibility identity.
mag=bpy.data.objects['LMG201_Magazine']
for i,m in enumerate(mag.data.materials):
 if m.name=='M_LMG201_Inside':
  m=m.copy();m.name='M_LMG201_MagazineInside';mag.data.materials[i]=m
materials={}
for key in sorted(set(material_keys)):
 base=bpy.data.materials['M_LMG201_ReceiverReferenceCover' if key.endswith('Paint') else 'M_LMG201_ReceiverReferenceHardware']
 mat=base.copy();mat.name=key
 bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if bsdf:
  if key.endswith('Copper'):bsdf.inputs['Base Color'].default_value=(.31,.13,.038,1)
  elif key.endswith('Case'):bsdf.inputs['Base Color'].default_value=(.19,.16,.085,1)
 materials[key]=mat
me=bpy.data.meshes.new('201_BoxAndBelt');me.from_pydata([rr@Vector(v) for v in vs],[],faces);me.update()
keys=sorted(materials)
for k in keys:me.materials.append(materials[k])
uv=me.uv_layers.new(name='UVMap');normals=[]
for p,tex,key,ns in zip(me.polygons,uvs,material_keys,normal_rows):
 p.material_index=keys.index(key);p.use_smooth=True
 for li,xy in zip(p.loop_indices,tex):uv.data[li].uv=xy
 normals.extend((rr.to_3x3()@Vector(n)).normalized() for n in ns)
me.normals_split_custom_set(normals)
ob=bpy.data.objects.new('LMG201_BoxAndBelt',me);sc.collection.objects.link(ob);ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
vgs={n:ob.vertex_groups.new(name=n) for n in new_rest}
for i,weights in enumerate(ws):
 for n,w in weights.items():vgs[n].add([i],w,'REPLACE')
ob.modifiers.new('201FeedRig','ARMATURE').object=r
def box(name,center,size,material,bone='WPN_root'):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name='LMG201_'+name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=False)
 bevel=o.modifiers.new('EdgeFinish','BEVEL');bevel.width=.00035;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
 o.data.materials.append(bpy.data.materials[material]);o.data.transform(rr);o.parent=r;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
 o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))),1,'REPLACE');o.modifiers.new('WeaponRig','ARMATURE').object=r
 return o
# Visible game-art surfaces only: shallow tray, aperture lips, and lid underside.
box('FeedTray',(.0008,-.171,.047),(.061,.124,.004),'M_LMG201_Inside')
for x in [-.030,.0316]:box('FeedTrayRim_'+str(x),(x,-.171,.052),(.003,.124,.007),'M_LMG201_ReceiverReferenceHardware')
box('FeedTrayRearLip',(.0008,-.111,.052),(.061,.003,.007),'M_LMG201_ReceiverReferenceHardware')
box('CoverInnerPanel',(.0008,-.167,.0626),(.051,.108,.0014),'M_LMG201_Inside','LMG201_Cover')
for y in [-.197,-.162,-.127]:box('CoverInnerRib_'+str(y),(.0008,y,.061),(.045,.003,.002),'M_LMG201_ReceiverReferenceHardware','LMG201_Cover')
new_rest={n:[list(row) for row in r.data.bones[n].matrix_local] for n in new_rest}
meta={'source_mesh':d['asset'],'donor_clips':{k:v['asset'] for k,v in d['clips'].items()},'scale':SCALE,'donor_feed_origin':list(origin),'target_feed_origin':list(FEED),'hinge':list(HINGE),'new_rest':new_rest,'cover_objects':cover,'feed_vertices':len(vs),'feed_triangles':sum(len(f)-2 for f in faces),'new_materials':keys,'game_art_only':True,'new_box_capacity_game_setting':100,'private_skeleton':True}
(O/'geometry_authoring.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltFeed_Editable.blend'))
print('201_BELTFEED_GEOMETRY_AUTHORED',len(new_rest),'bones',len(vs),'feed_vertices',flush=True)
