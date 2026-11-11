#include "KukriWeaponComponent.h"
#include "../ModularSwordVisual.h"
#include "KukriDecisiveComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriWhirlwindRhythm.h"
#include "../Staff/StaffOffhandMeleeComponent.h"
#include "../MeleeWeaponStats.h"
#include "../RuneSwordHitQuery.h"
#include "../RuneSwordWhirlwindFeel.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Skills/WhirlwindWeapon.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "../../Movement/FPSTraversalComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "Sound/SoundBase.h"

// Whirlwind (active skill whirlwind, 2026-10-24) for the kukri: an original one-handed spin on the sword whirlwind's
// contract (RuneSwordWhirlwind.cpp, Docs/Skills/whirlwind-*.md).  WhirlwindStats damage / radius / stun / knockback,
// CommitWhirlwindCast pays the stamina and starts the cooldown once at entry (a remote client asks the PlayerState, which
// commits on the server and validates every 0x20 hit report), one hit per target per cast, TrainWhirlwind once.  The
// controller/world body turn +720 degrees on WhirlwindFeel's eased phase, and damage keeps that signed angular clock.
// The single-blade owner view turns oppositely through a presentation-only yaw correction. Movement / jump / dodge /
// slide / mouse look are locked (the character reads
// IsWhirlwindActive), 55 ms hit-stops within a 130 ms budget freeze turn, sweep, pose and camera together, and the
// background-only focus blur follows the turn speed.  Martial clock: Lightning Haste only.  The clip is the arms only
// (SourceAssets/Kukri20261020/fit_whirl.py -> author_kukri_whirlwind.py, "Whirlwind", phases 15/30 + 32/30 + 16/30 s):
// coil to the right hip, the blade held level out to the right with the edge leading through both turns, the free hand a
// guard fist at the lower left, a forward brake and the roll back to the stance.

namespace
{
const FName KukriWhirlwindClip(TEXT("Whirlwind"));
/** Author phases of the clip; the runtime maps its own ready / spin / recover seconds onto them. */
constexpr float KukriWhirlClipReady=15.f/30.f, KukriWhirlClipSpin=32.f/30.f, KukriWhirlClipRecover=16.f/30.f;
/** Swing cues on the turn phase: a full whoosh plus the stab layer as the blade leaves, a lighter one on the second turn. */
constexpr float KukriWhirlFirstPass=.035f, KukriWhirlSecondPass=.535f;
constexpr float KukriWhirlSweepRadius=32.f, KukriWhirlSweepDrop=45.f, KukriWhirlSweepBase=15.f;
constexpr int32 KukriWhirlFocusStencil=231;
/** Dual-wield whirlwind: the whirlwind clip raises the free left arm into the sightline, and a dual-wield off-hand
 *  weapon rides hand_l -- it filled the upper left of the frame.  The left arm is blended down to the natural hanging
 *  pose (KukriLeftRest.h) for the spin and back to the clip's own arm for the recovery. */
constexpr float KukriWhirlOffhandRestEase=.20f;

UColdSteelStatusModel* KukriWhirlwindProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}

float KukriWhirlwindPoseTime(float Time,const FWhirlwindTuning& T,float ClipLength)
{
    float Source;
    if(Time<T.ReadySeconds)Source=KukriWhirlClipReady*FMath::Clamp(Time/T.ReadySeconds,0.f,1.f);
    else if(Time<T.ReadySeconds+T.SpinSeconds)Source=KukriWhirlClipReady+KukriWhirlClipSpin*FMath::Clamp((Time-T.ReadySeconds)/T.SpinSeconds,0.f,1.f);
    else Source=KukriWhirlClipReady+KukriWhirlClipSpin+KukriWhirlClipRecover*FMath::Clamp((Time-T.ReadySeconds-T.SpinSeconds)/T.RecoverSeconds,0.f,1.f);
    return Source/(KukriWhirlClipReady+KukriWhirlClipSpin+KukriWhirlClipRecover)*ClipLength;
}
}

