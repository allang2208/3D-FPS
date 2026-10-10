from pathlib import Path
root=Path(__file__).resolve().parent
text=(root.parent/'ElementHeadsV37/install_ue.py').read_text(encoding='utf-8')
text=text.replace('V37','V38').replace("'revision':37","'revision':38")
text=text.replace('the four existing paths','the three requested existing paths')
text=text.replace("if conflicts:raise RuntimeError('Unsaved target crystal assets: '+', '.join(conflicts))", "conflicts=[p for p in conflicts if p not in globals().get('OWNED_INCOMPLETE_ASSETS',())]\nif conflicts:raise RuntimeError('Unsaved target crystal assets: '+', '.join(conflicts))")
text=text.replace("'Ice':(.10,.54,.75)","'Ice':(.78,.88,1.)")
text=text.replace("'Magma':(1.,.095,.003)","'Magma':(1.,.17,.008)")
text=text.replace("if kind in ('Ice','Storm'):","if kind=='Storm':")
text=text.replace("idle={'Ice':.12,'Magma':3.2", "idle={'Ice':.06,'Magma':4.8")
start=text.index("for kind in ('Ice','Storm'):")
end=text.index('\nmesh_editor=',start)
text=text[:start]+'''def custom(g,filename,inputs,width):
    node=g.node(u.MaterialExpressionCustom,
        code=(ROOT/filename).read_text(encoding='utf-8'),
        output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)),
        desc=filename)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    node.set_editor_property('inputs',pins)
    for name,source in inputs.items():g.wire(source,node,name)
    return node


# The existing shell encloses an animated emissive discharge, with no solid center.
name='M_StaffCraft_StormInner_V38';g=Graph(name)
g.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
g.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
g.mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
time=g.node(u.MaterialExpressionTime)
vertex=g.node(u.MaterialExpressionVertexColor)
offset=custom(g,'core_displacement.hlsl',{'UV':uv,'Clock':time},3)
world=g.node(u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
g.wire(offset,world,'Input');g.output(world,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
radiance=custom(g,'core_radiance.hlsl',{'UV':uv,'Clock':time,'Core':g.channel(vertex,'R')},3)
amount=g.node(u.MaterialExpressionScalarParameter,parameter_name='StaffLightAmount',default_value=0.)
exposure=g.node(u.MaterialExpressionEyeAdaptationInverse,desc='StaffLightExposureV32')
boost=g.add(g.scalar(1.),g.mul(amount,g.scalar(.08)))
g.output(g.mul(g.mul(radiance,exposure),boost),u.MaterialProperty.MP_EMISSIVE_COLOR)
g.output(g.scalar(1.),u.MaterialProperty.MP_OPACITY)
materials[name]=g.finish()
''' +text[end:]
text=text.replace("receipt['gameplay_or_cpp_changed']=False", "receipt['gameplay_or_cpp_changed']=False\nreceipt['jade_changed']=False\nreceipt['storm_core_animation']='12 Hz reshaping plus traveling pulses; GPU WPO; no solid center'")
(root/'install_ue.py').write_text(text,encoding='utf-8')
print('V38_INSTALLER_WRITTEN')
