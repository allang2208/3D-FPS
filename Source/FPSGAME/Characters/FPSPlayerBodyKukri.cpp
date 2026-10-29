#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "../Weapons/Kukri/KukriDashRhythm.h"
#include "../Weapons/Kukri/KukriQuickRhythm.h"
#include "../Weapons/Kukri/KukriHeavyRhythm.h"
#include "../Skills/LightningHasteSpeed.h"
#include "Animation/AnimSequence.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyGrip.h"
#include "FPSBodyKukriGripData.h"
#include "FPSBodyKukriDualGripData.h"
#include "FPSBodyKukriMotion.h"
#include "FPSBodyKukriPresentationData.h"
#include "FPSPlayerBodyPoses.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

void UFPSPlayerBodyComponent::UpdateKukriPresentation()
{
    auto* Body=GetBodyMesh();
    if(!BodyAnimation||!Body||!Body->GetSkeletalMeshAsset())return;
    const auto& S=BodyAnimation->BodyState;
    const bool Dual=S.Family==TEXT("Kukri")&&FPSBodyKukriMotion::MatchesOffhand(
        S,BodyAnimation->bOffhandKukriEquipment,BodyAnimation->OffhandKukriEquipmentInstance);
    const bool Kaitlin=Body->GetSkeletalMeshAsset()->GetName().Contains(TEXT("Kaitlin"));
    const float Progress=FPSBodyPoses::Progress(S,BodyAnimation->Clock);
    const bool Draw=S.Family==TEXT("Kukri")&&S.Action==EFPSBodyAction::Equip&&
        BodyAnimation->Clips.FindRef(Dual?TEXT("Kukri.FullBody.Dual.Equip"):TEXT("Kukri.FullBody.Equip"));
    const bool Uppercut=FPSBodyKukriMotion::IsOffhandUppercut(S)&&
        BodyAnimation->Clips.FindRef(TEXT("Pistol.KukriUppercut"));
    for(const auto& Binding:MotionBindings)
    {
        const auto& W=Binding.Definition;
        if(W.PoseFamily!=TEXT("Kukri")&&W.PoseFamily!=TEXT("OffhandKukri"))continue;
        auto* Blade=Binding.Static.Get();if(!Blade)continue;
        const bool Matching=W.ItemInstance==(W.AttachHand==0?S.WeaponInstance:S.OffhandInstance);
        FTransform Delta=FTransform::Identity;
        if(Matching&&Draw&&(W.AttachHand==0||Dual))
            Delta=FPSBodyKukriPresentationData::Equip(Kaitlin,Dual,W.AttachHand,Progress);
        else if(Matching&&Uppercut&&W.PoseFamily==TEXT("OffhandKukri"))
            Delta=FPSBodyKukriPresentationData::Uppercut(Kaitlin,Progress);
        else if(Matching&&Dual&&W.AttachHand==0&&S.Action!=EFPSBodyAction::Dead&&
            !FPSBodyPoses::Traversing(S.Motion)&&BodyAnimation->Clips.FindRef(TEXT("Kukri.FullBody.Dual.Run")))
        {
            // Same grip axis as the FPS DualRun flip. SprintAlpha unwinds on
            // attack entry, so a stopped sprint cannot leave the blade reversed.
            const float A=FMath::Clamp(BodyAnimation->SprintAlpha,0.f,1.f);
            Delta.SetRotation(FQuat(FVector::RightVector,PI*A*A*(3.f-2.f*A)));
        }
        // Binding.Mount is captured once when equipment is built. Always derive
        // from it, including cancellation, replacement and late replicated state.
        Blade->SetRelativeTransform(Delta*Binding.Mount);
    }
}

void UFPSPlayerBodyComponent::BuildKukriGrip(const FFPSBodyWeapon& Definition,UStaticMeshComponent& Blade)
{
    auto* Body=GetBodyMesh();auto* Native=Definition.Mesh.LoadSynchronous();
    if(!Body||!Body->GetSkeletalMeshAsset()||!Native||!BodyAnimation)return;
    const auto& Ref=Native->GetRefSkeleton();auto Pose=Ref.GetRefBonePose();
    for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
    if(Definition.AttachHand==1)
    {
        // The dual knife uses its accepted forward left grip, independently
        // of the pistol + reverse-kukri offhand presentation.
        for(const auto& Bone:FPSBodyKukriDualGripData::Bones)
            if(const int32 I=Ref.FindBoneIndex(Bone.Name);I!=INDEX_NONE)Pose[I]=Bone.Transform;
        FFPSBodyGripRig Grip;Grip.Initialize(Ref,Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
        if(!Grip.IsValid())return;
        Grip.Transfer(Pose,BodyAnimation->EquipmentFingers);BodyAnimation->EquipmentGripHands|=2;
        BodyAnimation->bOffhandKukriEquipment=true;
        BodyAnimation->OffhandKukriEquipmentInstance=Definition.ItemInstance;
        Blade.SetRelativeTransform(FPSBodyKukriDualGripData::BladeInHand*Grip.Mount);
        return;
    }
    // Component-space samples from the accepted native idle, authored once.
    // A single static blade follows the target wrist; no hidden FPS rig ticks.
    for(const auto& Bone:FPSBodyKukriGripData::Bones)
        if(const int32 I=Ref.FindBoneIndex(Bone.Name);I!=INDEX_NONE)Pose[I]=Bone.Transform;
    FFPSBodyGripRig Grip;Grip.Initialize(Ref,Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_r"),TEXT("hand_r"));
    const int32 Weapon=Ref.FindBoneIndex(TEXT("WPN_root"));
    if(!Grip.IsValid()||Weapon==INDEX_NONE)return;
    Grip.Transfer(Pose,BodyAnimation->EquipmentFingers);BodyAnimation->EquipmentGripHands|=1;
    FTransform Hand=Pose[Grip.SourceHand];Hand.SetScale3D(FVector::OneVector);
    const FTransform BladeFrame=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f))*Pose[Weapon];
    Blade.SetRelativeTransform(BladeFrame.GetRelativeTransform(Hand)*Grip.Mount);
}