FString UKukriWeaponComponent::WhirlwindStatusText() const
{
    const auto* P=Pawn();
    const auto* Pair=P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    const bool WithStaff=Pair&&Pair->IsEquipped();
    if(!IsEquipped()&&!WithStaff)return TEXT("需要持刀");
    if(bWhirlwind)return TEXT("旋风");
    const auto* Profile=KukriWhirlwindProfile(GetWorld());
    if(!P||!Profile||!CanUse())return TEXT("暂不可用");
    if(Profile->WhirlwindCooldown()>0.f)return TEXT("冷却中");
    if(!Profile->CanSpendStamina(Profile->WhirlwindStats().StaminaCost))return TEXT("体力不足");
    if(IsBusy())return TEXT("动作中");
    if(P->IsCastBlockingLeftHandAction()||P->IsDodging()||P->IsSliding()||P->IsSpellGestureBlocking())return TEXT("动作占用");
    if(!Camera||(WithStaff?!Pair->CanWhirlwind():(!Viewmodel||!Animations.FindRef(KukriWhirlwindClip))))return TEXT("动作未就绪");
    return FString();
}

bool UKukriWeaponComponent::BeginWhirlwind()
{
    auto* P=Pawn();
    if(!P||UBoundCongregateCaptureComponent::IsCaptured(P)||!WhirlwindStatusText().IsEmpty()||!P->GetController())return false;
    auto* Profile=KukriWhirlwindProfile(GetWorld());
    const auto* Item=WhirlwindWeapon::Resolve(Profile);
    auto* Pair=P->FindComponentByClass<UStaffOffhandMeleeComponent>();
    if(!Pair||!Pair->IsEquipped())Pair=nullptr;
    if(!Item||(Pair?!WhirlwindWeapon::IsStaffBlade(Profile,Item):Item->InstanceId!=InstanceId)||
        Profile->ActiveProductionTool()||!ColdSteelInventory::IsMeleeWeapon(*Item))return false;
    const FColdSteelItem CastItem=*Item;
    // Equipment, clip and assets are checked above; the cost and cooldown are committed once, here.
    const FWhirlwindCast Cast=Profile->WhirlwindStats();
    if(P->GetNetMode()==NM_Client)
    {
        auto* PS=P->GetPlayerState<AColdSteelPlayerState>();
        if(!PS||!PS->RequestSwordWhirlwind(false,P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D()))return false;
    }
    else if(!Profile->CommitWhirlwindCast(Cast,false))return false;
    WhirlwindCast=Cast;WhirlwindTuning=KukriWhirlwindRhythm::Resolve(Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind);
    const bool Modular=ColdSteelModularSword::Supports(CastItem);
    WhirlwindWallBase=Modular?ColdSteelModularSword::BladePoint(CastItem,false):KukriRhythm::BladeRoot;
    WhirlwindWallTip=Modular?ColdSteelModularSword::BladePoint(CastItem,true):KukriRhythm::BladeTip;
    LastSkillWallBeat=INDEX_NONE;bHavePreviousBlade=false;
    bStaffOffhandWhirlwind=Pair!=nullptr;
    // A left-hand blade (beside the staff, or the lone off-hand blade's mirrored clip) spins the other way.
    if(bStaffOffhandWhirlwind||bLoneOffhand)WhirlwindTuning.TurnDegrees=-FMath::Abs(WhirlwindTuning.TurnDegrees);
    const auto Stats=ColdSteelMelee::Evaluate(CastItem,Profile);
    WhirlwindReaction=float(Stats.Modifiers.HitReaction);
    Shot=ColdSteelSkills::Snapshot(P,&CastItem);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.bMelee=true;Shot.bMeleeStrike=true;
    Shot.AttackForm=KukriRhythm::Form;
    Shot.AttackMeta=0x20;           // whirlwind: the server recomputes from WhirlwindStats and accepts exactly 0x20
    bWhirlwind=bWhirlwindTrainingPending=true;bWhirlwindSwingPlayed=false;
    if(auto* Pendant=P->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginLocal(Shot,true);
    WhirlwindHits=WhirlwindKills=0;WhirlwindPause=WhirlwindPauseSpent=0.f;
    WhirlwindImpactAge=1.f;WhirlwindImpactStrength=1.f;
    WhirlwindYaw=P->GetControlRotation().Yaw;
    HitActors.Reset();HitStop=0.f;ImpactAge=-1.f;
    ResetStrike();StrikeAge=-1.f;CameraCarryAge=-1.f;StopRift();
    // The swing combo starts over after the whirlwind.
    NextStage=0;LastAttackEnd=-1.;
    // Stop locomotion like AFPSGAMECharacter::StopMovementForMeleeSkill (private), keeping gravity if cast in the air;
    // sprint drops by itself while IsMeleeSkillMovementLocked reads the active whirlwind.
    P->ConsumeMovementInputVector();
    P->StopJumping();
    if(auto* Traversal=P->FindComponentByClass<UFPSTraversalComponent>())Traversal->SetJumpHeld(false);
    if(auto* Movement=P->GetCharacterMovement())
    {
        const double FallingSpeed=Movement->IsFalling()?Movement->Velocity.Z:0.;
        Movement->StopMovementImmediately();
        Movement->Velocity.Z=FallingSpeed;
        Movement->UpdateComponentVelocity();
    }
    // The 0.11 s entry blend from the displayed pose runs inside the ready phase.
    if(Pair)
    {
        SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(CastItem,TEXT("swing_sound")));
        HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(CastItem,TEXT("hit_sound")));
        StabWhooshSound=LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
        StabThudSounds.Reset();
        for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))StabThudSounds.Add(Thud);
        Elapsed=0.f;Pair->BeginWhirlwindPresentation();
        Pair->SetWhirlwindPose(0.f,0.f,WhirlwindTuning.ReadySeconds,WhirlwindTuning.SpinSeconds,WhirlwindTuning.RecoverSeconds);
    }
    else SetClip(KukriWhirlwindClip,false,KukriRhythm::EntryBlendSeconds);
    BeginWhirlwindFocus();
    return true;
}

