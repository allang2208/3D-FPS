#pragma once
#include "CoreMinimal.h"
#include "StaffCastMotion.h"
class USkeletalMesh;
namespace StaffGripPose
{
    // 70% of the 160 cm staff: 48 cm of shaft/head remains above the hand.
    inline FVector HoldPoint(){return FVector(0,0,32);}
    inline constexpr double ShaftRadius=2.98;
    struct FGripData
    {
        TArray<FTransform> Local[FStaffCastPose::ArmPoseCount];
        TArray<int32> RightChain,LeftChain,HandParents;
        int32 Shoulder=INDEX_NONE,Upper=INDEX_NONE;
        int32 Hand=INDEX_NONE,Lower=INDEX_NONE;
        FVector ElbowHinge=FVector::UpVector;
        FTransform HandInGrip=FTransform::Identity;
    };
    int32 VariantForMesh(const FString& MeshPath);
    const FGripData& Get(USkeletalMesh* Mesh,const TArray<FTransform>& Reference,int32 Variant,bool bCharge=false);
    FTransform BlendLocal(const FGripData& Data,const FStaffCastPose& Motion,int32 Bone,bool bCharge=false);
    FTransform ContactFromArm(const FGripData& Data,const FStaffCastPose& Motion,bool bCharge=false);
}