void UFPSPlayerBodyComponent::SampleKukriState(const UKukriWeaponComponent& K,FFPSBodyState& S,float Now) const
{
    S.Family=TEXT("Kukri");S.Weapon=TEXT("ue_kukri");
    S.Action=EFPSBodyAction::None;S.ActionVariant=K.CurrentClip;
    const float SkillRate=FMath::Max(.05f,LightningHaste::ActionSpeed(Character.Get()));
    // PressStop is the saved impact-envelope length, not a remaining pause.
    const bool Paused=K.HitStop>0.f||K.WhirlwindPause>0.f;
    const auto Timed=[&](EFPSBodyAction Action,float Length,float Rate)
    {
        Length=FMath::Max(.01f,Length);
        S.Action=Action;S.bHasActionProgress=true;
        S.ActionDuration=Length/FMath::Max(.01f,Rate);
        S.ActionStartedAt=Now-K.Elapsed/FMath::Max(.01f,Rate);
        S.ActionProgress=FMath::Clamp(K.Elapsed/Length,0.f,1.f);
        S.ActionProgressRate=Paused?0.f:Rate/Length;
    };
    const float Length=K.CurrentAnimation?K.CurrentAnimation->GetPlayLength():1.f;
    if(K.bWhirlwind)
    {
        if(K.IsDual())S.ActionVariant=TEXT("DualWhirlwind");
        const auto& T=K.WhirlwindTuning;
        const float End=T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds;
        Timed(EFPSBodyAction::Whirlwind,End,SkillRate);
        S.ContactFraction=T.ReadySeconds/End;S.ReleaseFraction=(T.ReadySeconds+T.SpinSeconds)/End;
        S.WhirlwindTurns=T.TurnDegrees/360.f;
    }
    else if(K.bHeavyCharging)
    {
        Timed(EFPSBodyAction::Charge,KukriHeavyRhythm::ChargeLength,
            KukriHeavyRhythm::ChargeLength/FMath::Max(.01f,K.HeavyRequiredSeconds));
        // AdvanceHeavyCharge waits for a tap, raises at martial speed, then
        // stretches only the loading phase. Observers need that same rate.
        const float Delay=K.bHeavyAuto?0.f:KukriHeavyRhythm::TapSeconds;
        const float Held=GetWorld()?float(GetWorld()->GetTimeSeconds()-K.HeavyChargeStartedAt):0.f;
        const float Rate=Held<Delay||K.Elapsed>=KukriHeavyRhythm::ChargeLength?0.f:
            K.Elapsed<KukriHeavyRhythm::RaiseEnd?SkillRate:
            (KukriHeavyRhythm::ChargeLength-KukriHeavyRhythm::RaiseEnd)/
                FMath::Max(.2f,K.HeavyRequiredSeconds-Delay-KukriHeavyRhythm::RaiseEnd/SkillRate);
        S.ActionProgressRate=Rate/KukriHeavyRhythm::ChargeLength;
    }
    else if(K.bDashAttack)
    {
        Timed(EFPSBodyAction::HeavyStrike,Length,SkillRate);
        S.ContactFraction=KukriDashRhythm::ContactStart/Length;S.ReleaseFraction=KukriDashRhythm::ContactEnd/Length;
    }
    else if(K.bQuickCombat)
    {
        Timed(EFPSBodyAction::Pommel,Length,SkillRate);
        S.ContactFraction=KukriQuickRhythm::ContactAt/Length;
        S.ReleaseFraction=FMath::Min(.95f,S.ContactFraction+.12f);
    }
    else if(K.bAttacking||K.bUppercut||K.bHeavyAttack)
    {
        const int32 Stage=FMath::Clamp(K.Stage,0,KukriRhythm::StageCount-1);
        const auto& Swing=KukriRhythm::Swings[Stage];
        // The dual kukri's clips run on their own clocks (the owner's AdvanceAttack / AdvanceHeavy): the two-blade
        // sweeps on DualSweepTempo, the double thrust untimed, the X on DualHeavyTempo -- remote bodies follow the same.
        const bool DualThrust=K.bAttacking&&K.bDualThrust, DualHeavy=K.bHeavyAttack&&K.bDualHeavy;
        const float Tempo=DualHeavy?KukriRhythm::SampleTempo(KukriRhythm::DualHeavyTempo,K.Elapsed):DualThrust?1.f:
            K.bAttacking&&K.bDualSweep?KukriRhythm::DualSweepTempo(Stage,K.Elapsed):KukriRhythm::StageTempo(Stage,K.Elapsed);
        const float Rate=(K.bUppercut||K.bHeavyAttack?SkillRate:K.PlayRate)*Tempo;
        Timed(K.bUppercut||K.bHeavyAttack?EFPSBodyAction::HeavyStrike:
            Stage==2?EFPSBodyAction::Thrust:EFPSBodyAction::Strike,Length,Rate);
        S.ContactFraction=K.StrikeProfile().At/Length;
        S.ReleaseFraction=(DualThrust?KukriRhythm::DualThrustContactEnd:DualHeavy?KukriRhythm::DualHeavyContactEnd:
            Swing.ContactEnd+(K.bAttacking&&K.bDualSweep?KukriRhythm::DualSweepOffset(Stage):0.f))/Length;
    }
    else if(K.bEquipping)Timed(EFPSBodyAction::Equip,Length,SkillRate);
}
