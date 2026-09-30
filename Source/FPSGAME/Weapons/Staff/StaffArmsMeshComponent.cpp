#include "StaffArmsMeshComponent.h"
#include "StaffWeaponComponent.h"
#include "StaffGripPose.h"
#include "StaffFreeHandPose.h"
#include "../../FPSGAMECharacter.h"
#include "GameFramework/Character.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void UStaffArmsMeshComponent::CacheReferencePose()
{
    auto* Mesh=GetSkeletalMeshAsset();if(!Mesh||CachedMesh.Get()==Mesh)return;
    const auto& Skeleton=Mesh->GetRefSkeleton();
    CachedMesh=Mesh;RefLocal=Skeleton.GetRefBonePose();RefComponent=RefLocal;
    for(int32 I=0;I<RefComponent.Num();++I)
    {const int32 P=Skeleton.GetParentIndex(I);if(P>=0)RefComponent[I]=RefComponent[I]*RefComponent[P];}
}
FTransform UStaffArmsMeshComponent::AuthoredContactInCamera(const FStaffCastPose& Motion,int32 Variant)
{
    auto* Mesh=GetSkeletalMeshAsset();if(!Mesh)return Motion.Contact;
    CacheReferencePose();
    return StaffGripPose::ContactFromArm(StaffGripPose::Get(Mesh,RefComponent,Variant),Motion);
}

void UStaffArmsMeshComponent::FinalizeBoneTransform()
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const bool OffhandPistol=Player&&Player->HasOffhandPistol();
    // Only one rig owns the left arm, including potion/spell overlays and outfit followers.
    bApplyLeftHandCast=!OffhandPistol;
    auto* Weapon=GetOwner()?GetOwner()->FindComponentByClass<UStaffWeaponComponent>():nullptr;
    auto* Camera=GetOwner()?GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    auto* Mesh=GetSkeletalMeshAsset();
    if(Weapon&&Weapon->IsEquipped()&&Camera&&Mesh)
    {
        const FName LeftRoot(TEXT("clavicle_l"));
        if(IsBoneHiddenByName(LeftRoot)!=OffhandPistol)
        {
            if(OffhandPistol)HideBoneByName(LeftRoot,EPhysBodyOp::PBO_None);
            else UnHideBoneByName(LeftRoot);
        }
        const auto& Skeleton=Mesh->GetRefSkeleton();
        CacheReferencePose();
        auto& Pose=GetEditableComponentSpaceTransforms();
        if(Pose.Num()==RefComponent.Num())
        {
            const auto& Authored=StaffGripPose::Get(Mesh,RefComponent,Weapon->GripVariant());
            const auto Motion=Weapon->ActionPoseInCamera();
            const auto& Carry=Weapon->CarryPose();
            // Blend complete LOCAL transforms so interpolation preserves native
            // segment lengths and wrist/helper relationships across cast phases.
            for(int32 I=0;I<Pose.Num();++I)Pose[I]=StaffGripPose::BlendLocal(Authored,Motion,I);
            if(Authored.Lower>=0&&!Weapon->IsPrimaryAttacking())
            {
                const float CarryWeight=Motion.ArmWeights[0]+Motion.ArmWeights[5];
                const double Bend=FMath::DegreesToRadians(FMath::Clamp(Carry.RightElbow.X*.6+Carry.RightElbow.Z*.5,-3.,3.)*CarryWeight);
                Pose[Authored.Lower].SetRotation((FQuat(Authored.ElbowHinge,Bend)*Pose[Authored.Lower].GetRotation()).GetNormalized());
            }
            const auto* Character=Cast<ACharacter>(GetOwner());
            const float FreeHandWeight=Carry.MoveWeight()*(Character&&Character->bIsCrouched?.6f:1.f);
            if(!OffhandPistol)
                StaffFreeHandPose::Apply(Mesh,RefComponent,Pose,Carry.StridePhase(),FreeHandWeight,Carry.RunWeight(),Carry.MotionTime());
            for(int32 I=0;I<Pose.Num();++I)
            {const int32 P=Skeleton.GetParentIndex(I);if(P>=0)Pose[I]=Pose[I]*Pose[P];}

            const FTransform CameraToMesh=Camera->GetComponentTransform().GetRelativeTransform(GetComponentTransform());
            // Read the assembly transform already applied by this weapon tick.
            // Equip, movement, casts and melee share the exact current contact.
            const FTransform Grip=Weapon->AssemblyRoot()->GetRelativeTransform();
            const FTransform Contact(Grip.GetRotation(),Grip.TransformPosition(StaffGripPose::HoldPoint()));
            if(Authored.Hand>=0)
            {
                const FTransform Goal=Authored.HandInGrip*Contact;
                const FQuat Turn=(Goal.GetRotation()*Pose[Authored.Hand].GetRotation().Inverse()).GetNormalized();
                const FVector Origin=Pose[Authored.Hand].GetLocation();
                // Transport the entire authored chain. No fresh rest-pose IK,
                // independent wrist rotation or fractional helper twist.
                for(const int32 I:Authored.RightChain)
                {
                    const FVector Point=Goal.GetLocation()+Turn.RotateVector(Pose[I].GetLocation()-Origin);
                    Pose[I].SetLocation(CameraToMesh.TransformPosition(Point));
                    Pose[I].SetRotation((CameraToMesh.GetRotation()*Turn*Pose[I].GetRotation()).GetNormalized());
                }
            }
            // Zero scale alone leaves each joint at a different translation.
            // Vertices weighted to several joints can still span those points.
            // Collapse the complete chain to one shoulder point, including the
            // leader pose consumed by equipped gloves and sleeves.
            const FVector LeftAnchor=Authored.LeftChain.IsEmpty()?FVector::ZeroVector:
                CameraToMesh.TransformPosition(Pose[Authored.LeftChain[0]].GetLocation());
            const FTransform HiddenLeft(FQuat::Identity,LeftAnchor,FVector::ZeroVector);
            for(const int32 I:Authored.LeftChain)
            {
                if(OffhandPistol){Pose[I]=HiddenLeft;continue;}
                // The full chain was authored around its anchored shoulder.
                // Do not lift/translate the whole arm from the hand pivot.
                Pose[I].SetLocation(CameraToMesh.TransformPosition(Pose[I].GetLocation()));
                Pose[I].SetRotation((CameraToMesh.GetRotation()*Pose[I].GetRotation()).GetNormalized());
            }
        }
    }
    Super::FinalizeBoneTransform();
}