void UKukriWeaponComponent::FinishWhirlwindTraining()
{
    if(!bWhirlwindTrainingPending)return;
    bWhirlwindTrainingPending=false;
    // Remote casts train from the hits the server accepted.
    if(GetNetMode()==NM_Client)return;
    if(auto* Profile=KukriWhirlwindProfile(GetWorld()))Profile->TrainWhirlwind(WhirlwindHits,WhirlwindKills);
}

void UKukriWeaponComponent::FinishWhirlwind(bool Interrupted)
{
    if(!bWhirlwind)return;
    const bool RefreshStaffCamera=bStaffOffhandWhirlwind&&Interrupted;
    if(bStaffOffhandWhirlwind)
    {
        // Keep the displayed heading when interrupted between full turns, before removing its camera correction.
        if(Interrupted)if(auto* P=Pawn())if(auto* Controller=P->GetController())
        {
            FRotator Aim=Controller->GetControlRotation();Aim.Yaw+=GetWhirlwindFirstPersonYawOffset();
            Controller->SetControlRotation(Aim);P->FaceRotation(Aim,0.f);
        }
        if(auto* Pair=GetOwner()->FindComponentByClass<UStaffOffhandMeleeComponent>())Pair->EndWhirlwindPresentation(Interrupted);
        StopSkillRift();
    }
    // Clear first: saving the training can refresh the equipment and re-enter the cancellation.
    bWhirlwind=false;bStaffOffhandWhirlwind=false;
    if(GetNetMode()==NM_Client)
        if(auto* P=Pawn())if(auto* PS=P->GetPlayerState<AColdSteelPlayerState>())PS->FinishSwordWhirlwind();
    EndWhirlwindFocus();
    // The left arm returns to the clip's own pose on the next frame anyway; clear the override so no stale weight is left.
    if(Viewmodel)Viewmodel->SetLeftArmRest(0.f,.12f);
    WhirlwindPause=0.f;WhirlwindImpactAge=1.f;
    FinishWhirlwindTraining();
    HitActors.Reset();
    if(Viewmodel&&IsEquipped()&&Animations.Num())SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
    // Cancellation can happen in PostPhysics, after the character's camera tick.
    // FaceRotation above moves the attached camera too; remove its old spin-relative
    // rotation now, before PlayerCameraManager caches this frame's view.
    if(RefreshStaffCamera)if(auto* P=Pawn();P&&!P->IsActorBeingDestroyed())P->RefreshQuickCombatCamera();
}

