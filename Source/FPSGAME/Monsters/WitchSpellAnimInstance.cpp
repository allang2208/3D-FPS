#include "WitchSpellAnimInstance.h"
#include "WitchMonster.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "TwoBoneIK.h"

// Native graph node: no added bones and no change to the original mesh/cloth skin.
struct FWitchSpellSupport : FAnimNode_SkeletalControlBase
{
    FBoneReference Hip, Upper[2], Knee[2], Foot[2], Toe[2];
    FVector Anchor[2] = {FVector::ZeroVector, FVector::ZeroVector};
    FVector GroundNormal[2] = {FVector::UpVector, FVector::UpVector};
    float GroundHeight[2] = {0.f, 0.f};
    bool bGround[2] = {false, false};
    bool bSpell = false;
    uint32 Generation = 0, CapturedGeneration = MAX_uint32;
    float LockWeight = 0.f, GroundBlend = 1.f;

    FWitchSpellSupport()
    {
        Hip.BoneName = TEXT("Hips");
        for (int32 I = 0; I < 2; ++I)
        {
            const FString Side = I == 0 ? TEXT("Left") : TEXT("Right");
            Upper[I].BoneName = FName(*(Side + TEXT("UpLeg")));
            Knee[I].BoneName = FName(*(Side + TEXT("Leg")));
            Foot[I].BoneName = FName(*(Side + TEXT("Foot")));
            Toe[I].BoneName = FName(*(Side + TEXT("ToeBase")));
        }
        Alpha = 1.f;
    }
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override
    {
        Hip.Initialize(Bones);
        for (int32 I = 0; I < 2; ++I) { Upper[I].Initialize(Bones); Knee[I].Initialize(Bones); Foot[I].Initialize(Bones); Toe[I].Initialize(Bones); }
    }
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override
    {
        if (!Hip.IsValidToEvaluate(Bones)) return false;
        for (int32 I = 0; I < 2; ++I)
            if (!Upper[I].IsValidToEvaluate(Bones) || !Knee[I].IsValidToEvaluate(Bones) || !Foot[I].IsValidToEvaluate(Bones) || !Toe[I].IsValidToEvaluate(Bones)) return false;
        return true;
    }
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& Out) override
    {
        const auto& Bones = Output.Pose.GetPose().GetBoneContainer();
        const FTransform Component = Output.AnimInstanceProxy->GetComponentTransform();
        const auto HipIndex = Hip.GetCompactPoseIndex(Bones);
        FTransform HipPose = Output.Pose.GetComponentSpaceTransform(HipIndex);
        FTransform U[2], K[2], F[2];
        FQuat FootRotation[2];
        FVector Target[2];
        float FloorOffset[2] = {0.f, 0.f};
        for (int32 I = 0; I < 2; ++I)
        {
            U[I] = Output.Pose.GetComponentSpaceTransform(Upper[I].GetCompactPoseIndex(Bones));
            K[I] = Output.Pose.GetComponentSpaceTransform(Knee[I].GetCompactPoseIndex(Bones));
            F[I] = Output.Pose.GetComponentSpaceTransform(Foot[I].GetCompactPoseIndex(Bones));
            const FVector ToeCS = Output.Pose.GetComponentSpaceTransform(Toe[I].GetCompactPoseIndex(Bones)).GetLocation();
            const FVector ToeWorld = Component.TransformPosition(ToeCS);
            const FVector ToeLocal = F[I].InverseTransformPosition(ToeCS);
            FootRotation[I] = F[I].GetRotation();
            if (bSpell && CapturedGeneration != Generation) Anchor[I] = ToeWorld;
            FVector Goal = ToeWorld;
            // Both soles settle vertically during the pose blend; horizontal support
            // remains at the previous visible footprint, not a guessed default stance.
            if (bGround[I])
            {
                FloorOffset[I] = FMath::Clamp(GroundHeight[I] - Component.GetLocation().Z, -20.f, 20.f) * GroundBlend;
                Goal.Z += FloorOffset[I];
                const FVector Up = Component.InverseTransformVectorNoScale(FVector::UpVector);
                const FVector Normal = Component.InverseTransformVectorNoScale(GroundNormal[I]);
                FootRotation[I] = FQuat::Slerp(FQuat::Identity, FQuat::FindBetweenNormals(Up, Normal), GroundBlend) * FootRotation[I];
            }
            const FVector Horizontal(Anchor[I].X - ToeWorld.X, Anchor[I].Y - ToeWorld.Y, 0);
            Goal += Horizontal.GetClampedToMaxSize(25.f) * LockWeight;
            // Rotate around the planted toe, not the ankle: slope alignment must
            // not move the footprint after the horizontal lock was calculated.
            Target[I] = Component.InverseTransformPosition(Goal)
                - FootRotation[I].RotateVector(F[I].GetScale3D() * ToeLocal);
        }
        if (bSpell) CapturedGeneration = Generation;
        // A small pelvis adjustment shares the ground correction across the body.
        const float PelvisZ = FMath::Min(0.f, FMath::Min(FloorOffset[0], FloorOffset[1]));
        FVector PelvisOffset = Component.InverseTransformVectorNoScale(FVector(0, 0, PelvisZ));
        float ReachDrop = 0.f;
        for (int32 I = 0; I < 2; ++I)
        {
            const float Length = FVector::Distance(U[I].GetLocation(), K[I].GetLocation())
                + FVector::Distance(K[I].GetLocation(), F[I].GetLocation());
            const FVector Offset = U[I].GetLocation() + PelvisOffset - Target[I];
            const float ReachZ = FMath::Sqrt(FMath::Max(1.f, FMath::Square(Length * .98f) - Offset.SizeSquared2D()));
            ReachDrop = FMath::Max(ReachDrop, Offset.Z - ReachZ);
        }
        PelvisOffset.Z -= FMath::Clamp(ReachDrop, 0.f, 12.f);
        HipPose.AddToTranslation(PelvisOffset); Out.Emplace(HipIndex, HipPose);
        for (int32 I = 0; I < 2; ++I)
        {
            U[I].AddToTranslation(PelvisOffset); K[I].AddToTranslation(PelvisOffset); F[I].AddToTranslation(PelvisOffset);
            const FVector Pole = K[I].GetLocation();
            AnimationCore::SolveTwoBoneIK(U[I], K[I], F[I], Pole, Target[I], false, 1.f, 1.f);
            F[I].SetRotation(FootRotation[I]);
            Out.Emplace(Upper[I].GetCompactPoseIndex(Bones), U[I]);
            Out.Emplace(Knee[I].GetCompactPoseIndex(Bones), K[I]);
            Out.Emplace(Foot[I].GetCompactPoseIndex(Bones), F[I]);
        }
        Out.Sort(FCompareBoneTransformIndex());
    }
};

