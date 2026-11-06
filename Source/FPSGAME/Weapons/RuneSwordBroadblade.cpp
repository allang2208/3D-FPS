#include "RuneSwordComponent.h"
#include "HighlandBreakSweep.h"
#include "HighlandRidgeThrust.h"
#include "SwordGripClearance.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"

namespace
{
FSoftObjectPath SweepPath(bool LongGrip,bool FromReady)
{
    FString Name=LongGrip?TEXT("A_Highland_BreakSweep_LongGrip"):TEXT("A_Highland_BreakSweep_Standard");
    if(FromReady)Name+=TEXT("_FromReady");
    return FSoftObjectPath(TEXT("/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104/")+Name+TEXT(".")+Name);
}
}

void URuneSwordComponent::RefreshBroadblade(const FColdSteelItem* Item)
{
    const bool Enabled=HighlandBreakSweep::Installed(GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item);
    if(!Enabled || Item->InstanceId!=InstanceId)
    {
        SweepReadyUntil=SweepServerHitUntil=0.;
        SweepServerTargets.Reset();
        if(bAttacking && CurrentClip==HighlandBreakSweep::Clip)CancelAction();
    }
    bBroadbladeInstalled=Enabled;
    if(!Enabled)
    {
        BroadbladeLoad.Reset();
        return;
    }
    if(!BroadbladeLoad && Character->IsLocallyControlled())
        BroadbladeLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{SweepPath(false,false),SweepPath(true,false),SweepPath(false,true),SweepPath(true,true),
                HighlandBreakSweep::RiftPath(false),HighlandBreakSweep::RiftPath(true)});
}

void URuneSwordComponent::GrantBroadbladeSweep(const FString& Weapon)
{
    if(!Character.IsValid() || Weapon!=InstanceId)return;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!HighlandBreakSweep::Installed(GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item)
        || Item->InstanceId!=Weapon)return;
    SweepReadyUntil=GetWorld()->GetTimeSeconds()+HighlandBreakSweep::Window;
}

ESwordGripMode URuneSwordComponent::GripMode() const
{
    // The charge and its matching release keep both hands on their idle
    // grip stations as the wrists turn. Share the same fit at button-up.
    if(CurrentClip==HighlandRidgeThrust::Charge||HighlandRidgeThrust::IsRelease(CurrentClip))
        return ESwordGripMode::HeldAuthoredArms;
    if(bBroadbladeInstalled && (CurrentClip==TEXT("HeavyCharge") || CurrentClip==TEXT("HeavyRelease") ||
        CurrentClip==HighlandBreakSweep::Clip))return ESwordGripMode::Held;
    return ESwordGripMode::Adaptive;
}

bool URuneSwordComponent::IsBroadbladeSweepReady() const
{
    return bBroadbladeInstalled && GetWorld()->GetTimeSeconds()<SweepReadyUntil;
}

bool URuneSwordComponent::BeginBroadbladeSweep()
{
    if(!IsBroadbladeSweepReady() || (bAttacking && !bHeavyAttack))return false;
    if(bAttacking && Elapsed<RuneSwordHeavyRhythm::FollowEnd)
    {
        bQueuedAttack=true;
        return true;
    }
    if(bAttacking && Elapsed>RuneSwordHeavyRhythm::ArrestEnd)
    {
        // The blade has left the landing pose. Buffer the click and finish the
        // authored return instead of blending across opposite elbow planes.
        bQueuedAttack=true;
        SwingRate=FMath::Max(SwingRate,2.f);
        return true;
    }
    const bool FromReady=!bHeavyAttack;
    auto* Animation=Cast<UAnimSequence>(SweepPath(EquippedAnimationFolder.EndsWith(TEXT("/LongGripAnimations")),FromReady).ResolveObject());
    if(!Animation || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset() ||
        Animation->GetSkeleton()!=Viewmodel->GetSkeletalMeshAsset()->GetSkeleton())return false;
    Animations.Add(HighlandBreakSweep::Clip,Animation);
    if(!StartSwing(HighlandBreakSweep::Clip,false,-1.f,false))return true;
    SwingSkills.AttackMeta=HighlandBreakSweep::AttackMeta;
    SwingReach=HighlandBreakSweep::Radius(SwingReach);
    // Scale physical only. The total and its physical/magic panel must agree.
    const double Total=SwingSkills.DamagePanel.Total();
    SwingSkills.DamagePanel.BasePhysical*=HighlandBreakSweep::PhysicalScale;
    SwingSkills.DamagePanel.AddedPhysical*=HighlandBreakSweep::PhysicalScale;
    SwingDamage*=Total>0.?SwingSkills.DamagePanel.Total()/Total:HighlandBreakSweep::PhysicalScale;
    NextSlash=0;
    StopRift();
    SweepReadyUntil=0.;
    if(!Character->HasAuthority())ServerStartBroadbladeSweep(InstanceId,SwingSkills.GuardAttackSerial);
    return true;
}

