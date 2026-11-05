"""M24-specific material regions in the unchanged stock's local centimetres."""
def apply_stock_identity(m,L,u):
    ex=L.get_material_expressions(m)
    cs={str(n.get_editor_property('description')):n for n in ex if isinstance(n,u.MaterialExpressionCustom)}
    if 'M24 measured stock regions' in cs:raise RuntimeError('Stock identity already authored; do not stack')
    p=L.create_material_expression(m,u.MaterialExpressionPreSkinnedPosition)
    interp=L.create_material_expression(m,u.MaterialExpressionVertexInterpolator)
    L.connect_material_expressions(p,'',interp,'VS')
    region=L.create_material_expression(m,u.MaterialExpressionCustom)
    region.set_editor_property('description','M24 measured stock regions')
    region.set_editor_property('code','float rubber=smoothstep(30.8,31.2,P.y);float cheek=smoothstep(12.45,12.65,P.z)*(1-smoothstep(30.0,30.2,P.y));return float4((1-rubber)*(1-cheek),rubber,cheek,0);')
    region.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
    pin=u.CustomInput();pin.set_editor_property('input_name','P');region.set_editor_property('inputs',[pin]);L.connect_material_expressions(interp,'',region,'P')
    for desc,pin_name in [('WS_ColorRough','Identity'),('WS_MetalAO','Metal')]:
        target=cs[desc]
        if pin_name=='Identity':
            ins=list(target.get_editor_property('inputs'))
            if not any(str(x.get_editor_property('input_name'))=='Identity' for x in ins):
                x=u.CustomInput();x.set_editor_property('input_name','Identity');ins.append(x);target.set_editor_property('inputs',ins)
        if pin_name=='Metal':
            mask=L.create_material_expression(m,u.MaterialExpressionComponentMask);mask.set_editor_property('r',True)
            L.connect_material_expressions(region,'',mask,'');L.connect_material_expressions(mask,'',target,pin_name)
            L.connect_material_property(mask,'',u.MaterialProperty.MP_METALLIC)
        else:L.connect_material_expressions(region,'',target,pin_name)
    cr=cs['WS_ColorRough'];code=cr.get_editor_property('code')
    begin=code.index('float metal=');end=code.index('base*=1.',begin)
    code=code[:begin]+'float metal=Identity.r;float ink=smoothstep(.62,.85,min(Src.r,min(Src.g,Src.b)));float3 nonmetal=lerp(float3(.018,.020,.021),float3(.011,.012,.013),Identity.g);float3 base=lerp(lerp(nonmetal,Finish,metal),Src,max(saturate(SrcW),ink*.35));\n'+code[end:]
    code=code.replace('float r=lerp(max(Rough,.59),Rough,metal)+(SrcR-Pivot)*SrcRW;','float r=lerp(lerp(.59,.72,Identity.g),Rough,metal)+(SrcR-Pivot)*SrcRW;')
    cr.set_editor_property('code',code)

if __name__=='__main__':
    import unreal as u,json,shutil
    from pathlib import Path
    O=Path(__file__).resolve().parent;R=json.loads((O/'publish_receipt.json').read_text());L=u.MaterialEditingLibrary
    row=next(v for v in R['materials'].values() if v['mode']=='stock');mi=u.load_asset(row['path']);m=mi.get_base_material()
    path=m.get_path_name().split('.')[0]
    if path in {x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Unsaved stock graph retained')
    b=O/'BeforeIdentity';b.mkdir(exist_ok=True);f=Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
    if (b/f.name).exists():raise RuntimeError('Existing stock graph backup retained')
    shutil.copy2(f,b/f.name)
    apply_stock_identity(m,L,u)
    errs=L.recompile_material(m)
    if errs:raise RuntimeError(str(errs))
    u.EditorAssetLibrary.set_metadata_tag(m,'M24StockIdentity','Frame metal; butt Y 30.8-31.2 cm; cheek Z 12.45-12.65 cm, Y<30 cm; original geometry and UV retained')
    if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Stock graph save failed')
    (O/'stock_identity_receipt.json').write_text(json.dumps({'complete':True,'master':m.get_path_name(),'metallic_source':'measured local part regions','geometry_changed':False,'roughness':{'frame':.48,'cheek':.59,'butt':.72}},indent=2))
    print('M24_STOCK_IDENTITY_SAVED',flush=True)
