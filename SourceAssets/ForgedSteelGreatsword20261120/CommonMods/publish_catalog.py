"""Add the fitted forged-steel sword to the existing melee workbench."""
import copy
import json
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
data = here.parents[2] / 'Content/ColdSteelData'
weapon = 'ue_forged_steel_greatsword'
mesh_folder = '/Game/Weapons/ForgedSteelGreatsword20261120/CommonMods/Meshes'
common = {
    'blade_1': ('extended_edge', 'heavy_spine', 'feather_edge'),
    'blade_material': ('folded_steel', 'dark_iron', 'mithril', 'damascus_steel', 'meteoric_iron'),
    'blade_2': ('strength_rune', 'haste_rune', 'resonance_rune', 'erosion_rune', 'conduction_rune'),
    'guard': ('bastion_guard', 'riposte_guard', 'light_guard'),
    'grip': ('shock_wrap', 'swift_grip', 'long_twohand', 'iron_spine_power_grip', 'lockweave_guard_grip'),
    'pommel': ('pommel_hardened', 'pommel_runic', 'ballast_hardened', 'ballast_magic_orb'),
}
grip_labels = {
    'shock_wrap':'交错的吸震皮带包覆握区。',
    'swift_grip':'握区收细，浅钢脊沿柄身延伸。',
    'long_twohand':'延长皮革握区，剑首随柄尾后移。',
    'iron_spine_power_grip':'钢脊与箍环分隔三段皮革握区。',
    'lockweave_guard_grip':'织带交叠成细密的菱纹。',
}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def update(filename, change):
    path = data / filename
    for _ in range(3):
        old = path.read_bytes()
        obj = json.loads(old.decode('utf-8-sig'))
        change(obj)
        new = json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
        if b'\r\n' in old:
            new = new.replace('\n','\r\n')
        result = new.encode('utf-8-sig' if old.startswith(b'\xef\xbb\xbf') else 'utf-8')
        if old == result:
            return
        temp = path.with_suffix('.forged-steel.tmp')
        temp.write_bytes(result)
        if path.read_bytes() == old:
            temp.replace(path)
            return
    raise RuntimeError('Concurrent edits to '+filename)

def mesh(name):
    return f'{mesh_folder}/{name}.{name}'

def add_weapon(entry):
    allowed = entry.get('weapons')
    if allowed and weapon not in allowed:
        allowed.append(weapon)

def register_hollow_blade(gunsmith):
    entry = {
        'id': 'hollow_blade', 'name': '镂空剑身', 'tier': 'legendary', 'weapons': [weapon],
        'description': '锻钢双手剑专属。原厂修长刃形的剑脊中央有一道贯穿孔，两侧保留银灰色的锻钢刃面。',
        'stats': {'attack_speed_mult': 1.20, 'stamina_mult': 0.85,
                  'physical_attack_mult': 1.05, 'melee_hit_bleed_stacks': 2},
        'effects': [{'text': text, 'benefit': 1} for text in
                    ('攻击速度+20%', '体力消耗−15%', '物理攻击+5%')],
        'special_effects': ['双痕｜剑刃每次有效命中附加2层流血。同一段攻击对每个目标触发一次。'],
    }
    register_blade_entry(gunsmith, entry)

def register_executioner_blade(gunsmith):
    register_blade_entry(gunsmith, {
        'id': 'executioner_blade', 'name': '处刑剑身', 'tier': 'legendary', 'weapons': [weapon],
        'description': '宽大的锻钢刃根贴合护手，深色长槽在前段收拢，两侧刃面汇成尖锋。',
        'stats': {'attack_speed_mult': .50, 'stamina_mult': 1.30,
                  'physical_attack_mult': 2., 'toughness_damage_mult': 1.50},
        'effects': [{'text': text, 'benefit': benefit} for text, benefit in
                    [('攻击速度−50%', -1), ('体力消耗+30%', -1),
                     ('物理攻击+100%', 1), ('韧性伤害+50%', 1)]],
        'special_effects': ['钝击｜剑身命中以钝伤结算韧性伤害。',
                            '震慑｜每段剑身攻击命中时，有50%概率使目标眩晕1秒。目标已破韧或被本击打破韧性时，触发概率为100%。'],
    })

