from pathlib import Path
import json
import shutil

ROOT = Path(r'D:\FPS3D\FPSGAME')
HERE = Path(__file__).resolve().parent
changed = []

def edit(path, transform):
    target = ROOT / path
    raw = target.read_bytes()
    old = raw.decode('utf-8-sig').replace('\r\n', '\n')
    new = transform(old)
    if old == new:
        raise RuntimeError(f'No edit: {path}')
    backup = HERE / 'Before' / path
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(target, backup)
    newline = '\r\n' if b'\r\n' in raw else '\n'
    prefix = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    target.write_bytes(prefix + new.replace('\n', newline).encode('utf-8'))
    changed.append(path)

def replace(old, before, after, count=1):
    if old.count(before) != count:
        raise RuntimeError(f'Expected {count} anchors: {before[:110]}')
    return old.replace(before, after)

def catalog(s):
    start = s.index('  "ue_alchemy_spellbook": {')
    end = s.index('\n  }', start) + len('\n  }')
    book = json.loads('{' + s[start:end] + '}')['ue_alchemy_spellbook']
    book['matkFormula'] = dict(base=2, intMul=.2, wisMul=.2, enhanceBase=.4, enhanceIntMul=.08, enhanceWisMul=.08)
    book['focusEffects'] = dict(castSpeedMultiplier=2, manaCostMultiplier=.75)
    book['spellbookStatsRevision'] = 1
    block = json.dumps({'ue_alchemy_spellbook': book}, ensure_ascii=False, indent=2)[2:-2]
    return s[:start] + block + s[end:]

edit('Content/ColdSteelData/items.json', catalog)
edit('Source/FPSGAME/UI/ColdSteelStatusModel.h', lambda s:
    replace(replace(s, '    double EquipmentMagicAttack() const;', '''    double EquipmentMagicAttack() const;
    double ItemMagicAttack(const FColdSteelItem& Item) const;
    const FColdSteelItem* ActiveSpellbook() const;
    void ApplySpellbookFocus(float& CastSpeed,float& ManaCost) const;'''),
    'FLightningCast LightningStats(int32 AtLevel=-1) const;',
    'FLightningCast LightningStats(int32 AtLevel=-1,bool bApplyFocus=true) const;'))

def formula_data(s):
    s = replace(s, '    static const TSharedPtr<FJsonObject> Catalog=[] {', '''    // Definition-owned balance fields also apply to books created before this update.
    // Instance-owned enhancement level and inventory data remain untouched.
    if(Item.Definition==TEXT("ue_alchemy_spellbook"))
    {
        static const TSharedPtr<FJsonObject> BookDefaults=[] {
            FString Text;TSharedPtr<FJsonObject> Root;
            if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)&&Root)
            {
                const TSharedPtr<FJsonObject>* Book=nullptr;
                if(Root->TryGetObjectField(TEXT("ue_alchemy_spellbook"),Book))return *Book;
            }
            return TSharedPtr<FJsonObject>();}();
        if(BookDefaults)for(const TCHAR* Field:{TEXT("matkFormula"),TEXT("focusEffects"),TEXT("spellbookStatsRevision")})
            if(const auto* Value=BookDefaults->Values.Find(Field))Data->SetField(Field,*Value);
    }
    static const TSharedPtr<FJsonObject> Catalog=[] {''')
    return replace(s, 'const FString Key=FString::FromInt(Item.Definition.Len())+TEXT(":")+Item.Definition+Item.Data;',
        'const FString Key=FString::FromInt(Item.Definition.Len())+TEXT(":")+Item.Definition+Item.Data\n        +(Item.Definition==TEXT("ue_alchemy_spellbook")?TEXT(":spellbook-stats-v1"):TEXT(""));')

edit('Source/FPSGAME/Combat/CombatItemFormula.cpp', formula_data)

