#include "KukriWeaponComponent.h"
#include "KukriRelentlessComponent.h"
#include "KukriDecisiveComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriHeavyRhythm.h"
#include "SwiftFalconHeavy.h"
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
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

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
bool HeavyNetworkTrace()
{static const bool Enabled=FParse::Param(FCommandLine::Get(),TEXT("KukriHeavyNetTrace"));return Enabled;}
UColdSteelStatusModel* KukriHeavyProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
}

bool UKukriWeaponComponent::CanBeginHeavyCharge() const
{
    const auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    return P&&IsEquipped()&&!IsBusy()&&CanUse()&&Viewmodel&&Item&&Item->InstanceId==InstanceId&&!Profile->ActiveProductionTool()&&
        Profile->MasteryProgress(TEXT("heavyStrike")).Level>=1&&(Profile->Stamina()>0.f||Profile->HeavyChargeStaminaPerSecond()<=0.f)&&
        Profile->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile,DualHeavyReady()))&&
        !UBoundCongregateCaptureComponent::IsCaptured(P)&&!P->IsCastBlockingLeftHandAction()&&!P->IsSpellGestureBlocking()&&
        ((Animations.FindRef(KukriHeavyRhythm::ChargeClip)&&Animations.FindRef(KukriHeavyRhythm::ReleaseClip))||DualHeavyReady());
}

bool UKukriWeaponComponent::DualHeavyReady() const
{
    // The dual kukri's X (KukriHeavyRhythm::DualCharge*, KukriRhythm::DualHeavy*); without its clips the pair charges single.
    return IsDual()&&Animations.FindRef(KukriHeavyRhythm::DualChargeClip)&&Animations.FindRef(KukriHeavyRhythm::DualReleaseClip);
}

void UKukriWeaponComponent::BeginHeavyCharge()
{
    auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    if(!Item||!GetWorld())return;
    // The charge clock starts at the press (the sword's rule); the skill tier is fixed for this charge.
    bDualHeavy=DualHeavyReady();
    const auto* Off=bDualHeavy?ColdSteelMelee::PairedOneHandedWeapon(Item,Profile):nullptr;
    bDualHeavy=Off!=nullptr;HeavyOffhandWeapon=Off?Off->InstanceId:FString();
    bFalconHeavy=SwiftFalconHeavy::Eligible(Item,Profile,bDualHeavy)&&
        Animations.FindRef(bDualHeavy?SwiftFalconHeavy::DualCharge:SwiftFalconHeavy::Charge)&&
        Animations.FindRef(bDualHeavy?SwiftFalconHeavy::DualRelease:SwiftFalconHeavy::Release);
    HeavyRequiredSeconds=FMath::Max(.3f,float(ColdSteelMelee::HeavyChargeSeconds(*Item,Profile,bDualHeavy)));
    HeavyMultiplier=float(Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier);
    HeavyChargeStartedAt=GetWorld()->GetTimeSeconds();
    if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET owner_assets now=%.3f required=%.3f dual=%d arms=%d charge=%d release=%d dual_charge=%d dual_release=%d"),HeavyChargeStartedAt,HeavyRequiredSeconds,bDualHeavy,Viewmodel!=nullptr,Animations.FindRef(KukriHeavyRhythm::ChargeClip)!=nullptr,Animations.FindRef(KukriHeavyRhythm::ReleaseClip)!=nullptr,Animations.FindRef(KukriHeavyRhythm::DualChargeClip)!=nullptr,Animations.FindRef(KukriHeavyRhythm::DualReleaseClip)!=nullptr);
    bHeavyAuto=bHeavyFull=false;bQueued=false;
    SetHeavyCharging(true,false);
    const FName ChargeClip=bFalconHeavy?(bDualHeavy?SwiftFalconHeavy::DualCharge:SwiftFalconHeavy::Charge):
                                         (bDualHeavy?KukriHeavyRhythm::DualChargeClip:KukriHeavyRhythm::ChargeClip);
    SetClip(ChargeClip,false,KukriRhythm::EntryBlendSeconds);
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
    if(P&&P->IsLocallyControlled()&&!P->HasAuthority())
    {
        const auto* World=GetWorld();const auto* GS=World?World->GetGameState():nullptr;
        const double Stamp=GS?GS->GetServerWorldTimeSeconds():World->GetTimeSeconds();
        if(bCharging)FalconChargeKey=Stamp;
        ServerSetKukriHeavyCharge(InstanceId,bCharging,bRelease,bDualHeavy,Stamp);
    }
}

