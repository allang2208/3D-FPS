#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "../MeleeWeaponStats.h"
#include "../RuneSwordUppercutMotion.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Skills/SwordUppercutTuning.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Uppercut (active skill swordUppercut, 2026-10-23) for the kukri: the reference slide uppercut (BV1CeYUeSE7b 106.2-107.3 s,
// 近战动作（滑铲）#9 上撩; SourceAssets/Kukri20261020/fit_upper.py -> author_kukri_upper.py, clip "Uppercut", 38/30 s).
// Same skill contract as the two-handed sword and hammer uppercuts: CommitSwordUppercutRelease pays the stamina and starts
// the cooldown at the release, the damage is the uppercut multiplier of the heavy formula (SwordUppercut::HeavyDamageScale),
// AttackMeta SwordUppercut::AttackMeta (the shared forced launch in ColdSteelSkills::ApplyHit), the reach grows with the
// skill level, one training tier per cast.  The swing runs as stage KukriRhythm::UppercutStage on the combo's tables
// (impact moment, hit-stop, rift, camera) on a martial clock: Lightning Haste only, KukriRhythm::UpperTempo on top.
// The reference slides forward; the cut carries a forward stride (LungeCM) through the shared melee-lunge movement.

namespace
{
const FName KukriUppercutClip(TEXT("Uppercut"));
constexpr float LungeStart=.24f, LungeEnd=.37f, LungeCM=120.f;   // author s; <= the sword uppercut's 150 cm server budget

UColdSteelStatusModel* KukriUppercutProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
}

FString UKukriWeaponComponent::UppercutStatusText() const
{
    if(!IsEquipped())return TEXT("需要持刀");
    if(bUppercut)return TEXT("上挑中");
    const auto* P=Pawn();
    const auto* Profile=KukriUppercutProfile(GetWorld());
    if(!P||!Profile||!CanUse())return TEXT("暂不可用");
    if(Profile->SwordUppercutCooldown()>0.f)return TEXT("冷却中");
    if(!Profile->CanSpendStamina(Profile->SwordUppercutStaminaCost()))return TEXT("体力不足");
    if(IsBusy())return TEXT("动作中");
    if(P->IsCastBlockingLeftHandAction()||P->IsDodging()||P->IsSpellGestureBlocking())return TEXT("动作占用");
    if(!Viewmodel||!Animations.FindRef(KukriUppercutClip))return TEXT("动作未就绪");
    return FString();
}

bool UKukriWeaponComponent::BeginUppercut()
{
    auto* P=Pawn();
    if(!P||UBoundCongregateCaptureComponent::IsCaptured(P)||!UppercutStatusText().IsEmpty())return false;
    auto* Profile=KukriUppercutProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||Item->InstanceId!=InstanceId||Profile->ActiveProductionTool())return false;
    // Snapshot at the start: damage, reach and skill tier stay fixed for this cast (the cost is paid at the release).
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    const auto Effect=Profile->MasteryEffect(TEXT("swordUppercut"));
    SwingDamage=float(Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers));
    Reach=float((Stats.BaseReach>0.?Stats.BaseReach:KukriRhythm::DefaultReachCM)*Effect.UppercutReachMultiplier*Stats.Modifiers.MartialRange);
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.bMelee=true;Shot.bMeleeStrike=true;
    Shot.AttackForm=KukriRhythm::Form;
    Shot.AttackMeta=SwordUppercut::AttackMeta;     // heavy formula family + the shared forced launch
    Shot.ToughnessDamageMultiplier*=float(Stats.Modifiers.HeavyToughness);
    Stage=KukriRhythm::UppercutStage;
    bUppercut=true;bUppercutReleased=bUppercutTrainingPending=false;bUppercutLungeStarted=bUppercutLungeBlocked=false;
    UppercutDirection=FVector::ZeroVector;
    bSwingPlayed=bImpactConfirmed=bWallHit=false;HitActors.Reset();HitStop=0.f;ImpactAge=-1.f;
    ResetStrike();StrikeAge=-1.f;CameraCarryAge=-1.f;StopRift();
    // The swing combo starts over after the uppercut.
    NextStage=0;LastAttackEnd=-1.;
    SetClip(KukriUppercutClip,false,KukriRhythm::EntryBlendSeconds);
    PreviousBlade=BladeFrame();bHavePreviousBlade=true;
    return true;
}

