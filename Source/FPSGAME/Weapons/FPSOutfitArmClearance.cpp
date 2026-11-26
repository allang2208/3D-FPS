#include "FPSOutfitArmClearance.h"
#include "FPSGunplayAnimInstance.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Actor.h"
#include "M870ArmOpeningControls.inl"

namespace
{
FQuat M870OpeningRetreat(const FTransform& Clavicle,const FTransform& Upper,
    const FVector& Wrist,const FTransform& MeshToCamera,double VerticalTangent)
{
    // Fixed authored rim controls, not a bounding box: the empty box corners
    // would lower the already-safe idle arm by another 7-9 degrees.
    constexpr int32 Count=UE_ARRAY_COUNT(M870ArmOpening::Controls);
    FVector Points[Count];FVector Centre=FVector::ZeroVector;
    const FVector Normal=FVector(VerticalTangent,0.,1.).GetSafeNormal();
    double Maximum=-DBL_MAX,Forward=-DBL_MAX;
    for(int32 I=0;I<Count;++I)
    {
        const auto& Control=M870ArmOpening::Controls[I];
        const FVector Point=FMath::Lerp(Clavicle.TransformPosition(FVector(Control.Clavicle)),
            Upper.TransformPosition(FVector(Control.Upper)),double(Control.UpperWeight));
        Points[I]=MeshToCamera.TransformPosition(Point);Centre+=Points[I];
        Maximum=FMath::Max(Maximum,FVector::DotProduct(Points[I],Normal));
        Forward=FMath::Max(Forward,Points[I].X);
    }
    // One centimetre of advance warning, with zero slope at its entry, keeps
    // the actual lip below the bottom plane through inspection/reload blends.
    const double Distance=FMath::Max(0.,Maximum+1.);
    const double Retreat=Distance*Distance/(Distance+.75);
    if(Forward<0.||Retreat<UE_SMALL_NUMBER)return FQuat::Identity;
    const FVector Pivot=MeshToCamera.TransformPosition(Wrist);
    const FVector Axis=FVector::CrossProduct(Normal,Centre/double(Count)-Pivot).GetSafeNormal();
    if(Axis.IsNearlyZero())return FQuat::Identity;
    double Constant[Count],Cosine[Count],Sine[Count];
    const double NormalAxis=FVector::DotProduct(Normal,Axis);
    const double NormalPivot=FVector::DotProduct(Normal,Pivot);
    for(int32 I=0;I<Count;++I)
    {
        const FVector Reach=Points[I]-Pivot;
        const double Axial=NormalAxis*FVector::DotProduct(Reach,Axis);
        Constant[I]=NormalPivot+Axial;
        Cosine[I]=FVector::DotProduct(Reach,Normal)-Axial;
        Sine[I]=FVector::DotProduct(FVector::CrossProduct(Axis,Reach),Normal);
    }
    // Solve a small rigid rotation of the whole bent arm about its fixed hand.
    // The requested saved poses need at most 12 degrees; retain a bounded limit.
    double Low=0.,High=FMath::DegreesToRadians(35.);
    const double Target=Maximum-Retreat;
    for(int32 Step=0;Step<12;++Step)
    {
        const double Mid=(Low+High)*.5;double Sin,Cos;FMath::SinCos(&Sin,&Cos,Mid);
        double Height=-DBL_MAX;
        for(int32 I=0;I<Count;++I)Height=FMath::Max(Height,Constant[I]+Cosine[I]*Cos+Sine[I]*Sin);
        if(Height>Target)Low=Mid;else High=Mid;
    }
    const FQuat CameraRotation(Axis,High);
    return (MeshToCamera.GetRotation().Inverse()*CameraRotation*MeshToCamera.GetRotation()).GetNormalized();
}
}

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
    // No animation loads, mesh readback, new tick or view-dependent mesh hiding.
    if (!Mesh.GetOwner() || !Mesh.GetSkeletalMeshAsset() || !Mesh.bOnlyOwnerSee
        || Mesh.bOwnerNoSee || !Mesh.IsVisible() || Mesh.bHiddenInGame
        || !Cast<UFPSGunplayAnimInstance>(Mesh.GetAnimInstance())) return;
    if (CachedMesh.Get() != Mesh.GetSkeletalMeshAsset()) Cache(Mesh);
    const auto* Equipment = Outfit.Get();
    const auto* View = Camera.Get();
    static const FName M870Viewmodel(TEXT("SK_M870_V7"));
    const bool bM870=CachedMesh->GetFName()==M870Viewmodel;
    const bool bChainmail=Equipment&&Equipment->IsChainmailEquipped();
    if (!View || (!bChainmail&&!bM870)) return;
    const FTransform MeshToCamera = Mesh.GetComponentTransform().GetRelativeTransform(View->GetComponentTransform());
    for (int32 Side = 0; bChainmail&&Side < 2; ++Side)
    {
        const FArm& Arm = Arms[Side];
        if (!Pose.IsValidIndex(Arm.Upper) || !Pose.IsValidIndex(Arm.Lower) || !Pose.IsValidIndex(Arm.Hand)
            || Arm.UpperBones.IsEmpty()) continue;
        const FTransform OldUpper = Pose[Arm.Upper], OldLower = Pose[Arm.Lower];
        const FVector Shoulder = MeshToCamera.TransformPosition(OldUpper.GetLocation());
        const FVector Elbow = MeshToCamera.TransformPosition(OldLower.GetLocation());
        const FVector Hand = MeshToCamera.TransformPosition(Pose[Arm.Hand].GetLocation());
        // Thick sleeves and the forward-framed pistol/book pair can bring the
        // shoulder opening close to the eye. Continuous weights include ADS
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
    if(bM870)
    {
        const FArm& Arm=Arms[0];
        if(Arm.UpperBones.IsEmpty()||!Pose.IsValidIndex(Arm.Upper)||!Pose.IsValidIndex(Arm.Hand))return;
        // Reference skeleton parents precede children: the first cached upper
        // bone is the clavicle. Reuse the existing cache without changing layout.
        const int32 Clavicle=Arm.UpperBones[0];
        const double VerticalTangent=FMath::Tan(FMath::DegreesToRadians(double(View->FieldOfView)*.5))
            /FMath::Max(.1,double(View->AspectRatio));
        const FVector Wrist=Pose[Arm.Hand].GetLocation();
        const FQuat Rotation=M870OpeningRetreat(Pose[Clavicle],Pose[Arm.Upper],Wrist,MeshToCamera,VerticalTangent);
        if(Rotation.IsIdentity())return;
        const FTransform OldUpper=Pose[Arm.Upper];FTransform NewUpper=OldUpper;
        NewUpper.SetLocation(Wrist+Rotation.RotateVector(OldUpper.GetLocation()-Wrist));
        NewUpper.SetRotation((Rotation*OldUpper.GetRotation()).GetNormalized());
        for(int32 I:Arm.UpperBones)Pose[I]=Pose[I].GetRelativeTransform(OldUpper)*NewUpper;
        for(int32 I:Arm.LowerBones)Pose[I]=Pose[I].GetRelativeTransform(OldUpper)*NewUpper;
    }
}
