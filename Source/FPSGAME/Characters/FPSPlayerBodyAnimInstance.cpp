#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/BoneReference.h"
#include "Components/SkeletalMeshComponent.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "TwoBoneIK.h"

namespace FPSBodyAnimation
{
static float Ease(float T) { T=FMath::Clamp(T,0.f,1.f); return T*T*(3.f-2.f*T); }
static constexpr float CrouchStrideScale=.72f;
static constexpr float CrouchLiftScale=.45f;

// Template clips contain different numbers of strides and start on different feet.
// Phase 0 is a left-foot contact, .5 a right-foot contact, for every blended clip.
struct FStrideTiming
{
    float Length=1.f;
    TArray<float> Left,Right;
    explicit FStrideTiming(const UAnimSequence* Clip,const UAnimSequence* PhaseReference=nullptr)
    {
        if(!Clip)return;
        Length=FMath::Max(Clip->GetPlayLength(),SMALL_NUMBER);
        // Four derived rifle diagonals omit markers but retain their forward/back
        // source foot trajectories and duration. Use that source's contact timing.
        const UAnimSequence* MarkerSource=Clip->AuthoredSyncMarkers.IsEmpty()&&PhaseReference?PhaseReference:Clip;
        const float TimeScale=Length/FMath::Max(MarkerSource->GetPlayLength(),SMALL_NUMBER);
        for(const auto& Marker:MarkerSource->AuthoredSyncMarkers)
        {
            if(Marker.MarkerName==TEXT("L"))Left.Add(Marker.Time*TimeScale);
            else if(Marker.MarkerName==TEXT("R"))Right.Add(Marker.Time*TimeScale);
        }
        Left.Sort();Right.Sort();
    }
    float Duration() const {return Length/FMath::Max(Left.Num(),1);}
    float Sample(float Cycles) const
    {
        if(Left.IsEmpty()||Right.IsEmpty())return FMath::Fmod(Cycles,1.f)*Length;
        const int32 Cycle=FMath::FloorToInt(Cycles)%Left.Num();
        const float Start=Left[Cycle];
        const float End=Cycle+1<Left.Num()?Left[Cycle+1]:Left[0]+Length;
        float Middle=(Start+End)*.5f;
        for(const float Contact:Right)
        {
            const float Time=Contact>Start?Contact:Contact+Length;
            if(Time>Start&&Time<End){Middle=Time;break;}
        }
        const float Phase=FMath::Frac(Cycles);
        const float Time=Phase<.5f?FMath::Lerp(Start,Middle,Phase*2.f):FMath::Lerp(Middle,End,(Phase-.5f)*2.f);
        return FMath::Fmod(Time,Length);
    }
};

// Blend upper-body local transforms only; feet keep the independent movement cycle.
struct FUpperLayer : FAnimNode_Base
{
    FPoseLink Base, Upper;
    float Weight = 0.f;
    TArray<FCompactPoseBoneIndex> UpperBones;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override { Base.Initialize(C); Upper.Initialize(C); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Base.CacheBones(C); Upper.CacheBones(C); UpperBones.Reset();
        const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        const auto& Ref=Bones.GetReferenceSkeleton();
        const int32 Spine=Ref.FindBoneIndex(TEXT("spine_01"));
        for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
        {
            const FCompactPoseBoneIndex Compact(I);
            for(int32 Parent=Bones.GetSkeletonIndex(Compact);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                if(Parent==Spine){UpperBones.Add(Compact);break;}
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override { Base.Update(C); Upper.Update(C); }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH)return;
        FPoseContext Overlay(Out); Upper.Evaluate(Overlay);
        for(const auto Bone:UpperBones)
        {
            FTransform Blended; Blended.Blend(Out.Pose[Bone],Overlay.Pose[Bone],Weight);
            Out.Pose[Bone]=Blended;
        }
    }
};

// Small world-body corrections. Bone transforms are derived locally, never replicated.
struct FControls : FAnimNode_Base
{
    FPoseLink Source,Neutral;
    FBoneReference Pelvis, Spine, Hands[2], Feet[2],Toes[2];
    FFPSBodyState State;
    FFPSBodyState MotionState;
    float Clock=0.f,Crouch=0.f,MotionWeight=0.f,Aim=0.f,Sprint=0.f,Delta=0.f;
    FVector Handholds[2];
    FTransform LastHands[2],EntryHands[2];
    FTransform CastRecoveryEntry=FTransform::Identity;
    float CastRecoveryStartProgress=0.f;
    EFPSBodyAction LastAction=EFPSBodyAction::None;
    FName LastVariant;
    bool bHasHandHistory=false;
    float HandBlendAge=1.f;
    FTransform LeftGrip=FTransform::Identity;
    bool bLeftGrip=false;
    FControls()
    {
        Pelvis.BoneName=TEXT("pelvis");Spine.BoneName=TEXT("spine_03");
        Hands[0].BoneName=TEXT("hand_r");Hands[1].BoneName=TEXT("hand_l");
        Feet[0].BoneName=TEXT("foot_r");Feet[1].BoneName=TEXT("foot_l");
        Toes[0].BoneName=TEXT("ball_r");Toes[1].BoneName=TEXT("ball_l");
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override { Source.Initialize(C);Neutral.Initialize(C); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Source.CacheBones(C);Neutral.CacheBones(C);bHasHandHistory=false;const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        Pelvis.Initialize(Bones);Spine.Initialize(Bones);
        for(auto& B:Hands)B.Initialize(Bones);for(auto& B:Feet)B.Initialize(Bones);for(auto& B:Toes)B.Initialize(Bones);
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override { Source.Update(C);Neutral.Update(C); }
    static void Solve(FCSPose<FCompactPose>& Pose,const FBoneReference& End,const FTransform& Target,const FVector& Pole,float Weight)
    {
        const auto& Bones=Pose.GetPose().GetBoneContainer();if(!End.IsValidToEvaluate(Bones)||Weight<=0.f)return;
        const auto E=End.GetCompactPoseIndex(Bones), J=Bones.GetParentBoneIndex(E);
        if(J==INDEX_NONE)return;
        const auto R=Bones.GetParentBoneIndex(J);if(R==INDEX_NONE)return;
        FTransform Root=Pose.GetComponentSpaceTransform(R), Joint=Pose.GetComponentSpaceTransform(J), Tip=Pose.GetComponentSpaceTransform(E);
        const double Upper=FVector::Distance(Root.GetLocation(),Joint.GetLocation()),Lower=FVector::Distance(Joint.GetLocation(),Tip.GetLocation());
        AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,Pole,Target.GetLocation(),Upper,Lower,false,1.,1.);
        Tip.SetRotation(Target.GetRotation());
        TArray<FBoneTransform,TInlineAllocator<3>> Changes;
        Changes.Emplace(R,Root);Changes.Emplace(J,Joint);Changes.Emplace(E,Tip);
        Pose.LocalBlendCSBoneTransforms(Changes,Weight);
    }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Source.Evaluate(Out);const auto& Bones=Out.Pose.GetBoneContainer();
        if(!Pelvis.IsValidToEvaluate(Bones)||!Spine.IsValidToEvaluate(Bones))return;
        FTransform FootTargets[2];FVector KneePoles[2];
        if(Crouch>ZERO_ANIMWEIGHT_THRESH)
        {
            FCSPose<FCompactPose> Before;Before.InitPose(Out.Pose);
            FPoseContext NeutralPose(Out);Neutral.Evaluate(NeutralPose);
            FCSPose<FCompactPose> NeutralCS;NeutralCS.InitPose(NeutralPose.Pose);
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            {
                const auto Foot=Feet[I].GetCompactPoseIndex(Bones);
                const auto Knee=Bones.GetParentBoneIndex(Foot),Hip=Bones.GetParentBoneIndex(Knee);
                FootTargets[I]=Before.GetComponentSpaceTransform(Foot);
                const FTransform& Rest=NeutralCS.GetComponentSpaceTransform(Foot);
                const FVector Offset=FootTargets[I].GetLocation()-Rest.GetLocation();
                // Keep the source left/right contact timing, but use short, low
                // crouch steps around this weapon family's actual idle footprint.
                const FVector ShortStep=Rest.GetLocation()+Offset*FVector(CrouchStrideScale,CrouchStrideScale,CrouchLiftScale);
                FootTargets[I].SetLocation(FMath::Lerp(FootTargets[I].GetLocation(),ShortStep,Crouch));
                FootTargets[I].SetRotation(FQuat::Slerp(FootTargets[I].GetRotation(),Rest.GetRotation(),.75f*Crouch).GetNormalized());
                if(Toes[I].IsValidToEvaluate(Bones))
                {
                    const auto Toe=Toes[I].GetCompactPoseIndex(Bones);
                    Out.Pose[Toe].SetRotation(FQuat::Slerp(Out.Pose[Toe].GetRotation(),NeutralPose.Pose[Toe].GetRotation(),.75f*Crouch).GetNormalized());
                }
                // A foot-relative pole swings across the hip when strafing/backing
                // up. Keep each knee forward and slightly outside its own hip.
                const FVector HipPosition=Before.GetComponentSpaceTransform(Hip).GetLocation()+FVector(0,-6,-40)*Crouch;
                const FVector ForwardPole=HipPosition+FVector(FMath::Sign(Rest.GetLocation().X)*18.f,85.f,-25.f);
                KneePoles[I]=FMath::Lerp(Before.GetComponentSpaceTransform(Knee).GetLocation(),ForwardPole,Crouch);
            }
        }
        Out.Pose[Pelvis.GetCompactPoseIndex(Bones)].AddToTranslation(FVector(0,-6.f,-40.f)*Crouch);
        FCSPose<FCompactPose> Pose;Pose.InitPose(Out.Pose);
        // Targets and pelvis already contain the crouch blend. Blending IK again
        // leaves the feet partway below their targets during crouch/stand changes.
        if(Crouch>ZERO_ANIMWEIGHT_THRESH)for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            Solve(Pose,Feet[I],FootTargets[I],KneePoles[I],1.f);

        const auto Motion=MotionState.Motion;
        const float MT=MotionState.MotionProgress;
        const bool Traversing=FPSBodyPoses::Traversing(Motion);
        if(MotionWeight>ZERO_ANIMWEIGHT_THRESH)
        {
            FPoseContext RestPose(Out);Neutral.Evaluate(RestPose);
            FCSPose<FCompactPose> RestCS;RestCS.InitPose(RestPose.Pose);
            FVector Offset=FVector::ZeroVector;
            if(Motion==EFPSBodyMotion::Slide)Offset=FVector(0,-18,-22);
            else if(Motion==EFPSBodyMotion::Dodge)Offset=(MotionState.MotionDirection*10.f+FVector(0,0,-15))*FMath::Sin(PI*MT);
            else if(Traversing)Offset=FVector(0,-7,-14)*FMath::Sin(PI*MT);
            auto Hip=Pose.GetComponentSpaceTransform(Pelvis.GetCompactPoseIndex(Bones));
            Hip.AddToTranslation(Offset*MotionWeight);
            TArray<FBoneTransform,TInlineAllocator<1>> HipChange;HipChange.Emplace(Pelvis.GetCompactPoseIndex(Bones),Hip);
            Pose.LocalBlendCSBoneTransforms(HipChange,1.f);
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            {
                auto Target=RestCS.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones));
                FVector FootOffset=FVector::ZeroVector;
                if(Motion==EFPSBodyMotion::Slide)
                    FootOffset=MotionState.MotionDirection*(I==0?66.f:18.f)+FVector(I==0?-6:6,0,I==0?4:9);
                else if(Motion==EFPSBodyMotion::Dodge)
                {
                    const int32 Lead=MotionState.MotionDirection.X<=0.f?0:1;
                    const float Step=FMath::Sin(PI*MT);
                    FootOffset=MotionState.MotionDirection*(I==Lead?34.f:-12.f)*Step+FVector(0,0,I==Lead?12.f:3.f)*Step;
                }
                else if(Traversing)
                {
                    const float Phase=FMath::Clamp((MT-(I==0?.1f:.3f))/(I==0?.7f:.65f),0.f,1.f);
                    const float Lift=FMath::Sin(PI*Phase);
                    FootOffset=FVector(I==0?-5:5,28*Lift,(Motion==EFPSBodyMotion::Vault?48.f:38.f)*Lift);
                }
                Target.AddToTranslation(FootOffset);
                FTransform Blended;Blended.Blend(Pose.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones)),Target,MotionWeight);
                Solve(Pose,Feet[I],Blended,FVector(I==0?-30:30,95,Hip.GetLocation().Z-20),1.f);
            }
        }
        const float T=FPSBodyPoses::Progress(State,Clock);
        const float Shot=FMath::Clamp(1.f-(Clock-State.LastShotAt)/.14f,0.f,1.f);
        auto SpinePose=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        // Manny's mesh faces +Y; mesh-X is the pitch axis.
        const float MotionPitch=Motion==EFPSBodyMotion::Slide?18.f:Motion==EFPSBodyMotion::Dodge?-12.f*MotionState.MotionDirection.Y*FMath::Sin(PI*MT):Traversing?-12.f*FMath::Sin(PI*MT):0.f;
        const float Pitch=FMath::Clamp(State.AimPitch,-70.f,70.f)*.65f-4.f*Shot-6.f*Crouch+MotionPitch*MotionWeight;
        SpinePose.SetRotation(FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Pitch))*SpinePose.GetRotation());
        if(Motion==EFPSBodyMotion::Dodge)
            SpinePose.SetRotation(FQuat(FVector::RightVector,.16f*MotionState.MotionDirection.X*FMath::Sin(PI*MT)*MotionWeight)*SpinePose.GetRotation());
        TArray<FBoneTransform,TInlineAllocator<1>> SpineChange;SpineChange.Emplace(Spine.GetCompactPoseIndex(Bones),SpinePose);
        Pose.LocalBlendCSBoneTransforms(SpineChange,1.f);
        if(Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
        {
            FTransform Targets[2]={Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)),Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones))};
            const bool Melee=State.Family==TEXT("Melee")||State.Family==TEXT("Tool");
            const bool Gun=State.Family==TEXT("Rifle")||State.Family==TEXT("Pistol");
            if(!State.bDual)Targets[0]=FPSBodyPoses::RightHand(State,T,Crouch,Aim,Sprint,Targets[0]);
            const bool FreeLeft=!Melee&&(State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty||State.Action==EFPSBodyAction::Equip);
            const bool PistolBash=State.Action==EFPSBodyAction::GunBash&&State.Family==TEXT("Pistol");
            bool AdjustHand[2]={Melee||(Gun&&!FreeLeft)||State.bDual,State.bDual||(bLeftGrip&&!FreeLeft)||PistolBash};
            if(State.bDual)
            {
                for(int32 I=0;I<2;++I)
                {
                    const auto& Hand=I==0?State.RightHand:State.LeftHand;const float Side=I==0?-1.f:1.f;
                    const float HandSprint=Hand.bEquipping||Hand.bReloading?0.f:Sprint;
                    // Both weapons retain independent forward holds; the support hand
                    // no longer remains at the single-pistol two-hand grip.
                    const float Kick=FMath::Clamp(1.f-(Clock-Hand.LastShotAt)/.13f,0.f,1.f);
                    FVector Target(Side*25.f,47.f-8.f*HandSprint-5.f*Kick,128.f-40.f*Crouch-15.f*HandSprint+3.f*Kick);
                    FQuat Rotation=FQuat(FVector::ForwardVector,.12f*(1.f-Aim)+.2f*HandSprint)
                        *FQuat(FVector::UpVector,Side*.35f*HandSprint)*Targets[I].GetRotation();
                    if(PistolBash)
                    {
                        const bool Striking=(State.ActionVariant==TEXT("PistolBashLeft"))==(I==1);
                        Target+=(Striking?FVector(-Side*9,18,16):FVector(Side*7,-14,3))*FPSBodyPoses::Pulse(T,State.ContactFraction);
                        // Both translation and impact rotation belong to the selected hand.
                        if(Striking)Rotation=FQuat(FVector::ForwardVector,.8f*FPSBodyPoses::PistolBashLift(T,State.ContactFraction))*Rotation;
                    }
                    if(Hand.bReloading)
                    {
                        const float Dip=Ease(Hand.Progress/.15f)*(1.f-Ease((Hand.Progress-.72f)/.28f));
                        Target+=FVector(Side*8,-18,-32)*Dip;
                        Rotation=FQuat(FVector::ForwardVector,.7f*Dip)*Rotation;
                    }
                    else if(Hand.bEquipping)
                    {
                        // Each hand draws from the hip using its own source equip clock.
                        const float Lowered=1.f-Ease(Hand.Progress/.85f);
                        Target+=FVector(Side*8,-18,-42)*Lowered;
                        Rotation=FQuat(FVector::ForwardVector,.55f*Lowered)*Rotation;
                    }
                    Targets[I].SetRotation(Rotation.GetNormalized());
                    Targets[I].SetLocation(Target);
                }
            }
            else if(bLeftGrip&&!FreeLeft&&!PistolBash)Targets[1]=LeftGrip*Targets[0];
            if(PistolBash&&!State.bDual)
                Targets[1].SetLocation(FVector(30,18,110-40*Crouch));
            const bool RecoveringCast=State.Action==EFPSBodyAction::Cast&&State.ActionVariant==TEXT("Recover");
            if(RecoveringCast)
            {
                if(!bHasHandHistory||LastAction!=EFPSBodyAction::Cast||LastVariant!=TEXT("Recover"))
                {
                    CastRecoveryEntry=bHasHandHistory?LastHands[1]:Targets[1];
                    CastRecoveryStartProgress=State.ActionProgress;
                }
                const float Return=Ease((State.ActionProgress-CastRecoveryStartProgress)/FMath::Max(.001f,1.f-CastRecoveryStartProgress));
                FTransform Recovered;Recovered.Blend(CastRecoveryEntry,Targets[1],Return);
                Targets[1]=Recovered;AdjustHand[1]=true;
            }
            else if(State.Action==EFPSBodyAction::Cast)
            {Targets[1]=FPSBodyPoses::CastHand(State,Crouch,Targets[1]);AdjustHand[1]=true;}
            // A cancelled traversal must blend from LastHands, not keep chasing stale world contacts.
            if(FPSBodyPoses::Traversing(State.Motion)&&MotionWeight>ZERO_ANIMWEIGHT_THRESH)
            {
                const float Plant=State.MotionHandContact;
                for(int32 I=0;I<2;++I)
                {Targets[I].SetLocation(FMath::Lerp(Targets[I].GetLocation(),Handholds[I],Plant*MotionWeight));AdjustHand[I]=true;}
            }
            if(bHasHandHistory&&(LastAction!=State.Action||LastVariant!=State.ActionVariant))
            {
                EntryHands[0]=LastHands[0];EntryHands[1]=LastHands[1];HandBlendAge=0.f;
            }
            LastAction=State.Action;LastVariant=State.ActionVariant;HandBlendAge+=Delta;
            const float Blend=Ease(HandBlendAge/(State.Action==EFPSBodyAction::GunBash?.065f:.1f));
            for(int32 I=0;I<2;++I)
            {
                if(bHasHandHistory&&Blend<1.f&&!(I==1&&RecoveringCast))
                {FTransform Mixed;Mixed.Blend(EntryHands[I],Targets[I],Blend);Targets[I]=Mixed;}
                if(I==1&&bLeftGrip&&!FreeLeft&&!State.bDual&&!PistolBash&&State.Action!=EFPSBodyAction::Cast&&!(Traversing&&MotionWeight>ZERO_ANIMWEIGHT_THRESH))
                    Targets[1]=LeftGrip*Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
                if(AdjustHand[I]||(bHasHandHistory&&Blend<1.f))Solve(Pose,Hands[I],Targets[I],FVector(I==0?-65:65,10,105-40*Crouch),1.f);
                LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
            }
            bHasHandHistory=true;
        }
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    }
};

