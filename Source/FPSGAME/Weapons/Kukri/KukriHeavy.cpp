#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriHeavyRhythm.h"
#include "../MeleeWeaponStats.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Heavy strike (skill heavyStrike, 2026-10-24) for the kukri: the reference jump melee #12 ↙ (BV1CeYUeSE7b 115.6-117.0 s;
// SourceAssets/Kukri20261020/fit_heavy.py -> author_kukri_heavy.py, clips "HeavyCharge" 2.0 s and "HeavyRelease" 35/30 s).
// Same rule as the two-handed sword: with the skill learned the left press starts the charge; a release within
// TapSeconds or before the full charge is the ordinary click, a release after the full charge (the item/skill's
// HeavyChargeSeconds, from the press) is the heavy.  The quick-bar skill charges and releases by itself.  The charge drains
// the skill's stamina per second (FPSStaminaModel, IsHeavyCharging) and the release pays one attack's stamina; damage is the
// heavy formula (FMeleeModifiers::HeavyMultiplier with the skill's multiplier), AttackMeta 0x10, heavy toughness, reach with
// the martial range.  The release runs as stage KukriRhythm::HeavyStage on the combo's tables (impact moment, hit-stop, rift,
// camera) on a martial clock: Lightning Haste only, KukriRhythm::HeavyTempo on top.  Online the server keeps its own charge
// clock and stamina bill and opens a short receipt for the heavy hit reports (ColdSteelPlayerState hit validation).

namespace
{
UColdSteelStatusModel* KukriHeavyProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
}

bool UKukriWeaponComponent::CanBeginHeavyCharge() const
{
    const auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    return P&&IsEquipped()&&!IsBusy()&&CanUse()&&Viewmodel&&Item&&Item->InstanceId==InstanceId&&!Profile->ActiveProductionTool()&&
        Profile->MasteryProgress(TEXT("heavyStrike")).Level>=1&&Profile->Stamina()>0.f&&
        Profile->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile))&&
        !UBoundCongregateCaptureComponent::IsCaptured(P)&&!P->IsCastBlockingLeftHandAction()&&!P->IsSpellGestureBlocking()&&
        Animations.FindRef(KukriHeavyRhythm::ChargeClip)&&Animations.FindRef(KukriHeavyRhythm::ReleaseClip);
}

void UKukriWeaponComponent::BeginHeavyCharge()
{
    auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||!GetWorld())return;
    // The charge clock starts at the press (the sword's rule); the skill tier is fixed for this charge.
    HeavyRequiredSeconds=FMath::Max(.3f,float(ColdSteelMelee::Evaluate(*Item,Profile).HeavyChargeSeconds));
    HeavyMultiplier=float(Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier);
    HeavyChargeStartedAt=GetWorld()->GetTimeSeconds();
    bHeavyAuto=bHeavyFull=false;bQueued=false;
    SetHeavyCharging(true,false);
    SetClip(KukriHeavyRhythm::ChargeClip,false,KukriRhythm::EntryBlendSeconds);
}

bool UKukriWeaponComponent::TriggerHeavySkill()
{
    if(!CanBeginHeavyCharge())return false;
    BeginHeavyCharge();
    bHeavyAuto=bHeavyCharging;
    return bHeavyCharging;
}

float UKukriWeaponComponent::HeavyChargeFraction() const
{
    if(!bHeavyCharging||!GetWorld())return 0.f;
    return FMath::Clamp(float(GetWorld()->GetTimeSeconds()-HeavyChargeStartedAt)/FMath::Max(.01f,HeavyRequiredSeconds),0.f,1.f);
}

void UKukriWeaponComponent::SetHeavyCharging(bool bCharging,bool bRelease)
{
    if(bHeavyCharging==bCharging)return;
    bHeavyCharging=bCharging;
    const auto* P=Pawn();
    if(P&&P->IsLocallyControlled()&&!P->HasAuthority())ServerSetKukriHeavyCharge(InstanceId,bCharging,bRelease);
}

