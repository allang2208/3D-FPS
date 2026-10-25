"""Local crown repair: retain the published atlas, interfaces and corner normals."""
import bpy,bmesh,ast,types,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;OLD=P.parent/'StormDriveBuildV1';ROOT=P.parents[2]
RUNE=ROOT/'SourceAssets/RuneboundWarhammer20261022'
code=(RUNE/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('trim_repair');m.__file__=str(P/'repair_model.py')
exec(compile(code,'<solid_tools>','exec'),m.__dict__)
def key(p):return tuple(round(float(x),7) for x in p)
plans={};reports=[]
for label,bottom,high,left,right,depth in [('Steel',.865,.985,-.04,.04,.0255),('Runebound',.842,.980,-.0354452141,.0345547859,.024)]:
    bpy.ops.wm.open_mainfile(filepath=str(OLD/('StormDrive_'+label+'_Construction.blend')))
    cz=(bottom+.012+high)/2;h=(high-bottom-.012)/2;w=(right-left)/2-.0015
    parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('host_variant')==label]
    strips=[o for o in parts if o.name.startswith('Continuous_ivory_silver_edge')]
    pins=[o for o in parts if o.name.startswith('Small_flush_binding_rivet') and min((o.matrix_world@v.co).z for v in o.data.vertices)>cz+h*.9]
    removed={key(o.matrix_world@v.co) for o in strips for v in o.data.vertices};moved={};pin_rows=[]
    for o in pins:
        pts=[o.matrix_world@v.co for v in o.data.vertices];center=sum(pts,Vector())/len(pts);sy=1 if center.y>0 else -1
        band_depth=depth*.94;dz=.00075;half=.0015
        normal=Vector((0,sy,band_depth*.04/half)).normalized()
        rotation=Vector((0,sy,0)).rotation_difference(normal)
        contact=Vector((center.x,sy*band_depth*(1-.04*dz/half),high-.004+dz))
        newcenter=contact+normal*.000075
        for pt in pts:moved[key(pt)]=(newcenter+rotation@(pt-center),rotation)
        pin_rows.append({'old_center_m':list(center),'new_center_m':list(newcenter),'normal':list(normal),'base_embed_mm':.2})
    assert len(strips)==4 and len(pins)==14,(label,len(strips),len(pins))
    plans[label]={'remove':removed,'move':moved,'cz':cz,'h':h,'w':w,'depth':depth,'cx':(left+right)/2}
    reports.append({'variant':label,'removed_floating_strokes':len(strips),'reseated_top_rivets':len(pins),'rivet_seating':pin_rows})

def extract_preserved(source,name,removed=None,moved=None):
    removed=removed or set();moved=moved or {};mesh=source.data
    keep=[v.index for v in mesh.vertices if key(v.co) not in removed]
    mapping={old:i for i,old in enumerate(keep)};vertices=[moved.get(key(mesh.vertices[i].co),(mesh.vertices[i].co,None))[0] for i in keep]
    polys=[p for p in mesh.polygons if all(i in mapping for i in p.vertices)]
    loops=[li for p in polys for li in p.loop_indices]
    normals=[]
    for li in loops:
        n=mesh.corner_normals[li].vector.copy();motion=moved.get(key(mesh.vertices[mesh.loops[li].vertex_index].co))
        normals.append(motion[1]@n if motion else n)
    data=bpy.data.meshes.new(name+'_Geometry');data.from_pydata(vertices,[],[tuple(mapping[i] for i in p.vertices) for p in polys]);data.update()
    for material in mesh.materials:data.materials.append(material)
    for dst,src in zip(data.polygons,polys):dst.material_index=src.material_index;dst.use_smooth=src.use_smooth
    for layer in mesh.uv_layers:
        uv=data.uv_layers.new(name=layer.name)
        for dst,li in zip(uv.data,loops):dst.uv=layer.data[li].uv
    sharp={tuple(sorted((mapping[e.vertices[0]],mapping[e.vertices[1]]))) for e in mesh.edges if e.use_edge_sharp and all(v in mapping for v in e.vertices)}
    for e in data.edges:e.use_edge_sharp=tuple(sorted(e.vertices)) in sharp
    data.normals_split_custom_set(normals)
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    for prop in source.keys():obj[prop]=source[prop]
    # This repair's geometry/UV preservation check is explicitly user-requested.
    assert all(tuple(data.uv_layers[0].data[j].uv)==tuple(mesh.uv_layers[0].data[li].uv) for j,li in enumerate(loops))
    unchanged=sum(1 for old in keep if key(mesh.vertices[old].co) not in moved)
    assert all((data.vertices[mapping[i]].co-mesh.vertices[i].co).length<1e-9 for i in keep if key(mesh.vertices[i].co) not in moved)
    return obj,{'retained_vertices':len(keep),'unchanged_vertices':unchanged,'removed_vertices':len(mesh.vertices)-len(keep),'preserved_face_corners':len(loops),'uv_preserved':True}