void UKukriWeaponComponent::TickWhirlwind(float Delta)
{
    auto* P=Pawn();
    AController* Controller=P?P->GetController():nullptr;
    auto* Pair=bStaffOffhandWhirlwind&&P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    const UAnimSequence* Clip=Pair?Pair->WhirlwindAnimation():CurrentAnimation.Get();
    if(!Clip||!Controller||(bStaffOffhandWhirlwind&&(!Pair||!Pair->OwnsLeftHand()))||
        P->IsDodging()||P->IsTraversing()){FinishWhirlwind();return;}
    const auto& T=WhirlwindTuning;
    WhirlwindImpactAge+=Delta;
    const float Paused=FMath::Min(Delta,WhirlwindPause);
    WhirlwindPause-=Paused;Delta-=Paused;
    // The hit-stop holds the contact resistance, the pose, the turn and the sweep on the same paused clock.
    WhirlwindImpactAge=FMath::Max(0.f,WhirlwindImpactAge-Paused);
    if(Delta<=0.f){P->RefreshQuickCombatCamera();UpdateWhirlwindFocus(0.f);return;}
    const float End=T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds;
    float Remaining=FMath::Min(Delta*FMath::Max(.05f,LightningHaste::ActionSpeed(P)),End-Elapsed);
    while(Remaining>UE_SMALL_NUMBER&&bWhirlwind)
    {
        // 120 Hz substeps; a confirmed hit ends the frame on its own sample (the pause starts there).
        const float Step=FMath::Min(Remaining,1.f/120.f),Before=Elapsed;
        Elapsed=FMath::Min(End,Elapsed+Step);Remaining-=Step;
        // The ring of space distortion starts with the spin, from the held blade (KukriSkillRift.cpp).
        if(Before<T.ReadySeconds&&Elapsed>=T.ReadySeconds)StartWhirlwindRift();
        const float BeforePhase=WhirlwindFeel::Phase(Before,T),Phase=WhirlwindFeel::Phase(Elapsed,T);
        FRotator Aim=Controller->GetControlRotation();
        Aim.Yaw=WhirlwindYaw+T.TurnDegrees*Phase;
        Controller->SetControlRotation(Aim);
        if(!bWhirlwindSwingPlayed&&Phase>=KukriWhirlFirstPass)
        {
            bWhirlwindSwingPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.95f,1.03f);
            if(StabWhooshSound)UGameplayStatics::PlaySound2D(this,StabWhooshSound,.8f,1.05f);
        }
        if(BeforePhase<KukriWhirlSecondPass&&Phase>=KukriWhirlSecondPass&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.86f,1.18f);
        if(Phase>BeforePhase)SweepWhirlwind(T.TurnDegrees*BeforePhase,T.TurnDegrees*Phase);
        if(Elapsed>=T.ReadySeconds+T.SpinSeconds)FinishWhirlwindTraining();
        if(WhirlwindPause>0.f||Elapsed>=End-UE_SMALL_NUMBER)break;
    }
    if(!bWhirlwind)return;
    // The controller already faced the pawn before this PostPhysics tick turned it: publish the final heading on the body,
    // then compose the camera (with any contact accent) before the arms are sampled for this frame.
    P->FaceRotation(Controller->GetControlRotation(),0.f);
    const float ClipTime=KukriWhirlwindPoseTime(Elapsed,T,Clip->GetPlayLength());
    if(Pair)Pair->SetWhirlwindPose(Elapsed,ClipTime,T.ReadySeconds,T.SpinSeconds,T.RecoverSeconds);
    P->RefreshQuickCombatCamera();
    if(!Pair)
    {
        // Dual hatchets: drop the off-hand arm to its natural hanging pose, then restore the clip's own arm before the
        // recovery ends (see KukriWhirlOffhandRestEase).  Set before the sample: the mesh finalizes its pose inside it.
        if(Viewmodel)
        {
            // The off-hand arm hangs through the whole whirlwind; it is released when the cast ends (FinishWhirlwind),
            // and the next locomotion clip brings the idle arm back.
            Viewmodel->SetLeftArmRest(IsDual()&&bOffhandHatchet?1.f:0.f,KukriWhirlOffhandRestEase);
        }
        SamplePose(ClipTime);
        TrackWhirlwindWall(BladeFrame());
    }
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Pair&&(!Body||!Body->IsThirdPersonViewEnabled()))UpdateWhirlwindRiftPose(BladeFrame());
    UpdateWhirlwindFocus(WhirlwindPause>0.f?0.f:T.MotionBlur*WhirlwindFeel::Speed(Elapsed,T));
    if(Elapsed>=End-UE_SMALL_NUMBER)FinishWhirlwind(false);
}

