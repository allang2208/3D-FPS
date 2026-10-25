#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "../MeleeWeaponStats.h"
#include "../RuneSwordHitQuery.h"
#include "../RuneSwordWhirlwindFeel.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
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
// controller turns TurnDegrees (two turns to the left) on WhirlwindFeel's eased phase, the damage sweeps the right side of
// the view on the same signed angle, movement / jump / dodge / slide / mouse look are locked (the character reads
// IsWhirlwindActive), 45 ms hit-stops within a 135 ms budget freeze turn, sweep, pose and camera together, and the
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
    if(!IsEquipped())return TEXT("需要持刀");
    if(bWhirlwind)return TEXT("旋风");
    const auto* P=Pawn();
    const auto* Profile=KukriWhirlwindProfile(GetWorld());
    if(!P||!Profile||!CanUse())return TEXT("暂不可用");
    if(Profile->WhirlwindCooldown()>0.f)return TEXT("冷却中");
    if(!Profile->CanSpendStamina(Profile->WhirlwindStats().StaminaCost))return TEXT("体力不足");
    if(IsBusy())return TEXT("动作中");
    if(P->IsCastBlockingLeftHandAction()||P->IsDodging()||P->IsSliding()||P->IsSpellGestureBlocking())return TEXT("动作占用");
    if(!Viewmodel||!Camera||!Animations.FindRef(KukriWhirlwindClip))return TEXT("动作未就绪");
    return FString();
}

bool UKukriWeaponComponent::BeginWhirlwind()
{
    auto* P=Pawn();
    if(!P||UBoundCongregateCaptureComponent::IsCaptured(P)||!WhirlwindStatusText().IsEmpty()||!P->GetController())return false;
    auto* Profile=KukriWhirlwindProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||Item->InstanceId!=InstanceId||Profile->ActiveProductionTool()||!ColdSteelInventory::IsMeleeWeapon(*Item))return false;
    // Equipment, clip and assets are checked above; the cost and cooldown are committed once, here.
    const FWhirlwindCast Cast=Profile->WhirlwindStats();
    if(P->GetNetMode()==NM_Client)
    {
        auto* PS=P->GetPlayerState<AColdSteelPlayerState>();
        if(!PS||!PS->RequestSwordWhirlwind(false,P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D()))return false;
    }
    else if(!Profile->CommitWhirlwindCast(Cast,false))return false;
    WhirlwindCast=Cast;WhirlwindTuning=Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    WhirlwindReaction=float(Stats.Modifiers.HitReaction);
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.bMelee=true;Shot.bMeleeStrike=true;
    Shot.AttackForm=KukriRhythm::Form;
    Shot.AttackMeta=0x20;           // whirlwind: the server recomputes from WhirlwindStats and accepts exactly 0x20
    bWhirlwind=bWhirlwindTrainingPending=true;bWhirlwindSwingPlayed=false;
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
    SetClip(KukriWhirlwindClip,false,KukriRhythm::EntryBlendSeconds);
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

void UKukriWeaponComponent::FinishWhirlwind()
{
    if(!bWhirlwind)return;
    // Clear first: saving the training can refresh the equipment and re-enter the cancellation.
    bWhirlwind=false;
    if(GetNetMode()==NM_Client)
        if(auto* P=Pawn())if(auto* PS=P->GetPlayerState<AColdSteelPlayerState>())PS->FinishSwordWhirlwind();
    EndWhirlwindFocus();
    WhirlwindPause=0.f;WhirlwindImpactAge=1.f;
    FinishWhirlwindTraining();
    HitActors.Reset();
    if(Viewmodel&&IsEquipped()&&Animations.Num())SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
}

void UKukriWeaponComponent::TickWhirlwind(float Delta)
{
    auto* P=Pawn();
    AController* Controller=P?P->GetController():nullptr;
    if(!CurrentAnimation||!Controller||P->IsDodging()||P->IsTraversing()){FinishWhirlwind();return;}
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
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.95f,.9f);
            if(StabWhooshSound)UGameplayStatics::PlaySound2D(this,StabWhooshSound,.75f,.94f);
        }
        if(BeforePhase<KukriWhirlSecondPass&&Phase>=KukriWhirlSecondPass&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.78f,1.1f);
        if(Phase>BeforePhase)SweepWhirlwind(T.TurnDegrees*BeforePhase,T.TurnDegrees*Phase);
        if(Elapsed>=T.ReadySeconds+T.SpinSeconds)FinishWhirlwindTraining();
        if(WhirlwindPause>0.f||Elapsed>=End-UE_SMALL_NUMBER)break;
    }
    if(!bWhirlwind)return;
    // The controller already faced the pawn before this PostPhysics tick turned it: publish the final heading on the body,
    // then compose the camera (with any contact accent) before the arms are sampled for this frame.
    P->FaceRotation(Controller->GetControlRotation(),0.f);
    P->RefreshQuickCombatCamera();
    SamplePose(KukriWhirlwindPoseTime(Elapsed,T,CurrentAnimation->GetPlayLength()));
    UpdateWhirlwindFocus(WhirlwindPause>0.f?0.f:T.MotionBlur*WhirlwindFeel::Speed(Elapsed,T));
    if(Elapsed>=End-UE_SMALL_NUMBER)FinishWhirlwind();
}

void UKukriWeaponComponent::SweepWhirlwind(float FromDegrees,float ToDegrees)
{
    auto* P=Pawn();
    UWorld* World=GetWorld();
    if(!P||!World)return;
    // The blade line on the right of the view (yaw + 90) from the hips out to the skill radius, on the signed turn angle.
    const FVector Origin=P->GetMeleeAimTransform().GetLocation()-FVector(0.f,0.f,KukriWhirlSweepDrop);
    auto Sample=[&](float Degrees)
    {
        FRuneSwordBladeSample S;
        S.Origin=Origin;S.Forward=FRotator(0.f,WhirlwindYaw+90.f+Degrees,0.f).Vector();
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
        SpawnContactFX(Hit,false);
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
        if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,At,.9f,.88f);
        if(StabThudSounds.Num())
            UGameplayStatics::PlaySoundAtLocation(this,StabThudSounds[FMath::RandRange(0,StabThudSounds.Num()-1)],At,
                KukriRhythm::StabThudVolume*.8f,KukriRhythm::StabThudPitch);
    }
    else WhirlwindImpactStrength=FMath::Max(WhirlwindImpactStrength,Strength);
}

void UKukriWeaponComponent::GetWhirlwindCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    // The sword's whirlwind body language (coil, carry, plant, contact resistance); the turn itself is the controller's.
    WhirlwindFeel::Camera(Elapsed,WhirlwindTuning,WhirlwindImpactAge,WhirlwindImpactStrength,Location,Rotation);
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
    TArray<USceneComponent*> Parts;Viewmodel->GetChildrenComponents(true,Parts);Parts.Add(Viewmodel);
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
