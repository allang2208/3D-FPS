"""Save two hollow-flue hearths with explicit non-obstructing collision and charcoal finishes."""
import json
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
out=here.parents[3]/'SourceAssets/HillsVillageTavern/KitchenHearth'
stage=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
dest='/Game/WorldGeneration/VillageTavern/KitchenHearth'
api=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=[]

def save(obj):
    if not u.EditorAssetLibrary.save_loaded_asset(obj,False):
        raise RuntimeError('Failed to save '+obj.get_path_name())
    saved.append(obj.get_name())

inputs=json.loads((here/'surfaces.json').read_text())
surfaces={}
for key,path in inputs.items():
    obj=u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing surface dependency '+path)
    surfaces[key]=obj

def finish(label,lower,upper,emission=None):
    # Use the Quixel charcoal scan on real lumps. The mesh supplies the physical silhouette.
    name='M_TavernHearth'+label
    material=api.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    material.set_editor_property('used_with_instanced_static_meshes',True)
    def node(kind,x,y):
        return edit.create_material_expression(material,getattr(u,'MaterialExpression'+kind),x,y)
    def wire(a,out,b,pin):
        if not edit.connect_material_expressions(a,out,b,pin):
            raise RuntimeError('Failed to connect '+name+' '+pin)
    def output(a,pin,mp):
        if not edit.connect_material_property(a,pin,getattr(u.MaterialProperty,'MP_'+mp)):
            raise RuntimeError('Failed to connect '+name+' '+mp)
    def sample(key,kind,y):
        tex=node('TextureSample',-720,y)
        tex.texture=surfaces[key]
        tex.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
        return tex
    def color(value,x,y):
        c=node('Constant3Vector',x,y)
        c.constant=u.LinearColor(*value,1)
        return c
    scan=sample('QuixelColor','COLOR',-140)
    normal=sample('QuixelNormal','NORMAL',150)
    packed=sample('QuixelORM','MASKS',390)
    # Multiply the fine charcoal detail by a controlled pigment, retaining a little substrate
    # in the alpha gaps of the original scatter texture.
    pigment=node('Multiply',-300,-140)
    wire(scan,'RGB',pigment,'A')
    wire(color(upper,-580,-330),'',pigment,'B')
    base=node('Add',-60,-140)
    wire(pigment,'',base,'A')
    wire(color(lower,-310,-330),'',base,'B')
    output(base,'','BASE_COLOR')
    output(normal,'RGB','NORMAL')
    output(packed,'G','ROUGHNESS')
    if emission:
        glow=node('Multiply',120,40)
        wire(base,'',glow,'A')
        wire(color(emission,-140,90),'',glow,'B')
        output(glow,'','EMISSIVE_COLOR')
    edit.recompile_material(material)
    save(material)
    surfaces[label]=material

finish('Ash',(.15,.135,.118),(.48,.46,.42))
finish('Coal',(.015,.013,.012),(.80,.73,.68))
finish('Ember',(.20,.035,.004),(.9,.26,.052),(3.8,2.2,.5))

def box(bounds):
    xa,xb,ya,yb,za,zb=bounds
    b=u.KBoxElem()
    b.set_editor_property('center',u.Vector((xa+xb)/2,(ya+yb)/2,(za+zb)/2))
    for prop,span in zip(('x','y','z'),(xb-xa,yb-ya,zb-za)):
        b.set_editor_property(prop,span)
    return b

for name in ('SM_TavernCookHearth','SM_TavernCookHearthRuined'):
    task=u.AssetImportTask()
    task.filename=str(out/(name+'.fbx'))
    task.destination_path=dest
    task.destination_name=name
    task.automated=True
    task.factory=u.FbxFactory()
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.import_mesh=True
    opt.import_as_skeletal=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False
    opt.import_textures=False
    data=opt.static_mesh_import_data
    data.combine_meshes=True
    data.convert_scene=True
    data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True
    data.import_mesh_lods=True
    data.auto_generate_collision=False
    data.generate_lightmap_u_vs=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt
    api.import_asset_tasks([task])
    mesh=u.load_asset(dest+'/'+name)
    if not mesh:
        raise RuntimeError('Cook hearth import failed '+name)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,surfaces[str(slot.material_slot_name)])
    sm.set_lod_screen_sizes(mesh,[1.,.23,.075])
    body=mesh.get_editor_property('body_setup')
    agg=body.get_editor_property('agg_geom')
    solids=[(.1,104.5,-72.6,72.6,0,9.8),(.2,84.3,-71,71,9.8,26.3),
            (.6,13,-52,52,26.3,140.9),
            (.6,76.3,-69.6,-52,26.3,140.9),(.6,76.3,52,69.6,26.3,140.9),
            (.6,84.5,-71,-64.6,140.9,151),(.6,84.5,64.6,71,140.9,151),
            (78,84.5,-64.6,64.6,140.9,151)]
    # Back, front and both sides of the throat are independently solid through the open shaft.
    for z1,z2,x1,x2,w,g in [(151,177,3,73,55,6),(177,205,7,62,36,6),
                              (205,229,13,55,22,6),(229,665,13,55,21.6,6.2)]:
        solids.extend([(x1,x1+g,-w,w,z1,z2),(x2-g,x2,-w,w,z1,z2),
                       (x1+g,x2-g,-w,-w+g,z1,z2),(x1+g,x2-g,w-g,w,z1,z2)])
    agg.set_editor_property('box_elems',[box(b) for b in solids])
    agg.set_editor_property('convex_elems',[])
    body.set_editor_property('agg_geom',agg)
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    save(mesh)

(stage/'saved.json').write_text(json.dumps(saved,indent=2))
u.log('TAVERN_COOK_HEARTH_SAVED')