void UKukriWeaponComponent::AdvanceUppercutLunge(float From,float To)
{
    auto* P=Pawn();
    if(!P||!P->IsLocallyControlled()||bUppercutLungeBlocked||To<=LungeStart||From>=LungeEnd)return;
    const float Distance=LungeCM*(FMath::SmoothStep(LungeStart,LungeEnd,To)-FMath::SmoothStep(LungeStart,LungeEnd,From));
    if(Distance<=0.f)return;
    auto* Move=Cast<UFPSCharacterMovementComponent>(P->GetCharacterMovement());
    if(!Move||!Move->IsMovingOnGround()||P->IsSliding()||P->IsTraversing()||Move->IsDodging()){bUppercutLungeBlocked=true;return;}
    if(!bUppercutLungeStarted)
    {
        bUppercutLungeStarted=true;
        UppercutDirection=P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Uppercut,UppercutDirection);
    }
    if(Move->IsMeleeLungeRejected()){bUppercutLungeBlocked=true;return;}
    const FVector Moved=Move->ApplyMeleeLungeStep(UppercutDirection,Distance);
    const float Actual=FMath::Max(0.f,float(FVector::DotProduct(Moved,UppercutDirection)));
    Move->RecordMeleeLungeStep(Actual);
    // The rift crescent rides along with the stride (it is frozen in world space at its start).
    if(bRiftActive)RiftOrigin.AddToTranslation(Moved);
    if(Actual+.01f<Distance)bUppercutLungeBlocked=true;
}

void UKukriWeaponComponent::AdvanceUppercut(float Delta)
{
    auto* P=Pawn();
    auto* Profile=KukriUppercutProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!P||!Item||Item->InstanceId!=InstanceId){CancelAction();return;}
    const auto& S=KukriRhythm::Swings[Stage];
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bUppercut&&++Guard<64)
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
        // Release: the skill's stamina and cooldown are committed when the cut starts (as for the sword); a refused
        // payment (cooldown, stamina, a server rejection) cancels the cast before anything lands.
        if(!bUppercutReleased&&Elapsed>=S.ContactStart-UE_KINDA_SMALL_NUMBER)
        {
            if(!Profile->CommitSwordUppercutRelease()){CancelAction();return;}
            if(!bUppercut)return;
            bUppercutReleased=bUppercutTrainingPending=true;
        }
        AdvanceUppercutLunge(Before,Elapsed);
        SamplePose(Elapsed);
        const FTransform Now=BladeFrame();
        if(!bSwingPlayed&&Elapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bSwingPlayed=true;
            const bool bWhoosh=KukriRhythm::Strikes[Stage].bWhoosh&&StabWhooshSound;
            if(USoundBase* Cue=bWhoosh?StabWhooshSound.Get():SwingSound.Get())
                UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume:.6f,S.SwingPitch);
            if(bWhoosh&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.45f,S.SwingPitch*.9f);
        }
        if(bUppercutReleased&&bHavePreviousBlade&&Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd)
            TraceBlade(PreviousBlade,Now);
        PreviousBlade=Now;bHavePreviousBlade=true;
        if(StrikeAt>0.f&&!bStrikeDone&&Elapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveStrike();
        if(!bRiftStarted&&Elapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bRiftStarted=true;StartRift();}
        if(bUppercutTrainingPending&&Elapsed>=S.ContactEnd-UE_KINDA_SMALL_NUMBER)FinishUppercut(true);
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            bUppercut=false;
            FinishUppercut(true);
            HitActors.Reset();
            Stage=0;
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::FinishUppercut(bool bTrain)
{
    // One training tier per released cast (use / hit / kill), also when it is cancelled after the release.
    if(!bUppercutTrainingPending)return;
    bUppercutTrainingPending=false;
    if(!bTrain)return;
    auto* P=Pawn();
    auto* Profile=KukriUppercutProfile(GetWorld());
    if(!P||!Profile)return;
    if(GetNetMode()==NM_Client)
    {
        // The server counted the reported hits of this release (ServerSwordUppercut / SettleSwordUppercut).
        if(auto* PS=P->GetPlayerState<AColdSteelPlayerState>())PS->FinishSwordUppercut();
        return;
    }
    int32 Hits=0,Kills=0;
    for(const auto& Actor:HitActors)
    {
        AActor* Target=Actor.Get();
        const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||!ColdSteelSkills::IsMasteryTrainingTarget(P,Target))continue;
        Hits=1;if(Combat->IsDead())Kills=1;
    }
    Profile->TrainSwordUppercut(Hits,Kills);
}
