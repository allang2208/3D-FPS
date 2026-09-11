#include "FPSTraversalArmsComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "TwoBoneIK.h"

void UFPSTraversalArmsComponent::SetSurfaceContact(UPrimitiveComponent* Surface,FVector Edge,FVector Outward,float Weight)
{
    ContactSurface=Surface; EdgePoint=Edge; WallOut=Outward; ContactWeight=Weight;
}
void UFPSTraversalArmsComponent::ResetSurfaceContact()
{
    ContactWeight=0; ContactSurface.Reset(); bAnchored[0]=bAnchored[1]=false;
    SurfaceCorrections=0; MaxBoneLengthError=0;
}
void UFPSTraversalArmsComponent::FinalizeBoneTransform()
{
    if (ContactWeight>0 && ContactSurface.IsValid()) FitSurfacePose();
    Super::FinalizeBoneTransform();
}
void UFPSTraversalArmsComponent::FitSurfacePose()
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    const FTransform MeshToWorld=GetComponentTransform();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(TraversalArmSurface),false,GetOwner());
    const FName Profile=CastChecked<ACharacter>(GetOwner())->GetCapsuleComponent()->GetCollisionProfileName();
    const auto Ray=[&](FHitResult& Hit,FVector From,FVector To)
    { return GetWorld()->LineTraceSingleByProfile(Hit,From,To,Profile,Query) && !Hit.bStartPenetrating; };
    const auto ClearPoint=[&](FVector Point,float Radius)
    {
        // Approach from free space; this also finds penetrations whose end point
        // is inside a convex collision shape (closest-point alone cannot do that).
        FHitResult Hit;
        FVector Out=WallOut*60.f+FVector::UpVector*40.f;
        if (GetWorld()->SweepSingleByProfile(Hit,Point+Out,Point,FQuat::Identity,Profile,
            FCollisionShape::MakeSphere(Radius),Query) && !Hit.bStartPenetrating)
            return Hit.Location+Hit.Normal*.5f;
        return Point;
    };
    SourcePose=Pose; // Reuse allocation across frames; both limbs read the same source pose.
    const auto& Original=SourcePose;
    for (int32 Side=0;Side<2;++Side)
    {
        const FString Suffix=Side==0?TEXT("_l"):TEXT("_r");
        const int32 U=GetBoneIndex(FName(*(TEXT("upperarm")+Suffix)));
        const int32 L=GetBoneIndex(FName(*(TEXT("lowerarm")+Suffix)));
        const int32 H=GetBoneIndex(FName(*(TEXT("hand")+Suffix)));
        if (!Pose.IsValidIndex(U)||!Pose.IsValidIndex(L)||!Pose.IsValidIndex(H)) continue;
        const FVector Wrist=MeshToWorld.TransformPosition(Pose[H].GetLocation());
        FVector Wanted=Wrist;
        if (!bAnchored[Side])
        {
            // Each hand samples its own top and front face: uneven/chamfered
            // ledges need not share the centre probe's height or front plane.
            FVector Seed=Wrist-WallOut*FVector::DotProduct(Wrist-EdgePoint,WallOut)-WallOut*8.f;
            Seed.Z=EdgePoint.Z;
            FHitResult Top,Front;
            if (Ray(Top,Seed+FVector::UpVector*35.f,Seed-FVector::UpVector*35.f) &&
                Top.GetComponent()==ContactSurface.Get() && Top.Normal.Z>.65f)
            {
                FVector Face=Top.ImpactPoint-FVector::UpVector*4.f;
                if (Ray(Front,Face+WallOut*60.f,Face-WallOut*20.f) && Front.GetComponent()==ContactSurface.Get())
                {
                    Anchors[Side]=Front.ImpactPoint+Front.Normal*5.f;
                    Anchors[Side].Z=Top.ImpactPoint.Z+3.f;
                    SurfaceNormals[Side]=Top.ImpactNormal;
                    bAnchored[Side]=true;
                }
            }
        }
        if (bAnchored[Side]) Wanted=FMath::Lerp(Wrist,Anchors[Side],ContactWeight);
        // Preserve finger pose and add clearance for glove/palm volume, instead
        // of forcing only a zero-radius wrist joint onto a mathematical surface.
        Wanted=ClearPoint(Wanted,4.f);
        FVector Delta=Wanted-Wrist;
        for (const TCHAR* Finger : {TEXT("index_01"),TEXT("middle_02"),TEXT("pinky_01"),TEXT("thumb_02")})
        {
            const int32 I=GetBoneIndex(FName(*(FString(Finger)+Suffix)));
            if (!Pose.IsValidIndex(I)) continue;
            const FVector P=MeshToWorld.TransformPosition(Pose[I].GetLocation())+Delta;
            Delta+=ClearPoint(P,2.f)-P;
        }
        Wanted=Wrist+Delta.GetClampedToMaxSize(22.f);
        FTransform Upper=Pose[U],Lower=Pose[L],Hand=Pose[H];
        const FVector Elbow=MeshToWorld.TransformPosition(Lower.GetLocation());
        FVector Pole=ClearPoint(Elbow,5.f);
        // Forearm thickness matters at irregular lips even when the wrist and
        // elbow joints themselves are outside. Move the elbow pole around the lip.
        for (float Along : {.25f,.5f,.75f})
        {
            const FVector P=FMath::Lerp(Elbow,Wanted,Along);
            Pole+=(ClearPoint(P,4.f)-P).GetClampedToMaxSize(12.f);
        }
        Pole+=(Pole-MeshToWorld.TransformPosition(Upper.GetLocation())).GetSafeNormal()*12.f;
        if (bAnchored[Side])
        {
            const FVector N=MeshToWorld.InverseTransformVectorNoScale(SurfaceNormals[Side]);
            const FVector Up=MeshToWorld.InverseTransformVectorNoScale(FVector::UpVector);
            const FQuat Tilt=FQuat::Slerp(FQuat::Identity,FQuat::FindBetweenNormals(Up,N),ContactWeight);
            Hand.SetRotation(Tilt*Hand.GetRotation());
        }
        AnimationCore::SolveTwoBoneIK(Upper,Lower,Hand,MeshToWorld.InverseTransformPosition(Pole),
            MeshToWorld.InverseTransformPosition(Wanted),false,1.0,1.0);
        // Rebuild every child from its original local pose. Fingers and twist
        // helpers follow the whole chain without stretching bones or changing skin weights.
        for (int32 I=U;I<Pose.Num();++I)
        {
            if (I==U) Pose[I]=Upper;
            else if (I==L) Pose[I]=Lower;
            else if (I==H) Pose[I]=Hand;
            else if (Ref.BoneIsChildOf(I,U))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Original[I].GetRelativeTransform(Original[Parent])*Pose[Parent];
            }
        }
        MaxBoneLengthError=FMath::Max(MaxBoneLengthError,(float)FMath::Abs(
            FVector::Distance(Pose[U].GetLocation(),Pose[L].GetLocation())-FVector::Distance(Original[U].GetLocation(),Original[L].GetLocation())));
        MaxBoneLengthError=FMath::Max(MaxBoneLengthError,(float)FMath::Abs(
            FVector::Distance(Pose[H].GetLocation(),Pose[L].GetLocation())-FVector::Distance(Original[H].GetLocation(),Original[L].GetLocation())));
        if (Delta.SizeSquared()>1.f) ++SurfaceCorrections;
    }
}