void UKukriWeaponComponent::CancelHeavyCharge(bool bNotifyServer)
{
    if(!bHeavyCharging)return;
    // The view eases out of the charge camera instead of snapping back.
    (bFalconHeavy?SwiftFalconHeavy::ChargeCamera:bDualHeavy?KukriHeavyRhythm::DualChargeCamera:KukriHeavyRhythm::ChargeCamera)(Elapsed,CameraCarry,CameraCarryFov);CameraCarryAge=0.f;
    if(bNotifyServer)SetHeavyCharging(false,false);else bHeavyCharging=false;
    bHeavyAuto=bHeavyFull=bDualHeavy=bFalconHeavy=false;
    if(IsEquipped()&&Viewmodel)SetClip(LocomotionClip(),true,KukriHeavyRhythm::CancelBlendSeconds);
}

void UKukriWeaponComponent::ReleasePrimaryAttack()
{
    // The quick-bar charge releases itself; a physical release only answers the left-button charge.
    if(!bHeavyCharging||bHeavyAuto||!GetWorld())return;
    auto* P=Pawn();
    if(!P||!CanUse(true)||P->IsCastBlockingLeftHandAction()){CancelHeavyCharge(true);return;}
    // Decide from the input's gameplay time (input is dispatched before the component tick).
    const double Held=GetWorld()->GetTimeSeconds()-HeavyChargeStartedAt;
    if(Held>=HeavyRequiredSeconds){ReleaseHeavyCharge();return;}
    // A tap or a short hold is the ordinary click: the combo stage enters from the current pose on its entry blend
    // (a tap never left the stance -- the raise waits TapSeconds).
    (bFalconHeavy?SwiftFalconHeavy::ChargeCamera:bDualHeavy?KukriHeavyRhythm::DualChargeCamera:KukriHeavyRhythm::ChargeCamera)(Elapsed,CameraCarry,CameraCarryFov);CameraCarryAge=0.f;
    SetHeavyCharging(false,false);bHeavyAuto=bHeavyFull=bDualHeavy=bFalconHeavy=false;
    StartComboClick();
    if(!bAttacking&&IsEquipped()&&Viewmodel)SetClip(LocomotionClip(),true,KukriHeavyRhythm::CancelBlendSeconds);
}