struct FProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle,Neutral,WalkA,WalkB,JogA,JogB,Air,Action,Death;
    FAnimNode_TwoWayBlend Walk,Jog,Pace,Movement,AirBlend,DeathBlend;
    FUpperLayer Upper,AirHold;
    FControls Controls;
    TMap<const UAnimSequence*,FStrideTiming> Strides;
    float SmoothedSpeed=0.f,SmoothedHeading=0.f,GaitCycles=0.f;
    bool bHasHeading=false;
    const FStrideTiming& Timing(const UAnimSequence* Clip,const UAnimSequence* PhaseReference=nullptr)
    {
        if(const auto* Existing=Strides.Find(Clip))return *Existing;
        return Strides.Add(Clip,FStrideTiming(Clip,PhaseReference));
    }
    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        Walk.A.SetLinkNode(&WalkA);Walk.B.SetLinkNode(&WalkB);
        Jog.A.SetLinkNode(&JogA);Jog.B.SetLinkNode(&JogB);
        Pace.A.SetLinkNode(&Walk);Pace.B.SetLinkNode(&Jog);
        Movement.A.SetLinkNode(&Idle);Movement.B.SetLinkNode(&Pace);
        AirBlend.A.SetLinkNode(&Movement);AirBlend.B.SetLinkNode(&Air);
        AirHold.Base.SetLinkNode(&AirBlend);AirHold.Upper.SetLinkNode(&Idle);
        Upper.Base.SetLinkNode(&AirHold);Upper.Upper.SetLinkNode(&Action);
        Controls.Source.SetLinkNode(&Upper);Controls.Neutral.SetLinkNode(&Neutral);
        DeathBlend.A.SetLinkNode(&Controls);DeathBlend.B.SetLinkNode(&Death);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &DeathBlend;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {Nodes.Append({&Idle,&Neutral,&WalkA,&WalkB,&JogA,&JogB,&Walk,&Jog,&Pace,&Movement,&Air,&AirBlend,&AirHold,&Action,&Upper,&Controls,&Death,&DeathBlend});}
    virtual void PreUpdate(UAnimInstance* Instance,float Delta) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Delta);
        const auto* D=CastChecked<UFPSPlayerBodyAnimInstance>(Instance);
        const FString Family=(D->BodyState.Family==TEXT("Rifle")||D->BodyState.Family==TEXT("Pistol"))?D->BodyState.Family.ToString():TEXT("Unarmed");
        const auto Clip=[&](const FString& Key){return D->Clips.FindRef(FName(*Key)).Get();};
        const auto Set=[](FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Asset,float Time,bool Loop)
        {
            Node.SetSequence(Asset);Node.SetShouldLoop(Loop);Node.SetTeleportToExplicitTime(true);
            const float Length=Asset?Asset->GetPlayLength():0.f;
            Node.SetExplicitTime(Loop&&Length>0.f?FMath::Fmod(FMath::Max(Time,0.f),Length):FMath::Clamp(Time,0.f,Length));
        };
        UAnimSequence* IdleClip=Clip(Family+TEXT(".Idle"));Set(Idle,IdleClip,D->Clock,true);
        Set(Neutral,IdleClip,0.f,false);
        static const TCHAR* Directions[]={TEXT("Fwd"),TEXT("Fwd_Right"),TEXT("Right"),TEXT("Bwd_Right"),TEXT("Bwd"),TEXT("Bwd_Left"),TEXT("Left"),TEXT("Fwd_Left")};
        const float Dt=FMath::Max(Delta,0.f);
        SmoothedSpeed=FMath::FInterpTo(SmoothedSpeed,D->Speed,Dt,10.f);
        if(D->Speed>5.f)
        {
            if(!bHasHeading){SmoothedHeading=D->Direction;bHasHeading=true;}
            else SmoothedHeading=FMath::UnwindDegrees(SmoothedHeading+
                FMath::FindDeltaAngleDegrees(SmoothedHeading,D->Direction)*FMath::Clamp(Dt*10.f,0.f,1.f));
        }
        const float Heading=FMath::Fmod(SmoothedHeading+360.f,360.f)/45.f;
        const int32 A=FMath::FloorToInt(Heading)%8,B=(A+1)%8;
        Walk.Alpha=Jog.Alpha=Heading-FMath::FloorToFloat(Heading);
        auto* WA=Clip(Family+TEXT(".Walk.")+Directions[A]);auto* WB=Clip(Family+TEXT(".Walk.")+Directions[B]);
        auto* JA=Clip(Family+TEXT(".Jog.")+Directions[A]);auto* JB=Clip(Family+TEXT(".Jog.")+Directions[B]);
        Timing(JA,Clip(Family+(A>=3&&A<=5?TEXT(".Jog.Bwd"):TEXT(".Jog.Fwd"))));
        Timing(JB,Clip(Family+(B>=3&&B<=5?TEXT(".Jog.Bwd"):TEXT(".Jog.Fwd"))));
        // Crouched locomotion uses the walking contact sequence, never a jog pose.
        Pace.Alpha=FMath::Clamp((SmoothedSpeed-180.f)/260.f,0.f,1.f)*(1.f-D->CrouchAlpha);
        Movement.Alpha=FMath::Clamp(SmoothedSpeed/80.f,0.f,1.f)*(1.f-D->MotionAlpha);
        const float WalkDuration=FMath::Lerp(Timing(WA).Duration(),Timing(WB).Duration(),Walk.Alpha);
        const float JogDuration=FMath::Lerp(Timing(JA).Duration(),Timing(JB).Duration(),Jog.Alpha);
        const float StrideDuration=FMath::Lerp(WalkDuration,JogDuration,Pace.Alpha);
        // Source root tracks average 300 cm/s walking and 600 cm/s jogging.
        // Movement stays capsule-driven; the full-body presentation only changes tempo.
        const float SourceSpeed=FMath::Lerp(300.f,600.f,Pace.Alpha)*FMath::Lerp(1.f,CrouchStrideScale,D->CrouchAlpha);
        const float PlayRate=FMath::Clamp(SmoothedSpeed/SourceSpeed,0.f,1.25f);
        // Twelve is a common multiple of the template's one-to-four-stride clips.
        GaitCycles=FMath::Fmod(GaitCycles+Dt*PlayRate*(1.f-D->MotionAlpha)/FMath::Max(StrideDuration,.1f),12.f);
        Set(WalkA,WA,Timing(WA).Sample(GaitCycles),true);Set(WalkB,WB,Timing(WB).Sample(GaitCycles),true);
        Set(JogA,JA,Timing(JA).Sample(GaitCycles),true);Set(JogB,JB,Timing(JB).Sample(GaitCycles),true);
        const bool Landing=!D->bFalling&&D->LandTime<.22f;
        Set(Air,Clip(Landing?TEXT("Land"):(D->VerticalSpeed>0.f?TEXT("Jump"):TEXT("Fall"))),Landing?D->LandTime:D->AirTime,!Landing&&D->VerticalSpeed<=0.f);
        AirBlend.Alpha=D->AirAlpha*(1.f-D->MotionAlpha);
        AirHold.Weight=(Family!=TEXT("Unarmed"))?AirBlend.Alpha:0.f;
        const bool Reload=D->UpperState.Action==EFPSBodyAction::Reload||D->UpperState.Action==EFPSBodyAction::ReloadEmpty;
        UAnimSequence* ActionClip=Clip(Family+(Reload?TEXT(".Reload"):TEXT(".Equip")));
        const float Elapsed=FMath::Max(0.f,D->Clock-D->BodyState.ActionStartedAt);
        const float Fraction=FPSBodyPoses::Progress(D->UpperState,D->Clock);
        Set(Action,ActionClip?ActionClip:IdleClip,Fraction*(ActionClip?ActionClip->GetPlayLength():0.f),false);
        Upper.Weight=ActionClip?D->UpperAlpha:0.f;
        Controls.State=D->BodyState;Controls.Clock=D->Clock;Controls.Crouch=D->CrouchAlpha;
        Controls.MotionState=D->MotionState;Controls.MotionWeight=D->MotionAlpha;
        Controls.Aim=D->AimAlpha;Controls.Sprint=D->SprintAlpha;Controls.Delta=Dt;
        if(const auto* Mesh=Instance->GetSkelMeshComponent();Mesh&&D->MotionState.bHasHandholds)
        {
            Controls.Handholds[0]=Mesh->GetComponentTransform().InverseTransformPosition(D->MotionState.RightHandhold);
            Controls.Handholds[1]=Mesh->GetComponentTransform().InverseTransformPosition(D->MotionState.LeftHandhold);
        }
        else {Controls.Handholds[0]=FVector(-25,45,160);Controls.Handholds[1]=FVector(25,45,160);}
        Controls.LeftGrip=D->LeftGripFromRight;Controls.bLeftGrip=D->bHasLeftGrip;
        Set(Death,Clip(TEXT("Dead")),Elapsed,false);DeathBlend.Alpha=D->BodyState.Action==EFPSBodyAction::Dead?Ease(Elapsed/.12f):0.f;
    }
};
}

