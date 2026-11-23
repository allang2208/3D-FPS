#include "WoodenTorchArmsComponent.h"
#include "Staff/StaffGripPose.h"
#include "Staff/StaffWeaponComponent.h"
#include "Staff/StaffPrimaryKeys.h"
#include "WeaponPresentationMaterials.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
    FQuat MirrorCameraY(const FQuat& Q) { return FQuat(-Q.X, Q.Y, -Q.Z, Q.W); }
    FVector MirrorCameraY(const FVector& P) { return FVector(P.X, -P.Y, P.Z); }
}

FTransform UWoodenTorchArmsComponent::MirrorContact(const FTransform& Contact)
{
    return FTransform(MirrorCameraY(Contact.GetRotation()),MirrorCameraY(Contact.GetLocation()),Contact.GetScale3D());
}

FTransform UWoodenTorchArmsComponent::BuildStaffCarry(USkeletalMesh& Mesh, int32 Side, TArray<FTransform>& Pose, int32 SwingKey)
{
    const FReferenceSkeleton& Ref = Mesh.GetRefSkeleton();
    const auto& RefLocal = Ref.GetRefBonePose();
    TArray<FTransform> Bind = RefLocal;
    for (int32 I = 0; I < Bind.Num(); ++I)
    {
        const int32 Parent = Ref.GetParentIndex(I);
        if (Parent != INDEX_NONE) Bind[I] *= Bind[Parent];
    }

    const auto& Staff = StaffGripPose::Get(&Mesh, Bind, 0);
    Pose = Staff.Local[SwingKey == INDEX_NONE ? 0 : 6 + SwingKey];
    for (int32 I = 0; I < Pose.Num(); ++I)
    {
        const int32 Parent = Ref.GetParentIndex(I);
        if (Parent != INDEX_NONE) Pose[I] *= Pose[Parent];
    }
    FTransform Contact = SwingKey == INDEX_NONE ? StaffGripPose::RestContactInCamera() : StaffPrimaryKeys::Contacts[SwingKey];
    const FTransform WristGoal = Staff.HandInGrip * Contact;
    const FVector Origin = Pose[Staff.Hand].GetLocation();
    const FQuat Turn = (WristGoal.GetRotation() * Pose[Staff.Hand].GetRotation().Inverse()).GetNormalized();
    for (const int32 I : Staff.RightChain)
    {
        Pose[I].SetLocation(WristGoal.GetLocation() + Turn.RotateVector(Pose[I].GetLocation() - Origin));
        Pose[I].SetRotation((Turn * Pose[I].GetRotation()).GetNormalized());
    }

    int32 Wrist = Staff.Hand;
    if (Side == 1)
    {
        // Screen symmetry is across camera Y. Native M4 bind symmetry is across mesh X.
        // The half-turn changes reflection planes; the bind correction retains the left bone axes.
        const FQuat ChangePlane(FVector::UpVector, PI);
        for (const int32 L : Staff.LeftChain)
        {
            const FString Name = Ref.GetBoneName(L).ToString();
            const int32 R = Ref.FindBoneIndex(FName(*(Name.LeftChop(2) + TEXT("_r"))));
            if (R == INDEX_NONE) continue;
            const FQuat Q = Bind[R].GetRotation();
            const FQuat ReflectedBind(Q.X, -Q.Y, -Q.Z, Q.W);
            const FQuat Rotation = MirrorCameraY(Pose[R].GetRotation()) * ChangePlane * ReflectedBind.Inverse() * Bind[L].GetRotation();
            Pose[L].SetRotation(Rotation.GetNormalized());
            const int32 Parent = Ref.GetParentIndex(L);
            Pose[L].SetLocation(L == Staff.LeftChain[0] ? MirrorCameraY(Pose[R].GetLocation())
                : Pose[Parent].TransformPosition(RefLocal[L].GetLocation()));
        }
        Contact = MirrorContact(Contact);
        Wrist = Ref.FindBoneIndex(TEXT("hand_l"));
    }

    return Contact.GetRelativeTransform(FTransform(Pose[Wrist].GetRotation(), Pose[Wrist].GetLocation()));
}