void UKukriWeaponComponent::AdvanceHeavyCharge(float Delta)
{
    auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    const auto* Off=bDualHeavy?ColdSteelMelee::PairedOneHandedWeapon(Item,Profile):nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId||!CanUse(true)||P->IsCastBlockingLeftHandAction()||(Profile->Stamina()<=0.f&&Profile->HeavyChargeStaminaPerSecond()>0.f))
    {CancelHeavyCharge(true);return;}
    if((bDualHeavy&&(!Off||Off->InstanceId!=HeavyOffhandWeapon))||
        (bFalconHeavy&&!SwiftFalconHeavy::Eligible(Item,Profile,bDualHeavy))){CancelHeavyCharge(true);return;}
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
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId){CancelHeavyCharge(true);return;}
    const auto* Off=bDualHeavy?ColdSteelMelee::PairedOneHandedWeapon(Item,Profile):nullptr;
    if((bDualHeavy&&(!Off||Off->InstanceId!=HeavyOffhandWeapon))||
        (bFalconHeavy&&!SwiftFalconHeavy::Eligible(Item,Profile,bDualHeavy))){CancelHeavyCharge(true);return;}
    // One action bill, split between participating blades; the server settles the same pair once.
    if(!Profile->SpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile,bDualHeavy))){CancelHeavyCharge(true);return;}
    SetHeavyCharging(false,true);bHeavyAuto=bHeavyFull=false;
    // Snapshot at the release: damage, reach and toughness stay fixed for this swing.
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    Reach=float((Stats.BaseReach>0.?Stats.BaseReach:KukriRhythm::DefaultReachCM)*Stats.Modifiers.MartialRange);
    Shot=ColdSteelSkills::Snapshot(P,Item);
    // Both phases use this release snapshot, so the pull inherits the chop's damage exactly once.
    if(bFalconHeavy)SwiftFalconHeavy::ScalePhysicalDamage(Shot.DamagePanel);
    SwingDamage=float(Shot.DamagePanel.Total()*Stats.Modifiers.HeavyMultiplier(HeavyMultiplier));
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.bMeleeStrike=true;
    Shot.AttackForm=KukriRhythm::Form;
    Shot.AttackMeta=0x10;                          // heavy: the authority re-derives the multiplier and checks the receipt
    Shot.ToughnessDamageMultiplier*=float(Stats.Modifiers.HeavyToughness);
    if(Off)
    {
        const auto OffStats=ColdSteelMelee::Evaluate(*Off,Profile);
        OffhandReach=float((OffStats.BaseReach>0.?OffStats.BaseReach:KukriRhythm::DefaultReachCM)*OffStats.Modifiers.MartialRange);
        OffhandShot=ColdSteelSkills::Snapshot(P,Off);
        if(bFalconHeavy)SwiftFalconHeavy::ScalePhysicalDamage(OffhandShot.DamagePanel);
        OffhandSwingDamage=float(OffhandShot.DamagePanel.Total()*OffStats.Modifiers.HeavyMultiplier(HeavyMultiplier));
        OffhandShot.bRifle=false;OffhandShot.bPistol=false;OffhandShot.WeakpointPercent=0;OffhandShot.bMeleeStrike=true;
        OffhandShot.AttackForm=KukriRhythm::Form;OffhandShot.AttackMeta=0x10;
        OffhandShot.ToughnessDamageMultiplier*=float(OffStats.Modifiers.HeavyToughness);
        // One release, one mastery serial: the authority trains each victim of the X once across both blades.
        OffhandShot.MasteryAttackSerial=Shot.MasteryAttackSerial;
    }
    Stage=KukriRhythm::HeavyStage;
    if(bFalconHeavy)FalconReleaseRate=SwiftFalconHeavy::ReleaseRate(*Item,Off,Profile);
    PairedHeavyContacts.Reset();
    ResetFalconHooks();
    HeavyTrainedTargets.Reset();
    bHeavyAttack=true;bHeavyTrainingPending=true;HeavyHits=HeavyKills=0;
    if(auto* Pendant=P->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginLocal(Shot,true,Off?Off->InstanceId:FString());
    bSwingPlayed=bImpactConfirmed=bWallHit=false;HitActors.Reset();HitStop=0.f;ImpactAge=-1.f;
    ResetStrike();StrikeAge=-1.f;CameraCarryAge=-1.f;StopRift();
    // The swing combo starts over after the heavy strike.
    NextStage=0;LastAttackEnd=-1.;
    const FName ReleaseClip=bFalconHeavy?(bDualHeavy?SwiftFalconHeavy::DualRelease:SwiftFalconHeavy::Release):
                                          (bDualHeavy?KukriHeavyRhythm::DualReleaseClip:KukriHeavyRhythm::ReleaseClip);
    SetClip(ReleaseClip,false,KukriHeavyRhythm::ReleaseEntryBlend);
    PreviousBlade=BladeFrame();bHavePreviousBlade=true;
    // The dual X: the left blade traces the same window with its own contact set.
    OffhandHitActors.Reset();if(bDualHeavy)PreviousOffhandBlade=OffhandBladeFrame();
}

