#include "RuneSwordComponent.h"
#include "ModularSwordVisual.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

void URuneSwordComponent::ClearClovenCounter()
{
    ClovenReadyUntil=0.;ClovenGrantedAt=-100.;ClovenGlow=0.f;
}

void URuneSwordComponent::GrantClovenCounter()
{
    if(MeleeModifiers.ClovenSeconds<=0)return;
    ClovenGrantedAt=GetWorld()->GetTimeSeconds();
    ClovenReadyUntil=ClovenGrantedAt+MeleeModifiers.ClovenSeconds;
}

bool URuneSwordComponent::TryClovenCounter()
{
    if(ClovenReadyUntil<=0 || GetWorld()->GetTimeSeconds()>=ClovenReadyUntil)return false;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->Equipped():nullptr;
    const auto Mods=ColdSteelMelee::EquippedModifiers(Profile);
    if(!Item || Item->InstanceId!=InstanceId || Item->Definition!=TEXT("ue_highland_claymore") || Mods.ClovenSeconds<=0)
    {ClearClovenCounter();return false;}
    // A blocked press must not fall through into a normal charge or spend the token.
    if(!IsEquipped() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset() ||
        Character->IsCastBlockingLeftHandAction() || Character->IsDodging() || Character->IsSliding() ||
        bWhirlwind || bDashAttack || bGuardBreakPose || bCharging || bReturningCharge)return true;
    if(bAttacking || bEquipping)
    {if(bEquipping || Elapsed>=ContactEnd)bQueuedAttack=true;return true;}
    if(!Animations.FindRef(TEXT("HeavyRelease")) || !Profile->CanSpendStamina(ColdSteelMelee::AttackStamina(Item,Profile)))return true;

    // The guard grants the release itself; mastery still supplies its current multiplier.
    ChargedMultiplier=Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier;
    if(!StartSwing(TEXT("HeavyRelease"),true))return true;
    ClearGuard();bInspecting=false;
    // Scale the physical channels and total together, preserving the magic amount
    // when ApplyWeaponHit reconstructs damage parts from this swing's snapshot.
    const double PreviousTotal=SwingSkills.DamagePanel.Total();
    SwingSkills.DamagePanel.BasePhysical*=Mods.ClovenPhysical;
    SwingSkills.DamagePanel.AddedPhysical*=Mods.ClovenPhysical;
    if(PreviousTotal>0)SwingDamage*=SwingSkills.DamagePanel.Total()/PreviousTotal;
    else SwingDamage*=Mods.ClovenPhysical;
    SwingSkills.ToughnessDamageMultiplier*=Mods.ClovenToughness;
    ClovenReadyUntil=0.;NextSlash=1;
    return true;
}

void URuneSwordComponent::TickClovenCounter(float Delta)
{
    const double Now=GetWorld()->GetTimeSeconds();
    const bool Ready=MeleeModifiers.ClovenSeconds>0 && Now<ClovenReadyUntil;
    const float Target=Ready?FMath::SmoothStep(0.f,.10f,float(Now-ClovenGrantedAt)):0.f;
    ClovenGlow=FMath::FInterpConstantTo(ClovenGlow,Target,Delta,Ready?12.f:4.f);
    if(!ModularSword)return;
    for(auto* Module:ColdSteelModularSword::Components(ModularSword))
    {
        if(!Module->ComponentHasTag(TEXT("SwordSlot=guard")))continue;
        const int32 Index=Module->GetMaterialIndex(TEXT("M_Cloven_Inlay"));
        if(Index==INDEX_NONE)continue;
        auto* Material=Cast<UMaterialInstanceDynamic>(Module->GetMaterial(Index));
        if(!Material)Material=Module->CreateDynamicMaterialInstance(Index);
        if(!Material)continue;
        Material->SetScalarParameterValue(TEXT("GuardCharge"),ClovenGlow);
        Material->SetScalarParameterValue(TEXT("GuardWave"),FMath::Clamp(float(Now-ClovenGrantedAt)/.22f,0.f,1.f));
    }
}