void UKukriWeaponComponent::CancelHeavyCharge(bool bNotifyServer)
{
    if(!bHeavyCharging)return;
    // The view eases out of the charge camera instead of snapping back.
    KukriHeavyRhythm::ChargeCamera(Elapsed,CameraCarry,CameraCarryFov);CameraCarryAge=0.f;
    if(bNotifyServer)SetHeavyCharging(false,false);else bHeavyCharging=false;
    bHeavyAuto=bHeavyFull=false;
    if(IsEquipped()&&Viewmodel)SetClip(LocomotionClip(),true,KukriHeavyRhythm::CancelBlendSeconds);
}

void UKukriWeaponComponent::ReleasePrimaryAttack()
{
    // The quick-bar charge releases itself; a physical release only answers the left-button charge.
    if(!bHeavyCharging||bHeavyAuto||!GetWorld())return;
    auto* P=Pawn();
    if(!P||!CanUse()||P->IsCastBlockingLeftHandAction()){CancelHeavyCharge(true);return;}
    // Decide from the input's gameplay time (input is dispatched before the component tick).
    const double Held=GetWorld()->GetTimeSeconds()-HeavyChargeStartedAt;
    if(Held>=HeavyRequiredSeconds){ReleaseHeavyCharge();return;}
    // A tap or a short hold is the ordinary click: the combo stage enters from the current pose on its entry blend
    // (a tap never left the stance -- the raise waits TapSeconds).
    KukriHeavyRhythm::ChargeCamera(Elapsed,CameraCarry,CameraCarryFov);CameraCarryAge=0.f;
    SetHeavyCharging(false,false);bHeavyAuto=bHeavyFull=false;
    StartComboClick();
    if(!bAttacking&&IsEquipped()&&Viewmodel)SetClip(LocomotionClip(),true,KukriHeavyRhythm::CancelBlendSeconds);
}

void UKukriWeaponComponent::AdvanceHeavyCharge(float Delta)
{
    auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId||!CanUse()||P->IsCastBlockingLeftHandAction()||Profile->Stamina()<=0.f)
    {CancelHeavyCharge(true);return;}
    const float Held=float(GetWorld()->GetTimeSeconds()-HeavyChargeStartedAt);
    // A left-button press waits TapSeconds before the raise, so a click does not bob the hand; the quick bar raises at once.
    const float Delay=bHeavyAuto?0.f:KukriHeavyRhythm::TapSeconds;
    Elapsed=KukriHeavyRhythm::ChargePoseTime(FMath::Max(0.f,Held-Delay),HeavyRequiredSeconds-Delay,
        FMath::Max(.05f,LightningHaste::ActionSpeed(P)));
    SamplePose(Elapsed);
    if(!bHeavyFull&&Held>=HeavyRequiredSeconds)
    {
        // Full charge: the grip tightens (a short grip slap) and the hand starts its tension tremble (ViewmodelKick).
        bHeavyFull=true;
        if(CatchSound)UGameplayStatics::PlaySound2D(this,CatchSound,.45f,.82f);
    }
    if(bHeavyAuto&&bHeavyFull)ReleaseHeavyCharge();
}

