#include "KukriWeaponComponent.h"
#include "KukriDecisiveComponent.h"
#include "KukriAttackTiming.h"
#include "../../Characters/FPSComponentVisibility.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDrawRhythm.h"
#include "HatchetDrawRhythm.h"
#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "HatchetReadyRhythm.h"
#include "HatchetPairRhythm.h"
#include "KukriDualDashRhythm.h"
#include "KukriDualEquipBlade.h"
#include "KukriOffhandDraw.h"
#include "OffhandBladeDraw.h"
#include "KukriHeavyRhythm.h"
#include "SwiftFalconHeavy.h"
#include "../MeleeWeaponStats.h"
#include "../MeleeSmallTargetQuery.h"
#include "../RuneSwordRhythm.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

#include "KukriWeaponPrivate.h"
using namespace KukriWeaponPrivate;
void UKukriWeaponComponent::SetClip(FName Name,bool bLoop,float Blend)
{
    if(!Viewmodel)return;
    if(Blend>0.f&&!CurrentClip.IsNone()&&Name!=CurrentClip)Viewmodel->CaptureEntry(Blend);
    // Into or out of the dual hold the left arm (and its kukri) travels in or out of the frame: it gets its own
    // longer blend, also under clips that start without one (the right arm keeps the clip's own entry).
    if(!CurrentClip.IsNone()&&IsDualClip(Name)!=IsDualClip(CurrentClip))Viewmodel->CaptureLeftEntry(OffhandBladeDraw::IsClip(Name)?.06f:KukriDualArmBlendSeconds);
    CurrentClip=Name;CurrentAnimation=Animations.FindRef(Name);Elapsed=0.f;
    if(!CurrentAnimation)return;
    // Manual-sample contract: play once, freeze, then SetPosition each frame.
    Viewmodel->PlayAnimation(CurrentAnimation,bLoop);Viewmodel->SetPlayRate(0.f);
    SamplePose(0.f);
}

void UKukriWeaponComponent::SamplePose(float Time)
{
    if(!Viewmodel||!CurrentAnimation)return;
    Viewmodel->SetPosition(Time,false);Viewmodel->TickAnimation(0.f,false);Viewmodel->RefreshBoneTransforms();
    if(bLoneOffhand&&OffhandBlade)
    {
        // The lone blade rides hand_l as the mirror image of the clip's right weapon (grip and draw flight alike).
        FTransform Grip=Viewmodel->MirroredWeaponToHandL();
        Grip.SetScale3D(FVector(.01f));
        OffhandBlade->SetRelativeTransform(Grip);
    }
}

FName UKukriWeaponComponent::LocomotionClip() const
{
    const auto* P=Pawn();
    if(!P)return KukriIdle;
    const auto* Move=P->GetCharacterMovement();
    const bool Ground=!Move||Move->IsMovingOnGround();
    const float Speed=P->GetVelocity().Size2D();
    const auto Pick=[this](FName Single,FName Dual){return bDual&&Animations.FindRef(Dual)?Dual:Single;};
    // A pair with the hatchet in the right hand (and the ready-run set) keeps the hold's walk carry while sprinting until the
    // sprint attack is ready (user 2026-11-04); TickReadyRun raises the hatchet from there.
    if(Ground&&P->IsSprinting()&&Speed>300.f)
        return bDual&&bMainHatchet&&bHatchetReadyRun?Pick(KukriWalk,KukriDualWalk):Pick(KukriRun,KukriDualRun);
    if(Ground&&Speed>40.f)return Pick(KukriWalk,KukriDualWalk);
    return Pick(KukriIdle,KukriDualIdle);
}

