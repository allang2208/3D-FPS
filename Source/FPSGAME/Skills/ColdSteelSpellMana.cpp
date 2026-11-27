#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSpellCrafting.h"
#include "../Weapons/Bow/BowStats.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatItemFormula.h"
#include "../Combat/ResourceCostFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../FPSGAMECharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"

float UColdSteelStatusModel::SpellManaCost(FName Id,int32 AtLevel,bool bApplyFocus) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelSpellManaCost);
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
    else if(Id==TEXT("illuminationArrow"))Cost=D->IlluminationArrow.ManaCost;
    else if(Id==TEXT("magicArrowRain"))Cost=D->MagicArrowRain.ManaCost;
    else if(Id==TEXT("lightningStrike"))Cost=D->Lightning.ManaCost;
    else if(Id==TEXT("holyLight"))Cost=D->HolyLight.ManaCost;
    else if(Id==TEXT("iceArmor"))Cost=D->IceArmor.ManaBase+(L-1)*D->IceArmor.ManaPerLevel;
    else if(Id==TEXT("lightningHaste"))Cost=D->LightningHaste.ManaBase+(L-1)*D->LightningHaste.ManaPerLevel;
    else if(FireMagic::IsSkill(Id))Cost=D->FireMagic.ManaBase+FMath::FloorToFloat(Growth*D->FireMagic.ManaGrowth);
    else if(ElectricMagic::IsSkill(Id))Cost=D->ElectricMagic.ManaBase+FMath::FloorToFloat(Growth*D->ElectricMagic.ManaGrowth);
    else return 0.f;

    return AdjustedManaCost(Cost,bApplyFocus);
}

float UColdSteelStatusModel::AdjustedManaCost(float Cost,bool bApplyFocus) const
{
    const FStatCacheKey CacheKey=MakeStatCacheKey();
    if(!(CachedManaMultKey==CacheKey))
    {
        CachedManaMultKey=CacheKey;
        CachedManaMultiplier[0]=CachedManaMultiplier[1]=-1.0;
        CachedManaMultChain[0]=CachedManaMultChain[1]=-1;
        CachedManaMultFocus[0]=CachedManaMultFocus[1]=false;
    }
    const auto* Item=Equipped();
    const bool bStaff=Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff");
    const int32 Chain=bStaff?ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn()):0;
    const auto* Book=bApplyFocus?ActiveSpellbook():nullptr;
    bool bFocusActive=false;
    if(Book)
    {
        const auto* Pawn=RuntimePawn();
        const auto* Focus=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
        bFocusActive=Focus&&Focus->IsFocusEmpowered();
    }
    const int32 SlotIdx=bApplyFocus?1:0;
    if(CachedManaMultiplier[SlotIdx]>=0.0 && CachedManaMultChain[SlotIdx]==Chain && CachedManaMultFocus[SlotIdx]==bFocusActive)
    {
        return float(ColdSteelResourceCost::Apply(Cost,CachedManaMultiplier[SlotIdx]));
    }

    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    double StaffCost=0.,ChainCost=0.;
    if(bStaff)
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            StaffCost=E->CraftEffect(*Item,TEXT("magicMpCostPercent"));
            ChainCost=Chain*E->CraftEffect(*Item,TEXT("chainSpellMpCostPercent"));
        }

    double FocusCost=1.;
    if(bFocusActive && Book)
    {
        const auto Data=CombatItemFormula::ReadOnly(*Book);
        const TSharedPtr<FJsonObject>* Effects=nullptr;
        if(Data&&Data->TryGetObjectField(TEXT("focusEffects"),Effects))
            (*Effects)->TryGetNumberField(TEXT("manaCostMultiplier"),FocusCost);
    }

    // EquipmentBonus already multiplies item factors with a 50% per-item cap.
    // Crafting, chain status, runes and focus are separate multiplier zones.
    // Keep fractional mana and apply the 20% base-cost floor after focus too.
    const double Equipment=1.+EquipmentBonus(TEXT("magicCostPercent"));
    const auto* Aurora=ColdSteelBow::AuroraRiser(this,ActiveBow());
    const double Multiplier=(Aurora?Aurora->Bow.ManaCost:1.)*Equipment*FMath::Max(0.,1.+StaffCost)
        *FMath::Max(0.,1.+ChainCost)*FMath::Max(0.,double(Rune.MagicCost))
        *FMath::Max(0.,FocusCost);
    CachedManaMultChain[SlotIdx]=Chain;
    CachedManaMultFocus[SlotIdx]=bFocusActive;
    CachedManaMultiplier[SlotIdx]=Multiplier;
    return float(ColdSteelResourceCost::Apply(Cost,Multiplier));
}
