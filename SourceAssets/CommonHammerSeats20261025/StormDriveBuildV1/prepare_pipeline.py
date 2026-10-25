"""Derive the existing saved-asset pipeline without running or modifying its source."""
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
OLD=ROOT/'SourceAssets/CommonHammerSeats20261024/AncientSealBuildV1'
text=(OLD/'import_assets.py').read_text('utf-8')
text=text.replace('AncientSeal','StormDrive').replace('CommonHammerSeats20261024','CommonHammerSeats20261025')
text=text.replace('StormDriveBuildV1_20261024','StormDriveBuildV1_20261025')
start=text.index("m=material('M_StormDrive_Inlay')")
end=text.index('for name,mat in materials.items():',start)
text=text[:start]+'''m=material('M_StormDrive_GoldInlay')
time=node(m,u.MaterialExpressionTime)
glow=node(m,u.MaterialExpressionCustom,code='float pulse=.88+.12*sin(Age*4.2); return float3(3.2,1.65,.085)*pulse;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
pin=u.CustomInput();pin.set_editor_property('input_name','Age');glow.set_editor_property('inputs',[pin]);wire(time,glow,'Age')
materials['M_StormDrive_GoldInlay']=surface(m,{'basecolor':vector(m,(.22,.11,.012)),'roughness':constant(m,.27),'metallic':constant(m,.35),'emissivecolor':glow})
''' + text[end:]
text=text[:text.index('D=COMMON\nmesh=imp')]+'''D=COMMON
icon='head_mount_storm_drive_seat'
tex=imp(P/(icon+'.png'),icon);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
receipt.update(complete=True,icon=tex.get_path_name());record()
print('STORM_DRIVE_ASSETS_COMPILED_AND_SAVED')
'''
(P/'import_assets.py').write_text(text,encoding='utf-8')
text=(OLD/'author_icon_input.py').read_text('utf-8').replace('AncientSeal','StormDrive').replace('ancient_seal','storm_drive')
text=text.replace("center=Vector((0,0,.929))","center=Vector((0,0,.929))")
(P/'author_icon_input.py').write_text(text,encoding='utf-8')
for name in ('build.ps1','import_background.ps1'):
    (P/name).write_text((OLD/name).read_text('utf-8-sig'),encoding='utf-8-sig')
print('STORM_DRIVE_AUTHORING_PIPELINE_WRITTEN')
