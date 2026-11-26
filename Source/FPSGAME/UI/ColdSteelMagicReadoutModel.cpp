#include "Engine/HitResult.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Combat/CombatItemFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"

FColdSteelStaffManaReadout UColdSteelStatusModel::StaffManaReadout(const AFPSGAMECharacter* Pawn) const
{
    FColdSteelStaffManaReadout Result;
    Result.Maximum=FMath::Max(0.f,Derived(TEXT("maxMp")));
    Result.Current=FMath::Clamp(Mana(),0.f,Result.Maximum);
    Result.bInfinite=HasInfiniteMana();

    // The same equipped craft/set factors used by staff spell cast snapshots.
    double CraftReduction=0.;
    if(const auto* Item=Equipped();Item&&!ActiveProductionTool()&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(const auto* Enhancement=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
            CraftReduction=Enhancement->CraftEffect(*Item,TEXT("magicCooldownPercent"));
    double CooldownMultiplier=FMath::Max(.2,(1.-CraftReduction)*(1.-SetEffect(TEXT("cooldown"))))
        *ColdSteelMelee::EquippedModifiers(this).MagicCooldown;
    if(const auto* Rune=UJingangRuneComponent::From(this))CooldownMultiplier*=Rune->CooldownMultiplier();
    Result.CooldownReductionPercent=HasNoAbilityCooldown()?100.f:float((1.-CooldownMultiplier)*100.);

    const float BaseRate=FMath::Max(0.f,Derived(TEXT("mpRegen")));
    const float ProcSeconds=FMath::Max(0.f,KillProcTime);
    const float ProcRate=ProcSeconds>0.f?FMath::Max(0.f,KillProcMp):0.f;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool Recovering=Health&&!Health->IsDead();
    Result.RecoveryPerSecond=Recovering?BaseRate+ProcRate:0.f;
    const float Missing=Result.Maximum-Result.Current;
    if(Result.bInfinite||Missing<=0.f)return Result;
    if(!Recovering){Result.bRecoveryPaused=true;return Result;}

    // Kill recovery is a finite drip, not a permanent addition to regeneration.
    const float ProcRecovery=(BaseRate+ProcRate)*ProcSeconds;
    if(Result.RecoveryPerSecond>0.f&&Missing<=ProcRecovery)
        Result.FullRecoverySeconds=Missing/Result.RecoveryPerSecond;
    else if(BaseRate>0.f)
        Result.FullRecoverySeconds=ProcSeconds+FMath::Max(0.f,Missing-ProcRecovery)/BaseRate;
    else Result.bRecoveryDisabled=true;
    return Result;
}

FColdSteelSpellbookReadout UColdSteelStatusModel::SpellbookReadout(const AFPSGAMECharacter* Pawn) const
{
    FColdSteelSpellbookReadout Result;
    const auto* Book=ActiveSpellbook();
    if(!Book)return Result;
    const auto Data=CombatItemFormula::ReadOnly(*Book);
    const TSharedPtr<FJsonObject>* Effects=nullptr;
    if(Data&&Data->TryGetObjectField(TEXT("focusEffects"),Effects))
    {
        auto Number=[&](const TCHAR* Key,double Default){double Value=Default;(*Effects)->TryGetNumberField(Key,Value);return float(Value);};
        Result.CastSpeedMultiplier=Number(TEXT("castSpeedMultiplier"),1.);
        Result.ManaCostMultiplier=Number(TEXT("manaCostMultiplier"),1.);
        Result.MovementMultiplier=Number(TEXT("movementMultiplier"),.67);
        Result.InterruptMaxManaFraction=Number(TEXT("interruptMaxManaFraction"),.25);
    }
    const auto* Focus=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    if(Focus)
    {
        if(Focus->IsFocusEmpowered())Result.State=EColdSteelFocusReadout::Empowered;
        else if(Focus->IsFocusInterrupted())Result.State=EColdSteelFocusReadout::Interrupted;
        else if(Focus->IsConcentrating())Result.State=EColdSteelFocusReadout::Opening;
        else if(Focus->IsFocusActive())Result.State=EColdSteelFocusReadout::Closing;
    }
    return Result;
}
