#include "HorseRiderComponent.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraTypes.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

float UHorseRiderComponent::EyeHeightOffset() const
{
    if(!Active())return 0.f;
    // The character root already follows the stirrup and saddle. Only the lean
    // and gait need an eye offset on top of the standard anatomical camera.
    return EyeBob*GaitViewScale-6.f*FMath::Sin(PI*MountAmount());
}

namespace RiderPose
{
    struct FJoint { int32 Index; FQuat Orientation; };
    // Keep the wrist and boot inside the anatomical cone of their solved parent.
    static FQuat LimitRotation(const FQuat& Neutral,const FQuat& Goal,float LimitDegrees)
    {
        const double Angle=Neutral.AngularDistance(Goal);
        if(Angle<=FMath::DegreesToRadians(LimitDegrees))return Goal;
        return FQuat::Slerp(Neutral,Goal,FMath::DegreesToRadians(LimitDegrees)/Angle).GetNormalized();
    }
    // Solve in component space from bone lengths; pole points distinguish elbows from knees.
    static void Solve(const FReferenceSkeleton& Ref,const TArray<FTransform>& Base,
        FName Upper,FName Lower,FName End,const FVector& Goal,const FVector& Pole,
        TArray<FJoint,TInlineAllocator<16>>& Joints)
    {
        const int32 A=Ref.FindBoneIndex(Upper),B=Ref.FindBoneIndex(Lower),C=Ref.FindBoneIndex(End);
        if(A==INDEX_NONE||B==INDEX_NONE||C==INDEX_NONE)return;
        const FVector Hip=Base[A].GetLocation(),Knee=Base[B].GetLocation(),Tip=Base[C].GetLocation();
        const FVector Axis=(Goal-Hip).GetSafeNormal();
        const FVector Bend=FVector::VectorPlaneProject(Pole,Axis).GetSafeNormal();
        if(Axis.IsNearlyZero()||Bend.IsNearlyZero())return;
        const double L1=(Knee-Hip).Size(),L2=(Tip-Knee).Size();
        if(L1<1||L2<1)return;
        // Ease into extension as the saddle moves past elbow reach. A straight-arm
        // clamp snaps from a locked joint to deep flexion on the following frame.
        const double Reach=L1+L2, SoftZone=Reach*.18, Limit=Reach*.985;
        const double Start=Limit-SoftZone;
        const double Requested=FMath::Max((Goal-Hip).Size(),FMath::Abs(L1-L2)+.01);
        const double D=Requested<=Start?Requested:Limit-SoftZone*FMath::Exp(-(Requested-Start)/SoftZone);
        const double Along=(D*D+L1*L1-L2*L2)/(2.*D);
        const FVector Joint=Hip+Axis*Along+Bend*FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
        const FQuat UpperQ=FQuat::FindBetweenNormals((Knee-Hip).GetSafeNormal(),(Joint-Hip).GetSafeNormal());
        const FQuat LowerQ=FQuat::FindBetweenNormals(UpperQ.RotateVector((Tip-Knee).GetSafeNormal()),
            (Hip+Axis*D-Joint).GetSafeNormal())*UpperQ;
        Joints.Add({A,UpperQ*Base[A].GetRotation()});
        Joints.Add({B,LowerQ*Base[B].GetRotation()});
        Joints.Add({C,LowerQ*Base[C].GetRotation()});
    }
    // Keep the knee's hinge axis on the same side for both segments. Using two
    // independent shortest-arc swings loses the axial rotation at high hip flexion.
    static void Leg(const TArray<FTransform>& Base,int32 Hip,int32 Knee,int32 Foot,
        const FVector& Goal,const FVector& Pole,const FVector& RefFront,const FQuat& Boot,const FVector& Toe,float Release,
        TArray<FJoint,TInlineAllocator<16>>& Joints)
    {
        const FVector A=Base[Hip].GetLocation();
        const FVector Thigh=Base[Knee].GetLocation()-A;
        const FVector Shin=Base[Foot].GetLocation()-Base[Knee].GetLocation();
        const FVector BallGoal=Goal+Boot.RotateVector(Toe);
        const double L1=Thigh.Size(),L2=Shin.Size(),Limit=L1+L2-.65;
        if(L1<1. || L2<1.)return;
        const FVector RestHinge=FVector::CrossProduct((Thigh+Shin).GetSafeNormal(),RefFront).GetSafeNormal();
        const FQuat ThighBind=FRotationMatrix::MakeFromXY(Thigh,RestHinge).ToQuat();
        const FQuat ShinBind=FRotationMatrix::MakeFromXY(Shin,RestHinge).ToQuat();
        FQuat FootFrame=Boot,UpperFrame=Base[Hip].GetRotation(),LowerFrame=Base[Knee].GetRotation();
        // Solve around the ball of the foot so changing ankle pitch does not drag the stirrup.
        for(int Pass=0;Pass<3;++Pass)
        {
            const FVector Aim=BallGoal-FootFrame.RotateVector(Toe)-A;
            const FVector Line=Aim.GetSafeNormal();
            const FVector Bend=FVector::VectorPlaneProject(Pole,Line).GetSafeNormal();
            if(Line.IsNearlyZero()||Bend.IsNearlyZero())return;
            const double Reach=FMath::Max(Aim.Size(),FMath::Abs(L1-L2)+1.);
            const double D=Reach>Limit-4.?Limit-4.*FMath::Exp(-(Reach-Limit+4.)/4.):Reach;
            const double Along=(D*D+L1*L1-L2*L2)/(2.*D);
            const FVector ToKnee=Line*Along+Bend*FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
            const FVector Hinge=FVector::CrossProduct(Line,Bend).GetSafeNormal();
            UpperFrame=(FRotationMatrix::MakeFromXY(ToKnee,Hinge).ToQuat()*ThighBind.Inverse()*Base[Hip].GetRotation()).GetNormalized();
            LowerFrame=(FRotationMatrix::MakeFromXY(Line*D-ToKnee,Hinge).ToQuat()*ShinBind.Inverse()*Base[Knee].GetRotation()).GetNormalized();
            if(Release<=KINDA_SMALL_NUMBER||Pass==2)break;
            const FQuat Carried=LowerFrame*Base[Knee].GetRotation().Inverse()*Base[Foot].GetRotation();
            FootFrame=FQuat::Slerp(Boot,LimitRotation(Carried,Boot,32.f),Release).GetNormalized();
        }
        Joints.Add({Hip,UpperFrame});
        Joints.Add({Knee,LowerFrame});
        Joints.Add({Foot,FootFrame});
    }

}
void UHorseRiderComponent::ApplyPose(USkeletalMeshComponent& Mesh,TArray<FTransform>& Bones)
{
    if(State.Phase==ERiderPhase::Seated)BuildContactPose(Mesh,Bones);
}