void UKukriWeaponComponent::AdvanceHeavy(float Delta)
{
    auto* P=Pawn();
    const auto* Profile=KukriHeavyProfile(GetWorld());
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId){CancelAction();return;}
    if(bFalconHeavy)
    {
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Item,Profile);
        if(!SwiftFalconHeavy::Eligible(Item,Profile,bDualHeavy)||(bDualHeavy&&(!Off||Off->InstanceId!=HeavyOffhandWeapon)))
        {CancelAction();return;}
    }
    KukriRhythm::FSwing S=KukriRhythm::Swings[Stage];
    if(bDualHeavy)
    {
        // The dual X runs on its own authored phases and rift (KukriRhythm::DualHeavy*, two crossing crescents).
        S.SwingSound=KukriRhythm::DualHeavySwingSound;
        S.ContactStart=KukriRhythm::DualHeavyContactStart;S.ContactEnd=KukriRhythm::DualHeavyContactEnd;
    }
    const float Rate=bFalconHeavy?FalconReleaseRate:FMath::Max(.05f,LightningHaste::ActionSpeed(P));
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
        if(bFalconHeavy)
        {
            if(!Shot.MeleeDamagePhase&&Elapsed>=SwiftFalconHeavy::Hook-UE_KINDA_SMALL_NUMBER)
            {
                FlushPairedHeavyContacts(true);
                Shot.MeleeDamagePhase=OffhandShot.MeleeDamagePhase=1;
                HitActors.Reset();OffhandHitActors.Reset();
                bSwingPlayed=bImpactConfirmed=bWallHit=false;ResetStrike();ImpactAge=StrikeAge=-1.f;
            }
            const bool Pull=Shot.MeleeDamagePhase==1;
            S.SwingSound=Pull?SwiftFalconHeavy::PullTrail:SwiftFalconHeavy::ChopTrail;S.ContactStart=Pull?SwiftFalconHeavy::PullIn:SwiftFalconHeavy::ChopIn;
            S.ContactEnd=Pull?SwiftFalconHeavy::PullOut:SwiftFalconHeavy::ChopOut;
        }
        const float StageRate=bFalconHeavy ? SwiftFalconHeavy::PlaybackRate(Elapsed,Rate)
            : Rate*(bDualHeavy?KukriRhythm::SampleTempo(KukriRhythm::DualHeavyTempo,Elapsed):KukriRhythm::StageTempo(Stage,Elapsed));
        float Step=FMath::Min(Remaining*StageRate,1.f/120.f);
        const float StrikeAt=StrikeProfile().At;
        const float RiftAt=bFalconHeavy?S.SwingSound:bDualHeavy?KukriRhythm::DualHeavyRift.Start:KukriRhythm::Rifts[Stage].Start;
        for(const float Boundary:{S.SwingSound,S.ContactStart,S.ContactEnd,StrikeAt,RiftAt,
            bFalconHeavy?SwiftFalconHeavy::LowPoseAt:Length,bFalconHeavy?SwiftFalconHeavy::Hook:Length,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/StageRate);
        SamplePose(Elapsed);
        const FTransform Now=BladeFrame();
        if(!bSwingPlayed&&Elapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            if(bFalconHeavy&&Shot.MeleeDamagePhase==1)
            {
                if(P->HasAuthority())DrawFalconHooks();
                else ServerDrawFalconHooks(FalconChargeKey);
            }
            // A sharp whoosh on the cut with the item's own swing sound a little lower underneath.
            bSwingPlayed=true;
            const bool bWhoosh=StrikeProfile().bWhoosh&&StabWhooshSound;
            if(USoundBase* Cue=bWhoosh?StabWhooshSound.Get():SwingSound.Get())
                UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume*1.1f:.6f,S.SwingPitch);
            if(bWhoosh&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.5f,S.SwingPitch*.85f);
        }
        const bool bInContact=Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd;
        if(bHavePreviousBlade&&bInContact)TraceBlade(PreviousBlade,Now);
        if(bDualHeavy)
        {
            const FTransform NowLeft=OffhandBladeFrame();
            if(bInContact){Swap(HitActors,OffhandHitActors);TraceBlade(PreviousOffhandBlade,NowLeft,true);Swap(HitActors,OffhandHitActors);}
            PreviousOffhandBlade=NowLeft;
        }
        // Both blade sweeps run before committing the shared target receipt.
        FlushPairedHeavyContacts(Elapsed>=S.ContactEnd-UE_KINDA_SMALL_NUMBER);
        PreviousBlade=Now;bHavePreviousBlade=true;
        if(StrikeAt>0.f&&!bStrikeDone&&Elapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveStrike();
        if(!bRiftStarted&&Elapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bRiftStarted=true;StartRift();}
        if(bHeavyTrainingPending&&(!bFalconHeavy||Shot.MeleeDamagePhase==1)&&Elapsed>=S.ContactEnd-UE_KINDA_SMALL_NUMBER)FinishHeavy(true);
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            bHeavyAttack=false;
            FinishHeavy(true);
            HitActors.Reset();OffhandHitActors.Reset();bDualHeavy=bFalconHeavy=false;
            Stage=0;
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::CountHeavyVictim(AActor* Target,bool Killed)
{
    if(!HeavyTrainedTargets.Contains(Target)){HeavyTrainedTargets.Add(Target);++HeavyHits;}
    if(Killed)++HeavyKills;
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

bool UKukriWeaponComponent::IsDualHeavyCharging() const
{
    const auto* P=Pawn();
    return P&&(P->IsLocallyControlled()?(bHeavyCharging&&bDualHeavy):
        (P->HasAuthority()&&bServerHeavyCharging&&!ServerHeavyOffhandWeapon.IsEmpty()));
}

// ----------------------------------------------------------------------------- authority (remote owner)

void UKukriWeaponComponent::ServerSetKukriHeavyCharge_Implementation(const FString& Weapon,bool bCharging,bool bRelease,bool BothBlades,double ClientStartedAt)
{
    auto* P=Pawn();
    if(!P||!P->HasAuthority()||P->IsLocallyControlled()||!GetWorld())return;
    if(!bCharging)
    {
        if(Weapon!=ServerHeavyWeapon)return;
        if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET stop now=%.3f release=%d charging=%d started=%.3f expected=%s actual=%s"),GetWorld()->GetTimeSeconds(),bRelease,bServerHeavyCharging,ServerHeavyStartedAt,*ServerHeavyWeapon,*Weapon);
        // Only a real release after a long enough hold bills the release and opens the receipt; a cancel or a click does not.
        if(bRelease&&Weapon==ServerHeavyWeapon)PayServerHeavyRelease();
        if(!bRelease&&bServerFalconRelease){ResetFalconHooks();bServerFalconRelease=false;NetworkHeavyReleaseUntil=-1.;}
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    // Match the ordinary attack's bounded server-clock domain. Arrival-time
    // subtraction loses honest charge time when only the begin packet is delayed.
    // A duplicate begin cannot restart, backdate or replace an active charge.
    if(bServerHeavyCharging||!FMath::IsFinite(ClientStartedAt)||ClientStartedAt<=0.||
        ClientStartedAt>Now+.1||Now-ClientStartedAt>.9||ClientStartedAt<=ServerHeavyLastStartedAt)return;
    auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->ActiveKukriWeapon():nullptr;
    const auto* Off=BothBlades?ColdSteelMelee::PairedOneHandedWeapon(Item,Model):nullptr;
    if(!Item||Item->InstanceId!=Weapon||!IsKukri(*Item)||Model->ActiveProductionTool()||
        Model->MasteryProgress(TEXT("heavyStrike")).Level<1||(Model->Stamina()<=0.f&&Model->HeavyChargeStaminaPerSecond()>0.f)||
        (BothBlades&&!Off)||!Model->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Model,BothBlades))||UBoundCongregateCaptureComponent::IsCaptured(P))
    {
        if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET start_denied now=%.3f expected=%s actual=%s off=%s stamina=%.2f"),GetWorld()->GetTimeSeconds(),*Weapon,Item?*Item->InstanceId:TEXT("none"),Off?*Off->InstanceId:TEXT("none"),Model?Model->Stamina():-1.);
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        ClientCancelKukriHeavyCharge(Weapon);return;
    }
    // The shadow profile's stamina tick bills the charge at the owner's rate (FPSStaminaModel, IsHeavyCharging).
    if(!bServerHeavyCharging)
    {
        ServerHeavyStartedAt=FMath::Min(ClientStartedAt,Now);
        ServerHeavyLastStartedAt=ClientStartedAt;ServerHeavyReceivedAt=Now;
        ServerHeavyRequired=FMath::Max(.3,ColdSteelMelee::HeavyChargeSeconds(*Item,Model,BothBlades));
        ServerHeavyOffhandWeapon=Off?Off->InstanceId:FString();
        NetworkHeavyReleaseUntil=-1.;
    }
    bServerHeavyCharging=true;ServerHeavyWeapon=Weapon;
    if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET start now=%.3f started=%.3f required=%.3f pair=%s stamina=%.2f animation_count=%d release_clip_loaded=%d"),GetWorld()->GetTimeSeconds(),ServerHeavyStartedAt,ServerHeavyRequired,*ServerHeavyOffhandWeapon,Model->Stamina(),Animations.Num(),Animations.FindRef(BothBlades?KukriHeavyRhythm::DualReleaseClip:KukriHeavyRhythm::ReleaseClip)!=nullptr);
}

bool UKukriWeaponComponent::PayServerHeavyRelease()
{
    if(!GetWorld())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    // Network latency may hide a few frames of an honest full charge; the tolerance never lets a click through.
    if(!bServerHeavyCharging||ServerHeavyStartedAt<0.||Now-ServerHeavyStartedAt<FMath::Max(.1,ServerHeavyRequired-.15))
    {
        if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET release_denied charging=%d now=%.3f started=%.3f held=%.3f required=%.3f until=%.3f"),bServerHeavyCharging,Now,ServerHeavyStartedAt,Now-ServerHeavyStartedAt,ServerHeavyRequired,NetworkHeavyReleaseUntil);
        return false;
    }
    auto* Model=ColdSteelAuthority::ForPawn(Pawn());
    // FPSStaminaModel bills only after receipt. On a successful full charge,
    // also pay the portion of the required hold hidden by delayed delivery.
    // Do not bill network transit for a cancelled charge / ordinary click.
    const double UnbilledSeconds=ServerHeavyReceivedAt>=0.?FMath::Max(0.,
        FMath::Min(ServerHeavyRequired,Now-ServerHeavyStartedAt)-(Now-ServerHeavyReceivedAt)):0.;
    const double Catchup=Model?UnbilledSeconds*Model->HeavyChargeStaminaPerSecond():0.;
    bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
    const auto* Item=Model?Model->ActiveKukriWeapon():nullptr;
    if(!Item||Item->InstanceId!=ServerHeavyWeapon)return false;
    const bool BothBlades=!ServerHeavyOffhandWeapon.IsEmpty();
    const auto* Off=BothBlades?ColdSteelMelee::PairedOneHandedWeapon(Item,Model):nullptr;
    if(BothBlades&&(!Off||Off->InstanceId!=ServerHeavyOffhandWeapon)){ClientCancelKukriHeavyCharge(ServerHeavyWeapon);return false;}
    const double Cost=ColdSteelMelee::HeavyReleaseStamina(Item,Model,BothBlades)+Catchup;
    if(!Model->CanSpendStamina(Cost)){ClientCancelKukriHeavyCharge(ServerHeavyWeapon);return false;}
    Model->SpendStamina(Cost);
    ResetFalconHooks();
    bServerFalconRelease=SwiftFalconHeavy::Eligible(Item,Model,BothBlades);
    if(bServerFalconRelease)ServerFalconRate=SwiftFalconHeavy::ReleaseRate(*Item,Off,Model);
    ServerFalconReleasedAt=Now;
    NetworkHeavyReleaseUntil=Now+(bServerFalconRelease?SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::PullOut,ServerFalconRate)+.40:KukriHeavyRhythm::ReleaseWindowSeconds);
    if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET paid now=%.3f cost=%.2f catchup=%.3f pair=%s until=%.3f"),Now,Cost,Catchup,*ServerHeavyOffhandWeapon,NetworkHeavyReleaseUntil);
    if(++NetworkHeavyReleaseSerial==0)++NetworkHeavyReleaseSerial;
    if(auto* Pendant=GetOwner()->FindComponentByClass<UKukriRelentlessComponent>())Pendant->PrepareServerAttack(4);
    if(auto* Pendant=GetOwner()->FindComponentByClass<UKukriDecisiveComponent>())
    {
        const auto* Clip=Animations.FindRef(BothBlades?KukriHeavyRhythm::DualReleaseClip:KukriHeavyRhythm::ReleaseClip).Get();
        const float Length=Clip?Clip->GetPlayLength():(BothBlades?1.f:KukriRhythm::Swings[KukriRhythm::HeavyStage].Length);
        const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(Pawn()));float Seconds=0.f;
        for(float Time=0.f;Time<Length;Time+=1.f/120.f)
        {
            const float Tempo=BothBlades?KukriRhythm::SampleTempo(KukriRhythm::DualHeavyTempo,Time):KukriRhythm::StageTempo(KukriRhythm::HeavyStage,Time);
            Seconds+=FMath::Min(1.f/120.f,Length-Time)/(Rate*Tempo);
        }
        Pendant->BeginServer(4,ServerHeavyWeapon,ServerHeavyOffhandWeapon,true,bServerFalconRelease?SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::Length,ServerFalconRate):Seconds);
    }
    for(auto& Phase:NetworkHeavyTargets)for(auto& Targets:Phase)Targets.Reset();
    return true;
}