bpy.ops.wm.open_mainfile(filepath=str(OLD/'StormDriveSeats_Editable.blend'))
models={}
for label in ('Steel','Runebound'):
    old=bpy.data.objects['SM_'+label+'Warhammer_StormDrive_V1'];plan=plans[label]
    new,record=extract_preserved(old,'SM_'+label+'Warhammer_StormDrive_V2',plan['remove'],plan['move'])
    assert record['removed_vertices']==240,(label,record)
    models[label]=new;next(r for r in reports if r['variant']==label).update(record)
    bpy.data.objects.remove(old,do_unlink=True)
    new.hide_render=True;new.hide_set(True)

m.BUILD=bpy.data.collections.new('02_Closed_Seated_Silver_Rim');bpy.context.scene.collection.children.link(m.BUILD)
bpy.context.preferences.view.use_translate_new_dataname=False
bpy.context.preferences.view.use_translate_interface=False
sys.path.insert(0,str(RUNE/'HeadRunePBRV3'))
from surface_authoring import refine_metal
silver=m.procedural_metal('AUTHOR_ClosedRim_IvorySilver',(.26,.28,.30),(.51,.52,.53),.29,.000016);refine_metal(silver)
tree=ast.parse((OLD/'author_model.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('arch','ring')],type_ignores=[]),'<matched_vault_rim>','exec'))
new_rims=[];plan=plans['Steel']
for sy in (-1,1):
    f=m.frame((0,sy*plan['depth'],plan['cz']),(0,sy,0),(-sy,0,0))
    obj=ring('Closed_supported_silver_vault_rim',f,arch(plan['w']*.862,plan['h']*.895),arch(plan['w']*.826,plan['h']*.855),.00845,.00945,silver)
    new_rims.append(obj)
rim=m.join_group(new_rims,'StormDrive_ClosedSilverTrim');m.unwrap(rim)
bm=bmesh.new();bm.from_mesh(rim.data);rim_boundary=sum(e.is_boundary for e in bm.edges);rim_nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
assert rim_boundary==0 and rim_nonmanifold==0,(rim_boundary,rim_nonmanifold)
rim['back_embed_mm']=.55;rim['closed_boundary_edges']=rim_boundary
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDrive_TrimRepair_Construction.blend'))
start=code.index('def bake_maps(');end=code.index('\ndef finalize(',start)
bake=code[start:end].replace('4096','2048').replace('T_FinalToll_','T_StormDrive_ClosedTrim_').replace('M_FinalToll_PBR_Surface','M_StormDrive_ClosedSilverTrim')
exec(compile(bake,'<local_trim_pbr>','exec'),m.__dict__);m.bake_maps(rim)
runerim=rim.copy();runerim.data=rim.data.copy();m.BUILD.objects.link(runerim)
scale=Vector((plans['Runebound']['w']/plan['w'],1,plans['Runebound']['h']/plan['h']))
normals=[v.vector.copy() for v in runerim.data.corner_normals]
for v in runerim.data.vertices:
    v.co.x=v.co.x*scale.x+plans['Runebound']['cx']
    v.co.y+=(-1 if v.co.y<0 else 1)*(plans['Runebound']['depth']-plan['depth'])
    v.co.z=(v.co.z-plan['cz'])*scale.z+plans['Runebound']['cz']
runerim.data.normals_split_custom_set([Vector((n.x/scale.x,n.y,n.z/scale.z)).normalized() for n in normals])
rows=[]
for label,trim in [('Steel',rim),('Runebound',runerim)]:
    model=models[label];model.hide_set(False);model.hide_render=False
    final=m.join_group([model,trim],model.name);final['model_revision']='StormDriveTrimV2';final['rim_closed']=True
    fbx=P/'Export'/(final.name+'.fbx');m.activate(final)
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    final.data.calc_loop_triangles();models[label]=final
    rows.append({'variant':label,'mesh':final.name,'fbx':str(fbx),'triangles':len(final.data.loop_triangles),'materials':[v.name for v in final.data.materials]})
    final.hide_render=True;final.hide_set(True)
models['Steel'].hide_render=False;models['Steel'].hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDriveSeats_Editable_V2.blend'))
(P/'repair_receipt.json').write_text(json.dumps({'complete':True,'parts':rows,'repairs':reports,'new_rim_boundary_edges':rim_boundary,'new_rim_nonmanifold_edges':rim_nonmanifold,'original_4k_atlases_retained':True,'trim_pbr_resolution':2048,'game_tested':False},indent=2),encoding='utf-8')
print('STORM_DRIVE_CROWN_REPAIR_EXPORTED',flush=True)