def magic_bonus(s):
    s = replace(s, '#include "CombatItemFormula.h"', '#include "CombatItemFormula.h"\n#include "../Weapons/Spellbook/SpellbookComponent.h"')
    a = s.index('double UColdSteelStatusModel::EquipmentMagicAttack()const')
    b = s.index('float UColdSteelStatusModel::CombatMoveMultiplier()const', a)
    return s[:a] + '''double UColdSteelStatusModel::ItemMagicAttack(const FColdSteelItem& Item)const
{
    const FString Type=ColdSteelInventory::Text(Item,TEXT("weaponType"));
    if(Type!=TEXT("staff")&&Type!=TEXT("spellbook"))return 0;
    const auto F=Obj(Read(&Item),TEXT("matkFormula"));if(!F)return 0;
    const double L=ColdSteelInventory::Number(Item,TEXT("enhanceLevel"));
    return CoreCombatFormula::Round(Num(F,TEXT("base"))+L*Num(F,TEXT("enhanceBase"))+Attribute(TEXT("intt"))*(Num(F,TEXT("intMul"))+L*Num(F,TEXT("enhanceIntMul")))+Attribute(TEXT("wis"))*(Num(F,TEXT("wisMul"))+L*Num(F,TEXT("enhanceWisMul"))));
}
const FColdSteelItem* UColdSteelStatusModel::ActiveSpellbook()const
{
    if(ActiveProductionTool())return nullptr;
    const int32 Slot=Current.ActiveWeaponSlot==6?8:11;
    if(ColdSteelInventory::Locked(Current.Items,Slot))return nullptr;
    const auto* Book=Equipped(Slot);
    return Book&&Book->Definition==TEXT("ue_alchemy_spellbook")?Book:nullptr;
}
double UColdSteelStatusModel::EquipmentMagicAttack()const
{
    const auto* Main=Equipped();const auto* Book=ActiveSpellbook();
    return (Main?ItemMagicAttack(*Main):0)+(Book?ItemMagicAttack(*Book):0);
}
void UColdSteelStatusModel::ApplySpellbookFocus(float& CastSpeed,float& ManaCost)const
{
    const auto* Book=ActiveSpellbook();if(!Book)return;
    const auto* Pawn=RuntimePawn();
    const auto* Focus=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    if(!Focus||!Focus->IsFocusEmpowered())return;
    const auto Effects=Obj(Read(Book),TEXT("focusEffects"));
    CastSpeed*=float(Num(Effects,TEXT("castSpeedMultiplier"),1));
    // Apply after the spell's existing cost modifiers, without an extra integer rounding.
    ManaCost*=float(Num(Effects,TEXT("manaCostMultiplier"),1));
}
''' + s[b:]

edit('Source/FPSGAME/Combat/ColdSteelFormulaBonuses.cpp', magic_bonus)
edit('Source/FPSGAME/Weapons/Spellbook/SpellbookComponent.h', lambda s: replace(s,
    '    bool IsFocusActive() const {return FocusAge>=0.f;}',
    '    bool IsFocusActive() const {return FocusAge>=0.f;}\n    bool IsFocusEmpowered() const;'))
edit('Source/FPSGAME/Weapons/Spellbook/SpellbookFocus.cpp', lambda s: replace(s,
    'bool USpellbookComponent::ToggleFocus()', '''bool USpellbookComponent::IsFocusEmpowered() const
{
    // Opening/closing still own the animation, but only the fully open hold grants stats.
    return bFocusPair&&bFocusDesired&&!bFocusClosing&&FocusAge>=SpellbookFocusMotion::OpenLength&&OwnsLeftHand();
}

bool USpellbookComponent::ToggleFocus()'''))

edit('Source/FPSGAME/UI/ColdSteelEnhancementSystem.cpp', lambda s: replace(s,
    'ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff")||ColdSteelInventory::IsBow(I)',
    'ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff")||I.Definition==TEXT("ue_alchemy_spellbook")||ColdSteelInventory::IsBow(I)', 2))

def migration(s):
    s = replace(s, '// Refresh only presentation fields on books already in a save.',
        '// Refresh definition-owned presentation and balance fields; retain instance enhancement.')
    a = s.index('if(I.Definition==TEXT("ue_alchemy_spellbook"))')
    b = s.index('                if(Updated)', a)
    return s[:b] + '''                double Revision=0,OldRevision=0;
                Data->TryGetNumberField(TEXT("spellbookStatsRevision"),OldRevision);
                if(Defaults->TryGetNumberField(TEXT("spellbookStatsRevision"),Revision)&&OldRevision<Revision)
                {
                    for(const TCHAR* Key:{TEXT("matkFormula"),TEXT("focusEffects"),TEXT("spellbookStatsRevision")})
                        if(const auto* Value=Defaults->Values.Find(Key))Data->SetField(Key,*Value);
                    Updated=true;
                }
''' + s[b:]

edit('Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp', migration)

for name in ('Fireball', 'IceSpike', 'IceWall', 'Blizzard', 'HolyLight', 'FireMagic', 'Lightning', 'ElectricMagic'):
    def spell(s, name=name):
        if name == 'Lightning':
            s = replace(s, 'LightningStats(int32 AtLevel) const', 'LightningStats(int32 AtLevel,bool bApplyFocus) const')
        if name == 'ElectricMagic':
            s = replace(s, 'C.Hit=LightningStats();', 'C.Hit=LightningStats(-1,false);')
        invocation = ('if(bApplyFocus)' if name == 'Lightning' else '') + 'ApplySpellbookFocus(' + ('H' if name == 'ElectricMagic' else 'C') + '.CastSpeed,' + ('H' if name == 'ElectricMagic' else 'C') + '.ManaCost);'
        # These files each contain one stats snapshot returning C.
        return replace(s, 'return C;', invocation + '\n    return C;')
    edit(f'Source/FPSGAME/Skills/ColdSteel{name}Model.cpp', spell)