bool UKukriWeaponComponent::TickReadyRun(float Delta)
{
    const auto* P=Pawn();
    // The raised hatchet is the right hand's; the left keeps the dual run's arm whichever weapon it holds.
    if(!P||!bHatchetReadyRun||!bDual||!bMainHatchet)
    {
        if(ReadyRunPhase!=0){ReadyRunPhase=0;SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);}
        return false;
    }
    const auto* Move=P->GetCharacterMovement();
    const bool Ground=!Move||Move->IsMovingOnGround();
    const bool bWanted=Ground&&P->IsSprinting()&&P->GetVelocity().Size2D()>300.f&&
        DashReadyFraction()>=1.f-UE_SMALL_NUMBER;
    // Starting from a locomotion clip: the enter clip is the idle hand gesture held at its first frame, so the blend into
    // it reads as "settling back to the hold, then raising".
    if(ReadyRunPhase==0)
    {
        if(!bWanted)return false;
        SetClip(KukriHatchetReadyEnter,false,KukriRhythm::SprintBlendSeconds);
        ReadyRunPhase=1;
        return true;
    }
    if(ReadyRunPhase==3)
    {
        Elapsed+=Delta;
        if(Elapsed>=CurrentAnimation->GetPlayLength())
        {
            ReadyRunPhase=0;
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
            return true;
        }
        SamplePose(Elapsed);
        return true;
    }
    if(!bWanted)
    {
        // Back down through the idle hand gesture, then hand over to the ordinary locomotion.  Both fists swing in the
        // loop, which can stop anywhere in its stride: the exit's first frame is blended in from the present pose.
        SetClip(KukriHatchetReadyExit,false,KukriRhythm::SprintBlendSeconds);
        ReadyRunPhase=3;
        SamplePose(0.f);
        return true;
    }
    if(ReadyRunPhase==1)
    {
        Elapsed+=Delta;
        if(Elapsed>=CurrentAnimation->GetPlayLength())
        {
            SetClip(KukriHatchetReadyRun,true,0.f);
            ReadyRunPhase=2;Elapsed=0.f;
            return true;
        }
        SamplePose(Elapsed);
        return true;
    }
    // Loop: same cycle as the dual run, so the bob keeps the leg phase at full sprint.
    Elapsed=FMath::Fmod(Elapsed+Delta,FMath::Max(.01f,CurrentAnimation->GetPlayLength()));
    SamplePose(Elapsed);
    return true;
}

FTransform UKukriWeaponComponent::BladeFrame() const
{
    // The bone frame without its import scale: the grip frame of SM_Kukri in world space.
    if(!Viewmodel)return FTransform::Identity;
    // The lone off-hand blade cuts with the mirrored left one (the right weapon chain is hidden).
    if(bLoneOffhand&&OffhandBlade)
    {
        const FTransform Frame=OffhandBlade->GetRelativeTransform()*Viewmodel->GetSocketTransform(KukriOffhandSocket,RTS_World);
        return FTransform(Frame.GetRotation(),Frame.GetLocation());
    }
    const FTransform Bone=Viewmodel->GetSocketTransform(KukriWeaponSocket,RTS_World);
    return FTransform(Bone.GetRotation(),Bone.GetLocation());
}

FTransform UKukriWeaponComponent::OffhandBladeFrame() const
{
    // SM_Kukri is authored in its grip frame (cm): the left blade's component frame without the scale is the same frame
    // TraceBlade samples on the right one (the mirror about the blade plane keeps BladeRoot/Mid/Tip, which lie on it).
    // Read through the freshly sampled hand_l socket (like BladeFrame), not the attached component's cached transform.
    if(!Viewmodel||!OffhandBlade)return BladeFrame();
    const FTransform Frame=OffhandBlade->GetRelativeTransform()*Viewmodel->GetSocketTransform(KukriOffhandSocket,RTS_World);
    return FTransform(Frame.GetRotation(),Frame.GetLocation());
}

void UKukriWeaponComponent::BeginOffhandSwing()
{
    // The left blade swings as a stage of its own: fresh swing sound, contact set (a target the right blade cut can be
    // cut again), impact cue, impact moment and rift. The left blade keeps its own frozen stats and identity.
    bOffhandSwing=true;
    PlayRate=OffhandPlayRate;
    bSwingPlayed=false;bImpactConfirmed=false;bWallHit=false;
    HitActors.Reset();ResetStrike();
    PreviousBlade=OffhandBladeFrame();bHavePreviousBlade=true;
}

