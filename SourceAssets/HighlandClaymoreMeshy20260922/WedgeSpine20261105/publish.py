"""Publish the two finish/rune-compatible materials, then the live mesh and menu icon."""
from pathlib import Path
import json
import runpy
import unreal as u

if 'AUTHOR_FOLDER' not in globals():
    raise RuntimeError('Retired direct V1 entry. Run WedgeSpineJunctionR4_20261106/publish.py.')
P=Path(AUTHOR_FOLDER)
spec=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
folder,surface=spec['surface'].rsplit('/',1)
hosts='/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface'
channels=('BaseColor','Normal','Roughness','Metallic')
assets=u.EditorAssetLibrary
edit=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and editor and editor.is_in_play_in_editor():
    raise RuntimeError('End play before replacing the installed ridge-piercer.')
targets=[folder+'/T_RidgeWedge_'+k for k in channels]+[spec['surface'],spec['surface']+'_Whirlwind',
         folder.rsplit('/',1)[0]+'/SM_Highland_Blade_RidgePiercer_V1',
         '/Game/ColdSteelData/AttachmentIcons20260913/'+Path(spec['icon']).stem]
dirty={pkg.get_path_name() for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
occupied=dirty.intersection(targets)
if occupied:
    raise RuntimeError('Preserving unsaved targets: '+', '.join(sorted(occupied)))
assets.make_directory(folder)

def save(asset):
    if not assets.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())

textures={}
for key in channels:
    name='T_RidgeWedge_'+key
    task=u.AssetImportTask()
    task.filename=str(P/'Textures'/(name+'.png'))
    task.destination_path=folder
    task.destination_name=name
    task.factory=u.TextureFactory()
    task.automated=True
    task.replace_existing=True
    task.save=False
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Texture import failed: '+name)
    tex=u.load_asset(folder+'/'+name)
    tex.set_editor_property('srgb',key=='BaseColor')
    compression={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'Normal':u.TextureCompressionSettings.TC_NORMALMAP}
    tex.set_editor_property('compression_settings',compression.get(key,u.TextureCompressionSettings.TC_MASKS))
    if spec.get('etched_rune_mask') and key=='BaseColor':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
    if key=='Normal':
        tex.set_editor_property('flip_green_channel',True)
    save(tex)
    textures[key]=tex

for suffix,host in [('',hosts),('_Whirlwind',hosts+'_Whirlwind_HighlandExclusive20261103')]:
    dest=folder+'/'+surface+suffix
    mat=u.load_asset(dest) if assets.does_asset_exist(dest) else assets.duplicate_asset(host,dest)
    if not mat:
        raise RuntimeError('Could not create material from '+host)
    bound=set()
    for node in edit.get_material_expressions(mat):
        if not isinstance(node,u.MaterialExpressionTextureBase):
            continue
        old=node.get_editor_property('texture')
        if not old:
            continue
        for key in channels:
            if old.get_name() in ('T_Highland_'+key,'T_RidgeWedge_'+key):
                node.set_editor_property('texture',textures[key])
                bound.add(key)
                break
    if bound!=set(channels):
        raise RuntimeError('Material '+dest+' lacks source channels: '+str(set(channels)-bound))
    if spec.get('etched_rune_mask'):
        # Never infer emissive from the colour of steel or BC block noise. The
        # two original native-ink nodes retain their gold/wild selection logic.
        nodes=list(edit.get_material_expressions(mat))
        packed=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample)
                    and n.get_editor_property('texture')==textures['Metallic'])
        old_mask='saturate((min(Tex.g,Tex.b)-Tex.r-0.045)*14.0)*saturate((Tex.b-0.12)*8.0)'
        native=[n for n in nodes if isinstance(n,u.MaterialExpressionCustom)
                and 'HIGHLAND_WILD_NATIVE' in n.get_editor_property('code')]
        if len(native)!=2:
            raise RuntimeError('Missing native colour/emissive pair in '+dest)
        for node in native:
            code=node.get_editor_property('code')
            if 'RidgeInk' not in code:
                if old_mask not in code:
                    raise RuntimeError('Unrecognized native ink expression in '+dest)
                pins=list(node.get_editor_property('inputs'))
                pin=u.CustomInput()
                pin.set_editor_property('input_name','RidgeInk')
                node.set_editor_property('inputs',pins+[pin])
                node.set_editor_property('code',code.replace(old_mask,'saturate(RidgeInk)').replace(
                    'lerp(1.1,3.0,Gold)','lerp(.12,1.1,Gold)'))
            if not edit.connect_material_expressions(packed,'G',node,'RidgeInk'):
                raise RuntimeError('Could not bind the engraved rune mask in '+dest)
        # Preserve the inlaid silver, brass and hollow grind under other alloys.
        # Blend before the existing wetness/temporal graph so those effects
        # still apply to the complete weapon.
        def inputs(expr):
            return zip(edit.get_material_expression_input_names(expr),edit.get_inputs_for_material_expression(mat,expr))
        for field in ('BASE_COLOR','ROUGHNESS','NORMAL','METALLIC'):
            tag='Ridge inlay '+field
            if any(str(n.get_editor_property('desc'))==tag for n in nodes):
                continue
            finish=next(n for n in nodes if str(n.get_editor_property('desc'))=='SharedTwoHandFinish20261101V1 '+field)
            original=dict(inputs(finish))['Base']
            targets=[(n,pin) for n in nodes for pin,source in inputs(n) if source==finish]
            if not targets:
                raise RuntimeError('Missing finish output '+field+' in '+dest)
            blend=edit.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
            blend.set_editor_property('desc',tag)
            for source,output,target,pin in [(finish,'',blend,'A'),
                    (original,'R' if field in ('METALLIC','ROUGHNESS') else '',blend,'B'),
                    (packed,'B',blend,'Alpha')]+[(blend,'',n,pin) for n,pin in targets]:
                if not edit.connect_material_expressions(source,output,target,pin):
                    raise RuntimeError('Could not bind '+tag+' to '+str(pin))
    errors=edit.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compile: '+str(errors))
    save(mat)

previous=P.parent/'RidgePiercerRootV2_20260927'/'import_ridge_piercer_root_v2.py'
runpy.run_path(str(previous),init_globals={'AUTHOR_FOLDER':P})
print('WEDGE_SPINE_INSTALLED '+spec['revision'])
