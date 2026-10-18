#include "PotionArmPose.h"
#include "PotionUseMotion.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/CameraComponent.h"
#include "TwoBoneIK.h"

namespace { FQuat Frame(const FVector& X,const FVector& Z){return FRotationMatrix::MakeFromXZ(X,Z).ToQuat();} }
void FPotionArmPose::Reset(){CachedMesh.Reset();Bones.Reset();Rest.Reset();}
bool FPotionArmPose::Apply(USkeletalMeshComponent& Mesh,const FPotionUseMotion& Motion,float Age,FTransform& OutPalmWorld,
    bool bRight,const FTransform* PalmOverride,bool bFullWeight)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();const auto* Camera=Mesh.GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!Asset||!Camera)return false;
    const auto& Ref=Asset->GetRefSkeleton();
    const TCHAR* Side=bRight?TEXT("r"):TEXT("l");
    const auto Bone=[&](const TCHAR* Name){return Mesh.GetBoneIndex(FName(*FString::Printf(TEXT("%s_%s"),Name,Side)));};
    if(CachedMesh.Get()!=Asset||bCachedRight!=bRight)
    {
        Reset();CachedMesh=Asset;bCachedRight=bRight;Rest=Ref.GetRefBonePose();
        Clavicle=Bone(TEXT("clavicle"));Upper=Bone(TEXT("upperarm"));
        Lower=Bone(TEXT("lowerarm"));Hand=Bone(TEXT("hand"));
        const int32 Index=Bone(TEXT("index_01")),Middle=Bone(TEXT("middle_01")),Pinky=Bone(TEXT("pinky_01"));
        if(Clavicle<0||Upper<0||Lower<0||Hand<0||Index<0||Middle<0||Pinky<0)return false;
        for(int32 I=0;I<Rest.Num();++I)
        {
            const int32 P=Ref.GetParentIndex(I);if(P>=0)Rest[I]=Rest[I]*Rest[P];
            if((I==Clavicle||Ref.BoneIsChildOf(I,Clavicle))&&Ref.GetBoneName(I).ToString().EndsWith(bRight?TEXT("_r"):TEXT("_l")))Bones.Add(I);
        }
        const FVector H=Rest[Hand].GetLocation();
        PalmReference=Frame(Rest[Middle].GetLocation()-H,((Rest[Index].GetLocation()-H)^(Rest[Pinky].GetLocation()-H))*(bRight?-1.f:1.f));
    }
    if(Bones.IsEmpty())return false;
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();if(Pose.Num()!=Rest.Num())return false;
    Source=Pose;Goal=Pose;
    const FTransform MW=Mesh.GetComponentTransform(),CW=Camera->GetComponentTransform();
    const auto ToMesh=[&](const FVector& V){return MW.InverseTransformPosition(CW.TransformPosition(V));};
    const FQuat CToM=MW.GetRotation().Inverse()*CW.GetRotation();
    const FTransform Palm=PalmOverride?*PalmOverride:Motion.PalmAt(Age);
    const FVector RU=Rest[Lower].GetLocation()-Rest[Upper].GetLocation(),RL=Rest[Hand].GetLocation()-Rest[Lower].GetLocation();
    FVector Shoulder=Motion.Shoulder,Pole=Motion.Pole;
    if(bRight){Shoulder.Y=-Shoulder.Y;Pole.Y=-Pole.Y;}
    FVector A=ToMesh(Shoulder),Target=ToMesh(Palm.GetLocation());
    const FVector Reach=Target-A;const float Limit=(RU.Size()+RL.Size())*.93f;
    if(Reach.Size()>Limit)A+=Reach.GetSafeNormal()*(Reach.Size()-Limit);
    FVector E,H;AnimationCore::SolveTwoBoneIK(A,A+RU,A+RU+RL,ToMesh(Pole),Target,E,H,RU.Size(),RL.Size(),false,1.,1.);
    const FVector UD=(E-A).GetSafeNormal(),LD=(H-E).GetSafeNormal();
    const FQuat DesiredPalm=CToM*Palm.GetRotation();
    const FQuat HandRotation=DesiredPalm*PalmReference.Inverse()*Rest[Hand].GetRotation();
    // Follow the palm-width axis, then carry that same deformation through the
    // elbow. Helpers inherit a complete bone segment; no fractional double roll.
    const FVector Across=DesiredPalm.GetAxisY();
    const FQuat LowerDeform=FRotationMatrix::MakeFromXY(LD,Across).ToQuat()*
        FRotationMatrix::MakeFromXY(RL,PalmReference.GetAxisY()).ToQuat().Inverse();
    const FQuat UpperDeform=FQuat::FindBetweenNormals(LowerDeform.RotateVector(RU.GetSafeNormal()),UD)*LowerDeform;
    const float Closed=Motion.FingerClosure(Age);
    for(int32 I:Bones)
    {
        const int32 P=Ref.GetParentIndex(I);const FTransform Local=Ref.GetRefBonePose()[I];
        if(I==Clavicle){Goal[I]=Source[I];Goal[I].AddToTranslation(A-Source[Upper].GetLocation());}
        else if(I==Upper){Goal[I]=Rest[I];Goal[I].SetLocation(A);Goal[I].SetRotation(UpperDeform*Rest[I].GetRotation());}
        else if(I==Lower){Goal[I]=Rest[I];Goal[I].SetLocation(E);Goal[I].SetRotation(LowerDeform*Rest[I].GetRotation());}
        else if(I==Hand){Goal[I]=Rest[I];Goal[I].SetLocation(H);Goal[I].SetRotation(HandRotation);}
        else
        {
            Goal[I]=Local*Goal[P];const FString Name=Ref.GetBoneName(I).ToString();
            for(const auto& Digit:Motion.Digits)
            {
                const FString Prefix=Digit.Key.ToString()+TEXT("_");
                if(!Name.StartsWith(Prefix)||Name.Contains(TEXT("metacarpal")))continue;
                const int32 Segment=FCString::Atoi(*Name.Mid(Prefix.Len(),2))-1;if(Segment<0||Segment>2)break;
                const int32 Next=Mesh.GetBoneIndex(FName(*FString::Printf(TEXT("%s_%02d_%s"),*Digit.Key.ToString(),Segment+2,Side)));
                const FVector Direction=Next>=0?Rest[Next].GetLocation()-Rest[I].GetLocation():
                    Rest[I].GetRotation().RotateVector(Rest[P].GetRotation().UnrotateVector(Rest[I].GetLocation()-Rest[P].GetLocation()));
                float Closure=Closed;
                if(Digit.Key==TEXT("thumb")&&Motion.bOpensContainer)
                {
                    // Thumb lifts the stopper while the four fingers keep their hold.
                    const float Pop=FPotionUseMotion::Ease((Age-.47f)/.12f)*(1.f-FPotionUseMotion::Ease((Age-Motion.Uncap)/.13f));
                    Closure*=1.f-.72f*Pop;
                }
                const FPotionDigitPose* SupportDigit=bRight?Motion.RightDigits.Find(Digit.Key):nullptr;
                const FPotionDigitPose& DigitPose=SupportDigit?*SupportDigit:
                    (bRight&&Digit.Key==TEXT("thumb")&&Motion.bHasRightThumb?Motion.RightThumb:Digit.Value);
                if(DigitPose.bHasLocalRotations)
                {
                    // Carry opposition through the native thumb chain. MCP/IP
                    // flex about their own hinge, including entry and release,
                    // instead of re-aiming each segment against the palm plane.
                    const FQuat Delta=FQuat::Slerp(FQuat::Identity,DigitPose.LocalRotations[Segment],Closure);
                    Goal[I].SetRotation((Goal[I].GetRotation()*Delta).GetNormalized());
                    break;
                }
                const float Flex=FMath::DegreesToRadians(FMath::Lerp(8.f+Segment*4.f,float(DigitPose.Flex[Segment]),Closure));
                const float Spread=FMath::DegreesToRadians(DigitPose.Spread[Segment])*(bRight?-1.f:1.f);
                const FQuat Neutral=DesiredPalm*FQuat(FVector::UpVector,Spread);
                const FQuat Curled=Neutral*FQuat(FVector::RightVector,-Flex);
                if(DigitPose.bPreserveNativeRoll)
                {
                    // Thumb opposition has its own native frame. Rebuilding every
                    // phalanx against the palm normal adds axial roll at MCP/IP.
                    // Aim the inherited native segment with a shortest-arc swing;
                    // keep its roll, local translation and the authored grip axis.
                    const FVector NativeAxis=Rest[I].GetRotation().UnrotateVector(Direction.GetSafeNormal());
                    const FQuat Carried=Goal[I].GetRotation();
                    const FQuat Swing=FQuat::FindBetweenNormals(Carried.RotateVector(NativeAxis),Curled.GetAxisX());
                    Goal[I].SetRotation((Swing*Carried).GetNormalized());
                }
                else Goal[I].SetRotation((Curled*Frame(Direction,PalmReference.GetAxisZ()).Inverse()*Rest[I].GetRotation()).GetNormalized());
                break;
            }
        }
    }
    const float Weight=bFullWeight?1.f:Motion.Layer(Age);
    for(int32 I:Bones)
    {
        const int32 P=Ref.GetParentIndex(I);
        FTransform Local=Source[I].GetRelativeTransform(Source[P]);
        Local.BlendWith(Goal[I].GetRelativeTransform(Goal[P]),Weight);
        Pose[I]=Local*Pose[P];
    }
    const FTransform HandWorld=Pose[Hand]*MW;
    OutPalmWorld=FTransform(HandWorld.GetRotation()*Rest[Hand].GetRotation().Inverse()*PalmReference,HandWorld.GetLocation());
    return true;
}