def register_blade_entry(gunsmith, entry):
    register_option(gunsmith, 'blade_1', entry)

def register_option(gunsmith, slot, entry):
    options = next(col['options'] for col in gunsmith['columns'] if col['key'] == slot)
    for index, option in enumerate(options):
        if option['id'] == entry['id']:
            options[index] = entry
            return
    options.append(entry)

def register_ring_chain(gunsmith):
    register_option(gunsmith, 'pommel', {
        'id':'ring_chain_pommel', 'name':'环链配重', 'tier':'special', 'weapons':[weapon],
        'description':'深钢环首嵌在柄尾套筒下，七节铁链交错套接，随挥剑与收势回荡。',
        'stats':{'attack_speed_mult':1.10, 'stamina_mult':.90},
        'effects':[{'text':'攻击速度+10%', 'benefit':1}, {'text':'攻击体力消耗−10%', 'benefit':1}],
        'special_effects':['重击替换为横扫。点按左键普通攻击，长按蓄满后松开左键发动横扫。',
                           '普通重击｜沿剑刃挥过的轨迹命中身前目标，基础最远3.6米。',
                           '环链横扫｜从右向左扫过身前180°扇形，基础半径3.6米。两种重击的距离均受攻击范围加成影响。',
                           '回摆｜3秒内用两段普通攻击命中敌人，获得一次回摆。每段普通攻击命中多个目标只计一次。',
                           '蓄势横扫｜回摆就绪后的3秒内开始重击蓄力，蓄力时间缩短50%，本次重击体力消耗增加15%。开始蓄力时消耗回摆。'],
    })

def fit_ring_chain(catalog):
    pommels = catalog['slots']['pommel']
    part = copy.deepcopy(pommels['factory'])
    folder = '/Game/Weapons/ForgedSteelGreatsword20261120/RingChainPommel/'
    name = 'SM_ForgedSteelGreatsword_RingChainPommel'
    part.update(mesh=folder+name+'.'+name, appearance='锻钢椭圆环首下的七节铁链交错垂落。')
    part['material_slot_names']=['M_RingChain_Socket','M_RingChain_Links']
    part['materials']={name:folder+name+'.'+name for name in part['material_slot_names']}
    part.update(read(here.parent/'RingChainPommel/dynamics.json'))
    pommels['ring_chain_pommel']=part

def register_fishtail_pommel(gunsmith):
    register_option(gunsmith, 'pommel', {
        'id': 'fishtail_pommel', 'name': '鱼尾配重', 'tier': 'special', 'weapons': [weapon],
        'description': '扇形锻钢配重从柄尾向两侧展开，中央浅棱与剑脊呼应。',
        'stats': {'physical_attack_mult': 1.08},
        'effects': [{'text': '物理攻击+8%', 'benefit': 1}],
        'special_effects': [
            '乘隙｜普攻或重击的剑身直接命中已破韧的敌人时，本击物理伤害+25%。'
        ],
    })

def fit_fishtail_pommel(catalog):
    pommels = catalog['slots']['pommel']
    part = copy.deepcopy(pommels['factory'])
    name = 'SM_ForgedSteelGreatsword_FishtailPommel'
    part['mesh'] = f'/Game/Weapons/ForgedSteelGreatsword20261120/FishtailPommel/{name}.{name}'
    part['appearance'] = '原厂钢箍下接扁平鱼尾，两侧斜面在尾端连成浅弧。'
    pommels['fishtail_pommel'] = part