struct FWitchSpellProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FAnimNode_TwoWayBlend Blend;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FWitchSpellSupport Support;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    explicit FWitchSpellProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        Blend.A.SetLinkNode(&Previous); Blend.B.SetLinkNode(&Current);
        ToComponent.LocalPose.SetLinkNode(&Blend); Support.ComponentPose.SetLinkNode(&ToComponent);
        ToLocal.ComponentPose.SetLinkNode(&Support);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    { Nodes.Append({&Previous, &Current, &Blend, &ToComponent, &Support, &ToLocal}); }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UWitchSpellAnimInstance>(Instance);
        const auto* Witch = Cast<AWitchMonster>(Instance->TryGetPawnOwner());
        Previous.Snapshot = Data->PreviousPose;
        Current.SetSequence(Data->ActiveClip); Current.SetShouldLoop(Data->bLooping);
        Current.SetTeleportToExplicitTime(true); Current.SetExplicitTime(Data->ClipTime);
        Blend.Alpha = Data->PreviousPose.bIsValid ? Data->BlendAlpha : 1.f;
        Support.bSpell = Witch && Witch->State == ENurseState::Attack;
        Support.Generation = Data->SpellGeneration;
        Support.GroundBlend = Blend.Alpha;
        Support.LockWeight = Support.bSpell ? 1.f : FMath::FInterpConstantTo(Support.LockWeight, 0.f, DeltaSeconds, 4.f);
        const bool Grounded = Witch && Witch->GetCharacterMovement()->IsMovingOnGround();
        // Only the revised spells and their blend-out use this support solver.
        Support.Alpha = Grounded ? Support.LockWeight : 0.f;
        if (!Witch || Support.Alpha == 0.f) return;
        auto* Mesh = Instance->GetSkelMeshComponent();
        FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchSpellGround), false, Witch);
        for (int32 I = 0; I < 2; ++I)
        {
            FVector Probe = Support.CapturedGeneration == Support.Generation
                ? Support.Anchor[I] : Mesh->GetSocketLocation(Support.Foot[I].BoneName);
            Probe.Z = Mesh->GetComponentLocation().Z;
            FHitResult Hit;
            const bool WasGround = Support.bGround[I];
            Support.bGround[I] = Witch->GetWorld()->LineTraceSingleByChannel(Hit,
                Probe + FVector(0, 0, 45), Probe - FVector(0, 0, 45), ECC_Visibility, Query)
                && Hit.ImpactNormal.Z >= Witch->GetCharacterMovement()->GetWalkableFloorZ()
                && (!Hit.GetActor() || !Hit.GetActor()->IsA<APawn>());
            if (Support.bGround[I])
            {
                // Filter triangle-to-triangle ground changes without delaying the initial placement.
                Support.GroundHeight[I] = WasGround ? FMath::FInterpTo(Support.GroundHeight[I], Hit.ImpactPoint.Z, DeltaSeconds, 18.f) : Hit.ImpactPoint.Z;
                Support.GroundNormal[I] = WasGround ? FMath::VInterpTo(Support.GroundNormal[I], Hit.ImpactNormal, DeltaSeconds, 18.f).GetSafeNormal() : Hit.ImpactNormal;
            }
        }
    }
};

void UWitchSpellAnimInstance::PlayState(UAnimSequence* Clip, bool bLoop)
{
    if (!bLoop) ++SpellGeneration;
    // Full-body snapshots retain the incoming gait phase through the short settling interval.
    TransitionTo(Clip, bLoop, !bLoop, bLoop ? .25f : .24f);
}
FAnimInstanceProxy* UWitchSpellAnimInstance::CreateAnimInstanceProxy() { return new FWitchSpellProxy(this); }
void UWitchSpellAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