void UKukriWeaponComponent::PublishStaffWhirlwindBlade(const FTransform& DisplayedBlade)
{
    if(!bWhirlwind||!bStaffOffhandWhirlwind)return;
    TrackWhirlwindWall(DisplayedBlade);
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->IsThirdPersonViewEnabled())UpdateWhirlwindRiftPose(DisplayedBlade);
}

void UKukriWeaponComponent::TrackWhirlwindWall(const FTransform& Pose)
{
    const auto& T=WhirlwindTuning;
    if(bHavePreviousBlade&&Elapsed>=T.ReadySeconds&&Elapsed<=T.ReadySeconds+T.SpinSeconds)
    {
        const float Degrees=FMath::Abs(T.TurnDegrees*WhirlwindFeel::Phase(Elapsed,T));
        SampleSkillBladeWall(PreviousBlade,Pose,WhirlwindWallBase,WhirlwindWallTip,FMath::FloorToInt(Degrees/360.f));
    }
    PreviousBlade=Pose;bHavePreviousBlade=true;
}

void UKukriWeaponComponent::SweepWhirlwind(float FromDegrees,float ToDegrees)
{
    const float FirstTurn=WhirlwindTuning.TurnDegrees<0.f?-360.f:360.f;
    if(FMath::Abs(FromDegrees)<360.f&&FMath::Abs(ToDegrees)>360.f)
    {SweepWhirlwind(FromDegrees,FirstTurn);SweepWhirlwind(FirstTurn,ToDegrees);return;}
    auto* P=Pawn();
    UWorld* World=GetWorld();
    if(!P||!World)return;
    // The blade line on the right of the view (yaw + 90) from the hips out to the skill radius, on the signed turn angle.
    const FVector Origin=P->GetMeleeAimTransform().GetLocation()-FVector(0.f,0.f,KukriWhirlSweepDrop);
    auto Sample=[&](float Degrees)
    {
        FRuneSwordBladeSample S;
        S.Origin=Origin;S.Forward=FRotator(0.f,WhirlwindYaw+(bStaffOffhandWhirlwind?-90.f:90.f)+Degrees,0.f).Vector();
        S.Base=Origin+S.Forward*KukriWhirlSweepBase;S.Tip=Origin+S.Forward*WhirlwindCast.RadiusCM;
        return S;
    };
    FRuneSwordTraceSettings Settings;Settings.Radius=KukriWhirlSweepRadius;Settings.bCleavePawns=true;Settings.bAreaDamage=true;
    const auto Hits=RuneSwordCombat::Query(World,P,Sample(FromDegrees),Sample(ToDegrees),WhirlwindCast.RadiusCM,HitActors,Settings);
    auto* Profile=KukriWhirlwindProfile(World);
    int32 Confirmed=0;
    bool AnyKilled=false;
    FVector ImpactPoint=FVector::ZeroVector;
    for(const FHitResult& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!IsValid(Target)||Target->ActorHasTag(TEXT("Friendly"))||HitActors.Contains(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(Combat&&Combat->IsDead())continue;
        HitActors.Add(Target);
        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(P,Target);
        auto HitShot=Shot;
        HitShot.MeleeDamagePhase=FMath::Abs(FromDegrees)>=360.f?1:0;
        if(Eligible&&WhirlwindHits==1&&Profile)HitShot.ExtraMasteryExperience=Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience;
        const FVector Direction=(Target->GetActorLocation()-P->GetActorLocation()).GetSafeNormal2D();
        FWeaponDamageResult Receipt;
        auto Apply=[&]{return ColdSteelSkills::ApplyHit(P,Hit,WhirlwindCast.Damage,Direction,HitShot,&Receipt);};
        // The whole spin is the edge: blade toughness conversion.
        const MonsterToughness::FScopedForm FormScope(EMonsterAttackForm::Blade);
        const float Applied=Combat?Combat->ApplyHitWithReactionScale(WhirlwindReaction,Apply):Apply();
        const bool bKilled=Combat&&Combat->IsDead();
        if(Applied<=0.f&&!bKilled)continue;
        ++Confirmed;AnyKilled|=bKilled;ImpactPoint+=Hit.ImpactPoint;
        if(Eligible){++WhirlwindHits;if(bKilled)++WhirlwindKills;}
        if(Combat&&!bKilled)Combat->ReceiveStun(P,WhirlwindCast.StunSeconds,WhirlwindCast.KnockbackCM);
        P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
        if(Combat&&P->HasAuthority())SpawnContactFX(Hit,false);
    }
    if(!Confirmed)return;
    const float Hold=FMath::Min(WhirlwindTuning.HitStopSeconds,WhirlwindTuning.HitStopBudget-WhirlwindPauseSpent);
    WhirlwindPause=FMath::Max(0.f,Hold);WhirlwindPauseSpent+=WhirlwindPause;
    // Sound and recoil stay available after the hit-stop budget is spent; close contacts merge into one accent.
    const float Strength=1.f+.12f*FMath::Min(Confirmed-1,3)+(AnyKilled?.16f:0.f);
    if(WhirlwindImpactAge>=.065f)
    {
        WhirlwindImpactAge=0.f;WhirlwindImpactStrength=Strength;
        const FVector At=ImpactPoint/Confirmed;
        if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,At,1.f,.86f);
        if(StabThudSounds.Num())
            UGameplayStatics::PlaySoundAtLocation(this,StabThudSounds[FMath::RandRange(0,StabThudSounds.Num()-1)],At,
                KukriRhythm::StabThudVolume*1.1f,KukriRhythm::StabThudPitch);
    }
    else WhirlwindImpactStrength=FMath::Max(WhirlwindImpactStrength,Strength);
}