def fit_hollow_blade(catalog):
    blades = catalog['slots']['blade_1']
    part = copy.deepcopy(blades['factory'])
    name = 'SM_ForgedSteelGreatsword_HollowBlade'
    part['mesh'] = f'/Game/Weapons/ForgedSteelGreatsword20261120/HollowBlade/{name}.{name}'
    part['appearance'] = '沿原厂锻钢剑脊开出一道圆端细长透孔，剑肩和剑尖保留完整钢面。'
    blades['hollow_blade'] = part

def fit_executioner_blade(catalog):
    blades = catalog['slots']['blade_1']
    part = copy.deepcopy(blades['factory'])
    name = 'SM_ForgedSteelGreatsword_ExecutionerBlade'
    part['mesh'] = f'/Game/Weapons/ForgedSteelGreatsword20261120/ExecutionerBlade/{name}.{name}'
    part['appearance'] = '宽刃根贴合护手，两侧自下而上渐窄，中央长槽在尖锋下方收圆。'
    part['visual_tip_cm'] = read(here.parent / 'ExecutionerBlade/exports.json')['visual_tip_cm']
    base = part['trace_base_cm'][2]
    visible_length = part['visual_tip_cm'][2] - base
    part['rune_dimensions_cm'] = [7.35, round(base + .13*visible_length, 3), round(.71*visible_length, 3)]
    blades['executioner_blade'] = part
    fit_executioner_guard_seats(catalog)

def fit_executioner_guard_seats(catalog):
    seats = read(here.parent / 'ExecutionerBlade/GuardSeats/exports.json')
    blade_surface = read(here / 'blade_materials.json')['base']
    for guard, path in seats['mesh_by_guard'].items():
        part = catalog['slots']['guard'][guard]
        part.setdefault('mesh_by_blade', {})['executioner_blade'] = path
        part['material_slot_names'] = [seats['material_slot']]
        part.setdefault('materials', {})[seats['material_slot']] = blade_surface

def register_raven_quill_guard(gunsmith, update_effects=False):
    options = next(col['options'] for col in gunsmith['columns'] if col['key'] == 'guard')
    row = next((o for o in options if o['id'] == 'raven_quill_guard'), None)
    if row is not None and not update_effects:
        return
    if row is None:
        row = {'id':'raven_quill_guard','name':'暮鸦折羽','tier':'special','weapons':[weapon],
               'description':'三层蓝黑钢羽从中央羽脊向两侧舒展，锤纹之间露出细窄的银边。'}
        options.append(row)
    row.setdefault('stats', {}).update(melee_critical_chance_add=10, sprint_stamina_mult=0.9)
    row['effects'] = [{'text':'暴击率+10%', 'benefit':1}, {'text':'奔跑体力消耗-10%', 'benefit':1}]
    row['special_effects'] = ['折羽蓄能｜累计奔跑3秒蓄满，停跑保留未满进度。青光从握把一侧向上蔓延，蓄满时整副护手发光。',
                              '蓄满一击｜蓄满后5秒内，下一次命中目标的攻击额外获得暴击率+25%。挥空保留强化，超时消散。']

def raven_charge_surfaces():
    return read(here.parent/'RavenQuillGuard/Art/SprintCharge/import_receipt.json')

def fit_raven_quill_guard(catalog):
    guards = catalog['slots']['guard']
    part = copy.deepcopy(guards.get('raven_quill_guard', guards['factory']))
    saved = read(here.parent/'RavenQuillGuard/Art/NestedV4/import_receipt.json')
    paths = {path.rsplit('.', 1)[1]: path for path in saved['assets']}
    mesh_name = 'SM_ForgedSteelGreatsword_RavenQuillGuard'
    part['mesh'] = paths[mesh_name]
    part.setdefault('mesh_by_blade', {})['executioner_blade'] = paths[mesh_name + '_ExecutionerSeat']
    part['materials'] = raven_charge_surfaces()['materials']
    part['material_slot_names'] = list(saved['meshes'][mesh_name])
    guards['raven_quill_guard'] = part

def register_raven_temporal(mapping):
    mapping.update(raven_charge_surfaces()['temporal'])

def eagle_assets():
    return read(here.parent/'EagleTalonGuard/Art/gameplay_assets.json')