void UHorseRiderComponent::BuildContactPose(USkeletalMeshComponent& Mesh,TArray<FTransform>& Bones)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    if(!Active()||!IsValid(State.Horse)||!Player.IsValid()||!Asset)return;
    const auto& Ref=Asset->GetRefSkeleton();
    const auto& Local=Ref.GetRefBonePose();
    if(Bones.Num()!=Local.Num()||Bones.IsEmpty())return;
    const int32 Hip=Ref.FindBoneIndex(TEXT("pelvis"));
    if(Hip==INDEX_NONE)return;
    if(PoseAsset.Get()!=Asset)
    {
        PoseAsset=Asset;
        ReferenceCS=Local;
        for(int32 I=1;I<Local.Num();++I)
            ReferenceCS[I]=Local[I]*ReferenceCS[Ref.GetParentIndex(I)];
        SaddleLegBones.Init(false,Local.Num());
        const int32 LeftLeg=Ref.FindBoneIndex(TEXT("thigh_l")),RightLeg=Ref.FindBoneIndex(TEXT("thigh_r"));
        for(int32 I=0;I<Local.Num();++I)
        {
            const int32 Parent=Ref.GetParentIndex(I);
            SaddleLegBones[I]=I==LeftLeg||I==RightLeg||(Parent!=INDEX_NONE&&SaddleLegBones[Parent]);
        }
        GripLocalTurns.Reset();
        for(const bool bLeft:{true,false})
        {
            const TCHAR* Side=bLeft?TEXT("l"):TEXT("r");
            const auto Bone=[&](const TCHAR* Digit,int32 Segment)
            {return Ref.FindBoneIndex(*FString::Printf(TEXT("%s_%02d_%s"),Digit,Segment,Side));};
            const int32 Index=Bone(TEXT("index"),1),Pinky=Bone(TEXT("pinky"),1),Middle=Bone(TEXT("middle"),1);
            const int32 Tip=Bone(TEXT("middle"),3);
            if(Index==INDEX_NONE||Pinky==INDEX_NONE||Middle==INDEX_NONE||Tip==INDEX_NONE)continue;
            FVector KnuckleAxis=(ReferenceCS[Index].GetLocation()-ReferenceCS[Pinky].GetLocation()).GetSafeNormal();
            const FVector Fingers=ReferenceCS[Tip].GetLocation()-ReferenceCS[Middle].GetLocation();
            if(FVector::CrossProduct(KnuckleAxis,Fingers).Z>0.)KnuckleAxis*=-1.;
            for(const TCHAR* Digit:{TEXT("index"),TEXT("middle"),TEXT("ring"),TEXT("pinky")})
                for(int32 Segment=1;Segment<=3;++Segment)
                {
                    const int32 I=Bone(Digit,Segment);
                    if(I==INDEX_NONE)continue;
                    const float Degrees=Segment==2?46.f:(Segment==1?33.f:24.f);
                    GripLocalTurns.Add(I,FQuat(ReferenceCS[I].GetRotation().UnrotateVector(KnuckleAxis),
                        FMath::DegreesToRadians(Degrees)));
                }
        }
    }
    const float P=MountAmount();
    const float Weight=FMath::SmoothStep(.02f,.23f,P);
    if(Weight<=0.f)return;
    const bool Seated=State.Phase==ERiderPhase::Seated;
    const auto& Horse=*State.Horse;
    const FTransform& BodyFrame=Mesh.GetComponentTransform();
    FTransform Frame=BodyFrame;
    const FQuat Ground=Seated?Horse.GroundTilt():FQuat::Identity;
    if(Seated)
    {
        // Solve legs in the saddle's heading while the body graph faces the weapon aim.
        const FQuat Turn=Ground*Horse.GetActorQuat()*Player->GetActorQuat().Inverse();
        Frame.SetRotation((Turn*BodyFrame.GetRotation()).GetNormalized());
        Frame.SetLocation(Player->GetActorLocation()+Turn.RotateVector(BodyFrame.GetLocation()-Player->GetActorLocation()));
    }
    const FVector F=Ground.RotateVector(Horse.GetActorForwardVector()),R=Ground.RotateVector(Horse.GetActorRightVector()),Z=Ground.GetUpVector();
    const FVector Seat=Horse.Saddle();
    const FVector NearSide=State.bFromRight?R:-R;
    const auto S=[P](float A,float B){return FMath::SmoothStep(A,B,P);};
    const FVector Approach=FMath::Lerp(State.Start.GetLocation(),State.Ground,S(0,.22f));
    const FQuat GroundYaw=RiderFacing(FMath::Min(P,.23f)).Quaternion();
    const FTransform GroundFrame=Mesh.GetRelativeTransform()*FTransform(GroundYaw,Approach);
    const FVector StandingHip=GroundFrame.TransformPosition(Bones[Hip].GetLocation())-Approach;
    const FVector HipGoal=Frame.InverseTransformPosition(RiderRoot(P)+Z*(State.Phase==ERiderPhase::Seated?SeatCompression:0.f)+StandingHip*(1.f-S(.30f,.62f)));
    const FVector Offset=HipGoal-ReferenceCS[Hip].GetLocation();
    const auto Goal=[&](const FVector& World){return Frame.InverseTransformPosition(World)-Offset;};
    const auto Axis=[&](const FVector& World){return Frame.InverseTransformVectorNoScale(World);};
    const FVector NearGrip=Seat+F*22.f+NearSide*19.f+Z*9.f;
    // The pushing hand moves from the cantle to the pommel after the rider rises.
    const FVector FarGrip=FMath::Lerp(Seat-F*16.f+NearSide*16.f+Z*8.f,
        Seat+F*15.f-NearSide*7.f+Z*10.f,S(.48f,.79f));
    TArray<RiderPose::FJoint,TInlineAllocator<16>> Joints;
    const FVector RiderForward=Seated?F:Player->GetActorForwardVector(),RiderRight=Seated?R:Player->GetActorRightVector();
    const FVector RefFront=Axis(RiderForward);
    const float Flight=S(.32f,.65f)*(1.f-S(.77f,.98f));
    for(const bool Left:{true,false})
    {
        const int32 A=Ref.FindBoneIndex(Left?TEXT("thigh_l"):TEXT("thigh_r"));
        const int32 B=Ref.FindBoneIndex(Left?TEXT("calf_l"):TEXT("calf_r"));
        const int32 C=Ref.FindBoneIndex(Left?TEXT("foot_l"):TEXT("foot_r"));
        const int32 Ball=Ref.FindBoneIndex(Left?TEXT("ball_l"):TEXT("ball_r"));
        if(A==INDEX_NONE||B==INDEX_NONE||C==INDEX_NONE||Ball==INDEX_NONE)continue;
        const bool Support=Left!=State.bFromRight;
        const FVector Out=Left?-R:R;
        const float ToeOut=Left?-8.f:9.f;
        const FQuat BootTurn=FQuat(Axis(Z),FMath::DegreesToRadians(ToeOut*S(.2f,.8f)))*
            FQuat(Axis(RiderRight),FMath::DegreesToRadians(Support?0.f:22.f*Flight));
        const FVector Toe=ReferenceCS[Ball].GetLocation()-ReferenceCS[C].GetLocation();
        const FVector Tread=Horse.Stirrup(Left);
        const FVector SeatedFoot=Tread+Z*3.5f-Frame.TransformVector(BootTurn.RotateVector(Toe));
        const FVector Planted=GroundFrame.TransformPosition(Bones[C].GetLocation());
        FVector Foot;
        if(Support)
        {
            const float Engage=State.Phase==ERiderPhase::Dismounting?S(.19f,.46f):S(.095f,.39f);
            Foot=FMath::Lerp(Planted,SeatedFoot,Engage);
            // Free the boot to the outside of the iron before sliding down.
            if(State.Phase==ERiderPhase::Dismounting)Foot+=Out*13.f*S(.12f,.35f)*(1.f-S(.50f,.76f));
        }
        else
        {
            const FVector Near=Seat-F*38.f+NearSide*46.f+Z*3.f;
            const FVector Far=Seat-F*37.f-NearSide*39.f+Z*9.f;
            Foot=FMath::Lerp(Planted,Near,S(.30f,.61f));
            Foot=FMath::Lerp(Foot,Far,S(.57f,.86f));
            Foot+=Z*18.f*FMath::Sin(PI*S(.57f,.86f));
            Foot=FMath::Lerp(Foot,SeatedFoot,S(.78f,.99f));
        }
        const float StepUp=Support?S(.05f,.22f)*(1.f-S(.40f,.63f)):0.f;
        // Lead the swing with the knee. Let the foot trail the shin until it approaches the far iron.
        const FVector StandingPole=RiderForward+RiderRight*(Left?-.20f:.20f);
        const FVector RidingPole=F+Out*(Support?.32f:.45f);
        const FVector Pole=FMath::Lerp(StandingPole,RidingPole,S(.10f,.72f))
            +Out*(Support?0.f:.75f*Flight)+(F*.30f+Z*.45f)*StepUp;
        RiderPose::Leg(ReferenceCS,A,B,C,Goal(Foot),Axis(Pole),RefFront,
            BootTurn*ReferenceCS[C].GetRotation(),ReferenceCS[C].GetRotation().UnrotateVector(Toe),
            Support?.82f*S(.06f,.20f)*(1.f-S(.48f,.72f)):Flight,Joints);
    }
    if(Seated)
    {
        const FTransform SaddleToBody=Frame.GetRelativeTransform(BodyFrame);
        const FVector HipInBody=SaddleToBody.TransformPosition(HipGoal);
        const FVector OffsetToSeat=HipInBody-Bones[Hip].GetLocation();
        // Keep the complete evaluated weapon pose (including root-space weapon/hand IK,
        // spine correctives and melee windup). All of it receives the same seat translation.
        for(int32 I=1;I<Bones.Num();++I)
        {
            if(I==Hip)
            {
                Bones[I]=ReferenceCS[I]*SaddleToBody;
                Bones[I].SetLocation(HipInBody);
            }
            else if(SaddleLegBones[I])
            {
                Bones[I]=Local[I]*Bones[Ref.GetParentIndex(I)];
                for(const auto& Joint:Joints)
                    if(Joint.Index==I)
                    {
                        Bones[I].SetRotation((SaddleToBody.GetRotation()*Joint.Orientation).GetNormalized());
                        break;
                    }
            }
            else Bones[I].AddToTranslation(OffsetToSeat);
        }
        return;
    }
    const int32 Spine=Ref.FindBoneIndex(TEXT("spine_01"));
    // Lean over the saddle while loading the near iron; the head never drives camera roll.
    const float Lean=FMath::Sin(PI*S(.15f,.96f));
    const FQuat LeanQ=Spine!=INDEX_NONE?
        FQuat(Axis(R),FMath::DegreesToRadians(5.f+14.f*Lean))*
        FQuat(Axis(F),FMath::DegreesToRadians((State.bFromRight?9.f:-9.f)*Lean)):FQuat::Identity;
    const FVector Pivot=Spine!=INDEX_NONE?ReferenceCS[Spine].GetLocation():FVector::ZeroVector;
    if(Spine!=INDEX_NONE)Joints.Add({Spine,LeanQ*ReferenceCS[Spine].GetRotation()});
    const int32 FirstArm=Joints.Num();
    const auto ArmGoal=[&](const FVector& World){return Pivot+LeanQ.UnrotateVector(Goal(World)-Pivot);};
    RiderPose::Solve(Ref,ReferenceCS,TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),ArmGoal(State.bFromRight?FarGrip:NearGrip),LeanQ.UnrotateVector(Axis(-F-R)),Joints);
    RiderPose::Solve(Ref,ReferenceCS,TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r"),ArmGoal(State.bFromRight?NearGrip:FarGrip),LeanQ.UnrotateVector(Axis(-F+R)),Joints);
    for(int32 I=FirstArm;I<Joints.Num();++I)Joints[I].Orientation=LeanQ*Joints[I].Orientation;
    // Orient the knuckles toward the pommel during the transfer.
    for(const bool bLeft:{true,false})
    {
        const int32 Hand=Ref.FindBoneIndex(bLeft?TEXT("hand_l"):TEXT("hand_r"));
        const int32 Finger=Ref.FindBoneIndex(bLeft?TEXT("middle_01_l"):TEXT("middle_01_r"));
        if(Hand==INDEX_NONE||Finger==INDEX_NONE)continue;
        const FVector AcrossHand=(ReferenceCS[Finger].GetLocation()-ReferenceCS[Hand].GetLocation()).GetSafeNormal();
        const FVector Reach=(F*.68f+R*(bLeft?.28f:-.28f)-Z*.65f).GetSafeNormal();
        for(auto& Joint:Joints)if(Joint.Index==Hand)
            Joint.Orientation=RiderPose::LimitRotation(Joint.Orientation,
                FQuat::FindBetweenNormals(AcrossHand,Axis(Reach))*ReferenceCS[Hand].GetRotation(),33.f);
    }
    // Rebuild the target hierarchy once. Twist, garment and finger bones follow their real parents.
    TArray<FTransform> Target;
    Target.SetNumUninitialized(Bones.Num());
    // Fixed transfers own the saddle grip. The graph blends it into the current weapon pose.
    for(int32 I=0;I<Bones.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        FTransform BoneLocal=Local[I];
        if(const FQuat* Grip=GripLocalTurns.Find(I))BoneLocal.ConcatenateRotation(*Grip);
        Target[I]=Parent==INDEX_NONE?BoneLocal:BoneLocal*Target[Parent];
        if(I==Hip)Target[I].SetLocation(HipGoal);
        for(const auto& Joint:Joints)
            if(I==Joint.Index){Target[I].SetRotation(Joint.Orientation.GetNormalized());break;}
    }
    // Blend the held weapon pose down the hierarchy, in parent space. Blending
    // component-space endpoints independently shortens the arms midway through a reach.
    for(int32 I=Bones.Num()-1;I>=0;--I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        FTransform Incoming=Parent==INDEX_NONE?Bones[I]:Bones[I].GetRelativeTransform(Bones[Parent]);
        const FTransform& TargetBone=Target[I];
        const FTransform Desired=Parent==INDEX_NONE?TargetBone:TargetBone.GetRelativeTransform(Target[Parent]);
        Incoming.BlendWith(Desired,Weight);
        Bones[I]=Incoming;
    }
    for(int32 I=1;I<Bones.Num();++I)
    {
        Bones[I]=Bones[I]*Bones[Ref.GetParentIndex(I)];
    }
}
