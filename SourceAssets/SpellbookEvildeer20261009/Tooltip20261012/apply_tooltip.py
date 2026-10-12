from pathlib import Path
import json
import shutil

ROOT = Path(r'D:\FPS3D\FPSGAME')
HERE = Path(__file__).resolve().parent
changed = []

def replace(s, before, after, count=1):
    if s.count(before) != count:
        raise RuntimeError(f'Expected {count} anchors: {before[:90]}')
    return s.replace(before, after)

def edit(relative, transform):
    path = ROOT / relative
    raw = path.read_bytes()
    old = raw.decode('utf-8-sig').replace('\r\n', '\n')
    new = transform(old)
    if new == old:
        raise RuntimeError(f'No change: {relative}')
    backup = HERE / 'Before' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    newline = '\r\n' if b'\r\n' in raw else '\n'
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    path.write_bytes(bom + new.replace('\n', newline).encode('utf-8'))
    changed.append(relative)

edit('Source/FPSGAME/UI/ColdSteelWeaponText.h', lambda s: replace(s,
    'inline constexpr const TCHAR* MagicCostMultiplier=TEXT("魔法值消耗倍率");',
    '''inline constexpr const TCHAR* MagicCostMultiplier=TEXT("魔法值消耗倍率");
inline constexpr const TCHAR* EquipmentMagicAttack=TEXT("装备魔攻");
inline constexpr const TCHAR* MagicAttackFormula=TEXT("魔攻计算公式");
inline constexpr const TCHAR* EnhancedMagicAttackFormula=TEXT("强化后魔攻公式 · L=强化等级");
inline constexpr const TCHAR* CastSpeed=TEXT("施法速度");
inline constexpr const TCHAR* ManaCost=TEXT("魔法消耗");
inline constexpr const TCHAR* Focus=TEXT("专注");
inline constexpr const TCHAR* EnhancementLimit=TEXT("强化上限");'''))

edit('Source/FPSGAME/UI/ColdSteelItemTooltipData.h', lambda s: replace(s,
    '    bool bDashedAfter=false;', '''    bool bDashedAfter=false;
    // Show this mechanism after the core grid in both hover and pinned views.
    // Its source stays in the main card for other item-detail consumers.
    bool bPreview=false;'''))

def signature(s):
    s = replace(s, 'TEXT("|%d:%d:%d:%d:%s"),R.bSection,R.bContinuation,R.bStacked,R.bDashedAfter,*R.Label',
        'TEXT("|%d:%d:%d:%d:%d:%s"),R.bSection,R.bContinuation,R.bStacked,R.bDashedAfter,R.bPreview,*R.Label')
    return replace(s, '    Rows(Presentation.Summary);', '''    Rows(Presentation.Summary);
    if(!Presentation.Cards.IsEmpty())
    {
        const auto& Main=Presentation.Cards.Last();
        for(int32 Index=0;Index<Main.Rows.Num();++Index)
        {
            const auto& R=Main.Rows[Index];if(!R.bPreview)continue;
            Result+=FString::Printf(TEXT("|preview:%d:%d:%d:%d:%d:%d:%s"),Presentation.Cards.Num()-1,Index,R.bSection,R.bContinuation,R.bStacked,R.bDashedAfter,*R.Label);
        }
    }''')
edit('Source/FPSGAME/UI/ColdSteelItemTooltip.cpp', signature)

def layout(s):
    s = replace(s, 'const auto& Row=Main.Rows[Index];if(Row.bSection){PendingHeading=Row.Label;continue;}',
        '''const auto& Row=Main.Rows[Index];
                // Preview mechanisms are already visible above the details, once per view.
                if(Row.bPreview){if(Row.bSection)PendingHeading.Empty();continue;}
                if(Row.bSection){PendingHeading=Row.Label;continue;}''')
    return replace(s, '    if(bPinned)AddDetails(Body);', '''    if(!Presentation.Cards.IsEmpty())
    {
        const int32 CardIndex=Presentation.Cards.Num()-1;const auto& Main=Presentation.Cards[CardIndex];
        for(int32 Index=0;Index<Main.Rows.Num();++Index)
            if(Main.Rows[Index].bPreview)AddRow(Body,Main.Rows[Index],CardIndex,Index);
    }
    if(bPinned)AddDetails(Body);''')
edit('Source/FPSGAME/UI/ColdSteelItemTooltipLayout.cpp', layout)

def summary(s):
    s = replace(s, 'TEXT("equipment_magic_attack"),TEXT("装备魔攻")',
        'TEXT("equipment_magic_attack"),ColdSteelWeaponText::EquipmentMagicAttack', 2)
    return replace(s, '    if(ColdSteelInventory::IsBow(Item))Out.ValueScope=ColdSteelWeaponText::BowScope;',
        '''    if(Item.Definition==TEXT("ue_alchemy_spellbook"))Out.ValueScope=TEXT("装备魔攻按当前智力、精神与强化等级计算；装备于当前副手时生效。");
    else if(ColdSteelInventory::IsBow(Item))Out.ValueScope=ColdSteelWeaponText::BowScope;''')
edit('Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp', summary)