FTransform UWoodenTorchArmsComponent::ConfigureCarry(USkeletalMesh& Mesh, int32 Side)
{
    SetSkeletalMesh(&Mesh);
    const auto& Ref = Mesh.GetRefSkeleton();
    const FTransform GripInHand = BuildStaffCarry(Mesh, Side, CarryPose);
    const int32 Wrist = Ref.FindBoneIndex(Side == 0 ? TEXT("hand_r") : TEXT("hand_l"));
    const int32 HiddenRoot = Ref.FindBoneIndex(Side == 0 ? TEXT("clavicle_l") : TEXT("clavicle_r"));
    const FTransform Hidden(FQuat::Identity, CarryPose[HiddenRoot].GetLocation(), FVector::ZeroVector);
    for (int32 I = HiddenRoot; I < CarryPose.Num(); ++I)
        if (I == HiddenRoot || Ref.BoneIsChildOf(I, HiddenRoot)) CarryPose[I] = Hidden;
    bApplyLeftHandCast = Side == 1;
    if(Side==1)
    {
        LeftRoot=Ref.FindBoneIndex(TEXT("clavicle_l"));LeftWrist=Wrist;
        Reference=Ref.GetRefBonePose();CarryLocal=Ref.GetRefBonePose();
        for(int32 I=0;I<Reference.Num();++I)
        {
            const int32 P=Ref.GetParentIndex(I);
            if(P!=INDEX_NONE)Reference[I]*=Reference[P];
            if(I==LeftRoot||Ref.BoneIsChildOf(I,LeftRoot))
                CarryLocal[I]=CarryPose[I].GetRelativeTransform(P==INDEX_NONE?FTransform::Identity:CarryPose[P]);
        }
        WristInGrip = GripInHand.Inverse();
        LeftChain = StaffGripPose::Get(&Mesh, Reference, 0).LeftChain;
        for (int32 Key=0; Key<UE_ARRAY_COUNT(LeftSwingLocal); ++Key)
        {
            TArray<FTransform> Sample;
            BuildStaffCarry(Mesh, Side, Sample, Key);
            for (const int32 Bone : LeftChain)
                LeftSwingLocal[Key].Add(Sample[Bone].GetRelativeTransform(Sample[Ref.GetParentIndex(Bone)]));
        }
    }
    if (const auto* Render = Mesh.GetResourceForRendering())
    {
        for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
        {
            const auto& Sections = Render->LODRenderData[L].RenderSections;
            for (int32 S = 0; S < Sections.Num(); ++S)
            {
                const int32 M = Sections[S].MaterialIndex;
                ShowMaterialSection(M, S, WeaponPresentationMaterials::IsArmSection(Mesh.GetMaterials()[M]), L);
            }
        }
    }
    // V7 keeps the import scale on the skeleton; the wood and socket use actual cm.
    return GripInHand * FTransform(FQuat::Identity, FVector::ZeroVector, FVector::OneVector / CarryPose[Wrist].GetScale3D());
}

FTransform UWoodenTorchArmsComponent::AuthoredSwingContact(const FStaffCastPose& Motion) const
{
    const auto& Grip = StaffGripPose::Get(GetSkeletalMeshAsset(), Reference, 0);
    return StaffGripPose::ContactFromArm(Grip, Motion);
}

void UWoodenTorchArmsComponent::ApplyOffhandSwing(const FStaffCastPose& Motion, TArray<FTransform>& Pose) const
{
    const auto& Ref = GetSkeletalMeshAsset()->GetRefSkeleton();
    for (int32 J=0; J<LeftChain.Num(); ++J)
    {
        const int32 Bone = LeftChain[J];
        FTransform Local = CarryLocal[Bone];
        float Total = Motion.ArmWeights[0];
        for (int32 Key=0; Key<UE_ARRAY_COUNT(LeftSwingLocal); ++Key)
        {
            const float Weight = Motion.ArmWeights[6 + Key];
            if (Weight <= 0.f) continue;
            Total += Weight;
            Local.BlendWith(LeftSwingLocal[Key][J], Weight / Total);
        }
        Pose[Bone] = Local * Pose[Ref.GetParentIndex(Bone)];
    }
    // Keep the rendered grip on the same contact curve used by the hit sweep.
    // Fade the walking offset back in at both ends of the strike.
    FTransform CarryOffset;
    CarryOffset.Blend(FTransform::Identity, GetRelativeTransform(), Motion.ArmWeights[0]);
    const FTransform Desired = (WristInGrip * MirrorContact(Motion.Contact) * CarryOffset).GetRelativeTransform(GetRelativeTransform());
    const FTransform Wrist(Pose[LeftWrist].GetRotation(), Pose[LeftWrist].GetLocation());
    const FTransform Correction = Wrist.Inverse() * Desired;
    for (const int32 Bone : LeftChain) Pose[Bone] *= Correction;
}

void UWoodenTorchArmsComponent::FinalizeBoneTransform()
{
    auto& Pose = GetEditableComponentSpaceTransforms();
    if (CarryPose.Num() && Pose.Num() == CarryPose.Num()) Pose = CarryPose;
    if (LeftRoot != INDEX_NONE && Pose.Num() == CarryLocal.Num())
        if (const auto* Staff = GetOwner()->FindComponentByClass<UStaffWeaponComponent>(); Staff && Staff->IsPairedTorchSwing())
            ApplyOffhandSwing(Staff->OffhandSwingPose(), Pose);
    Super::FinalizeBoneTransform();
}