void UKukriWeaponComponent::ReleaseHeavyCharge()
{
    auto* P=Pawn();
    auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId){CancelHeavyCharge(true);return;}
    // One attack's stamina on the release (the sword's HeavyReleaseStamina); the server bills its shadow on the same release.
    if(!Profile->SpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile))){CancelHeavyCharge(true);return;}
    SetHeavyCharging(false,true);bHeavyAuto=bHeavyFull=false;
    // Snapshot at the release: damage, reach and toughness stay fixed for this swing.
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    SwingDamage=float(Stats.Damage*Stats.Modifiers.HeavyMultiplier(HeavyMultiplier));
    Reach=float((Stats.BaseReach>0.?Stats.BaseReach:KukriRhythm::DefaultReachCM)*Stats.Modifiers.MartialRange);
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.bMeleeStrike=true;
    Shot.AttackForm=KukriRhythm::Form;
    Shot.AttackMeta=0x10;                          // heavy: the authority re-derives the multiplier and checks the receipt
    Shot.ToughnessDamageMultiplier*=float(Stats.Modifiers.HeavyToughness);
    Stage=KukriRhythm::HeavyStage;
    bHeavyAttack=true;bHeavyTrainingPending=true;HeavyHits=HeavyKills=0;
    bSwingPlayed=bImpactConfirmed=bWallHit=false;HitActors.Reset();HitStop=0.f;ImpactAge=-1.f;
    ResetStrike();StrikeAge=-1.f;CameraCarryAge=-1.f;StopRift();
    // The swing combo starts over after the heavy strike.
    NextStage=0;LastAttackEnd=-1.;
    SetClip(KukriHeavyRhythm::ReleaseClip,false,KukriHeavyRhythm::ReleaseEntryBlend);
    PreviousBlade=BladeFrame();bHavePreviousBlade=true;
}

void UKukriWeaponComponent::AdvanceHeavy(float Delta)
{
    auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId){CancelAction();return;}
    const auto& S=KukriRhythm::Swings[Stage];
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bHeavyAttack&&++Guard<64)
    {
        if(HitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStop);
            HitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():S.Length;
        const float StageRate=Rate*KukriRhythm::StageTempo(Stage,Elapsed);
        float Step=FMath::Min(Remaining*StageRate,1.f/120.f);
        const float StrikeAt=KukriRhythm::Strikes[Stage].At, RiftAt=KukriRhythm::Rifts[Stage].Start;
        for(const float Boundary:{S.SwingSound,S.ContactStart,S.ContactEnd,StrikeAt,RiftAt,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/StageRate);
        SamplePose(Elapsed);
        const FTransform Now=BladeFrame();
        if(!bSwingPlayed&&Elapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            // A sharp whoosh on the cut with the item's own swing sound a little lower underneath.
            bSwingPlayed=true;
            const bool bWhoosh=KukriRhythm::Strikes[Stage].bWhoosh&&StabWhooshSound;
            if(USoundBase* Cue=bWhoosh?StabWhooshSound.Get():SwingSound.Get())
                UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume*1.1f:.6f,S.SwingPitch);
            if(bWhoosh&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.5f,S.SwingPitch*.85f);
        }
        if(bHavePreviousBlade&&Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd)TraceBlade(PreviousBlade,Now);
        PreviousBlade=Now;bHavePreviousBlade=true;
        if(StrikeAt>0.f&&!bStrikeDone&&Elapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveStrike();
        if(!bRiftStarted&&Elapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bRiftStarted=true;StartRift();}
        if(bHeavyTrainingPending&&Elapsed>=S.ContactEnd-UE_KINDA_SMALL_NUMBER)FinishHeavy(true);
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            bHeavyAttack=false;
            FinishHeavy(true);
            HitActors.Reset();
            Stage=0;
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::FinishHeavy(bool bTrain)
{
    // One completed release, the highest tier it reached (unique victims of its direct contact window), as the sword trains.
    if(!bHeavyTrainingPending)return;
    bHeavyTrainingPending=false;
    if(!bTrain)return;
    if(auto* Profile=KukriHeavyProfile(GetWorld()))Profile->TrainHeavyStrike(HeavyHits,HeavyKills);
}

bool UKukriWeaponComponent::IsHeavyCharging() const
{
    const auto* P=Pawn();
    return P&&(P->IsLocallyControlled()?bHeavyCharging:(P->HasAuthority()&&bServerHeavyCharging));
}

// ----------------------------------------------------------------------------- authority (remote owner)

void UKukriWeaponComponent::ServerSetKukriHeavyCharge_Implementation(const FString& Weapon,bool bCharging,bool bRelease)
{
    auto* P=Pawn();
    if(!P||!P->HasAuthority()||P->IsLocallyControlled()||!GetWorld())return;
    if(!bCharging)
    {
        // Only a real release after a long enough hold bills the release and opens the receipt; a cancel or a click does not.
        if(bRelease&&Weapon==ServerHeavyWeapon)PayServerHeavyRelease();
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        return;
    }
    auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Item||Item->InstanceId!=Weapon||!IsKukri(*Item)||Model->ActiveProductionTool()||
        Model->MasteryProgress(TEXT("heavyStrike")).Level<1||Model->Stamina()<=0.f||
        !Model->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Model))||UBoundCongregateCaptureComponent::IsCaptured(P))
    {
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        ClientCancelKukriHeavyCharge(Weapon);return;
    }
    // The shadow profile's stamina tick bills the charge at the owner's rate (FPSStaminaModel, IsHeavyCharging).
    if(!bServerHeavyCharging)
    {
        ServerHeavyStartedAt=GetWorld()->GetTimeSeconds();
        ServerHeavyRequired=ColdSteelMelee::Evaluate(*Item,Model).HeavyChargeSeconds;
        NetworkHeavyReleaseUntil=-1.;
    }
    bServerHeavyCharging=true;ServerHeavyWeapon=Weapon;
}