def formula(s):
    s = replace(s, '#include "ColdSteelItemTooltipData.h"', '#include "ColdSteelItemTooltipData.h"\n#include "ColdSteelWeaponText.h"')
    a = s.index('    const auto Number=[&](const TCHAR* Key)', s.index('void AppendColdSteelTooltipMagicFormula('))
    return s[:a] + '''    const auto Value=[&](const TCHAR* Key){return FormulaValue(*Formula,Key);};
    if(Model)Card.Rows.Add({ColdSteelWeaponText::EquipmentMagicAttack,FormulaNumber(Model->ItemMagicAttack(Item))});
    FString Base=FormulaNumber(Value(TEXT("base"))),Enhanced=Base;
    const double Flat=Value(TEXT("enhanceBase"));
    if(Flat!=0)Enhanced+=TEXT("+")+FormulaNumber(Flat)+TEXT("L");
    TArray<FFormulaGroup> Groups;
    for(const bool Wisdom:{false,true})
    {
        const double Coefficient=Value(Wisdom?TEXT("wisMul"):TEXT("intMul"));
        const double PerLevel=Value(Wisdom?TEXT("enhanceWisMul"):TEXT("enhanceIntMul"));
        if(Coefficient==0&&PerLevel==0)continue;
        auto* Group=Groups.FindByPredicate([&](const auto& Entry){return Entry.Base==Coefficient&&Entry.PerLevel==PerLevel;});
        if(!Group){Group=&Groups.AddDefaulted_GetRef();Group->Base=Coefficient;Group->PerLevel=PerLevel;}
        Group->Names.Add(Wisdom?TEXT("精神"):TEXT("智力"));
    }
    for(const auto& Group:Groups)
    {
        FString Names=FString::Join(Group.Names,TEXT("+"));
        if(Group.Names.Num()>1)Names=TEXT("(")+Names+TEXT(")");
        if(Group.Base!=0)Base+=TEXT("+")+FormulaNumber(Group.Base)+TEXT("×")+Names;
        const FString Factor=Group.PerLevel==0?FormulaNumber(Group.Base):TEXT("(")+FormulaNumber(Group.Base)+TEXT("+")+FormulaNumber(Group.PerLevel)+TEXT("L)");
        Enhanced+=TEXT("+")+Factor+TEXT("×")+Names;
    }
    FormulaRow(Card,ColdSteelWeaponText::MagicAttackFormula,Base);
    FormulaRow(Card,ColdSteelWeaponText::EnhancedMagicAttackFormula,Enhanced);
}
'''
edit('Source/FPSGAME/UI/ColdSteelItemTooltipFormula.cpp', formula)

def data(s):
    s = replace(s, '{TEXT("weapon_magic"),TEXT("魔法武器")}', '{TEXT("weapon_magic"),TEXT("魔法武器")},{TEXT("magic_book"),TEXT("魔法书")}')
    s = replace(s, '{TEXT("weapon"),TEXT("武器槽")}', '{TEXT("weapon"),TEXT("武器槽")},{TEXT("offhand"),TEXT("副手槽")}')
    s = replace(s, 'Row(Main,TEXT("武器类型"),String(O,TEXT("weaponTypeTag"),String(O,TEXT("weaponType"))));Row(Main,TEXT("装备槽位"),EquipSlotLabel(String(O,TEXT("equipSlot"))));',
        '''const FString WeaponType=String(O,TEXT("weaponTypeTag"),String(O,TEXT("weaponType")));
    Row(Main,TEXT("武器类型"),WeaponType==TEXT("spellbook")?TEXT("魔法书"):WeaponType);Row(Main,TEXT("装备槽位"),EquipSlotLabel(String(O,TEXT("equipSlot"))));''')
    a = s.index('        Section(Main,ColdSteelWeaponText::CombatParameters);AppendColdSteelTooltipMagicFormula(I,Model,Main);', s.index('}else if(I.Definition==TEXT("ue_alchemy_spellbook"))'))
    b = s.index('    }else if(ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff"))', a)
    return s[:a] + '''        Section(Main,TEXT("魔攻与强化"));AppendColdSteelTooltipMagicFormula(I,Model,Main);
        if(const auto* Enhancement=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr)
            Row(Main,ColdSteelWeaponText::EnhancementLimit,TEXT("+")+FString::FromInt(Enhancement->MaxLevel(I)));
        if(const auto Focus=Object(O,TEXT("focusEffects")))
        {
            const int32 PreviewStart=Main.Rows.Num();
            Section(Main,ColdSteelWeaponText::Focus);
            Note(Main,TEXT(""),TEXT("搭配法杖，右键完全展开书本后生效。"));
            const double Speed=(Number(Focus,TEXT("castSpeedMultiplier"),1)-1)*100;
            const double Cost=(Number(Focus,TEXT("manaCostMultiplier"),1)-1)*100;
            Delta(Main,ColdSteelWeaponText::CastSpeed,Speed,TEXT("%"));
            Delta(Main,ColdSteelWeaponText::ManaCost,Cost,TEXT("%"),true);
            Note(Main,TEXT(""),TEXT("开始合书、切换装备或专注中断时结束。"));
            for(int32 Index=PreviewStart;Index<Main.Rows.Num();++Index)Main.Rows[Index].bPreview=true;
        }
''' + s[b:]
edit('Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp', data)

edit('Source/FPSGAME/UI/ColdSteelEnhancementWidget.cpp', lambda s: replace(s,
    'Row(TEXT("装备魔攻"),P->ItemMagicAttack(Comparison),P->ItemMagicAttack(After),0);',
    'Row(ColdSteelWeaponText::EquipmentMagicAttack,P->ItemMagicAttack(Comparison),P->ItemMagicAttack(After),0);'))

(HERE / 'changed-files.json').write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Saved {len(changed)} scoped UI files; previous files retained in {HERE / "Before"}')