float UKukriWeaponComponent::GetWhirlwindFirstPersonYawOffset() const
{
    if(!bWhirlwind||(!IsEquipped()&&!bStaffOffhandWhirlwind))return 0.f;
    const auto* P=Pawn();
    const auto* Body=P?P->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(Body&&Body->IsThirdPersonViewEnabled())return 0.f;
    // Controller and world body keep +theta. The camera and its attached arms
    // receive -2 theta, presenting -theta on the same paused action clock.
    // (2026-11-03: dual wield too -- it used to skip the correction and presented +theta, i.e. the wrong way in
    // first person.  The controller, the sweep and the third-person body are untouched.)
    return FRotator::NormalizeAxis(-2.f*WhirlwindTuning.TurnDegrees*WhirlwindFeel::Phase(Elapsed,WhirlwindTuning));
}

void UKukriWeaponComponent::GetWhirlwindCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    // Lean and contact resistance follow the single-blade owner-view turn.
    // The full yaw correction is composed separately, outside shake scaling.
    FWhirlwindTuning ViewTuning=WhirlwindTuning;
    const auto* P=Pawn();
    const auto* Body=P?P->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    // First person (single or dual) presents -theta; third person keeps the world turn.  Dual used to skip this, so its
    // lean and roll read against the sweep.
    if(!Body||!Body->IsThirdPersonViewEnabled())ViewTuning.TurnDegrees=-ViewTuning.TurnDegrees;
    WhirlwindFeel::Camera(Elapsed,ViewTuning,WhirlwindImpactAge,
        WhirlwindImpactStrength*KukriWhirlwindRhythm::ContactKickScale,Location,Rotation);
    FovDelta=0.f;
}

