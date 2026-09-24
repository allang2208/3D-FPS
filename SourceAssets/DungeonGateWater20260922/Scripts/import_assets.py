"""Import authored gate/water assets. Shared fountain assets are read only."""
import unreal as u,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/GateWater'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('FPSGAME is required')
if any(p.get_path_name().startswith(BASE+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved GateWater assets')
textures={key:u.load_asset('/Game/Dungeons/AtmosphereV2/Services/Textures/T_Service_'+key) for key in ('AgeMask','Normal','RustColor')}
fountain_noise=u.load_asset('/Game/Props/RomanFountain20260917/OverflowV8/T_FountainFlowNoiseV8')
if not all(textures.values()) or not fountain_noise:raise RuntimeError('Existing service/fountain texture dependencies are required')

def node(kind):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
def wire(a,ao,b,bi):
    if not L.connect_material_expressions(a,ao,b,bi):raise RuntimeError('Material wire '+bi)
def output(a,prop,pin=''):
    if not L.connect_material_property(a,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def constant(v):n=node('Constant');n.set_editor_property('r',v);return n
def scalar(name,v):
    n=node('ScalarParameter');n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',v);return n
def color(name,v):
    n=node('VectorParameter');n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*v,1));return n
def sample(texture,mode,uv=None):
    n=node('TextureSample');n.set_editor_property('texture',texture);n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+mode))
    if uv:wire(uv,'',n,'UVs')
    return n
def custom(code,inputs,count=1):
    n=node('Custom');n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(count)))
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():
        if isinstance(value,tuple):wire(value[0],value[1],n,key)
        else:wire(value,'',n,key)
    return n
def blend(a,b,mask):
    n=node('LinearInterpolate');wire(a,'',n,'A');wire(b,'',n,'B');wire(mask,'',n,'Alpha');return n
def saved(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def finish():
    L.layout_material_expressions(mat)
    errors=list(L.recompile_material(mat))
    if errors:raise RuntimeError('Material compilation failed '+mat.get_path_name()+': '+'; '.join(errors))
    saved(mat)

materials={}
for key,r in MAN['materials'].items():
    name='M_DungeonGate_'+key if key!='Water' else 'M_Dungeon_ShallowPuddle'
    path=BASE+'/Materials/'+name;mat=u.load_asset(path)
    # Re-running scene assembly reuses saved graphs rather than deleting referenced expressions.
    if mat:
        materials['GateWater_'+key]=mat;continue
    mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    if key=='Water':
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property('tangent_space_normal',False);mat.set_editor_property('two_sided',False)
        pos=node('WorldPosition');uv=node('TextureCoordinate');time=node('Time');vc=node('VertexColor')
        uv1=custom('return P.xy/85.0+float2(T*0.007,-T*0.004);',{'P':pos,'T':time},2)
        uv2=custom('return P.yx/53.0+float2(-T*0.005,T*0.009);',{'P':pos,'T':time},2)
        # Fountain V8 noise uses TC_MASKS, not ordinary linear-color compression.
        n1=sample(fountain_noise,'MASKS',uv1);n2=sample(fountain_noise,'MASKS',uv2)
        normal=custom((ROOT/'Scripts/puddle_normal.hlsl').read_text(),dict(P=pos,UV=uv,T=time,Meta=vc,NoiseA=n1,NoiseB=n2,
            WaveStrength=scalar('WaveStrength',1.0),DripStrength=scalar('DripStrength',1.0)),3)
        output(normal,'NORMAL')
        view=node('CameraVectorWS')
        fres=custom('return pow(1.0-saturate(dot(normalize(V),N)),5.0);',{'V':view,'N':normal})
        opacity=custom('return Meta.r*saturate(Opacity+F*0.55);',{'Meta':vc,'F':fres,'Opacity':scalar('CenterOpacity',.22)})
        fade=node('DepthFade');wire(opacity,'',fade,'Opacity');wire(scalar('ContactFadeCm',.6),'',fade,'FadeDistance')
        output(fade,'OPACITY')
        rough=custom('return lerp(0.27,Core,smoothstep(0.05,0.78,Meta.r));',{'Meta':vc,'Core':scalar('CoreRoughness',.075)})
        output(rough,'ROUGHNESS');output(constant(0),'METALLIC');output(scalar('WaterSpecular',.255),'SPECULAR')
        output(color('WaterTint',r['color']),'BASE_COLOR')
        # Surface lighting reflects the actual dungeon. No outdoor emissive cubemap,
        # opaque caustics overlay, fountain foam, refraction offset or raised WPO.
    else:
        base=color('FinishColor',r['color']);rough=scalar('FinishRoughness',r['roughness']);metal=constant(r['metallic'])
        if key!='Dark':
            vc=node('VertexColor');noise=sample(textures['AgeMask'],'MASKS')
            chips=custom('return saturate((N.r-0.60)*8.0)*Meta.r*Wear;',{'N':noise,'Meta':vc,'Wear':scalar('EdgeWear',.80)})
            rust=custom('return smoothstep(0.30,0.73,N.r)*Meta.b*Amount;',{'N':noise,'Meta':vc,'Amount':scalar('RustAmount',.77)})
            if key=='Paint':
                base=blend(base,color('ExposedSteel',[.14,.16,.16]),chips)
                rough=blend(rough,constant(.32),chips);metal=blend(metal,constant(.9),chips)
            rust_tex=sample(textures['RustColor'],'COLOR')
            base=blend(base,rust_tex,rust);rough=blend(rough,constant(.88),rust);metal=blend(metal,constant(0),rust)
            base=custom('return C*(1.0-Meta.g*0.42);',{'C':base,'Meta':vc},3)
            normal=sample(textures['Normal'],'NORMAL')
            restrained=custom('return normalize(float3(N.xy*Strength,N.z));',{'N':normal,'Strength':scalar('MicroNormalStrength',.50)},3)
            output(restrained,'NORMAL')
        output(base,'BASE_COLOR');output(rough,'ROUGHNESS');output(metal,'METALLIC');output(constant(.38),'SPECULAR')
    if key=='Water':
        import sys
        sys.path.insert(0,str(ROOT.parents[1]/'Tools/Fluids'))
        from author_water_impacts_all import augment_static_surface
        augment_static_surface(mat)
    finish();materials['GateWater_'+key]=mat

meshes=[]
for entry in MAN['meshes']:
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=entry['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.generate_lightmap_u_vs=False;d.auto_generate_collision=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=u.load_asset(BASE+'/Meshes/'+entry['name'])
    if not mesh:raise RuntimeError('Mesh import failed '+entry['name'])
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));mesh.set_material(i,materials[key])
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    if entry['collision']:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    saved(mesh);meshes.append(mesh.get_path_name())
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/import.json').write_text(json.dumps(dict(stage='assets_saved',meshes=meshes,materials=[m.get_path_name() for m in materials.values()],reused_fountain_noise=fountain_noise.get_path_name(),tests_run=False),indent=2),encoding='utf-8')
print('DUNGEON_GATE_WATER_ASSETS_SAVED')
