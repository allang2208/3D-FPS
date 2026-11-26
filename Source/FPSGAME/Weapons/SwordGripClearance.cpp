#include "SwordGripClearance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

namespace
{
FQuat Plane(const FVector& Upper,const FVector& Lower)
{return FRotationMatrix::MakeFromXZ(Upper.GetSafeNormal(),FVector::CrossProduct(Upper,Lower).GetSafeNormal()).ToQuat();}
double Contact(double Value,double Full,double Free)
{
    const double X=FMath::Clamp((Value-Full)/(Free-Full),0.,1.);
    return 1.-X*X*X*(10.+X*(-15.+6.*X));
}
}

bool FSwordGripClearance::Configure(const FSwordGripFit& InFit)
{
    bool Same=Fit.Digits.Num()==InFit.Digits.Num();
    for(int32 Side=0;Side<2;++Side)
        Same=Same&&Fit.Offset[Side].Equals(InFit.Offset[Side])&&Fit.Rotation[Side].Equals(InFit.Rotation[Side]);
    for(const auto& Pair:InFit.Digits)
    {
        const FQuat* Current=Fit.Digits.Find(Pair.Key);
        Same=Same&&Current&&Current->Equals(Pair.Value);
    }
    if(Same)return false;
    Fit=InFit;ReferenceMesh.Reset();return true;
}

void FSwordGripClearance::CaptureIdle(USkeletalMeshComponent& Mesh)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();ReferenceMesh=Asset;
    const auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    Weapon=Mesh.GetBoneIndex(TEXT("WPN_root"));
    if(!Asset||!Pose.IsValidIndex(Weapon)){ReferenceMesh.Reset();return;}
    const auto& Ref=Asset->GetRefSkeleton();Parents.SetNum(Pose.Num());Arm.Init(INDEX_NONE,Pose.Num());
    DigitDelta.Init(FQuat::Identity,Pose.Num());IdleLocal.SetNum(Pose.Num());
    for(int32 I=0;I<Pose.Num();++I)
    {
        Parents[I]=Ref.GetParentIndex(I);
        IdleLocal[I]=Parents[I]==INDEX_NONE?Pose[I].GetRotation():Pose[I].GetRelativeTransform(Pose[Parents[I]]).GetRotation();
        if(const FQuat* Delta=Fit.Digits.Find(Ref.GetBoneName(I)))DigitDelta[I]=*Delta;
    }
    for(int32 Side=0;Side<2;++Side)
    {
        const FString S=Side==0?TEXT("r"):TEXT("l");
        Upper[Side]=Mesh.GetBoneIndex(FName(*(TEXT("upperarm_")+S)));
        Lower[Side]=Mesh.GetBoneIndex(FName(*(TEXT("lowerarm_")+S)));
        Hand[Side]=Mesh.GetBoneIndex(FName(*(TEXT("hand_")+S)));
        for(int32 J=0;J<2;++J)Twist[Side][J]=Mesh.GetBoneIndex(FName(*(FString(J==0?TEXT("lowerarm_twist_01_"):TEXT("lowerarm_twist_02_"))+S)));
        if(!Pose.IsValidIndex(Upper[Side])||!Pose.IsValidIndex(Lower[Side])||!Pose.IsValidIndex(Hand[Side]))continue;
        Grip[Side]=Pose[Hand[Side]].GetRelativeTransform(Pose[Weapon]);
        for(int32 I=0;I<Pose.Num();++I)
            if(I!=Weapon&&!Ref.BoneIsChildOf(I,Weapon)&&(I==Upper[Side]||Ref.BoneIsChildOf(I,Upper[Side])))Arm[I]=Side;
    }
}