void UFPSPlayerBodyAnimInstance::NativeUpdateAnimation(float Delta)
{
    Super::NativeUpdateAnimation(Delta);
    const float Dt=FMath::Max(Delta,0.f);
    CrouchAlpha=FMath::FInterpTo(CrouchAlpha,BodyState.bCrouched||BodyState.bSliding?1.f:0.f,Dt,10.f);
    const bool SpecialMove=BodyState.Motion!=EFPSBodyMotion::Ground;
    if(SpecialMove)MotionState=BodyState;
    MotionAlpha=FMath::FInterpTo(MotionAlpha,SpecialMove?1.f:0.f,Dt,16.f);
    AimAlpha=FMath::FInterpTo(AimAlpha,BodyState.bAiming?1.f:0.f,Dt,12.f);
    const bool Sprint=BodyState.bSprinting&&BodyState.Action==EFPSBodyAction::None&&!BodyState.bCrouched&&!SpecialMove;
    SprintAlpha=FMath::FInterpTo(SprintAlpha,Sprint?1.f:0.f,Dt,10.f);
    if(bFalling){AirTime+=Dt;LandTime=1.f;}else{if(bPreviouslyFalling)LandTime=0.f;else LandTime+=Dt;AirTime=0.f;}
    bPreviouslyFalling=bFalling;
    AirAlpha=FMath::FInterpTo(AirAlpha,bFalling||LandTime<.16f?1.f:0.f,Dt,14.f);
    const bool Gun=BodyState.Family==TEXT("Rifle")||BodyState.Family==TEXT("Pistol");
    const bool HasUpper=Gun&&!BodyState.bDual&&(BodyState.Action==EFPSBodyAction::Reload||BodyState.Action==EFPSBodyAction::ReloadEmpty||BodyState.Action==EFPSBodyAction::Equip);
    if(HasUpper)UpperState=BodyState;
    UpperAlpha=FMath::FInterpTo(UpperAlpha,HasUpper?1.f:0.f,Dt,15.f);
}
FAnimInstanceProxy* UFPSPlayerBodyAnimInstance::CreateAnimInstanceProxy(){return new FPSBodyAnimation::FProxy(this);}
void UFPSPlayerBodyAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
