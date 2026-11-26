"""Read saved UE packages, not the earlier import receipt. No asset mutation."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
SOURCE=ROOT/'SourceAssets/OneHandAxe20261101/CommonRunes20261104'
E=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
catalog=json.loads((ROOT/'Content/ColdSteelData/tactical-hatchet-modules.json').read_text('utf-8'))
source=json.loads((SOURCE/'sources.json').read_text('utf-8'))
ghost=json.loads((SOURCE.parent/'GhostScythe20261104/RuneSurfaces/GhostScythe.json').read_text('utf8'))
heads=[*source['heads'],ghost]
result={'passed':False,'saved_package_checks':[],'combinations':[],'icons':[],'errors':[],'rendered':False}
def require(ok,message):
    if not ok:result['errors'].append(message)
def load(path):
    asset=u.load_asset(path)
    require(bool(asset),'Missing asset: '+path)
    return asset
def fixed_textures(material):
    return {node.texture.get_path_name() for node in E.get_material_expressions(material)
            if isinstance(node,u.MaterialExpressionTextureSample) and node.texture
            and not isinstance(node,u.MaterialExpressionTextureSampleParameter2D)}
try:
    for head in heads:
        spec=catalog['slots']['blade_1'][head['id']]
        mesh=load(spec['mesh'])
        slots=mesh.get_editor_property('static_materials')
        actual=[str(s.get_editor_property('material_slot_name')) for s in slots]
        require(actual==spec['material_slot_names'],'Slot mismatch: '+head['id'])
        declared=head['target_slot']
        default=load(spec['materials'][declared])
        for index,name in enumerate(actual):
            require(mesh.get_material(index)==load(spec['materials'][name]),'Wrong default material: '+head['id']+'/'+name)
        result['combinations'].append({'head':head['id'],'rune':'factory','material':default.get_path_name()})
        plan=ghost if head is ghost else json.loads((SOURCE/(head['kind']+'.json')).read_text('utf-8'))
        for rune in source['runes']:
            material_path=catalog['slots']['blade_2'][rune['id']]['surface_materials'][declared]
            instance=load(material_path)
            parent=instance.get_editor_property('parent')
            # Compare textures against the active head. The legendary Falcon replaced
            # its original steel graph with a black-steel finish and cyan emission.
            expected_textures=fixed_textures(default)
            require(bool(expected_textures) and expected_textures.issubset(fixed_textures(parent)),
                    'Missing textures from equipped head: '+material_path)
            texture=E.get_material_instance_texture_parameter_value(instance,'RuneMask')
            expected='T_HatchetRune_'+head['kind']+'_'+rune['kind']
            require(texture and texture.get_name()==expected,'Wrong mask: '+material_path)
            require(not texture.get_editor_property('srgb'),'sRGB mask: '+expected)
            require(texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_MASKS,'Mask compression: '+expected)
            require(texture.blueprint_get_size_x()==2048 and texture.blueprint_get_size_y()==2048,'Mask resolution: '+expected)
            placement=next(p for p in plan['placements'] if p['id']==rune['id'])
            scales=placement['centimetres_per_pixel']
            require(abs(scales[0]-scales[1])<1e-8,'Nonuniform glyph scale: '+material_path)
            require(placement['body_margin_mm']>=(1 if head is ghost else 3),'Insufficient body margin: '+material_path)
            result['combinations'].append({'head':head['id'],'rune':rune['id'],'material':material_path,'mask':texture.get_path_name(),'uniform_scale':True})
        build=SM.get_lod_build_settings(mesh,0)
        result['saved_package_checks'].append({'head':head['id'],'mesh':mesh.get_path_name(),'slots':actual,
            'remove_degenerates':bool(build.get_editor_property('remove_degenerates'))})
    # Physical modules other than the head must not share its rune carrier slot.
    rune_slots=set(source_head['target_slot'] for source_head in heads)
    for key in ('grip','pommel','lanyard'):
        for name,spec in catalog['slots'][key].items():
            if spec.get('hidden') or not spec.get('mesh'):continue
            mesh=load(spec['mesh'])
            names={str(s.get_editor_property('material_slot_name')) for s in mesh.get_editor_property('static_materials')}
            require(not names.intersection(rune_slots),'Rune leaks onto '+key+'/'+name)
            for path in spec.get('materials',{}).values():load(path)
    for key in ('blade_1_axe_swift_crescent','blade_1_axe_heavy_cleaver','blade_1_axe_folded_arc'):
        icon=load('/Game/ColdSteelData/AttachmentIcons20260913/'+key)
        require(icon.get_editor_property('srgb') and icon.get_editor_property('never_stream'),'Icon sampling '+key)
        require(icon.get_editor_property('lod_group')==u.TextureGroup.TEXTUREGROUP_UI,'Icon group '+key)
        require(icon.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_EDITOR_ICON,'Icon compression '+key)
        result['icons'].append(icon.get_path_name())
    result['passed']=not result['errors'] and len(result['combinations'])==len(catalog['slots']['blade_1'])*(1+len(source['runes']))
finally:
    (P/'saved-assets.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if not result['passed']:raise RuntimeError('Hatchet asset audit failed: '+str(result['errors']))
u.log('HATCHET_ASSET_AUDIT_PASSED combinations='+str(len(result['combinations'])))
