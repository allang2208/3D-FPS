"""Chapel-specific stone, worn limewash and slate. Called by import_chapel.py."""
def surface_materials():
    master=get(DEST+'/Materials/M_ChapelArtifact')
    if not master.get_editor_property('used_with_nanite'):
        L.set_base_material_usage(master,u.MaterialUsage.MATUSAGE_NANITE,True)
        L.recompile_material(master)
        save(master)
        for name,mi in materials.items():
            if name.startswith('Chapel'):
                L.update_material_instance(mi)
                save(mi)

    slate='/Game/Building/Voxels/Rounded/Textures/T_RoofRoofSlate_'
    ground=runpy.run_path(str(Path(__file__).with_name('chapel_ground_materials.py')))
    patina=runpy.run_path(str(Path(__file__).with_name('chapel_patina.py')))
    scan_env=dict(globals(),ground=ground,patina=patina)
    scan_scope=runpy.run_path(str(Path(__file__).with_name('scan_materials.py')),init_globals=scan_env)
    result=scan_scope['relief_materials']()
    footing_path=DEST+'/Materials/M_ChapelFooting'
    if os.environ.get('CHAPEL_RESUME')=='1' and E.does_asset_exist(footing_path) and 'Footing' not in os.environ.get('CHAPEL_SURFACES','').split():
        result['Footing']=get(footing_path)
    else:
        result['Footing']=ground['footing'](create_mat,save)
    for slot in ('YardField','YardSlate','YardCap'):
        path=DEST+'/Materials/M_Chapel'+slot
        if os.environ.get('CHAPEL_RESUME')=='1' and E.does_asset_exist(path) and slot not in os.environ.get('CHAPEL_SURFACES','').split():
            result[slot]=get(path)
        else:
            result[slot]=ground['yard_stone'](create_mat,save,slot)
    for slot in ('Slate',):
        name='M_Chapel'+slot
        refresh=os.environ.get('CHAPEL_SURFACES','').split()
        if os.environ.get('CHAPEL_RESUME')=='1' and E.does_asset_exist(DEST+'/Materials/'+name) and slot not in refresh:
            result[slot]=get(DEST+'/Materials/'+name)
            continue
        mat=create_mat(name)
        def node(cls):return L.create_material_expression(mat,cls)
        def link(src,dst,pin,srcpin=''):
            if not L.connect_material_expressions(src,srcpin,dst,pin):raise RuntimeError('chapel surface '+pin)
        def scalar(value):
            n=node(u.MaterialExpressionConstant);n.r=value;return n
        def color(rgb):
            n=node(u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*rgb,1);return n
        def mult(a,b):
            n=node(u.MaterialExpressionMultiply);link(a,n,'A');link(b,n,'B');return n
        def tex(path,normals=False,repeat=1.):
            n=node(u.MaterialExpressionTextureSample);n.texture=get(path)
            n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normals else u.MaterialSamplerType.SAMPLERTYPE_COLOR
            uv=node(u.MaterialExpressionTextureCoordinate);uv.u_tiling=repeat;uv.v_tiling=repeat;link(uv,n,'UVs')
            return n
        c=mult(tex(slate+'BaseColor',repeat=.48),color((.29,.34,.39)))
        normal=tex(slate+'Normal',True,.48)
        slate_uv=node(u.MaterialExpressionTextureCoordinate);slate_uv.u_tiling=.48;slate_uv.v_tiling=.48
        packed=ground['texture'](mat,slate+'RHAOM',slate_uv)
        c,normal,rough,_=patina['finish_surface'](mat,'Slate',ground,c,normal,(packed,'R'),(packed,'B'))
        out(c,'','BASE_COLOR');out(normal,'RGB','NORMAL');out(rough,'','ROUGHNESS')
        L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
        L.recompile_material(mat);save(mat);result[slot]=mat
    for role in ('Door','Pew','Lancet','Buttress'):
        instance=materials['Chapel'+role]
        finish=DEST+'/Materials/M_Chapel'+role+'Finish'
        if role in os.environ.get('CHAPEL_SURFACES','').split() or not E.does_asset_exist(finish) or os.environ.get('CHAPEL_RESUME')!='1':
            patina['artifact_finish'](role,instance,create_mat,save,ground)
    return result

