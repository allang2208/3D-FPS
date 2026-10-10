"""Install palette, grip surfaces and weighted tails. Production only; no play/render."""
import json,shutil,traceback
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;PROJECT=P.parents[2]
B='/Game/Weapons/ApprenticeStaff20260927';D=B+'/GripTailRefinement20261009'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
entries=json.loads((P/'Export/meshes.json').read_text(encoding='utf-8'))
specs=json.loads((P/'Export/tail-dynamics.json').read_text(encoding='utf-8'))
surfaces=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
inputs=json.loads((P/'inputs.json').read_text(encoding='utf-8'))
palette=json.loads((P.parent/'RuneRefinement20261009/palette.json').read_text(encoding='utf-8'))
R={'complete':False,'saved_assets':[],'installed':[],'material_bindings':{},'backups':[],
   'runtime_tested':False,'rendered':False,'icons_changed':False,'native_build':'separate compile receipt'}
def record():(P/'install-receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def save(obj):
    if not obj or not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+str(obj))
    R['saved_assets'].append(obj.get_path_name());record();return obj
def backup(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing production source '+path)
    rel=Path(path.split('.')[0].removeprefix('/Game/')+'.uasset');disk=P/'Before/Content'/rel
    if not disk.exists():disk.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content'/rel,disk)
    R['backups'].append({'asset':path,'disk':str(disk)});record()
def clone(source,name):
    target=D+'/Materials/'+name
    return u.load_asset(target) or E.duplicate_asset(source,target)
class Graph:
    def __init__(self,mat):self.mat=mat
    def node(self,cls,**props):
        n=L.create_material_expression(self.mat,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(self,src,dst,pin):
        n,ch=src if isinstance(src,tuple) else (src,'')
        if not pin:pin=str(L.get_material_expression_input_names(dst)[0])
        if not L.connect_material_expressions(n,ch,dst,pin):raise RuntimeError('Cannot connect '+pin)
    def out(self,src,prop):
        n,ch=src if isinstance(src,tuple) else (src,'')
        if not L.connect_material_property(n,ch,prop):raise RuntimeError('Cannot connect output '+str(prop))
    def scalar(self,v,name=None):
        return self.node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=float(v)) if name else self.node(u.MaterialExpressionConstant,r=float(v))
    def color(self,v,name=None):
        return self.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*v,1)) if name else self.node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def custom(self,code,inputs,size=3,label='Staff surface'):
        n=self.node(u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
        fields=[]
        for key in inputs:
            f=u.CustomInput();f.set_editor_property('input_name',key);fields.append(f)
        n.set_editor_property('inputs',fields)
        for key,src in inputs.items():self.wire(src,n,key)
        return n
    def texture(self,path,uv,sampler):
        t=u.load_asset(path)
        if not t:raise RuntimeError('Missing surface input '+path)
        n=self.node(u.MaterialExpressionTextureSample,texture=t,sampler_type=sampler);self.wire(uv,n,'UVs');return n
    def transform(self,src,source,dest):
        n=self.node(u.MaterialExpressionTransform,transform_source_type=source,transform_type=dest);self.wire(src,n,'');return n
    def local_position(self):
        wp=self.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        lp=self.node(u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                     transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);self.wire(wp,lp,'');return lp
    def finish(self):
        L.layout_material_expressions(self.mat);errors=L.recompile_material(self.mat)
        if errors:raise RuntimeError('Material compile failed '+self.mat.get_name()+': '+str(errors))
        return save(self.mat)
def dry_inputs(g,color,rough,normal,metal):
    # Preserve the existing wetness layer exactly once, after the authored dry surface.
    wrappers={str(n.get_editor_property('description')):n for n in L.get_material_expressions(g.mat) if isinstance(n,u.MaterialExpressionCustom)}
    for name,src,prop in [('Color',color,u.MaterialProperty.MP_BASE_COLOR),('Roughness',rough,u.MaterialProperty.MP_ROUGHNESS),('Normal',normal,u.MaterialProperty.MP_NORMAL)]:
        wrapper=wrappers.get('MeleeRain'+name)
        if wrapper:g.wire(src,wrapper,'Base')
        else:g.out(src,prop)
    if 'MeleeRainColor' in wrappers:g.wire(metal,wrappers['MeleeRainColor'],'Metal')
    g.out(metal,u.MaterialProperty.MP_METALLIC)

def grip_materials():
    wood=clone(inputs['grip_lining_false']['materials'][0]['path'],'M_StaffGripCraft_Wood')
    g=Graph(wood);uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    suv=g.custom('return UV*Scale.xy;',{'UV':uv,'Scale':g.color([1,1,1],'GrainScale')},2,'Staff wood physical grain scale')
    source='/Game/UnrealNormandy/Textures/T_WoodSurface_00A_'
    base=g.texture(source+'BaseColor',suv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    packed=g.texture(source+'RHAOM',suv,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    g.out((packed,'B'),u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    normal=g.texture(source+'Normal',suv,u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    color=g.custom('return max(0,lerp(float3(.18,.135,.083),Base,Contrast))*Tint;',
        {'Base':(base,'RGB'),'Contrast':g.scalar(.78,'GrainContrast'),'Tint':g.color([.62,.42,.23],'FinishColor')})
    rough=g.custom('return clamp(Center+(Grain-.5)*Variation,.14,.55);',
        {'Center':g.scalar(.4,'FinishRoughness'),'Grain':(packed,'R'),'Variation':g.scalar(.11,'PoreRoughness')},1)
    n=g.custom('return normalize(float3(N.xy*Strength,N.z));',{'N':(normal,'RGB'),'Strength':g.scalar(.25,'PoreNormal')})
    dry_inputs(g,color,rough,n,g.scalar(0));g.finish()
    alloy=clone(inputs['grip_lining_alloy_grip']['materials'][0]['path'],'M_StaffGripCraft_Alloy');g=Graph(alloy)
    # Authored centimetre-space machining; sub-mm roughness, no coarse bump layer.
    pos=g.local_position()
    grain=g.custom('float a=atan2(Pos.y,Pos.x); float phase=a*370.0+sin(Pos.z*.41)*.16; '
        'float aa=1-smoothstep(.55,2.0,fwidth(phase)); '
        'float band=(1-smoothstep(.11,.18,abs(frac((Pos.z-25)/3.5+.5)-.5)*3.5))*step(24.8,Pos.z)*step(Pos.z,39.2); '
        'return float2(sin(phase)*aa,band);',{'Pos':pos},2,'Staff alloy: submillimetre satin machining and original raised bands')
    color=g.custom('return Tint*(1+Data.y*.055);',{'Tint':g.color([.33,.38,.43],'FinishColor'),'Data':grain})
    rough=g.custom('return Center+Data.x*.008-Data.y*.055;',{'Center':g.scalar(.285,'FinishRoughness'),'Data':grain},1)
    dry_inputs(g,color,rough,g.color([0,0,1]),g.scalar(1));g.finish()
    result={}
    for key,s in surfaces.items():
        name='MI_StaffGripCraft_'+key;mi=u.load_asset(D+'/Materials/'+name) or A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,alloy if s['metallic'] else wood)
        L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*s['color'],1))
        L.set_material_instance_scalar_parameter_value(mi,'FinishRoughness',s['roughness'])
        if not s['metallic']:
            L.set_material_instance_vector_parameter_value(mi,'GrainScale',u.LinearColor(*s['uv_scale'],1))
            for param,v in [('GrainContrast',s['grain_contrast']),('PoreRoughness',s['roughness_variation']),('PoreNormal',s['pore_normal'])]:L.set_material_instance_scalar_parameter_value(mi,param,v)
        L.update_material_instance(mi);result[name]=save(mi)
    return result

def tail_materials():
    result={}
    for name,spec in specs.items():
        key=name.removeprefix('SM_Staff_tail_charm_')
        for i,source in enumerate(inputs['tail_charm_'+key]['materials']):
            mn='M_StaffTailCraft_'+key+('_Metal' if i==0 else '_Element');m=clone(source['path'],mn);g=Graph(m)
            # Capture the existing wet-aware tangent normal before publishing the skin normal.
            rain=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='MeleeRainNormal'),None)
            normal=rain or L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL) or g.color([0,0,1])
            if i==0:
                # Real metal rather than the old whole-surface intermediate metallic value.
                metal=g.scalar(1);g.out(metal,u.MaterialProperty.MP_METALLIC)
                for node in L.get_material_expressions(m):
                    if isinstance(node,u.MaterialExpressionCustom) and str(node.get_editor_property('description'))=='MeleeRainColor':g.wire(metal,node,'Metal')
            skin=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
            vc=g.node(u.MaterialExpressionVertexColor);active=g.scalar(0,'TasselActive');lp=g.local_position()
            bindings={'Skin':skin,'Active':active,'Mask':(vc,'R')}
            for j,rest in enumerate(spec['guides_cm'][:7]):
                q=g.node(u.MaterialExpressionVectorParameter,parameter_name='TasselQ'+str(j),default_value=u.LinearColor(0,0,0,1))
                qa=g.node(u.MaterialExpressionAppendVector);g.wire((q,'RGB'),qa,'A');g.wire((q,'A'),qa,'B')
                bindings.update({'R'+str(j):g.color(rest),'P'+str(j):g.color(rest,'TasselP'+str(j)),'Q'+str(j):qa})
            pre='float3 R[7]={R0,R1,R2,R3,R4,R5,R6}; float3 P[7]={P0,P1,P2,P3,P4,P5,P6}; float4 Q[7]={Q0,Q1,Q2,Q3,Q4,Q5,Q6}; int a=clamp((int)floor(Skin.x+.01),0,6); int b=min(a+1,6); float w=saturate(1-Skin.y); '
            deform=g.custom(pre+'float3 va=V-R[a],vb=V-R[b]; float3 pa=va+2*cross(Q[a].xyz,cross(Q[a].xyz,va)+Q[a].w*va)+P[a]; float3 pb=vb+2*cross(Q[b].xyz,cross(Q[b].xyz,vb)+Q[b].w*vb)+P[b]; return (lerp(pa,pb,w)-V)*(Active*Mask);',dict(bindings,V=lp),label='StaffTailSkinPosition')
            wd=g.transform(deform,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.out(wd,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
            localn=g.transform(normal,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
            n=g.custom(pre+'float3 na=V+2*cross(Q[a].xyz,cross(Q[a].xyz,V)+Q[a].w*V); float3 nb=V+2*cross(Q[b].xyz,cross(Q[b].xyz,V)+Q[b].w*V); return normalize(lerp(V,lerp(na,nb,w),Active*Mask));',dict(bindings,V=localn),label='StaffTailSkinNormal')
            worldn=g.transform(n,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
            m.set_editor_property('tangent_space_normal',False);g.out(worldn,u.MaterialProperty.MP_NORMAL)
            result[mn]=g.finish()
    return result

def install():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE active; no staff assets changed')
    targets={folder+'/'+e['name'] for folder in [B+'/Meshes',B+'/BarkRebuildV21/Meshes'] for e in entries}
    rune_paths={B+'/RuneRefinement20261009/Materials/M_StaffRuneCraft_'+k for k in palette}
    table_path='/Game/Weather/MeleeWetness20261002/DA_MeleeWetMaterials'
    conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets|rune_paths|{table_path}]
    if conflicts:raise RuntimeError('Unsaved production assets preserved: '+str(conflicts))
    for path in sorted(targets|rune_paths|{table_path}):backup(path)
    if globals().get('RESUME_SAVED_MATERIALS',False):
        materials={mn:u.load_asset(D+'/Materials/'+mn) for e in entries for mn in e['materials']}
        if not all(materials.values()):raise RuntimeError('Resume requires previously saved surface materials')
        R['reused_saved_materials']=[m.get_path_name() for m in materials.values()]
    else:
        materials=grip_materials();materials.update(tail_materials())
        for key,p in palette.items():
            m=u.load_asset(B+'/RuneRefinement20261009/Materials/M_StaffRuneCraft_'+key)
            for n in L.get_material_expressions(m):
                if isinstance(n,u.MaterialExpressionVectorParameter):
                    if str(n.get_editor_property('parameter_name'))=='MetalColor':n.set_editor_property('default_value',u.LinearColor(*p['metal'],1))
                    if str(n.get_editor_property('parameter_name'))=='GlowColor':n.set_editor_property('default_value',u.LinearColor(*p['glow'],1))
            Graph(m).finish()
    R['rune_palette']=palette
    # Existing weather binding can then retain item-specific wetness on the new MIDs.
    table=u.load_asset(table_path);mapping=dict(table.get_editor_property('wet_materials'))
    for mat in materials.values():mapping[mat.get_path_name()]=mat
    table.set_editor_property('wet_materials',mapping);save(table)
    static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    def setup(mesh,dynamic):
        s=static.get_lod_build_settings(mesh,0);s.use_full_precision_u_vs=True;s.recompute_normals=False;s.recompute_tangents=True
        if dynamic:s.generate_lightmap_u_vs=False
        static.set_lod_build_settings(mesh,0,s)
        if dynamic:
            ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        opt=u.FbxImportUI()
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.automated_import_should_detect_type=False;opt.import_materials=False;opt.import_textures=False
        cfg=opt.static_mesh_import_data
        for k,v in dict(combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,build_nanite=False,
            import_uniform_scale=1.,convert_scene=True,convert_scene_unit=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
            vertex_color_import_option=u.VertexColorImportOption.REPLACE).items():cfg.set_editor_property(k,v)
        for entry in entries:
            task=u.AssetImportTask()
            for k,v in dict(filename=entry['fbx'],destination_path=D+'/Meshes',destination_name=entry['name'],automated=True,
                replace_existing=True,save=False,options=opt).items():task.set_editor_property(k,v)
            A.import_asset_tasks([task]);mesh=u.load_asset(D+'/Meshes/'+entry['name'])
            if not mesh:raise RuntimeError('Missing imported mesh '+entry['name'])
            for i,slot in enumerate(mesh.static_materials):
                mn=str(slot.get_editor_property('imported_material_slot_name'))
                if mn not in materials:raise RuntimeError('Unknown authored material '+mn)
                mesh.set_material(i,materials[mn])
            setup(mesh,entry['tail_dynamics']);save(mesh)
            dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy '+entry['name'])
            slots=list(mesh.static_materials)
            opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,
                new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],use_build_scale=False)
            for folder in [B+'/Meshes',B+'/BarkRebuildV21/Meshes']:
                old=u.load_asset(folder+'/'+entry['name'])
                # UV1 is authored skin data and must survive the geometry transfer.
                setup(old,entry['tail_dynamics'])
                _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,old,opts,u.GeometryScriptMeshWriteLOD())
                if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot install '+old.get_path_name())
                old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'],0,'GripTailRefinement20261009');setup(old,entry['tail_dynamics']);save(old)
                R['installed'].append(old.get_path_name());R['material_bindings'][old.get_path_name()]=[s.material_interface.get_path_name() for s in old.static_materials];record()
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    R['complete']=True;record();print('STAFF_GRIP_TAIL_SAVED grips=4 tails=4 rune_colors=3 game_tested=false',flush=True)
try:install()
except Exception:R['error']=traceback.format_exc();record();raise