void UKukriWeaponComponent::BeginWhirlwindFocus()
{
    // Background-only blur (the sword and hammer whirlwind material): the arms and the knife write stencil 231, engine
    // motion blur is off for the cast.  No temporal-material swap (sword only).
    if(!Camera||!Viewmodel)return;
    bWhirlwindFocusActive=true;
    auto& PP=Camera->PostProcessSettings;
    WhirlwindSavedBlur=PP.MotionBlurAmount;bWhirlwindSavedBlurOverride=PP.bOverride_MotionBlurAmount;
    PP.bOverride_MotionBlurAmount=true;PP.MotionBlurAmount=0.f;
    if(!WhirlwindFocus)
        if(auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus")).TryLoad()))
            WhirlwindFocus=UMaterialInstanceDynamic::Create(Material,this);
    TArray<USceneComponent*> Parts;
    if(bStaffOffhandWhirlwind)Camera->GetChildrenComponents(true,Parts);
    else {Viewmodel->GetChildrenComponents(true,Parts);Parts.Add(Viewmodel);}
    for(auto* Part:Parts)
        if(auto* Primitive=Cast<UPrimitiveComponent>(Part))
        {
            WhirlwindDepth.Add({Primitive,bool(Primitive->bRenderCustomDepth),Primitive->CustomDepthStencilValue,uint8(Primitive->CustomDepthStencilWriteMask)});
            Primitive->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
            Primitive->SetCustomDepthStencilValue(KukriWhirlFocusStencil);Primitive->SetRenderCustomDepth(true);
        }
}

void UKukriWeaponComponent::UpdateWhirlwindFocus(float Strength)
{
    if(!Camera||!WhirlwindFocus||!bWhirlwindFocusActive)return;
    WhirlwindFocus->SetScalarParameterValue(TEXT("Strength"),Strength);
    const auto* Resource=GetWorld()&&GetWorld()->Scene?WhirlwindFocus->GetMaterialResource(GetWorld()->Scene->GetShaderPlatform()):nullptr;
    // Only with a complete shader map: the engine's fallback post-process material draws a coloured screen border.
    if(Strength>UE_SMALL_NUMBER&&Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete())
        Camera->PostProcessSettings.AddBlendable(WhirlwindFocus,1.f);
    else Camera->PostProcessSettings.RemoveBlendable(WhirlwindFocus);
}

void UKukriWeaponComponent::EndWhirlwindFocus()
{
    if(!bWhirlwindFocusActive)return;
    bWhirlwindFocusActive=false;
    if(Camera)
    {
        if(WhirlwindFocus)Camera->PostProcessSettings.RemoveBlendable(WhirlwindFocus);
        Camera->PostProcessSettings.MotionBlurAmount=WhirlwindSavedBlur;
        Camera->PostProcessSettings.bOverride_MotionBlurAmount=bWhirlwindSavedBlurOverride;
    }
    for(const auto& Saved:WhirlwindDepth)
        if(auto* Part=Saved.Part.Get())
        {
            Part->SetRenderCustomDepth(Saved.bEnabled);Part->SetCustomDepthStencilValue(Saved.Stencil);
            Part->SetCustomDepthStencilWriteMask(ERendererStencilMask(Saved.WriteMask));
        }
    WhirlwindDepth.Reset();
}
