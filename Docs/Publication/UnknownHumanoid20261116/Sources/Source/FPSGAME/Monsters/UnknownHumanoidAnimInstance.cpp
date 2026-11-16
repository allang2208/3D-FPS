#include "UnknownHumanoidAnimInstance.h"
#include "UnknownHumanoid.h"
#include "../Characters/FPSBodySpineBlend.h"
#include "../Characters/FPSBodyGunAim.h"
#include "../Characters/FPSBodyStrideTiming.h"
#include "../Characters/FPSBodyMeleeTiming.h"
#include "../Characters/FPSBodyBowMotion.h"
#include "../Weapons/Kukri/KukriSweepClock.h"
#include "../Characters/FPSBodyWarhammerMotion.h"
#include "../Production/ProductionBluntCombo.h"
#include "UnknownHumanoidTurnPose.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNode_SequencePlayer.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimNode_TransitionPoseEvaluator.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"
#include "AnimNodes/AnimNode_LayeredBoneBlend.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"

namespace
{
    // This graph lives in a native proxy. Cache evaluated poses directly so
    // transitions also work during the mesh's first (zero-delta) evaluation.
    struct FUnknownPoseTransition : FAnimNode_Base
    {
        FPoseLink Source;
        FAnimNode_TransitionPoseEvaluator Poses[2];
        int32 LastOutput = 0;
        bool bHasOutput = false;
        float PendingDuration = 0.f, Duration = 0.f, Elapsed = 0.f;
        float LiveLegWeight = 0.f;
        bool bBlendAttachmentCurves = false;
        const FQuat* NaturalLower = nullptr;
        FQuat NaturalHistory[2] = {FQuat::Identity, FQuat::Identity};
        const FTransform* NaturalGrip = nullptr;
        FTransform GripHistory[2];
        FBoneReference RightHand{TEXT("hand_r")}, LeftHand{TEXT("hand_l")};
        bool bPairedGrip = false;
        bool bUseEquipmentGrip = false;
        FTransform EquipmentGrip = FTransform::Identity;
        FFPSBodySpineBlend Spine;
        TArray<bool> UpperBones;
        TArray<FPerBoneBlendWeight> BoneWeights;

        void RequestBlend(float Seconds)
        {
            PendingDuration = PendingDuration > 0.f ? FMath::Min(PendingDuration, Seconds) : Seconds;
        }

        void ClearHistory()
        {
            bHasOutput = false;
            PendingDuration = Duration = Elapsed = 0.f;
        }

        virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override
        {
            ClearHistory();
            Source.Initialize(Context);
        }

        virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
        {
            ClearHistory();
            Source.CacheBones(Context);
            const auto& Bones = Context.AnimInstanceProxy->GetRequiredBones();
            Spine.Initialize(Bones);
            RightHand.Initialize(Bones); LeftHand.Initialize(Bones);
            UpperBones.Init(false, Bones.GetCompactPoseNumBones());
            BoneWeights.SetNum(Bones.GetCompactPoseNumBones());
            if (Spine.Lower.IsValidToEvaluate(Bones))
                for (int32 I = 0; I < UpperBones.Num(); ++I)
                    for (auto Bone = FCompactPoseBoneIndex(I); Bone != INDEX_NONE; Bone = Bones.GetParentBoneIndex(Bone))
                        if (Bone == Spine.Lower.GetCompactPoseIndex(Bones)) { UpperBones[I] = true; break; }
        }

        virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
        {
            Elapsed = FMath::Min(Duration, Elapsed + Context.GetDeltaTime());
            Source.Update(Context);
        }

        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            Source.Evaluate(Output);
            FQuat Natural = NaturalLower ? *NaturalLower : FQuat::Identity;
            FTransform Grip = NaturalGrip ? *NaturalGrip : FTransform::Identity;
            if (PendingDuration > 0.f)
            {
                // Retain the previous blended animation, before the procedural
                // waist/foot corrections. Moving legs keep their current sample.
                LastOutput = 1 - LastOutput;
                Duration = bHasOutput ? PendingDuration : 0.f;
                Elapsed = PendingDuration = 0.f;
            }
            if (Elapsed < Duration)
            {
                FPoseContext Previous(Output);
                Poses[1 - LastOutput].Evaluate_AnyThread(Previous);
                FPoseContext Current(Output); Current = Output;
                const float OldWeight = 1.f - FMath::SmoothStep(0.f, Duration, Elapsed);
                for (int32 I = 0; I < BoneWeights.Num(); ++I)
                {
                    BoneWeights[I].SourceIndex = 0;
                    BoneWeights[I].BlendWeight = OldWeight * (UpperBones[I] ? 1.f : 1.f - LiveLegWeight);
                }
                FAnimationPoseData Result(Output);
                // Keep live moving feet. Mesh-space rotation blending prevents
                // unrelated old/new pelvis yaw from twisting the waist mid-fade.
                FAnimationRuntime::BlendPosesPerBoneFilter(Current.Pose, MakeArrayView(&Previous.Pose, 1),
                    Current.Curve, MakeArrayView(&Previous.Curve, 1), Current.CustomAttributes,
                    MakeArrayView(&Previous.CustomAttributes, 1), Result, BoneWeights,
                    FAnimationRuntime::EBlendPosesPerBoneFilterFlags::MeshSpaceRotation, ECurveBlendOption::UseBasePose);
                // Bow grip/nock curves must fade with the hands, rather than
                // snapping the attached bow to the next take ahead of the pose.
                if (bBlendAttachmentCurves)
                {
                    bool PreviousBow=false,CurrentBow=false;
                    Previous.Curve.Get(FPSBodyBowMotion::GripCurves[0],PreviousBow);
                    Current.Curve.Get(FPSBodyBowMotion::GripCurves[0],CurrentBow);
                    // Dual blades have no bow attachment curves. Blending
                    // those missing values as zero would drag the bow to the
                    // wrist during the return, despite a smooth body pose.
                    if (PreviousBow && CurrentBow) Output.Curve.Lerp(Current.Curve,Previous.Curve,OldWeight);
                }
                Natural = FQuat::Slerp(Natural, NaturalHistory[1 - LastOutput], OldWeight).GetNormalized();
                FTransform BlendedGrip; BlendedGrip.Blend(Grip, GripHistory[1 - LastOutput], OldWeight);
                Grip = BlendedGrip;
            }
            // Cache before the correction: feeding corrected spine rotations
            // back into the next fade would progressively over-correct the waist.
            Poses[LastOutput].CachePose(Output);
            NaturalHistory[LastOutput] = Natural;
            GripHistory[LastOutput] = Grip;
            bHasOutput = true;
            if (LiveLegWeight > ZERO_ANIMWEIGHT_THRESH)
            {
                FCSPose<FCompactPose> Pose; Pose.InitPose(Output.Pose);
                Spine.Distribute(Pose, Natural);
                FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose, Output.Pose);
            }
            const auto& Bones=Output.Pose.GetBoneContainer();
            if (bPairedGrip && (bUseEquipmentGrip||Elapsed<Duration) && RightHand.IsValidToEvaluate(Bones) && LeftHand.IsValidToEvaluate(Bones))
            {
                // Match the player's two-handed grip: blending two arm
                // chains independently separates the support palm from the haft.
                // Fitted native takes need this only during their fade. Generic
                // sword donors use the actual equipped handle, like the player.
                FCSPose<FCompactPose> Pose; Pose.InitPose(Output.Pose);
                const auto Hand=LeftHand.GetCompactPoseIndex(Bones), Elbow=Bones.GetParentBoneIndex(Hand);
                const auto Shoulder=Bones.GetParentBoneIndex(Elbow);
                FTransform Root=Pose.GetComponentSpaceTransform(Shoulder), Joint=Pose.GetComponentSpaceTransform(Elbow);
                FTransform Tip=Pose.GetComponentSpaceTransform(Hand);
                FTransform Goal=(bUseEquipmentGrip?EquipmentGrip:Grip)*Pose.GetComponentSpaceTransform(RightHand.GetCompactPoseIndex(Bones));
                const FVector H=Root.GetLocation(), E=Joint.GetLocation(), W=Tip.GetLocation();
                const double Upper=FVector::Distance(H,E), Lower=FVector::Distance(E,W);
                Goal.SetLocation(H+(Goal.GetLocation()-H).GetClampedToMaxSize((Upper+Lower)*.995));
                const FVector OldAxis=(W-H).GetSafeNormal(), NewAxis=(Goal.GetLocation()-H).GetSafeNormal();
                FVector Bend=(E-H)-OldAxis*FVector::DotProduct(E-H,OldAxis);
                Bend=FQuat::FindBetweenNormals(OldAxis,NewAxis).RotateVector(Bend);
                Bend.Normalize();
                AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,H+Bend*80.f,Goal.GetLocation(),Upper,Lower,false,1.,1.);
                Tip.SetRotation(Goal.GetRotation());
                TArray<FBoneTransform,TInlineAllocator<3>> Changes;
                Changes.Emplace(Shoulder,Root); Changes.Emplace(Elbow,Joint); Changes.Emplace(Hand,Tip);
                Pose.LocalBlendCSBoneTransforms(Changes,1.f);
                FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Output.Pose);
            }
        }

        virtual bool NeedsDynamicReset() const override { return true; }
        virtual void ResetDynamics(ETeleportType) override { ClearHistory(); }
        virtual void GatherDebugData(FNodeDebugData& DebugData) override { Source.GatherDebugData(DebugData); }
    };

    struct FUnknownAttackPlayer : FAnimNode_SequencePlayer_Standalone
    {
        FBoneReference LowerSpine{TEXT("spine_01")};
        FBoneReference RightHand{TEXT("hand_r")}, LeftHand{TEXT("hand_l")};
        FQuat LowerRotation=FQuat::Identity;
        FTransform SupportGrip=FTransform::Identity;
        bool bCaptureGrip=false;

        virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
        {
            FAnimNode_SequencePlayer_Standalone::CacheBones_AnyThread(Context);
            LowerSpine.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
            RightHand.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
            LeftHand.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
        }
        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            FAnimNode_SequencePlayer_Standalone::Evaluate_AnyThread(Output);
            const auto& Bones=Output.Pose.GetBoneContainer();
            if (LowerSpine.IsValidToEvaluate(Bones))
                LowerRotation=Output.Pose[LowerSpine.GetCompactPoseIndex(Bones)].GetRotation();
            if (bCaptureGrip && RightHand.IsValidToEvaluate(Bones) && LeftHand.IsValidToEvaluate(Bones))
            {
                FCSPose<FCompactPose> Pose; Pose.InitPose(Output.Pose);
                SupportGrip=Pose.GetComponentSpaceTransform(LeftHand.GetCompactPoseIndex(Bones))
                    .GetRelativeTransform(Pose.GetComponentSpaceTransform(RightHand.GetCompactPoseIndex(Bones)));
            }
        }
    };

    struct FUnknownMeleeLayers : FAnimNode_LayeredBoneBlend
    {
        bool bTravelOnly = true;
        bool bCarry = false;
        FUnknownAttackPlayer* Attack=nullptr;
        FUnknownAttackPlayer* Hold=nullptr;
        FBoneReference Lower{TEXT("spine_01")};
        FQuat NaturalLower=FQuat::Identity;
        FTransform NaturalGrip=FTransform::Identity;

        FUnknownMeleeLayers()
        {
            AddPose();
            auto& Filters = LayerSetup[0].BranchFilters;
            // Transfer travel from the root through the pelvis and feet. Keep the
            // authored swing above the waist, including its rotation in mesh space.
            Filters.AddDefaulted_GetRef().BoneName = TEXT("root");
            auto& Spine = Filters.AddDefaulted_GetRef();
            Spine.BoneName = TEXT("spine_01");
            Spine.BlendDepth = -1;
            bMeshSpaceRotationBlend = true;
            CurveBlendOption = ECurveBlendOption::UseBasePose;
        }

        virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
        {
            if (bTravelOnly) BlendPoses[0].Update(Context);
            else FAnimNode_LayeredBoneBlend::Update_AnyThread(Context);
        }

        virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
        {
            FAnimNode_LayeredBoneBlend::CacheBones_AnyThread(Context);
            Lower.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
        }

        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            if (bTravelOnly) BlendPoses[0].Evaluate(Output);
            else FAnimNode_LayeredBoneBlend::Evaluate_AnyThread(Output);
            const auto& Bones=Output.Pose.GetBoneContainer();
            if (Lower.IsValidToEvaluate(Bones))
                NaturalLower=!bTravelOnly&&Attack?Attack->LowerRotation:bCarry&&Hold?Hold->LowerRotation:
                    Output.Pose[Lower.GetCompactPoseIndex(Bones)].GetRotation();
            NaturalGrip=!bTravelOnly&&Attack?Attack->SupportGrip:bCarry&&Hold?Hold->SupportGrip:FTransform::Identity;
        }
    };

    struct FUnknownImplementLayers : FAnimNode_LayeredBoneBlend
    {
        TArray<TPair<int32,FQuat>> Fingers;
        bool bHolding=false;
        bool bFitFingers=false;
        bool bRightFingersOnly=false;
        int32 FingerSourceCount=INDEX_NONE;

        virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
        {
            if (bHolding) FAnimNode_LayeredBoneBlend::Update_AnyThread(Context);
            else BasePose.Update(Context);
        }
        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            if (bHolding) FAnimNode_LayeredBoneBlend::Evaluate_AnyThread(Output);
            else BasePose.Evaluate(Output);
            if (!bFitFingers) return;
            const auto& Bones=Output.Pose.GetBoneContainer();
            for (const auto& Finger:Fingers)
            {
                const auto Bone=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Finger.Key));
                if (Bone!=INDEX_NONE) Output.Pose[Bone].SetRotation(Finger.Value);
            }
        }
    };

}