def register_eagle_guard(gunsmith):
    register_option(gunsmith, 'guard', {
        'id':'eagle_talon_guard', 'name':'鹰爪之握', 'tier':'special', 'weapons':[weapon],
        'description':'鹰喙下方的钢羽向两侧叠开，末端内收成一对弯爪。',
        'stats':{'physical_defense_mult':1.10, 'block_stamina_mult':.75},
        'effects':[{'text':'防御力+10%', 'benefit':1},{'text':'格挡体力消耗-25%', 'benefit':1}],
        'special_effects':['鹰爪蓄能｜成功格挡敌方攻击积1次，弹反积2次。累计6次时，护手亮起冰蓝光。',
                           '满充反击｜下一次普通攻击或战技暴击率+30%，体力消耗为0。成功出招即消耗充能，同一招的所有段数均受益。']
    })

def fit_eagle_guard(catalog):
    saved=read(here.parent/'EagleTalonGuard/Art/import_receipt.json')
    names={path.rsplit('.',1)[1]:path for path in saved['assets']}
    name='SM_ForgedSteelGreatsword_EagleTalonGuard'
    guard=catalog['slots']['guard']
    materials=dict(saved['meshes'][name])
    materials['M_EagleTalon_ForgedSteel']=eagle_assets()['materials'][0]
    guard['eagle_talon_guard']={
        'mesh':names[name], 'location_cm':guard['factory']['location_cm'], 'interface':guard['factory']['interface'],
        'mesh_by_blade':{'executioner_blade':names[name+'_ExecutionerSeat']},
        'material_slot_names':list(materials), 'materials':materials
    }

def register_eagle_temporal(mapping):
    ordinary,whirlwind=eagle_assets()['materials']
    mapping[ordinary]=whirlwind

def require_saved(receipt):
    content = data.parent
    for path in receipt['assets']:
        filename = path.split('.')[0].removeprefix('/Game/') + '.uasset'
        if not (content/filename).is_file():
            raise RuntimeError('Missing saved package: '+path)

def fit_forged_grip_surfaces(catalog):
    saved = read(here.parent/'GripFinish/Art/ReferenceLeather/import_receipt.json')
    require_saved(saved)
    for option, binding in saved['grips'].items():
        catalog['slots']['grip'][option].update(binding)

def fit_refined_appearance(catalog):
    fit_raven_quill_guard(catalog)
    fit_forged_grip_surfaces(catalog)

def publish_raven_quill(update_effects=False):
    require_saved(raven_charge_surfaces())
    require_saved(read(here.parent/'RavenQuillGuard/Art/NestedV4/import_receipt.json'))
    update('forged-steel-greatsword-modules.json', fit_raven_quill_guard)
    update('whirlwind-temporal-materials.json', register_raven_temporal)
    update('melee-gunsmith.json', lambda data: register_raven_quill_guard(data, update_effects))

def register(gunsmith):
    for column in gunsmith['columns']:
        key = column['key']
        if key not in common:
            continue
        add_weapon(column)
        options = {o['id']: o for o in column['options']}
        for option in common[key]:
            add_weapon(options[option])
    entry = next((row for row in gunsmith['weapons'] if isinstance(row,dict) and row.get('id') == weapon), None)
    if entry is None:
        entry = {'id': weapon, 'traits': []}
        gunsmith['weapons'].append(entry)
    entry.setdefault('factory_icon_sources', {})['blade_material'] = weapon + '_blade_material_false'
    register_hollow_blade(gunsmith)
    register_executioner_blade(gunsmith)
    register_ring_chain(gunsmith)
    register_fishtail_pommel(gunsmith)
    register_raven_quill_guard(gunsmith)
    register_eagle_guard(gunsmith)