void FSwordGripClearance::Apply(USkeletalMeshComponent& Mesh,ESwordGripMode Mode)
{
    if(Fit.IsEmpty()||ReferenceMesh.Get()!=Mesh.GetSkeletalMeshAsset())return;
    const bool HoldPair=Mode!=ESwordGripMode::Adaptive;
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    if(!Pose.IsValidIndex(Weapon)||Pose.Num()!=Parents.Num())return;
    double Weights[2]={0.,0.};
    for(int32 Side=0;Side<2;++Side)if(Pose.IsValidIndex(Hand[Side]))
    {
        const FTransform Relative=Pose[Hand[Side]].GetRelativeTransform(Pose[Weapon]);
        const double Distance=FVector::Distance(Relative.GetLocation(),Grip[Side].GetLocation());
        const double Angle=FMath::RadiansToDegrees(Relative.GetRotation().AngularDistance(Grip[Side].GetRotation()));
        Weights[Side]=Contact(Distance,1.2,6.)*Contact(Angle,12.,50.);
        if(HoldPair)Weights[Side]=1.;
    }
    if(Weights[0]<=UE_SMALL_NUMBER&&Weights[1]<=UE_SMALL_NUMBER)return;
    Source=Pose;
    for(int32 Side=0;Side<2;++Side)
    {
        const double Weight=Weights[Side];
        if(Weight<=UE_SMALL_NUMBER||!Pose.IsValidIndex(Upper[Side])||!Pose.IsValidIndex(Lower[Side]))continue;
        const int32 U=Upper[Side],L=Lower[Side],H=Hand[Side];
        const FVector OldA=Source[U].GetLocation(),E=Source[L].GetLocation(),OldH=Source[H].GetLocation();
        const double UpperLength=(E-OldA).Size(),LowerLength=(OldH-E).Size();
        const FQuat WQ=Source[Weapon].GetRotation();
        FQuat HandleTurn=FQuat::Identity;
        if(HoldPair)
        {
            const FVector Rest=Grip[Side].GetLocation();
            const FVector Now=Source[H].GetRelativeTransform(Source[Weapon]).GetLocation();
            HandleTurn=FQuat(FVector::UpVector,FMath::FindDeltaAngleRadians(FMath::Atan2(Rest.Y,Rest.X),FMath::Atan2(Now.Y,Now.X)));
        }
        const FQuat Roll=FQuat::Slerp(FQuat::Identity,Fit.Rotation[Side],Weight).GetNormalized();
        const FVector Local=HoldPair?Grip[Side].GetLocation()*Source[Weapon].GetScale3D():
            WQ.UnrotateVector(OldH-Source[Weapon].GetLocation());
        const FVector Pivot(0.,0.,Local.Z);
        // Keep each accepted grasp attached to its authored side of the handle.
        // The support wrist must not inherit the leading hand's different roll.
        FVector Offset=Fit.Offset[Side]*Weight;
        // The Highland pommel shoulder rises into the little finger as the
        // two-hand grasp rolls. Give it 1.5 mm here, easing to zero at idle.
        if(HoldPair && Side==1)
            Offset.Z+=.15*FMath::SmoothStep(0.,FMath::DegreesToRadians(30.),HandleTurn.AngularDistance(FQuat::Identity));
        FVector Goal=Source[Weapon].GetLocation()+(WQ*HandleTurn).RotateVector(Pivot+Roll.RotateVector(Local-Pivot)+Offset);
        const FQuat HandQ=HoldPair?(WQ*HandleTurn*Roll*Grip[Side].GetRotation()).GetNormalized():
            (WQ*Roll*WQ.Inverse()*Source[H].GetRotation()).GetNormalized();
        // Preserve actual segment lengths and shoulder support at extreme poses.
        FVector A,NewE,NewH;
        FQuat UQ,LQ;
        if(Mode==ESwordGripMode::HeldAuthoredArms)
        {
            // These tracks already solve the shoulder, elbow, wrist and twist
            // stations. Carry their complete frame through the hilt fitting.
            // Solving the elbow plane again at full reach can reverse its side.
            const FQuat Delta=(HandQ*Source[H].GetRotation().Inverse()).GetNormalized();
            const auto FitPoint=[&](const FVector& Point){return Goal+Delta.RotateVector(Point-OldH);};
            A=FitPoint(OldA);NewE=FitPoint(E);NewH=Goal;
            UQ=Delta*Source[U].GetRotation();LQ=Delta*Source[L].GetRotation();
            const int32 Clavicle=Parents[U];
            if(Clavicle!=INDEX_NONE)
            {
                Pose[Clavicle].SetLocation(FitPoint(Source[Clavicle].GetLocation()));
                Pose[Clavicle].SetRotation((Delta*Source[Clavicle].GetRotation()).GetNormalized());
            }
        }
        else
        {
            const FVector Reach=Goal-OldA;const double Limit=(UpperLength+LowerLength)*.98;
            const FVector Shift=HoldPair?Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-Limit):FVector::ZeroVector;
            A=OldA+Shift;
            if(!HoldPair && Reach.Size()>Limit)Goal=A+Reach.GetSafeNormal()*Limit;
            AnimationCore::SolveTwoBoneIK(A,E+Shift,OldH+Shift,E+Shift,Goal,NewE,NewH,UpperLength,LowerLength,false,1.,1.);
            UQ=(Plane(NewE-A,NewH-NewE)*Plane(E-OldA,OldH-E).Inverse()*Source[U].GetRotation()).GetNormalized();
            LQ=(Plane(NewH-NewE,NewE-A)*Plane(OldH-E,E-OldA).Inverse()*Source[L].GetRotation()).GetNormalized();
            if(HoldPair && Parents[U]!=INDEX_NONE)Pose[Parents[U]].AddToTranslation(Shift);
        }
        for(int32 I=0;I<Pose.Num();++I)if(Arm[I]==Side)
        {
            if(I==U){Pose[I].SetLocation(A);Pose[I].SetRotation(UQ);}
            else if(I==L){Pose[I].SetLocation(NewE);Pose[I].SetRotation(LQ);}
            else if(I==H){Pose[I]=Source[I];Pose[I].SetLocation(NewH);Pose[I].SetRotation(HandQ);}
            else if(Parents[I]!=INDEX_NONE)
            {
                FTransform Relative=Source[I].GetRelativeTransform(Source[Parents[I]]);
                if(HoldPair && Mesh.GetSkeletalMeshAsset()->GetRefSkeleton().BoneIsChildOf(I,H))
                    Relative.SetRotation(IdleLocal[I]);
                // Leave authored finger gestures alone as they leave the resting grasp.
                if(!DigitDelta[I].IsIdentity())
                {
                    const double FingerWeight=Weight*Contact(FMath::RadiansToDegrees(Relative.GetRotation().AngularDistance(IdleLocal[I])),10.,45.);
                    Relative.SetRotation((Relative.GetRotation()*FQuat::Slerp(FQuat::Identity,DigitDelta[I],FingerWeight)).GetNormalized());
                }
                Pose[I]=Relative*Pose[Parents[I]];
            }
        }
        const FQuat OldLQ=Source[L].GetRotation();
        const FVector Axis=OldLQ.UnrotateVector((OldH-E).GetSafeNormal());
        FQuat Delta=(LQ.Inverse()*HandQ)*(OldLQ.Inverse()*Source[H].GetRotation()).Inverse();Delta.Normalize();
        const double Turn=FMath::UnwindRadians(2.*FMath::Atan2(FVector(Delta.X,Delta.Y,Delta.Z)|Axis,Delta.W));
        for(int32 J=0;J<2;++J)if(Pose.IsValidIndex(Twist[Side][J]))
        {
            const int32 I=Twist[Side][J];
            Pose[I].SetRotation((LQ*FQuat(Axis,Turn*(J==0?1.:.5))*OldLQ.Inverse()*Source[I].GetRotation()).GetNormalized());
        }
    }
}
