#include "StaffChargeFlow.h"
#include "StaffArmsMeshComponent.h"
#include "StaffWeaponComponent.h"

namespace StaffChargeFlow
{
namespace
{
constexpr int32 FirstKey=6,ControlCount=6;

void Weights(float Fraction,float (&Out)[ControlCount])
{
    const float T=FMath::Clamp(Fraction,0.f,1.f);
    if(T>=1.f){Out[ControlCount-1]=1.f;return;}
    // Clamped cubic B-spline: carry, coil, shoulder lift, elbow follow,
    // compression and settled. A single eased clock crosses all controls
    // without starting/stopping a fresh ease at each authoring landmark.
    const float U=T*T*(3.f-2.f*T);
    if(U>=1.f){Out[ControlCount-1]=1.f;return;}
    constexpr float Knots[]={0,0,0,0,.40f,.72f,1,1,1,1};
    float Basis[9]={};
    for(int32 I=0;I<9;++I)Basis[I]=U>=Knots[I]&&U<Knots[I+1]?1.f:0.f;
    for(int32 Degree=1;Degree<=3;++Degree)
    {
        for(int32 I=0;I<9-Degree;++I)
        {
            const float A=Knots[I+Degree]-Knots[I];
            const float B=Knots[I+Degree+1]-Knots[I+1];
            Basis[I]=(A>0.f?(U-Knots[I])/A*Basis[I]:0.f)
                +(B>0.f?(Knots[I+Degree+1]-U)/B*Basis[I+1]:0.f);
        }
    }
    for(int32 I=0;I<ControlCount;++I)Out[I]=Basis[I];
}

UStaffArmsMeshComponent* Arms(const UStaffWeaponComponent& Staff)
{return Cast<UStaffArmsMeshComponent>(Staff.ArmsMesh());}

FTransform RawContact(UStaffArmsMeshComponent& Mesh,const UStaffWeaponComponent& Staff,const FStaffCastPose& Pose)
{return Mesh.AuthoredContactInCamera(Pose,Staff.GripVariant(),true);}
}

bool UsesKeys(const FStaffCastPose& Pose)
{
    for(int32 I=FirstKey;I<FStaffCastPose::ArmPoseCount;++I)
        if(Pose.ArmWeights[I]>0.f)return true;
    return false;
}

FStaffCastPose Raise(const FStaffCastPose& Entry,float Fraction,float& EntryWeight)
{
    float W[ControlCount]={};Weights(Fraction,W);EntryWeight=W[0];
    auto Pose=StaffCastMotion::Blend(Entry,StaffCastMotion::Raised(),1.f-EntryWeight);
    for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)Pose.ArmWeights[I]=Entry.ArmWeights[I]*EntryWeight;
    for(int32 I=1;I<ControlCount;++I)Pose.ArmWeights[FirstKey+I-1]+=W[I];
    return Pose;
}

FStaffCastPose Ready(const FStaffCastPose& Entry,float Fraction,float& EntryWeight)
{
    const float U=StaffCastMotion::Ease(Fraction);EntryWeight=1.f-U;
    auto Pose=StaffCastMotion::Blend(Entry,StaffCastMotion::Raised(),U);
    for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)Pose.ArmWeights[I]=Entry.ArmWeights[I]*EntryWeight;
    Pose.ArmWeights[FStaffCastPose::ArmPoseCount-1]+=U;
    return Pose;
}

FStaffCastPose ResolveEntry(const UStaffWeaponComponent& Staff,FStaffCastPose Pose,
    const FStaffCastPose& Entry,float EntryWeight)
{
    if(auto* Mesh=Arms(Staff))
    {
        const FTransform EntryDelta=RawContact(*Mesh,Staff,Entry).Inverse()*Entry.Contact;
        FTransform Correction;Correction.Blend(FTransform::Identity,EntryDelta,EntryWeight);
        Pose.Contact=RawContact(*Mesh,Staff,Pose)*Correction;
    }
    return Pose;
}

FStaffCastPose ResolveRelease(const UStaffWeaponComponent& Staff,FStaffCastPose Pose)
{
    // The shaft follows the same interpolated shoulder/elbow/hand FK as the
    // visible arm, rather than moving independently and dragging it by the wrist.
    if(auto* Mesh=Arms(Staff))Pose.Contact=RawContact(*Mesh,Staff,Pose);
    return Pose;
}

FStaffCastPose ResolveRecovery(const UStaffWeaponComponent& Staff,FStaffCastPose Pose,
    const FStaffCastPose& From,const FStaffCastPose& Current,float Fraction)
{
    if(auto* Mesh=Arms(Staff))
    {
        const FTransform FromDelta=RawContact(*Mesh,Staff,From).Inverse()*From.Contact;
        const FTransform CurrentDelta=RawContact(*Mesh,Staff,Current).Inverse()*Current.Contact;
        FTransform Correction;Correction.Blend(FromDelta,CurrentDelta,StaffCastMotion::Ease(Fraction));
        Pose.Contact=RawContact(*Mesh,Staff,Pose)*Correction;
    }
    return Pose;
}

FStaffCastPose Settled(const UStaffWeaponComponent& Staff)
{
    auto Pose=StaffCastMotion::Raised();
    for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)Pose.ArmWeights[I]=0.f;
    Pose.ArmWeights[FStaffCastPose::ArmPoseCount-1]=1.f;
    if(auto* Mesh=Arms(Staff))Pose.Contact=RawContact(*Mesh,Staff,Pose);
    return Pose;
}
}