bool URuneSwordComponent::CommitBroadbladeSweep(const FString& Weapon,uint32 Serial)
{
    const double Now=GetWorld()->GetTimeSeconds();
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Serial || !Character.IsValid() || !Character->HasAuthority() || !Item || Item->InstanceId!=Weapon ||
        Model->ActiveProductionTool() || !HighlandBreakSweep::Installed(GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item))return false;
    if(Serial==SweepServerSerial)return Now<SweepServerHitUntil;
    if(int32(Serial-SweepServerSerial)<=0 || Now>=SweepReadyUntil)return false;
    if(!Model->SpendStamina(ColdSteelMelee::AttackStamina(Item,Model)))return false;
    SweepReadyUntil=0.;
    SweepServerSerial=Serial;
    SweepServerHitUntil=Now+1.0;
    SweepServerTargets.Reset();
    return true;
}

void URuneSwordComponent::ServerStartBroadbladeSweep_Implementation(const FString& Weapon,uint32 Serial)
{
    CommitBroadbladeSweep(Weapon,Serial);
}

bool URuneSwordComponent::AcceptBroadbladeContact(const FString& Weapon,uint32 Serial,AActor* Target)
{
    if(!Target || !CommitBroadbladeSweep(Weapon,Serial) || SweepServerTargets.Contains(Target))return false;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const float AllowedReach=HighlandBreakSweep::Radius(ColdSteelMelee::Evaluate(*Model->Equipped(),Model).SlashReach);
    const FVector Aim=Character->GetBaseAimRotation().Vector().GetSafeNormal2D(UE_SMALL_NUMBER,Character->GetActorForwardVector().GetSafeNormal2D());
    // Validate the same front arc, including the target's footprint and world cover.
    const auto Hits=RuneSwordCombat::QuerySector(GetWorld(),Character.Get(),Character->GetActorLocation(),
        Aim,AllowedReach,HighlandBreakSweep::ArcDegrees,SweepServerTargets);
    if(!Hits.ContainsByPredicate([Target](const FHitResult& Hit){return Hit.GetActor()==Target;}))return false;
    SweepServerTargets.Add(Target);
    return true;
}

void URuneSwordComponent::ClientBroadbladeImpact_Implementation(const FString& Weapon,uint32 Serial)
{
    if(Weapon!=InstanceId || !bAttacking || CurrentClip!=HighlandBreakSweep::Clip ||
        Serial!=SwingSkills.GuardAttackSerial || bImpactFeedbackPlayed)return;
    bImpactFeedbackPlayed=true;
    ImpactDirection=-1.f;
    ImpactStrength=HighlandBreakSweep::ImpactStrength;
    ImpactAge=0.f;
    // Late receipts still kick the camera, but never arrest a returning blade.
    if(Elapsed<=ContactEnd)SweepHitPause=HighlandBreakSweep::HitPauseSeconds;
}