bool UKukriWeaponComponent::IsNetworkHeavyTargetNew(const FString& Weapon,AActor* Target,uint8 Phase) const
{
    if(!IsValid(Target)||Phase>1||!IsNetworkHeavyReleaseWindowOpen(Weapon))return false;
    if(Phase&&!bServerFalconRelease)return false;
    if(bServerFalconRelease)
    {
        const auto* Model=ColdSteelAuthority::ForPawn(Pawn());
        const auto* Main=Model?Model->ActiveKukriWeapon():nullptr;
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
        if(!Main||Main->InstanceId!=ServerHeavyWeapon||(Off?Off->InstanceId:FString())!=ServerHeavyOffhandWeapon||
            !SwiftFalconHeavy::Eligible(Main,Model,Off!=nullptr))return false;
        const double Age=GetWorld()->GetTimeSeconds()-ServerFalconReleasedAt;
        if(Phase&&Age<SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::PullIn,ServerFalconRate)-.16)return false;
        if(!Phase&&Age>SwiftFalconHeavy::ChopOut/ServerFalconRate+.35)return false;
    }
    return !NetworkHeavyTargets[Phase][Weapon==ServerHeavyWeapon?0:1].Contains(Target);
}

void UKukriWeaponComponent::RecordNetworkHeavyTarget(const FString& Weapon,AActor* Target,uint8 Phase)
{
    if(IsNetworkHeavyTargetNew(Weapon,Target,Phase))NetworkHeavyTargets[Phase][Weapon==ServerHeavyWeapon?0:1].Add(Target);
}

