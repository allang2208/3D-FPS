"""Reuse the established native asset writer with this revision's real PBR inputs."""
import ast
from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet')
if (T/'combat2_save.py').exists():
    raise SystemExit('The production writer now contains bounded resume and material signatures; keep combat2_save.py as the authoritative source.')
s=(T/'shirt_save.py').read_text();tree=ast.parse(s);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='material');lines=s.splitlines(True)
replacement='''def material():
    for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
        textures={}
        for channel in ['BaseColor','NormalGL','ORM']:
            file=R/'Textures'/(name+'_'+channel+'.png');path=DEST+'/Textures/'+file.stem
            texture=u.load_asset(path)
            if not texture or E.get_metadata_tag(texture,'CombatTextureSHA')!=sha(file):
                task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST+'/Textures';task.destination_name=file.stem;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=load(path)
                normal=channel=='NormalGL';colour=channel=='BaseColor'
                for key,value in dict(srgb=colour,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if colour else u.TextureCompressionSettings.TC_MASKS,flip_green_channel=normal,never_stream=False,compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,max_texture_size=1024).items():texture.set_editor_property(key,value)
                E.set_metadata_tag(texture,'CombatTextureSHA',sha(file));save(texture)
            textures[channel]=texture
        path=DEST+'/Materials/M_'+name;mat=u.load_asset(path) or A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('two_sided',False)
        for channel,texture in textures.items():
            expression=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name=channel,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if channel=='BaseColor':L.connect_material_property(expression,'RGB',u.MaterialProperty.MP_BASE_COLOR)
            elif channel=='NormalGL':L.connect_material_property(expression,'RGB',u.MaterialProperty.MP_NORMAL)
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:L.connect_material_property(expression,pin,prop)
        L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=.26),'',u.MaterialProperty.MP_SPECULAR)
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Textile material compilation '+str(errors))
        save(mat);receipt['materials'][name]=mat.get_path_name();record()
'''
s=''.join(lines[:node.lineno-1])+replacement+''.join(lines[node.end_lineno:]);s=s.replace('CombatShirtR1','CombatShirtR2').replace("receipt['completed']=len(receipt['wear'])==62","receipt['completed']=all(receipt['wear'].get(row['asset'],{}).get('sha256')==sha(row['file']) for row in manifest['rows'])")
(T/'combat2_save.py').write_text(s,encoding='utf-8')
