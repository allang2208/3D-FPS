#include "ColdSteelItemTooltipData.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemReadCache.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"

namespace
{
FString FormulaNumber(double Value)
{
    FString Result=FString::Printf(TEXT("%.6f"),Value);
    while(Result.EndsWith(TEXT("0")))Result.LeftChopInline(1);
    if(Result.EndsWith(TEXT(".")))Result.LeftChopInline(1);
    return Result==TEXT("-0")?TEXT("0"):Result;
}
double FormulaValue(const TSharedPtr<const FJsonObject>& Object,const TCHAR* Key)
{double Value=0;if(Object)Object->TryGetNumberField(Key,Value);return Value;}
FString FormulaAttributeName(FName Key)
{
    static const TMap<FName,FString> Names={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("intt"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")}};
    const auto* Name=Names.Find(Key);return Name?*Name:Key.ToString();
}
void FormulaRow(FColdSteelTooltipCard& Card,const FString& Label,const FString& Value)
{
    auto& Row=Card.Rows.AddDefaulted_GetRef();Row.Label=Label;Row.Value=Value;Row.bStacked=true;
}
struct FFormulaGroup
{
    double Base=0,PerLevel=0;
    TArray<FString> Names;
};
}

void AppendColdSteelTooltipAttackFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double WeaponBase,FColdSteelTooltipCard& Card)
{
    const bool bProductionAxe=ColdSteelInventory::IsEquippedProductionTool(Item);
    const auto* Enhancement=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    if(!Enhancement){FormulaRow(Card,TEXT("攻击力计算公式"),TEXT("—"));return;}
    double ForgeMultiplier=1;
    if(const auto Data=ColdSteelItemData::Read(Item.Data))
    {
        const TSharedPtr<FJsonObject>* Forge=nullptr;
        if(Data->TryGetObjectField(TEXT("_forgeQuality"),Forge)&&*Forge)
            (*Forge)->TryGetNumberField(TEXT("multiplier"),ForgeMultiplier);
    }
    ForgeMultiplier=FMath::Clamp(ForgeMultiplier,.75,1.25);
    // Match ProcessedDamage: forging scales the base formula, not every added damage term.
    auto WithForging=[&](const FString& Expression)
    {return FMath::IsNearlyEqual(ForgeMultiplier,1.)?Expression:TEXT("(")+Expression+TEXT(")×")+FormulaNumber(ForgeMultiplier);};
    if(const auto Formula=Enhancement->AttackFormula(Item))
    {
        const double Base=FormulaValue(Formula,TEXT("base")),Flat=FormulaValue(Formula,TEXT("enhanceFlat"));
        FString BaseExpression=FormulaNumber(Base),EnhancedExpression=BaseExpression;
        TArray<FFormulaGroup> Groups;
        if(Flat!=0)EnhancedExpression+=TEXT("+")+FormulaNumber(Flat)+TEXT("L");
        for(const auto& Value:Formula->GetArrayField(TEXT("attrs")))
        {
            const auto Term=Value->AsObject();const FName Key(*Term->GetStringField(TEXT("key")));
            const double Coefficient=FormulaValue(Term,TEXT("base")),PerLevel=FormulaValue(Term,TEXT("perEnhance"));
            if(Coefficient==0&&PerLevel==0)continue;
            auto* Group=Groups.FindByPredicate([&](const auto& Entry){return Entry.Base==Coefficient&&Entry.PerLevel==PerLevel;});
            if(!Group){Group=&Groups.AddDefaulted_GetRef();Group->Base=Coefficient;Group->PerLevel=PerLevel;}
            Group->Names.Add(FormulaAttributeName(Key));
        }
        for(const auto& Group:Groups)
        {
            FString Names=FString::Join(Group.Names,TEXT("+"));
            if(Group.Names.Num()>1)Names=TEXT("(")+Names+TEXT(")");
            if(Group.Base!=0)BaseExpression+=TEXT("+")+FormulaNumber(Group.Base)+TEXT("×")+Names;
            const FString Factor=Group.PerLevel==0?FormulaNumber(Group.Base):TEXT("(")+FormulaNumber(Group.Base)+TEXT("+")+FormulaNumber(Group.PerLevel)+TEXT("L)");
            EnhancedExpression+=TEXT("+")+Factor+TEXT("×")+Names;
        }
        const auto* Gunsmith=Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        // 近战读剑类倍率，采集工具读工具倍率；两者都作用在基础公式结果上、四舍五入之前。
        const bool bTool=Gunsmith&&Gunsmith->IsTool(Item.Definition);
        if(Gunsmith&&(bTool||Gunsmith->IsMelee(Item.Definition)))
        {
            const auto Stats=Gunsmith->CalculateItem(Item,Gunsmith->Installed(Item));
            const double Multiplier=bTool?Stats.Tool.Damage:Stats.Melee.Damage;
            if(!FMath::IsNearlyEqual(Multiplier,1.))
            {
                BaseExpression=TEXT("(")+BaseExpression+TEXT(")×")+FormulaNumber(Multiplier);
                EnhancedExpression=TEXT("(")+EnhancedExpression+TEXT(")×")+FormulaNumber(Multiplier);
            }
        }
        FormulaRow(Card,TEXT("攻击力计算公式"),WithForging(BaseExpression));
        if(!bProductionAxe)FormulaRow(Card,TEXT("强化后攻击力公式 · L=强化等级"),WithForging(EnhancedExpression));
    }
    else
    {
        const bool bBow=ColdSteelInventory::IsBow(Item);
        const double AttackScale=bBow?ColdSteelInventory::Number(Item,TEXT("bow_damage_coefficient_scale"),1.5):1.;
        const FString AttackTerm=TEXT("+")+(FMath::IsNearlyEqual(AttackScale,1.)?FString():FormulaNumber(AttackScale)+TEXT("×"))+TEXT("角色攻击力");
        FormulaRow(Card,TEXT("攻击力计算公式"),WithForging(FormulaNumber(WeaponBase)+AttackTerm));
        if(!bProductionAxe)FormulaRow(Card,TEXT("强化后攻击力公式 · L=强化等级"),WithForging(
            bBow?FormulaNumber(WeaponBase)+TEXT("+")+FormulaNumber(WeaponBase*Enhancement->IncreasePerLevel())+TEXT("L")+AttackTerm:
            FormulaNumber(WeaponBase)+TEXT("×(1+")+FormulaNumber(Enhancement->IncreasePerLevel())+TEXT("L)")+AttackTerm));
    }
}
