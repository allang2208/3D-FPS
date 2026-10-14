#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"

float UColdSteelStatusModel::SpellManaCost(FName Id,int32 AtLevel) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelSpellManaCost);
    float Cost=SpellManaCostBeforeFocus(Id,AtLevel),UnusedCastSpeed=1.f;
    ApplySpellbookFocus(UnusedCastSpeed,Cost);
    return Cost;
}

float UColdSteelStatusModel::SpellManaCostBeforeFocus(FName Id,int32 AtLevel) const
{
    const auto* D=QuickSkillDefinition(Id);
    if(!D)return 0.f;
    const auto* Progress=Current.Skills.Find(Id);
    const int32 L=FMath::Clamp(AtLevel<0?(Progress?Progress->Level:FColdSteelSkillProgress().Level):AtLevel,1,D->MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D->MaxLevel-1);
    float Cost=0.f;
    if(Id==TEXT("fireball"))Cost=D->Fireball.ManaCost+(L-1)*D->Fireball.ManaCostPerLevel;
    else if(Id==TEXT("iceSpike"))Cost=D->IceSpike.ManaCost+(L-1)*D->IceSpike.ManaCostPerLevel;
    else if(Id==TEXT("iceWall"))Cost=D->IceWall.ManaCost;
    else if(Id==TEXT("blizzard"))Cost=D->Blizzard.ManaCost;
    else if(Id==TEXT("lightningStrike"))Cost=D->Lightning.ManaCost;
    else if(Id==TEXT("holyLight"))Cost=D->HolyLight.ManaCost;
    else if(FireMagic::IsSkill(Id))Cost=D->FireMagic.ManaBase+FMath::FloorToFloat(Growth*D->FireMagic.ManaGrowth);
    else if(ElectricMagic::IsSkill(Id))Cost=D->ElectricMagic.ManaBase+FMath::FloorToFloat(Growth*D->ElectricMagic.ManaGrowth);
    else return 0.f;

    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    double StaffCost=0.,ChainCost=0.;
    bool bStaffCraft=false;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            const auto* Pawn=RuntimePawn();
            const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
            const int32 Chain=Status?Status->ChainSpellStacks():0;
            StaffCost=E->CraftEffect(*Item,TEXT("magicMpCostPercent"));
            ChainCost=Chain*E->CraftEffect(*Item,TEXT("chainSpellMpCostPercent"));
            bStaffCraft=true;
        }

    // Preserve each spell's existing rounding order. Fireball applies the rune
    // first and rounds only with staff crafting; other spells round before it.
    if(Id==TEXT("fireball"))
    {
        Cost*=Rune.MagicCost;
        if(bStaffCraft)Cost=FMath::Max(0.f,FMath::FloorToFloat(Cost*(1.+StaffCost+ChainCost)));
        return Cost;
    }
    const double CostFactor=Id==TEXT("iceSpike")?(1.+StaffCost)+ChainCost:1.+(StaffCost+ChainCost);
    // Blizzard and the fire-area spells previously multiplied in float precision.
    const float Rounded=(Id==TEXT("blizzard")||FireMagic::IsSkill(Id))
        ?FMath::FloorToFloat(Cost*float(CostFactor)):FMath::FloorToFloat(Cost*CostFactor);
    return FMath::Max(0.f,Rounded*float(Rune.MagicCost));
}
