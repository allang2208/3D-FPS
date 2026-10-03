#include "FPSPlayerBodyGrip.h"
#include "Math/RotationMatrix.h"

namespace FPSBodyGrip
{
TArray<FTransform> ComponentBind(const FReferenceSkeleton& Ref)
{
    auto Result=Ref.GetRefBonePose();
    for(int32 I=0;I<Result.Num();++I)if(Ref.GetParentIndex(I)>=0)Result[I]=Result[I]*Result[Ref.GetParentIndex(I)];
    return Result;
}
FVector RelativePoint(const FTransform& Hand,const FVector& Point)
{return Hand.GetRotation().UnrotateVector(Point-Hand.GetLocation());}
FQuat Align(const FVector& A,const FVector& B)
{return FQuat::FindBetweenNormals(A.GetSafeNormal(),B.GetSafeNormal());}
}

void FFPSBodyGripRig::Initialize(const FReferenceSkeleton& Source,const FReferenceSkeleton& Target,FName From,FName To)
{
    using namespace FPSBodyGrip;
    Digits.Reset();Descendants.Reset();Parents.Reset();HalfJoint.Reset();IsFinger.Reset();Mount=FTransform::Identity;
    SourceHand=Source.FindBoneIndex(From);TargetHand=Target.FindBoneIndex(To);
    if(SourceHand==INDEX_NONE||TargetHand==INDEX_NONE)return;
    SourceBind=ComponentBind(Source);TargetBind=ComponentBind(Target);TargetLocal=Target.GetRefBonePose();
    const FString FromSide=From.ToString().Right(1),ToSide=To.ToString().Right(1);
    for(const TCHAR* Digit:{TEXT("thumb"),TEXT("index"),TEXT("middle"),TEXT("ring"),TEXT("pinky")})
    {
        FDigit D;bool Valid=true;
        for(int32 J=0;J<3;++J)
        {
            D.Source[J]=Source.FindBoneIndex(*FString::Printf(TEXT("%s_%02d_%s"),Digit,J+1,*FromSide));
            D.Target[J]=Target.FindBoneIndex(*FString::Printf(TEXT("%s_%02d_%s"),Digit,J+1,*ToSide));
            Valid&=D.Source[J]!=INDEX_NONE&&D.Target[J]!=INDEX_NONE;
        }
        if(Valid)Digits.Add(D);
    }
    for(int32 I=0;I<Target.GetNum();++I)
    {
        Parents.Add(Target.GetParentIndex(I));
        HalfJoint.Add(Target.GetBoneName(I).ToString().Contains(TEXT("_half_")));
        IsFinger.Add(Target.BoneIsChildOf(I,TargetHand));
        if(IsFinger.Last())Descendants.Add(I);
    }
    // Match the actual anatomical palm frames, including native left-hand rigs.
    // Place the weapon against the palm, not against an assumed wrist origin.
    if(Digits.Num()==5)
    {
        FVector P[2][3];
        for(int32 I=0;I<3;++I)
        {
            const auto& D=Digits[I==0?1:I==1?2:4];
            P[0][I]=RelativePoint(SourceBind[SourceHand],SourceBind[D.Source[0]].GetLocation());
            P[1][I]=RelativePoint(TargetBind[TargetHand],TargetBind[D.Target[0]].GetLocation());
        }
        const FQuat A=FRotationMatrix::MakeFromXY(P[0][1],P[0][0]-P[0][2]).ToQuat();
        const FQuat B=FRotationMatrix::MakeFromXY(P[1][1],P[1][0]-P[1][2]).ToQuat();
        const FQuat Rotation=(B*A.Inverse()).GetNormalized();
        Mount=FTransform(Rotation,(P[1][0]+P[1][1]+P[1][2])/3.-Rotation.RotateVector((P[0][0]+P[0][1]+P[0][2])/3.));
    }
}