void UKukriWeaponComponent::AdvanceDualThrustLunge(float From,float To)
{
    // The reference lunges at the dummy before the double thrust; here a 1 m stride through the shared melee-lunge
    // movement (Thrust: the server authorises the dual kukri pair within the sword thrust's budget, FPSMeleeMovementNetwork).
    auto* P=Pawn();
    const float A=KukriRhythm::DualThrustLungeStart, B=KukriRhythm::DualThrustLungeEnd;
    if(!P||!P->IsLocallyControlled()||bDualThrustLungeBlocked||To<=A||From>=B)return;
    const float Distance=KukriRhythm::DualThrustLungeCM*(FMath::SmoothStep(A,B,To)-FMath::SmoothStep(A,B,From));
    if(Distance<=0.f)return;
    auto* Move=Cast<UFPSCharacterMovementComponent>(P->GetCharacterMovement());
    if(!Move||!Move->IsMovingOnGround()||P->IsSliding()||P->IsTraversing()||Move->IsDodging()){bDualThrustLungeBlocked=true;return;}
    if(!bDualThrustLungeStarted)
    {
        bDualThrustLungeStarted=true;
        DualThrustDirection=P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Thrust,DualThrustDirection);
    }
    if(Move->IsMeleeLungeRejected()){bDualThrustLungeBlocked=true;return;}
    const FVector Moved=Move->ApplyMeleeLungeStep(DualThrustDirection,Distance);
    const float Actual=FMath::Max(0.f,float(FVector::DotProduct(Moved,DualThrustDirection)));
    Move->RecordMeleeLungeStep(Actual);
    if(Actual+.01f<Distance)bDualThrustLungeBlocked=true;
}

FRotator UKukriWeaponComponent::ViewmodelKick() const
{
    if(bDashAttack)return DashViewmodelKick();
    if(bQuickCombat)return QuickViewmodelKick();
    if(bShadowStep)return ShadowStepViewmodelKick();
    if(bWhirlwind)return FRotator::ZeroRotator;   // the whirlwind's contact resistance is in its camera (WhirlwindFeel)
    if(bHeavyCharging&&bHeavyFull&&GetWorld())
    {
        // Full heavy charge: a fine tension tremble of the loaded arm until the release.
        const float T=float(GetWorld()->GetTimeSeconds())*2.f*PI*KukriHeavyRhythm::TrembleHz;
        const float A=KukriHeavyRhythm::TrembleDegrees;
        return FRotator(FMath::Sin(T)*A,FMath::Sin(T*1.37f+1.f)*A*.6f,FMath::Sin(T*.71f+2.f)*A*.5f);
    }
    if(ImpactAge<0.f)return FRotator::ZeroRotator;
    if(bFalconHeavy&&bHeavyAttack)
    {
        const float Pulse=SwiftFalconHeavy::ContactPulse(ImpactAge)*ImpactKick;
        return FRotator(Pulse*(Shot.MeleeDamagePhase?-.65f:1.f),0.f,0.f);
    }
    const float E=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick;
    // The contact pushes the arm back against its travel: right/down for the first sweep, left/up for the
    // down-right diagonal, left/down for the stab from the lower left (KukriRhythm::FSwing::KickYaw/KickPitch).
    // The dual sweep's left blade cuts the other way: its kick is the mirror image.
    const auto& S=SwingProfile();
    // The dual heavy's X chops both blades down at once: its kick is straight up (no yaw).
    const float KickYaw=bDualHeavy&&bHeavyAttack?0.f:bOffhandSwing?-S.KickYaw:S.KickYaw;
    const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
    return FRotator(E*.6f*S.KickPitch+Shake*.5f,E*.8f*KickYaw,(-E*.5f+Shake*.8f)*KickYaw);
}

