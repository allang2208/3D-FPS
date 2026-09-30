#include "FPSOutfitArmClearance.h"
#include "FPSGunplayAnimInstance.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Actor.h"

void FFPSOutfitArmClearance::Cache(USkeletalMeshComponent& Mesh)
{
    CachedMesh = Mesh.GetSkeletalMeshAsset();
    Camera = Mesh.GetOwner()->FindComponentByClass<UCameraComponent>();
    Outfit = Mesh.GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>();
    const FReferenceSkeleton& Ref = CachedMesh->GetRefSkeleton();
    for (int32 Side = 0; Side < 2; ++Side)
    {
        FArm& Arm = Arms[Side];
        Arm = FArm();
        const TCHAR* Suffix = Side == 0 ? TEXT("l") : TEXT("r");
        const auto Bone = [&](const TCHAR* Prefix)
        { return Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%s_%s"), Prefix, Suffix))); };
        const int32 Clavicle = Bone(TEXT("clavicle"));
        Arm.Upper = Bone(TEXT("upperarm"));
        Arm.Lower = Bone(TEXT("lowerarm"));
        Arm.Hand = Bone(TEXT("hand"));
        if (Clavicle == INDEX_NONE || Arm.Upper == INDEX_NONE || Arm.Lower == INDEX_NONE || Arm.Hand == INDEX_NONE)
            continue;
        for (int32 I = 0; I < Ref.GetNum(); ++I)
        {
            if (I == Arm.Hand || Ref.BoneIsChildOf(I, Arm.Hand)) continue;
            if (I == Arm.Lower || Ref.BoneIsChildOf(I, Arm.Lower)) Arm.LowerBones.Add(I);
            else if (I == Clavicle || Ref.BoneIsChildOf(I, Clavicle)) Arm.UpperBones.Add(I);
        }
    }
}

void FFPSOutfitArmClearance::Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose)
{
    // Operate on the evaluated firearm leader, once, before followers receive it.
    // No animation loads, per-vertex work, new tick or view-dependent mesh hiding.
    if (!Mesh.GetOwner() || !Mesh.GetSkeletalMeshAsset() || !Mesh.bOnlyOwnerSee
        || Mesh.bOwnerNoSee || !Mesh.IsVisible() || Mesh.bHiddenInGame
        || !Cast<UFPSGunplayAnimInstance>(Mesh.GetAnimInstance())) return;
    if (CachedMesh.Get() != Mesh.GetSkeletalMeshAsset()) Cache(Mesh);
    const auto* Equipment = Outfit.Get();
    const auto* View = Camera.Get();
    if (!Equipment || !View || !Equipment->IsChainmailEquipped()) return;
    const FTransform MeshToCamera = Mesh.GetComponentTransform().GetRelativeTransform(View->GetComponentTransform());
    for (int32 Side = 0; Side < 2; ++Side)
    {
        const FArm& Arm = Arms[Side];
        if (!Pose.IsValidIndex(Arm.Upper) || !Pose.IsValidIndex(Arm.Lower) || !Pose.IsValidIndex(Arm.Hand)
            || Arm.UpperBones.IsEmpty()) continue;
        const FTransform OldUpper = Pose[Arm.Upper], OldLower = Pose[Arm.Lower];
        const FVector Shoulder = MeshToCamera.TransformPosition(OldUpper.GetLocation());
        const FVector Elbow = MeshToCamera.TransformPosition(OldLower.GetLocation());
        const FVector Hand = MeshToCamera.TransformPosition(Pose[Arm.Hand].GetLocation());
        // Thick shoulders intersect the near plane when a long-eye-relief optic
        // moves the whole viewmodel forward. Continuous weights include ADS
        // transitions and reloads; no guessed clip time or optic-specific offset.
        // Start near the camera plane. The old X=-18 cm threshold also moved
        // shoulders behind the view during equip, melee and early reload.
        // Low shoulders remain part of the authored reload support.
        const double Weight = FMath::SmoothStep(-4., 4., Shoulder.X)
            * FMath::SmoothStep(-12., -4., Shoulder.Z)
            * (1. - FMath::SmoothStep(24., 40., FMath::Abs(Shoulder.Y)));
        if (Weight <= UE_SMALL_NUMBER) continue;
        const double UpperLength = FVector::Distance(Shoulder, Elbow);
        const double LowerLength = FVector::Distance(Elbow, Hand);
        if (UpperLength < 1. || LowerLength < 1.) continue;
        const double SideSign = Side == 0 ? -1. : 1.;
        FVector Target(FMath::Min(Shoulder.X, -10.),
            SideSign * FMath::Max(SideSign * Shoulder.Y, 18.), FMath::Min(Shoulder.Z, -18.));
        Target = FMath::Lerp(Shoulder, Target, Weight);
        // Rotate the authored shoulder/elbow chain as one shape about the
        // fixed wrist. Re-solving the elbow, even with a reach cap, changes
        // flexion and stretches skin/sleeve vertices weighted across the joint.
        const FVector AuthoredReach = Shoulder - Hand;
        const FVector DesiredReach = Target - Hand;
        if (AuthoredReach.IsNearlyZero() || DesiredReach.IsNearlyZero()) continue;
        const FQuat ReachRotation = FQuat::FindBetweenNormals(
            AuthoredReach.GetSafeNormal(), DesiredReach.GetSafeNormal());
        const FVector Wrist = Pose[Arm.Hand].GetLocation();
        const FQuat MeshReachRotation = (MeshToCamera.GetRotation().Inverse()
            * ReachRotation * MeshToCamera.GetRotation()).GetNormalized();
        FTransform NewUpper = OldUpper;
        NewUpper.SetLocation(Wrist + MeshReachRotation.RotateVector(OldUpper.GetLocation() - Wrist));
        NewUpper.SetRotation((MeshReachRotation * OldUpper.GetRotation()).GetNormalized());
        // Apply ONE rigid delta to both segments and all twist helpers. Their
        // relative transforms, scale and elbow shape remain authored. Hand,
        // finger and weapon transforms stay fixed; followers share this pose.
        for (int32 I : Arm.UpperBones) Pose[I] = Pose[I].GetRelativeTransform(OldUpper) * NewUpper;
        for (int32 I : Arm.LowerBones) Pose[I] = Pose[I].GetRelativeTransform(OldUpper) * NewUpper;
    }
}