bool UKukriWeaponComponent::IsNetworkHeavyReleaseWindowOpen(const FString& Weapon) const
{
    const auto* World=GetWorld();
    return GetOwner()&&GetOwner()->HasAuthority()&&World&&World->GetTimeSeconds()<=NetworkHeavyReleaseUntil&&
        !Weapon.IsEmpty()&&(Weapon==ServerHeavyWeapon||Weapon==ServerHeavyOffhandWeapon);
}

bool UKukriWeaponComponent::ConsumeNetworkHeavyChargeForRelease(const FString& Weapon,uint8 Phase,double HitStamp)
{
    // The hit report travels on the player state and can overtake the release RPC: settle the release from the charge.
    if(!GetOwner()||!GetOwner()->HasAuthority()||Weapon.IsEmpty()||
        (Weapon!=ServerHeavyWeapon&&Weapon!=ServerHeavyOffhandWeapon))return false;
    if(Phase>1||!PayServerHeavyRelease())return false;
    if(bServerFalconRelease&&FMath::IsFinite(HitStamp)&&HitStamp>0.)
    {
        // A pull can be the first contact and arrive before the release RPC on the other actor channel.
        // Bound the inferred start to a fully paid charge and the receipt we just opened.
        const double Now=GetWorld()->GetTimeSeconds();
        const double FirstTouch=SwiftFalconHeavy::PlaybackSeconds(Phase?SwiftFalconHeavy::PullIn:SwiftFalconHeavy::ChopIn,ServerFalconRate);
        ServerFalconReleasedAt=FMath::Clamp(FMath::Min(HitStamp,Now)-FirstTouch,
            FMath::Min(Now,ServerHeavyLastStartedAt+ServerHeavyRequired),Now);
        NetworkHeavyReleaseUntil=ServerFalconReleasedAt+SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::PullOut,ServerFalconRate)+.40;
    }
    return true;
}

