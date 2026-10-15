"""Read-only UE asset checks for the requested shared strength rune."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
source=json.loads((P/'source_report.json').read_text(encoding='utf-8'))
checks=[]
def check(label,passed):checks.append({'check':label,'pass':bool(passed)})
mask_path='/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_strength_rune'
icon_path='/Game/ColdSteelData/AttachmentIcons20260913/blade_2_strength_rune'
mask=u.load_asset(mask_path);icon=u.load_asset(icon_path)
check('saved strength mask loads as Texture2D',isinstance(mask,u.Texture2D))
check('saved shared strength icon loads as Texture2D',isinstance(icon,u.Texture2D))
if mask:check('mask uses linear sampling',not mask.get_editor_property('srgb'))
if icon:
    check('icon has UI texture group',icon.get_editor_property('lod_group')==u.TextureGroup.TEXTUREGROUP_UI)
    check('icon does not stream',icon.get_editor_property('never_stream'))
    check('icon uses EditorIcon compression',icon.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_EDITOR_ICON)

E=u.MaterialEditingLibrary
materials={}
def base_material(material):
    while isinstance(material,u.MaterialInstance):material=material.get_editor_property('parent')
    return material
def describe(material):
    base=base_material(material)
    if not base:return None
    path=base.get_path_name()
    if path not in materials:
        codes=[n.get_editor_property('code') for n in E.get_material_expressions(base) if isinstance(n,u.MaterialExpressionCustom)]
        materials[path]={'name':base.get_name(),
          'vectors':[str(n) for n in E.get_vector_parameter_names(base)],
          'textures':[str(n) for n in E.get_texture_parameter_names(base)],
          'scalars':[str(n) for n in E.get_scalar_parameter_names(base)],
          'shader_uses_red_palette_parameters':any('ConductionCoreColor' in c and 'ConductionGlowColor' in c for c in codes),
          'shader_samples_rune_texture':any('RuneTexture' in c and 'Texture2DSample' in c for c in codes)}
    return materials[path]

overlays={
 'sword':u.load_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2'),
 'hammer':u.load_asset('/Game/Weapons/SteelWarhammer20261014/Runes/ShaftWrapV2/M_SilverRuneSurface_WarhammerShaftV2')}
for kind,material in overlays.items():check(kind+' overlay loads',bool(material))
def rune_shader_ok(material):
    d=describe(material)
    return d and all(n in d['vectors'] for n in ('ConductionCoreColor','ConductionGlowColor')) and 'RuneTexture' in d['textures'] and 'RuneMode' in d['scalars'] and d['shader_uses_red_palette_parameters'] and d['shader_samples_rune_texture']
rows=[]
for weapon in source['weapons']:
    row={'id':weapon['id'],'name':weapon['name'],'slot':weapon['slot'],'variants':[]}
    hammer=weapon['slot']=='rune'
    for spec in weapon['variants']:
        mesh=u.load_asset(spec['mesh'])
        check(weapon['id']+'/'+spec['variant']+' carrier mesh loads',isinstance(mesh,u.StaticMesh))
        carriers=[]
        if mesh:
            for slot in mesh.get_editor_property('static_materials'):
                override=spec.get('materials',{}).get(str(slot.material_slot_name))
                material=u.load_asset(override) if override else slot.material_interface
                base=base_material(material)
                if not base:continue
                name=base.get_name()
                native=name.startswith('M_TangDaoBladeRuneSurface') or name.startswith('M_XuanChiBladeRuneSurface')
                supported=native or 'FrostCrystalSword' in name or 'AzureRunesword' in name or name in ('M_HighlandClaymoreSurface','M_TangDaoSurface') or (hammer and name=='M_SteelWarhammerSurface')
                if supported:
                    shader=material if native else overlays['hammer' if hammer else 'sword']
                    ok=bool(shader and rune_shader_ok(shader))
                    carriers.append({'material':material.get_path_name(),'rune_shader':shader.get_path_name() if shader else None,'binding_valid':ok})
        check(weapon['id']+'/'+spec['variant']+' rune carrier and shader bindings',bool(carriers) and all(c['binding_valid'] for c in carriers))
        row['variants'].append({'id':spec['variant'],'mesh':spec['mesh'],'carriers':carriers})
    rows.append(row)
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'passed':all(c['pass'] for c in checks),'checks_total':len(checks),'checks':checks,'weapons':rows,
 'rune_materials':materials,'pie_was_active':bool(editor and editor.is_in_play_in_editor()),
 'assets_saved':False,'world_modified':False,'inventory_or_saves_modified':False,
 'native_damage_evaluator_executed':False,'live_attack_tested':False,
 'scope':'Actual UE-loaded texture, carrier mesh, material and shader parameter readback; source damage-chain checks are recorded separately.'}
(P/'asset_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('STRENGTH_RUNE_ASSET_CHECK '+json.dumps({'passed':report['passed'],'checks':len(checks),
 'weapon_count':len(rows),'variant_count':sum(len(r['variants']) for r in rows),
 'failed':[c['check'] for c in checks if not c['pass']]},ensure_ascii=False))