void UKukriWeaponComponent::GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;FovDelta=0.f;
    if(!IsEquipped()&&!bStaffOffhandWhirlwind)return;
    // The lone off-hand blade plays the right-hand moveset mirrored: its view cues yaw and roll the other way (the whirlwind
    // mirrors through its own turn, BeginWhirlwind).
    const auto MirrorLone=[this,&Location,&Rotation]
    {if(bLoneOffhand){Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;Location.Y=-Location.Y;}};
    if(bDashAttack){GetDashCameraMotion(Location,Rotation,FovDelta);MirrorLone();return;}
    if(bQuickCombat){GetQuickCameraMotion(Location,Rotation,FovDelta);MirrorLone();return;}
    if(bShadowStep){GetShadowStepCameraMotion(Location,Rotation,FovDelta);MirrorLone();return;}
    if(bWhirlwind){GetWhirlwindCameraMotion(Location,Rotation,FovDelta);return;}
    // Toss-and-catch draw: the reference camera on the draw clip's own clock (KukriDrawRhythm; the hatchet's vertical toss
    // has its own curve in HatchetDrawRhythm).
    if(bEquipping&&OffhandBladeDraw::IsClip(CurrentClip))OffhandBladeDraw::Camera(IsLeftHatchetDraw(CurrentClip),Elapsed,Rotation,FovDelta);
    else if(bEquipping)(IsRightHatchetDraw(CurrentClip)?HatchetDrawRhythm::Camera:KukriDrawRhythm::Camera)(Elapsed,Rotation,FovDelta);
    // Heavy charge: the raise and the slow load on the charge clip's clock (KukriHeavyRhythm).
    if(bHeavyCharging)(bFalconHeavy?SwiftFalconHeavy::ChargeCamera:bDualHeavy?KukriHeavyRhythm::DualChargeCamera:KukriHeavyRhythm::ChargeCamera)(Elapsed,Rotation,FovDelta);
    if(bAttacking||bUppercut||bHeavyAttack)
    {
        // Same author clock as the clip: contact holds freeze the camera curve with the arm (the uppercut too).
        // The stab (stage 3) also pushes the camera forward along the view; the dual sweep adds the mirrored curve.
        if(bAttacking&&bDualSweep)KukriRhythm::DualSweepCamera(Stage,Elapsed,Rotation,FovDelta);
        else if(bAttacking&&IsHatchetDualChop())PairChopCamera(Elapsed,Rotation,FovDelta,&Location);
        else if(bAttacking&&bDualThrust)KukriRhythm::DualThrustCamera(Elapsed,Rotation,FovDelta);
        else if(bHeavyAttack&&bFalconHeavy)
        {
            SwiftFalconHeavy::ReleaseCamera(Elapsed,Location,Rotation,FovDelta);
        }
        else if(bHeavyAttack&&bDualHeavy)KukriRhythm::DualHeavyCamera(Elapsed,Rotation,FovDelta);
        else StageSwingCamera(Stage,Elapsed,Rotation,FovDelta,&Location);
    }
    if(CameraCarryAge>=0.f)
    {
        // A chained stage starts from the previous stage's camera offset and eases into its own curve.
        const float Keep=1.f-FMath::SmoothStep(0.f,1.f,CameraCarryAge/KukriRhythm::CameraCarrySeconds);
        Rotation+=CameraCarry*Keep;FovDelta+=CameraCarryFov*Keep;
    }
    if(ImpactAge>=0.f)
    {
        if(bFalconHeavy&&bHeavyAttack)
        {
            const bool Pull=Shot.MeleeDamagePhase==1;
            const float Pulse=SwiftFalconHeavy::ContactPulse(ImpactAge)*ImpactKick;
            Rotation.Pitch+=Pulse*(Pull?.65f:-.9f);
            Location+=FVector(Pull?-.55f:.35f,0.f,Pull?.12f:-.3f)*Pulse;
            FovDelta+=Pulse*(Pull?-.25f:.4f);
        }
        else
        {
        // Confirmed hit: short damped shake on top of the swing curve (real time).  The stab rattles its roll
        // harder, like the reference's contact frames (FSwing::HitRoll).
        const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
        const float HitRoll=IsHatchetDualChop()?HatchetDualChopRhythm::HitRoll:bDualThrust?KukriRhythm::DualThrustHitRoll:
            SwingProfile().HitRoll;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        // Contact punch: the view widens for a beat with the hit-stop (V4).
        FovDelta+=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick*1.4f;
        }
    }
    if(StrikeAge>=0.f)
    {
        // Impact-moment accent (hit or miss, real time): the view is carried along the strike for a beat
        // (stab: forward and wider; slashes: with the blade) -- KukriRhythm::Strikes.
        const auto& K=StrikeProfile();
        const float E=KukriRhythm::StrikeEnvelope(StrikeAge);
        FovDelta+=K.AccentFov*E;Location.X+=K.AccentPushCM*E;
        Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw+=(bOffhandSwing?-K.AccentYaw:K.AccentYaw)*E;
    }
    MirrorLone();
}