void UKukriWeaponComponent::TickServerHeavyCharge()
{
    auto* P=Pawn();
    auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->ActiveKukriWeapon():nullptr;
    const auto* Off=ServerHeavyOffhandWeapon.IsEmpty()?nullptr:ColdSteelMelee::PairedOneHandedWeapon(Item,Model);
    if(!P||!Item||Item->InstanceId!=ServerHeavyWeapon||(Model->Stamina()<=0.f&&Model->HeavyChargeStaminaPerSecond()>0.f)||UBoundCongregateCaptureComponent::IsCaptured(P)||
        (!ServerHeavyOffhandWeapon.IsEmpty()&&(!Off||Off->InstanceId!=ServerHeavyOffhandWeapon)))
    {
        if(HeavyNetworkTrace())UE_LOG(LogTemp,Display,TEXT("KUKRI_HEAVY_NET cancel now=%.3f expected=%s actual=%s off_expected=%s off_actual=%s stamina=%.2f"),GetWorld()->GetTimeSeconds(),*ServerHeavyWeapon,Item?*Item->InstanceId:TEXT("none"),*ServerHeavyOffhandWeapon,Off?*Off->InstanceId:TEXT("none"),Model?Model->Stamina():-1.);
        bServerHeavyCharging=false;ServerHeavyStartedAt=-1.;
        ClientCancelKukriHeavyCharge(ServerHeavyWeapon);
    }
}

void UKukriWeaponComponent::ClientCancelKukriHeavyCharge_Implementation(const FString& Weapon)
{
    const auto* P=Pawn();
    if(P&&P->IsLocallyControlled()&&!P->HasAuthority()&&Weapon==InstanceId&&bHeavyCharging)CancelHeavyCharge(false);
}