edit('Source/FPSGAME/UI/ColdSteelItemTooltipData.h', lambda s: s + '\nvoid AppendColdSteelTooltipMagicFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipCard& Card);\n')
edit('Source/FPSGAME/UI/ColdSteelItemTooltipFormula.cpp', lambda s:
    replace(s, '#include "ColdSteelItemReadCache.h"', '#include "ColdSteelItemReadCache.h"\n#include "../Combat/CombatItemFormula.h"') + '''
void AppendColdSteelTooltipMagicFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipCard& Card)
{
    const auto Data=CombatItemFormula::ReadOnly(Item);const TSharedPtr<FJsonObject>* Formula=nullptr;
    if(!Data||!Data->TryGetObjectField(TEXT("matkFormula"),Formula))return;
    const auto Number=[&](const TCHAR* Key){return FormulaNumber(FormulaValue(*Formula,Key));};
    if(Model)Card.Rows.Add({TEXT("装备魔攻"),FormulaNumber(Model->ItemMagicAttack(Item))});
    FormulaRow(Card,TEXT("基础魔攻公式"),Number(TEXT("base"))+TEXT(" + 智力×")+Number(TEXT("intMul"))+TEXT(" + 精神×")+Number(TEXT("wisMul")));
    FormulaRow(Card,TEXT("强化后魔攻公式 · L=强化等级"),Number(TEXT("base"))+TEXT(" + ")+Number(TEXT("enhanceBase"))+TEXT("L")
        +TEXT(" + 智力×(")+Number(TEXT("intMul"))+TEXT("+")+Number(TEXT("enhanceIntMul"))+TEXT("L)")
        +TEXT(" + 精神×(")+Number(TEXT("wisMul"))+TEXT("+")+Number(TEXT("enhanceWisMul"))+TEXT("L)"));
    FormulaRow(Card,TEXT("数值口径"),TEXT("按当前角色智力、精神计算，结果四舍五入"));
}
''')

def tooltip(s):
    a = s.index('        // 装备魔攻 = 实值行')
    b = s.index('        Note(Main,TEXT("握持"),TEXT("单手主手', a)
    s = s[:a] + '        AppendColdSteelTooltipMagicFormula(I,Model,Main);\n' + s[b:]
    return replace(s, '}else if(ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff")){', '''}else if(I.Definition==TEXT("ue_alchemy_spellbook")){
        Section(Main,ColdSteelWeaponText::CombatParameters);AppendColdSteelTooltipMagicFormula(I,Model,Main);
        if(const auto Focus=Object(O,TEXT("focusEffects")))
        {
            Row(Main,TEXT("专注施法速度"),Signed((Number(Focus,TEXT("castSpeedMultiplier"),1)-1)*100,TEXT("%")));
            Row(Main,TEXT("专注魔法消耗"),Signed((Number(Focus,TEXT("manaCostMultiplier"),1)-1)*100,TEXT("%")));
        }
        Note(Main,TEXT("被动"),TEXT("装备在当前副手时提高魔法攻击；强化提高基础值与智力、精神系数"));
        Note(Main,TEXT("专注"),TEXT("搭配法杖，右键展开书本后生效；开始合书或切换装备时结束"));
    }else if(ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff")){''')

edit('Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp', tooltip)
edit('Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp', lambda s:
    replace(replace(s, 'Model->EquipmentMagicAttack()', 'Model->ItemMagicAttack(Item)'),
    '    else if(ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("staff"))', '''    else if(Item.Definition==TEXT("ue_alchemy_spellbook"))
    {
        if(Model)Add(TEXT("equipment_magic_attack"),TEXT("装备魔攻"),Model->ItemMagicAttack(Item),TEXT(""),2);
    }
    else if(ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("staff"))'''))

def enhancement_ui(s):
    anchor = '''        else
        {
            auto Comparison=*I;
            if(bCompareBase)'''
    return replace(s, anchor, '''        else if(I->Definition==TEXT("ue_alchemy_spellbook")||ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("staff"))
        {
            auto Comparison=*I;
            if(bCompareBase){TSharedPtr<FJsonObject> Data;if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Comparison.Data),Data)){Data->SetNumberField(TEXT("enhanceLevel"),0);Data->RemoveField(TEXT("_enchantEffects"));FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Comparison.Data));}}
            Row(TEXT("装备魔攻"),P->ItemMagicAttack(Comparison),P->ItemMagicAttack(After),0);
            Row(TEXT("强化等级"),bCompareBase?0:Number(*I,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
        }
        else
        {
            auto Comparison=*I;
            if(bCompareBase)''')

edit('Source/FPSGAME/UI/ColdSteelEnhancementWidget.cpp', enhancement_ui)
(HERE / 'changed-files.json').write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Updated {len(changed)} scoped files; original copies retained in {HERE / "Before"}')