struct FUnknownHumanoidAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequencePlayer_Standalone Idle;
    FAnimNode_SequenceEvaluator_Standalone WalkA, WalkB, RunA, RunB;
    FAnimNode_SequenceEvaluator_Standalone CrouchIdle,CrouchA,CrouchB;
    FUnknownAttackPlayer Hold;
    FAnimNode_LayeredBoneBlend Carry;
    FUnknownAttackPlayer Action;
    FAnimNode_TwoWayBlend Walk, Run, Pace, Travel;
    FAnimNode_TwoWayBlend CrouchWalk,CrouchTravel,CrouchBlend;
    FUnknownMeleeLayers Layers;
    FAnimNode_SequencePlayer_Standalone StaffCarry, BookCarry;
    FUnknownImplementLayers Implements;
    FUnknownPoseTransition Transition;
    FFPSBodyGunAimNode GunAim;
    FUnknownTurnPose Turn;
    FName LastKey;
    bool bLastBlades=false;
    bool bGunAiming=false;
    uint16 ActionSerial = 0;
    TMap<const UAnimSequence*, FPSBodyAnimation::FStrideTiming> Strides;
    float GaitCycles = 0.f, Heading = 0.f;
    bool bHasHeading = false;
    FPSBodyWarhammerMotion::FDonorPlayback HammerPlayback;
    float HammerContact = .4f, HammerRelease = .65f;
    bool bHammerDonorClock = false;
    bool bNativeMeleeGrip = false;

    const FPSBodyAnimation::FStrideTiming& Timing(const UAnimSequence* Clip, const UAnimSequence* Reference = nullptr)
    {
        if (const auto* Existing = Strides.Find(Clip)) return *Existing;
        return Strides.Add(Clip, FPSBodyAnimation::FStrideTiming(Clip, Reference));
    }

    explicit FUnknownHumanoidAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Walk.A.SetLinkNode(&WalkA); Walk.B.SetLinkNode(&WalkB);
        Run.A.SetLinkNode(&RunA); Run.B.SetLinkNode(&RunB);
        Pace.A.SetLinkNode(&Walk);
        Pace.B.SetLinkNode(&Run);
        Travel.A.SetLinkNode(&Idle);
        Travel.B.SetLinkNode(&Pace);
        CrouchWalk.A.SetLinkNode(&CrouchA);CrouchWalk.B.SetLinkNode(&CrouchB);
        CrouchTravel.A.SetLinkNode(&CrouchIdle);CrouchTravel.B.SetLinkNode(&CrouchWalk);
        CrouchBlend.A.SetLinkNode(&Travel);CrouchBlend.B.SetLinkNode(&CrouchTravel);
        Layers.BasePose.SetLinkNode(&Action);
        Layers.Attack=&Action;
        Layers.Hold=&Hold;
        Carry.BasePose.SetLinkNode(&CrouchBlend);
        Carry.AddPose(); Carry.BlendPoses[0].SetLinkNode(&Hold);
        auto& CarrySpine=Carry.LayerSetup[0].BranchFilters.AddDefaulted_GetRef();
        CarrySpine.BoneName=TEXT("spine_01"); CarrySpine.BlendDepth=3;
        Carry.bMeshSpaceRotationBlend=true;
        Layers.BlendPoses[0].SetLinkNode(&Carry);
        Implements.BasePose.SetLinkNode(&Layers);
        Implements.AddPose();
        Implements.AddPose();
        Implements.LayerSetup[0].BranchFilters.AddDefaulted_GetRef().BoneName=TEXT("clavicle_r");
        Implements.LayerSetup[1].BranchFilters.AddDefaulted_GetRef().BoneName=TEXT("clavicle_l");
        Implements.BlendPoses[0].SetLinkNode(&StaffCarry);
        Implements.BlendPoses[1].SetLinkNode(&BookCarry);
        Implements.CurveBlendOption=ECurveBlendOption::UseBasePose;
        StaffCarry.SetPlayRate(.35f);
        BookCarry.SetPlayRate(0.f);
        Hold.SetLoopAnimation(true);
        Action.SetLoopAnimation(false);
        Transition.Source.SetLinkNode(&Implements);
        Transition.NaturalLower=&Layers.NaturalLower;
        Transition.NaturalGrip=&Layers.NaturalGrip;
        GunAim.Source.SetLinkNode(&Transition);
        Turn.Source.SetLinkNode(&GunAim);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &Turn; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &WalkA, &WalkB, &RunA, &RunB, &Walk, &Run, &Hold, &Pace, &Travel, &Carry,
            &CrouchIdle,&CrouchA,&CrouchB,&CrouchWalk,&CrouchTravel,&CrouchBlend,
            &Action, &Layers, &StaffCarry, &BookCarry, &Implements, &Transition, &GunAim, &Turn});
    }

    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Pawn = Cast<AUnknownHumanoid>(Instance->TryGetPawnOwner());
        if (!Pawn || !Pawn->bVisualReady) return;

        if (!Idle.GetSequence())
        {
            Idle.SetSequence(Pawn->Clips.FindRef(TEXT("Idle")));
            StaffCarry.SetSequence(Pawn->Clips.FindRef(TEXT("StaffCarry")));
            BookCarry.SetSequence(Pawn->Clips.FindRef(TEXT("BookCarry")));
        }

        if (Pawn->Loadout.Role==EUnknownRole::Bow)
            Idle.SetSequence(Pawn->Clips.FindRef(Pawn->bBowBlades?TEXT("DualIdle"):TEXT("Idle")));
        Hold.SetSequence(Idle.GetSequence());
        const bool GunAiming=Pawn->Loadout.Role==EUnknownRole::Gun && Pawn->bGunTracking && !Pawn->Controlled() &&
            (Pawn->Motion.Action==EUnknownAction::Ready || Pawn->Motion.Action==EUnknownAction::Fire);
        GunAim.Guns[0]=Pawn->GunAimFrame;
        GunAim.bPaired=true; GunAim.bUseTarget=true;
        GunAim.Enabled[0]=GunAiming;
        GunAim.bFitSupport=Pawn->Loadout.Role==EUnknownRole::Gun&&Pawn->bHasGunSupport&&
            (Pawn->Motion.Action==EUnknownAction::Ready||Pawn->Motion.Action==EUnknownAction::Fire);
        GunAim.SupportFromRight=Pawn->GunSupportGrip;
        GunAim.Recoil[0]=3.f*FMath::Clamp(1.f-(Pawn->ServerTime()-Pawn->LastShotTime)/.1f,0.f,1.f);
        if(const auto* Mesh=Instance->GetSkelMeshComponent())
        {
            // Torso residual handles the actor's deliberate turn lag. Bound a
            // newly acquired target behind the actor until the feet turn around.
            const FVector ToTarget=FVector(Pawn->GunAimPoint)-Pawn->AimOrigin();
            const FRotator Aim=ToTarget.Rotation();
            const float Yaw=Pawn->GetActorRotation().Yaw+FMath::Clamp(
                FMath::FindDeltaAngleDegrees(Pawn->GetActorRotation().Yaw,Aim.Yaw),-65.f,65.f);
            const FVector Point=Pawn->AimOrigin()+FRotator(FMath::Clamp(Aim.Pitch,-80.f,80.f),Yaw,0).Vector()*ToTarget.Size();
            GunAim.Target=Mesh->GetComponentTransform().InverseTransformPosition(Point);
            GunAim.Direction=Mesh->GetComponentTransform().InverseTransformVectorNoScale((Point-Pawn->AimOrigin()).GetSafeNormal());
        }
        if (GunAiming!=bGunAiming)
        {
            Transition.RequestBlend(GunAiming?FMath::Clamp(Pawn->Motion.Windup,.06f,.14f):.14f);
            bGunAiming=GunAiming;
        }
        // The existing pistol/rifle idle is ADS. Keep its upper body aimed
        // while the eight-direction gait still owns both travelling legs.
        Carry.BlendWeights[0]=(Pawn->Loadout.Role==EUnknownRole::Melee || Pawn->Loadout.Role==EUnknownRole::Bow || Pawn->Loadout.Role==EUnknownRole::Gun)?1.f:0.f;
        Layers.bCarry=Carry.BlendWeights[0]>0.f;
        const float Speed = Pawn->GetVelocity().Size2D();
        const float Dt = FMath::Max(DeltaSeconds, 0.f);
        static const TCHAR* Directions[]={TEXT("Fwd"),TEXT("Fwd_Right"),TEXT("Right"),TEXT("Bwd_Right"),TEXT("Bwd"),TEXT("Bwd_Left"),TEXT("Left"),TEXT("Fwd_Left")};
        if (Speed > 2.f)
        {
            const FVector Local=Pawn->GetActorQuat().UnrotateVector(Pawn->GetVelocity());
            const float Angle = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
            if (!bHasHeading) Heading=Angle;
            else Heading=FMath::UnwindDegrees(Heading+FMath::FindDeltaAngleDegrees(Heading,Angle)*FMath::Clamp(Dt*18.f,0.f,1.f));
            bHasHeading=true;
        }
        else bHasHeading=false;
        const float Sector=FMath::Fmod(Heading+360.f,360.f)/45.f;
        const int32 A=FMath::FloorToInt(Sector)%8, B=(A+1)%8;
        Walk.Alpha=Run.Alpha=FMath::Frac(Sector);
        const auto ClipFor=[&](const TCHAR* Gait,int32 Direction)
        {
            auto* Clip=Pawn->Clips.FindRef(FName(*(FString(Gait)+TEXT(".")+Directions[Direction]))).Get();
            if (!Clip) Clip=Pawn->Clips.FindRef(FName(Gait)).Get();
            auto* Reference=Pawn->Clips.FindRef(FName(*(FString(Gait)+(Direction>=3&&Direction<=5?TEXT(".Bwd"):TEXT(".Fwd"))))).Get();
            Timing(Clip,Reference);
            return Clip;
        };
        auto* WA=ClipFor(TEXT("Walk"),A); auto* WB=ClipFor(TEXT("Walk"),B);
        auto* RA=ClipFor(TEXT("Run"),A); auto* RB=ClipFor(TEXT("Run"),B);
        auto* CI=Pawn->Clips.FindRef(TEXT("CrouchIdle")).Get();
        auto* CA=Pawn->Clips.FindRef(FName(*(FString(TEXT("Crouch."))+Directions[A]))).Get();
        auto* CB=Pawn->Clips.FindRef(FName(*(FString(TEXT("Crouch."))+Directions[B]))).Get();
        const bool HasCrouch=CI&&CA&&CB;
        if(HasCrouch)
        {
            Timing(CA,Pawn->Clips.FindRef(A>=3&&A<=5?TEXT("Crouch.Bwd"):TEXT("Crouch.Fwd")));
            Timing(CB,Pawn->Clips.FindRef(B>=3&&B<=5?TEXT("Crouch.Bwd"):TEXT("Crouch.Fwd")));
        }
        CrouchBlend.Alpha=FMath::FInterpConstantTo(CrouchBlend.Alpha,HasCrouch&&Pawn->bIsCrouched?1.f:0.f,Dt,8.f);
        CrouchWalk.Alpha=Walk.Alpha;
        const float TravelWeight = WA && WB ? FMath::SmoothStep(2.f,35.f,Speed) : 0.f;
        Travel.Alpha = TravelWeight;
        CrouchTravel.Alpha=TravelWeight;
        Pace.Alpha = FMath::FInterpTo(Pace.Alpha,FMath::SmoothStep(400.f,520.f,Speed),Dt,12.f);
        const float WalkDistance=FMath::Lerp(Timing(WA).Distance(300.f),Timing(WB).Distance(300.f),Walk.Alpha);
        const float RunDistance=FMath::Lerp(Timing(RA).Distance(RA==WA?300.f:600.f),Timing(RB).Distance(RB==WB?300.f:600.f),Run.Alpha);
        const float CrouchDistance=HasCrouch?FMath::Lerp(Timing(CA).Distance(150.f),Timing(CB).Distance(150.f),CrouchWalk.Alpha):WalkDistance;
        const float Distance=FMath::Lerp(FMath::Lerp(WalkDistance,RunDistance,Pace.Alpha),CrouchDistance,CrouchBlend.Alpha);
        GaitCycles=FMath::Fmod(GaitCycles+Dt*Speed/FMath::Max(Distance,1.f),12.f);
        const auto Sample=[&](FAnimNode_SequenceEvaluator_Standalone& Player,UAnimSequence* Clip)
        {
            Player.SetSequence(Clip); Player.SetShouldLoop(true); Player.SetTeleportToExplicitTime(true);
            Player.SetExplicitTime(Timing(Clip).Sample(GaitCycles));
        };
        Sample(WalkA,WA); Sample(WalkB,WB); Sample(RunA,RA); Sample(RunB,RB);
        Sample(CrouchA,HasCrouch?CA:WA);Sample(CrouchB,HasCrouch?CB:WB);
        CrouchIdle.SetSequence(HasCrouch?CI:Idle.GetSequence());CrouchIdle.SetExplicitTime(0.f);

        const FUnknownMotion& Motion = Pawn->Motion;
        const bool bLiveLegs=Motion.Action!=EUnknownAction::Dead && Motion.Action!=EUnknownAction::Stagger;
        const bool bHammer=Pawn->Clips.Contains(TEXT("HammerSwing"));
        const bool bSword=Pawn->Loadout.Role==EUnknownRole::Melee&&!bHammer&&!Pawn->Clips.Contains(TEXT("BladeSwing"));
        Transition.bPairedGrip=(bHammer||bSword)&&bLiveLegs;
        Transition.bUseEquipmentGrip=bSword&&Pawn->bHasMeleeSupport;
        Transition.EquipmentGrip=Pawn->MeleeSupportGrip;
        Action.bCaptureGrip=Hold.bCaptureGrip=Transition.bPairedGrip;
        Transition.LiveLegWeight=bLiveLegs?FMath::Max(TravelWeight,CrouchBlend.Alpha):0.f;
        Transition.bBlendAttachmentCurves=Pawn->Loadout.Role==EUnknownRole::Bow && !Pawn->bBowBlades;
        if (const auto* Mesh=Instance->GetSkelMeshComponent())
            Turn.Prepare(*Mesh,Speed,bLiveLegs && !Pawn->Controlled(),
                Motion.Action!=EUnknownAction::Swing,Dt);
        Implements.bHolding=(Pawn->Loadout.Role==EUnknownRole::Magic || Pawn->bBowBlades) && Motion.Action!=EUnknownAction::Dead && Motion.Action!=EUnknownAction::Stagger;
        const bool GunFingers=Pawn->Loadout.Role==EUnknownRole::Gun&&Pawn->bHasGunSupport;
        Implements.bFitFingers=bLiveLegs&&(Implements.bHolding||Pawn->Loadout.Role==EUnknownRole::Melee||GunFingers);
        const bool RightOnly=GunFingers&&Motion.Action==EUnknownAction::Reload;
        if(Implements.FingerSourceCount!=Pawn->ImplementFingers.Num()||Implements.bRightFingersOnly!=RightOnly)
        {
            Implements.FingerSourceCount=Pawn->ImplementFingers.Num();Implements.bRightFingersOnly=RightOnly;
            Implements.Fingers=Pawn->ImplementFingers;
            // The reload frees the operating left hand; the carrying right
            // palm still owns the gun and keeps that weapon's finger contact.
            if(RightOnly)if(const auto* Mesh=Instance->GetSkelMeshComponent()->GetSkeletalMeshAsset())
            {
                const auto& Ref=Mesh->GetRefSkeleton();const int32 Palm=Ref.FindBoneIndex(TEXT("hand_r"));
                Implements.Fingers.RemoveAll([&](const auto& Finger){return !Ref.BoneIsChildOf(Finger.Key,Palm);});
            }
        }
        if (Implements.bHolding)
        {
            Implements.BlendWeights[0]=StaffCarry.GetSequence() && Motion.Action!=EUnknownAction::Cast ? 1.f : 0.f;
            Implements.BlendWeights[1]=BookCarry.GetSequence() ? 1.f : 0.f;
        }
        float Start = Motion.Started, Duration = Motion.Duration;
        const float Now = Pawn->ServerTime();
        FName Key;
        switch (Motion.Action)
        {
        case EUnknownAction::Swing: Key = Pawn->bBowBlades?TEXT("DualSwing"):bHammer?TEXT("HammerSwing"):Pawn->Clips.Contains(TEXT("BladeSwing"))?TEXT("BladeSwing"):TEXT("Swing"); break;
        case EUnknownAction::DrawBow:
            if (Now<Start+Motion.Preparation) { Key=TEXT("BowDraw"); Duration=Motion.Preparation; }
            else if (Now<Start+Motion.Windup && Pawn->Clips.Contains(TEXT("BowHold")))
            { Key=TEXT("BowHold"); Start+=Motion.Preparation; Duration=Motion.Windup-Motion.Preparation; }
            else if (Now<Start+Motion.Windup) { Key=TEXT("BowDraw"); Duration=Motion.Preparation; }
            else { Key=TEXT("BowRelease"); Start+=Motion.Windup; Duration-=Motion.Windup; }
            break;
        case EUnknownAction::Reload: Key = TEXT("Reload"); break;
        case EUnknownAction::Stagger: Key = TEXT("Stagger"); break;
        case EUnknownAction::Dead: Key = TEXT("Dead"); break;
        case EUnknownAction::Cast:
            if (Now < Start + Motion.Preparation) { Key = TEXT("Gather"); Duration=Motion.Preparation; }
            else { Key = TEXT("Release"); Start+=Motion.Preparation; Duration-=Motion.Preparation; }
            break;
        default: break;
        }

        if (Key!=LastKey || bLastBlades!=Pawn->bBowBlades || (Key!=NAME_None && ActionSerial!=Motion.Serial))
        {
            Transition.RequestBlend(Motion.Action==EUnknownAction::SwapWeapon?FMath::Clamp(Motion.Duration*.7f,.14f,.35f):
                Key==TEXT("BowRelease")||Key==TEXT("Release")?.06f:
                Motion.Action==EUnknownAction::Dead?.10f:.14f);
            LastKey=Key; bLastBlades=Pawn->bBowBlades;
        }
        auto* Clip = Key.IsNone() ? nullptr : Pawn->Clips.FindRef(Key).Get();
        Layers.bTravelOnly = !Clip;
        if (!Clip) return;
        Action.SetLoopAnimation(Key==TEXT("BowHold"));

        Layers.BlendWeights[0] = bLiveLegs ? FMath::Max(TravelWeight,CrouchBlend.Alpha) : 0.f;
        // While swinging, the stationary end of this blend is the attack's own stance.
        if (bLiveLegs) Travel.Alpha = 1.f;
        if (Action.GetSequence() != Clip || ActionSerial != Motion.Serial)
        {
            ActionSerial = Motion.Serial;
            const float Length = Clip->GetPlayLength();
            const float Rate = Duration > 0.f ? Length / Duration : 1.f;
            const float Position = FMath::Clamp((Now - Start) * Rate, 0.f, Length);
            Action.SetSequence(Clip);
            Action.SetPlayRate(Rate);
            Action.SetStartPosition(Position);
            Action.SetAccumulatedTime(Position);
            HammerPlayback.Reset();
            HammerContact=Key==TEXT("Release")?2.f/3.f:.4f; HammerRelease=.65f; bHammerDonorClock=false; bNativeMeleeGrip=false;
            for (const auto& Marker:Clip->AuthoredSyncMarkers)
            {
                if (Marker.MarkerName==TEXT("Contact")) HammerContact=Marker.Time/FMath::Max(.001f,Length);
                if (Marker.MarkerName==TEXT("Release")) HammerRelease=Marker.Time/FMath::Max(.001f,Length);
                if (Marker.MarkerName==TEXT("HammerDonorClock")) bHammerDonorClock=true;
                if (Marker.MarkerName==TEXT("NativeSwordGrip")) bNativeMeleeGrip=true;
            }
        }
        if (bNativeMeleeGrip) Transition.bUseEquipmentGrip=false;
        if (Motion.Action==EUnknownAction::Cast || Motion.Action==EUnknownAction::DrawBow)
        {
            // Sample the replicated action clock every frame. Route changes,
            // gait blends and a longer breath channel cannot restart this take.
            const float Length=Clip->GetPlayLength();
            float ActionSample=FMath::Clamp((Now-Start)/FMath::Max(Duration,.001f),0.f,1.f);
            if (Key==TEXT("BowHold")) ActionSample=FMath::Fmod(FMath::Max(0.f,Now-Start),FMath::Max(.001f,Length))/FMath::Max(.001f,Length);
            if (Motion.Action==EUnknownAction::Cast && Key==TEXT("Release"))
            {
                const float Age=Now-Motion.Started;
                const float RecoverStart=FMath::Max(Motion.Windup,Motion.Duration-Motion.Recovery);
                ActionSample=Age<Motion.Windup?HammerContact*FMath::Clamp(
                    (Age-Motion.Preparation)/FMath::Max(.001f,Motion.Windup-Motion.Preparation),0.f,1.f):
                    FMath::Lerp(HammerContact,1.f,FMath::Clamp((Age-RecoverStart)/FMath::Max(.001f,Motion.Recovery),0.f,1.f));
            }
            Action.SetPlayRate(0.f); Action.SetStartPosition(ActionSample*Length); Action.SetAccumulatedTime(ActionSample*Length);
        }
        else if (Key==TEXT("HammerSwing") && bHammerDonorClock && Motion.Windup>0.f)
        {
            // Same two-stage clock as the player: real attack age -> protected
            // hammer release -> authored third-person donor. Replicated windup
            // is also the authority's hit time, including attack-speed bonuses.
            const float BaseContact=Pawn->HammerBaseContact;
            const float Rate=BaseContact/Motion.Windup;
            const float Clock=ProductionBluntCombo::ClipTime(FMath::Max(0.f,Now-Start),Motion.Windup,
                Duration,BaseContact,Rate,0);
            FFPSBodyState State;
            State.Action=EFPSBodyAction::Strike; State.ActionVariant=TEXT("WarhammerSlash1");
            State.ActionProgress=FMath::Clamp(Clock/ProductionBluntCombo::SwingSeconds,0.f,1.f);
            State.ContactFraction=ProductionBluntCombo::ContactSeconds/ProductionBluntCombo::SwingSeconds;
            State.ActionEntryFraction=ProductionBluntCombo::Apex(0)/ProductionBluntCombo::SwingSeconds;
            State.ReleaseFraction=ProductionBluntCombo::Turn(0)/ProductionBluntCombo::SwingSeconds;
            const float Length=Clip->GetPlayLength();
            const float Position=HammerPlayback.Advance(State,Dt,Length,HammerContact*Length,HammerRelease*Length);
            Action.SetPlayRate(0.f); Action.SetStartPosition(Position); Action.SetAccumulatedTime(Position);
        }
        else if (Motion.Action==EUnknownAction::Swing && Motion.Duration>0.f)
        {
            float Progress=FMath::Clamp((Now-Start)/Duration,0.f,1.f);
            float Contact=Motion.Windup/Duration;
            float Release=RuneSwordRhythm::ContactEnd/RuneSwordRhythm::AttackEnd;
            const bool Blade=Key==TEXT("BladeSwing"),Pair=Key==TEXT("DualSwing");
            if (Blade||Pair)
            {
                const auto& Clock=KukriAttackTiming::FSweepClock::Get(Pair);
                Progress=Clock.AuthorSeconds(Now-Start,Clock.RateForDuration(Duration))/Clock.AuthorLength();
                Contact=Clock.ContactAuthor(0)/Clock.AuthorLength();
                Release=KukriRhythm::Swings[0].ContactEnd/Clock.AuthorLength();
            }
            // The pair contains both contacts on its authored clock. A remap
            // around only the right-hand marker would displace the left hit.
            const float AttackSample=Pair?Progress:FPSBodyMeleeTiming::ContactSample(
                Progress,Contact,Release,0.f,HammerContact,HammerRelease);
            const float Position=AttackSample*Clip->GetPlayLength();
            Action.SetPlayRate(0.f); Action.SetStartPosition(Position); Action.SetAccumulatedTime(Position);
        }
    }
};

UUnknownHumanoidAnimInstance::UUnknownHumanoidAnimInstance()
{
    // CharacterMovement owns displacement, even for clips with authored root travel.
    RootMotionMode = ERootMotionMode::IgnoreRootMotion;
}

FAnimInstanceProxy* UUnknownHumanoidAnimInstance::CreateAnimInstanceProxy()
{
    return new FUnknownHumanoidAnimProxy(this);
}

void UUnknownHumanoidAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy)
{
    delete Proxy;
}
