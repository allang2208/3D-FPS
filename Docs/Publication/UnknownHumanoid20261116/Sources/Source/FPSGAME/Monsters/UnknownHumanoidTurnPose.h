#pragma once
#include "Animation/AnimInstanceProxy.h"
#include "Animation/BoneReference.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

// Cosmetic stationary stepping only. Moving feet retain their authored gait;
// no actor displacement, root motion or terrain queries are introduced here.
struct FUnknownTurnPose : FAnimNode_Base
{
    FPoseLink Source;
    FBoneReference Feet[2] = {FBoneReference(TEXT("foot_l")), FBoneReference(TEXT("foot_r"))};
    FTransform Frame=FTransform::Identity, Anchors[2];
    FVector LastLocation=FVector::ZeroVector;
    float LastYaw=0.f, Cycles=0.f, Weight=0.f;
    int32 Lead=0;
    bool bInitialized=false, bCanPlant=false, bAnchored[2]={false,false};

    void ClearHistory()
    {
        bInitialized=bCanPlant=false; bAnchored[0]=bAnchored[1]=false;
        Weight=Cycles=0.f;
    }
    void Prepare(const USkeletalMeshComponent& Mesh,float Speed,bool Allowed,bool CanStep,float Delta)
    {
        Frame=Mesh.GetComponentTransform();
        const auto* Character=Cast<ACharacter>(Mesh.GetOwner());
        const auto* Move=Character?Character->GetCharacterMovement():nullptr;
        const bool Grounded=Move&&Move->IsMovingOnGround();
        const float Yaw=Frame.Rotator().Yaw;
        const float Turn=bInitialized?FMath::FindDeltaAngleDegrees(LastYaw,Yaw):0.f;
        if (!bInitialized || FVector::DistSquared(LastLocation,Frame.GetLocation())>FMath::Square(100.f) || FMath::Abs(Turn)>90.f)
            ClearHistory();
        const float Travel=bInitialized?Turn:0.f;
        LastYaw=Yaw; LastLocation=Frame.GetLocation(); bInitialized=true;
        bCanPlant=Allowed&&CanStep&&Grounded&&Speed<12.f;
        if (!Allowed || !Grounded) { Weight=0.f; bAnchored[0]=bAnchored[1]=false; return; }
        const bool Turning=bCanPlant&&Delta>UE_SMALL_NUMBER&&FMath::Abs(Travel)/Delta>20.f;
        if (Turning)
        {
            if (Weight<=ZERO_ANIMWEIGHT_THRESH) { Cycles=0.f; Lead=Travel>0.f?0:1; }
            Cycles=FMath::Fmod(Cycles+FMath::Abs(Travel)/120.f,1.f);
        }
        Weight=FMath::FInterpConstantTo(Weight,Turning?1.f:0.f,Delta,8.f);
        if (Weight<=ZERO_ANIMWEIGHT_THRESH) bAnchored[0]=bAnchored[1]=false;
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override
    { ClearHistory(); Source.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        ClearHistory(); Source.CacheBones(Context);
        for (auto& Foot:Feet) Foot.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override { Source.Update(Context); }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);
        if (Weight<=ZERO_ANIMWEIGHT_THRESH) return;
        FCSPose<FCompactPose> Pose; Pose.InitPose(Output.Pose);
        const auto& Bones=Output.Pose.GetBoneContainer();
        for (int32 I=0; I<2; ++I)
        {
            if (!Feet[I].IsValidToEvaluate(Bones)) continue;
            const auto Foot=Feet[I].GetCompactPoseIndex(Bones), Knee=Bones.GetParentBoneIndex(Foot);
            if (Knee==INDEX_NONE) continue;
            const auto Hip=Bones.GetParentBoneIndex(Knee);
            if (Hip==INDEX_NONE) continue;
            FTransform Root=Pose.GetComponentSpaceTransform(Hip), Joint=Pose.GetComponentSpaceTransform(Knee);
            FTransform Tip=Pose.GetComponentSpaceTransform(Foot), Goal=Tip;
            const float Phase=FMath::Frac(Cycles+(I==Lead?0.f:.5f));
            // Finish releasing the current support when travel/an attack starts;
            // dropping its anchor immediately would pop the ankle sideways.
            const bool Plant=(bCanPlant&&Phase>=.5f)||(!bCanPlant&&bAnchored[I]);
            if (Plant)
            {
                const FTransform World=Tip*Frame;
                if (!bAnchored[I]) { Anchors[I]=World; bAnchored[I]=true; }
                // Bound the plant before the knee can straighten or the feet cross.
                const FVector Offset=(Anchors[I].GetLocation()-World.GetLocation()).GetClampedToMaxSize(15.f);
                Anchors[I].SetLocation(World.GetLocation()+Offset);
                Goal=Anchors[I].GetRelativeTransform(Frame);
            }
            else
            {
                bAnchored[I]=false;
                Goal.AddToTranslation(FVector(0,0,Phase<.5f?FMath::Sin(Phase*2.f*PI)*6.f:0.f));
            }
            const FVector H=Root.GetLocation(), K=Joint.GetLocation(), F=Tip.GetLocation();
            const double Upper=FVector::Distance(H,K), Lower=FVector::Distance(K,F);
            const double Reach=FMath::Min(FVector::Distance(H,F)+.5,(Upper+Lower)*.995);
            FVector Target=Goal.GetLocation()-H;
            Target.Z=FMath::Clamp(Target.Z,-Reach*.999,Reach*.999);
            const double Radius=FMath::Sqrt(FMath::Max(0.,Reach*Reach-Target.Z*Target.Z));
            const double Horizontal=Target.Size2D();
            if (Horizontal>Radius&&Horizontal>UE_SMALL_NUMBER) { Target.X*=Radius/Horizontal; Target.Y*=Radius/Horizontal; }
            Goal.SetLocation(H+Target);
            const FVector OldAxis=(F-H).GetSafeNormal(), NewAxis=Target.GetSafeNormal();
            FVector Bend=(K-H)-OldAxis*FVector::DotProduct(K-H,OldAxis);
            Bend=FQuat::FindBetweenNormals(OldAxis,NewAxis).RotateVector(Bend);
            if (!Bend.Normalize()) Bend=(FVector::RightVector-NewAxis*FVector::DotProduct(FVector::RightVector,NewAxis)).GetSafeNormal();
            AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,H+Bend*80.f,Goal.GetLocation(),Upper,Lower,false,1.,1.);
            Tip.SetRotation(Goal.GetRotation());
            TArray<FBoneTransform,TInlineAllocator<3>> Changes;
            Changes.Emplace(Hip,Root); Changes.Emplace(Knee,Joint); Changes.Emplace(Foot,Tip);
            Pose.LocalBlendCSBoneTransforms(Changes,Weight);
        }
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Output.Pose);
    }
    virtual bool NeedsDynamicReset() const override { return true; }
    virtual void ResetDynamics(ETeleportType) override { ClearHistory(); }
    virtual void GatherDebugData(FNodeDebugData& DebugData) override { Source.GatherDebugData(DebugData); }
};