def fit(catalog):
    variants = read(here / 'variant_exports.json')
    grips = read(here / 'grip_exports.json')
    slots = catalog['slots']
    for row in variants['options']:
        choices = slots[row['slot']]
        part = copy.deepcopy(choices['factory'])
        part.update(mesh=mesh(row['mesh']), appearance=row['appearance'])
        if row['visual_tip_cm']:
            part['visual_tip_cm'] = row['visual_tip_cm']
        choices[row['option']] = part

    surface = read(here / 'blade_materials.json')
    widths = {'factory':1.,'extended_edge':1.,'heavy_spine':1.18,'feather_edge':.8}
    for key, width in widths.items():
        part = slots['blade_1'][key]
        part['material_slot_names'] = surface['slots'][key]
        for name in part['material_slot_names']:
            part.setdefault('materials',{})[name] = surface['base']
        base = part['trace_base_cm'][2]
        tip = part.get('visual_tip_cm',part['trace_tip_cm'])[2]
        # Keep the shared glyphs on the broad portion of the actual blade.
        part['rune_dimensions_cm'] = [round(4.67 * .86 * width,3),
                                      round(base + .13*(tip-base),3),
                                      round(.71*(tip-base),3)]
    fit_hollow_blade(catalog)
    fit_executioner_blade(catalog)
    fit_eagle_guard(catalog)
    fit_raven_quill_guard(catalog)
    fit_ring_chain(catalog)
    fit_fishtail_pommel(catalog)
    for row in grips['options']:
        part = copy.deepcopy(slots['grip']['factory'])
        part.update(mesh=mesh(row['mesh']), appearance=grip_labels[row['option']],
                    pommel_offset_cm=row['pommel_offset_cm'])
        if row['animation_folder']:
            part['animation_folder'] = row['animation_folder']
            # Same fitted mounting rings and 2.8 cm extension as the shared long grip.
            part['hand_fit'] = {'left_offset_cm':[0,0,-1.6]}
        slots['grip'][row['option']] = part
    fit_forged_grip_surfaces(catalog)
    interfaces = {}
    for row in variants['adapters']:
        loc = row['mount_cm'].copy()
        loc[2] -= row['depth_cm']
        interfaces[row['interface']] = {'location_cm':loc,'scale':[row['scale']]*3,
            'adapter':{'mesh':mesh(row['mesh']),'location_cm':row['mount_cm'],
                       'interface':catalog['interface']+'_to_'+row['interface']}}
    catalog['pommel_profile'] = {'library':'shared-sword-pommels.json','finish':'silver','interfaces':interfaces}

def publish():
    if not read(here/'import_receipt.json')['complete']:
        raise RuntimeError('The fitted components have not been saved')
    surface = read(here/'blade_materials.json')
    update('forged-steel-greatsword-modules.json', fit)
    update('whirlwind-temporal-materials.json',lambda mapping: mapping.update({surface['base']:surface['whirlwind']}))
    update('whirlwind-temporal-materials.json', register_raven_temporal)
    update('melee-gunsmith.json', register)
    update('whirlwind-temporal-materials.json', register_eagle_temporal)
    print('Registered',weapon, 'with',sum(map(len,common.values())),'common modifications.')

if __name__ == '__main__':
    if '--eagle-talon-guard' in sys.argv:
        assets=eagle_assets()
        require_saved({'assets':assets['materials']+assets['icons']})
        require_saved(read(here.parent/'EagleTalonGuard/Art/import_receipt.json'))
        update('forged-steel-greatsword-modules.json', fit_eagle_guard)
        update('whirlwind-temporal-materials.json', register_eagle_temporal)
        update('melee-gunsmith.json', register_eagle_guard)
    elif '--raven-sprint-charge' in sys.argv:
        publish_raven_quill(update_effects=True)
    elif '--raven-quill-guard' in sys.argv:
        publish_raven_quill()
    elif '--refined-appearance' in sys.argv:
        require_saved(read(here.parent/'RavenQuillGuard/Art/NestedV4/import_receipt.json'))
        update('whirlwind-temporal-materials.json', register_raven_temporal)
        update('forged-steel-greatsword-modules.json', fit_refined_appearance)
    else:
        publish()