bool UKukriWeaponComponent::PayServerHeavyRelease()
{
    if(!GetWorld())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    // Network latency may hide a few frames of an honest full charge; the tolerance never lets a click through.
    if(!bServerHeavyCharging||ServerHeavyStartedAt<0.||Now-ServerHeavyStartedAt<FMath::Max(.1,ServerHeavyRequired-.15))return false;
    bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
    auto* Model=ColdSteelAuthority::ForPawn(Pawn());
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Item||Item->InstanceId!=ServerHeavyWeapon)return false;
    const double Cost=ColdSteelMelee::HeavyReleaseStamina(Item,Model);
    if(!Model->CanSpendStamina(Cost)){ClientCancelKukriHeavyCharge(ServerHeavyWeapon);return false;}
    Model->SpendStamina(Cost);
    NetworkHeavyReleaseUntil=Now+KukriHeavyRhythm::ReleaseWindowSeconds;
    return true;
}

bool UKukriWeaponComponent::IsNetworkHeavyReleaseWindowOpen(const FString& Weapon) const
{
    const auto* World=GetWorld();
    return GetOwner()&&GetOwner()->HasAuthority()&&World&&World->GetTimeSeconds()<=NetworkHeavyReleaseUntil&&
        !Weapon.IsEmpty()&&Weapon==ServerHeavyWeapon;
}

bool UKukriWeaponComponent::ConsumeNetworkHeavyChargeForRelease(const FString& Weapon)
{
    // The hit report travels on the player state and can overtake the release RPC: settle the release from the charge.
    if(!GetOwner()||!GetOwner()->HasAuthority()||Weapon.IsEmpty()||Weapon!=ServerHeavyWeapon)return false;
    return PayServerHeavyRelease();
}

void UKukriWeaponComponent::TickServerHeavyCharge()
{
    auto* P=Pawn();
    auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!P||!Item||Item->InstanceId!=ServerHeavyWeapon||Model->Stamina()<=0.f||UBoundCongregateCaptureComponent::IsCaptured(P))
    {
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        ClientCancelKukriHeavyCharge(ServerHeavyWeapon);
    }
}

void UKukriWeaponComponent::ClientCancelKukriHeavyCharge_Implementation(const FString& Weapon)
{
    const auto* P=Pawn();
    if(P&&P->IsLocallyControlled()&&!P->HasAuthority()&&Weapon==InstanceId&&bHeavyCharging)CancelHeavyCharge(false);
}