void FFPSBodyGripRig::Transfer(const TArray<FTransform>& SourcePose,TArray<FTransform>& TargetPose) const
{
    using namespace FPSBodyGrip;
    if(!IsValid()||SourcePose.Num()!=SourceBind.Num())return;
    if(TargetPose.Num()!=TargetLocal.Num())TargetPose=TargetLocal;
    TArray<FQuat,TInlineAllocator<342>> World,Desired;
    TArray<bool,TInlineAllocator<342>> Driven;
    World.SetNum(TargetBind.Num());Desired.SetNum(TargetBind.Num());Driven.Init(false,TargetBind.Num());
    const FTransform& Hand=SourcePose[SourceHand];const FTransform& Native=TargetBind[TargetHand];
    const FQuat Frame=Native.GetRotation()*Mount.GetRotation()*Hand.GetRotation().Inverse();
    const auto Point=[&](int32 Bone)
    {return Native.TransformPosition(Mount.TransformPosition(RelativePoint(Hand,SourcePose[Bone].GetLocation())));};
    for(const auto& D:Digits)
    {
        for(int32 J=0;J<3;++J)
        {
            const int32 A=J<2?J:1,B=J<2?J+1:2;
            const FVector NativeAxis=TargetBind[D.Target[J]].GetRotation().UnrotateVector(TargetBind[D.Target[B]].GetLocation()-TargetBind[D.Target[A]].GetLocation());
            const FVector DonorAxis=SourceBind[D.Source[J]].GetRotation().UnrotateVector(SourceBind[D.Source[B]].GetLocation()-SourceBind[D.Source[A]].GetLocation());
            Desired[D.Target[J]]=(Frame*SourcePose[D.Source[J]].GetRotation()*Align(NativeAxis,DonorAxis)).GetNormalized();
            Driven[D.Target[J]]=true;
        }
        const FVector Root=TargetBind[D.Target[0]].GetLocation(),Goal=Point(D.Source[2]),Pole=Point(D.Source[1]);
        const double L1=FVector::Distance(Root,TargetBind[D.Target[1]].GetLocation());
        const double L2=FVector::Distance(TargetBind[D.Target[1]].GetLocation(),TargetBind[D.Target[2]].GetLocation());
        const FVector Axis=(Goal-Root).GetSafeNormal();
        const double Reach=FMath::Clamp(FVector::Distance(Root,Goal),FMath::Abs(L1-L2)+.001,L1+L2-.001);
        FVector Bend=(Pole-Root-Axis*FVector::DotProduct(Pole-Root,Axis)).GetSafeNormal();
        if(Bend.IsNearlyZero())Bend=FVector::CrossProduct(Axis,Native.GetRotation().GetAxisZ()).GetSafeNormal();
        const double Along=(L1*L1-L2*L2+Reach*Reach)/(2.*Reach);
        const FVector Joint=Root+Axis*Along+Bend*FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
        const FVector Spans[]={Joint-Root,Root+Axis*Reach-Joint};
        for(int32 J=0;J<2;++J)
        {
            const int32 Bone=D.Target[J];
            const FVector LocalAxis=TargetBind[Bone].GetRotation().UnrotateVector(TargetBind[D.Target[J+1]].GetLocation()-TargetBind[Bone].GetLocation());
            Desired[Bone]=(Align(Desired[Bone].RotateVector(LocalAxis),Spans[J])*Desired[Bone]).GetNormalized();
        }
    }
    for(int32 I=0;I<TargetBind.Num();++I)
    {
        const int32 Parent=Parents[I];const FQuat ParentPose=Parent>=0?World[Parent]:FQuat::Identity;
        FQuat Local=TargetLocal[I].GetRotation();
        if(Driven[I])Local=ParentPose.Inverse()*Desired[I];
        else if(HalfJoint[I]&&Parent>=0&&Driven[Parent])
        {
            const FQuat Delta=TargetLocal[Parent].GetRotation().Inverse()*TargetPose[Parent].GetRotation();
            Local=FQuat::Slerp(FQuat::Identity,Delta.Inverse(),.5f)*Local;
        }
        World[I]=(ParentPose*Local).GetNormalized();
        if(IsFinger[I])
        {TargetPose[I]=TargetLocal[I];TargetPose[I].SetRotation(Local.GetNormalized());}
    }
}
