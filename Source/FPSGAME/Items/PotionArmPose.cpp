#include "PotionArmPose.h"
#include "PotionUseMotion.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/CameraComponent.h"
#include "TwoBoneIK.h"

namespace { FQuat Frame(const FVector& X,const FVector& Z){return FRotationMatrix::MakeFromXZ(X,Z).ToQuat();} }
void FPotionArmPose::Reset(){CachedMesh.Reset();Bones.Reset();Rest.Reset();}
bool FPotionArmPose::Apply(USkeletalMeshComponent& Mesh,const FPotionUseMotion& Motion,float Age,FTransform& OutPalmWorld)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();const auto* Camera=Mesh.GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!Asset||!Camera)return false;
    const auto& Ref=Asset->GetRefSkeleton();
    if(CachedMesh.Get()!=Asset)
    {
        Reset();CachedMesh=Asset;Rest=Ref.GetRefBonePose();
        Clavicle=Mesh.GetBoneIndex(TEXT("clavicle_l"));Upper=Mesh.GetBoneIndex(TEXT("upperarm_l"));
        Lower=Mesh.GetBoneIndex(TEXT("lowerarm_l"));Hand=Mesh.GetBoneIndex(TEXT("hand_l"));
        const int32 Index=Mesh.GetBoneIndex(TEXT("index_01_l")),Middle=Mesh.GetBoneIndex(TEXT("middle_01_l")),Pinky=Mesh.GetBoneIndex(TEXT("pinky_01_l"));
        if(Clavicle<0||Upper<0||Lower<0||Hand<0||Index<0||Middle<0||Pinky<0)return false;
        for(int32 I=0;I<Rest.Num();++I)
        {
            const int32 P=Ref.GetParentIndex(I);if(P>=0)Rest[I]=Rest[I]*Rest[P];
            if((I==Clavicle||Ref.BoneIsChildOf(I,Clavicle))&&Ref.GetBoneName(I).ToString().EndsWith(TEXT("_l")))Bones.Add(I);
        }
        const FVector H=Rest[Hand].GetLocation();
        PalmReference=Frame(Rest[Middle].GetLocation()-H,(Rest[Index].GetLocation()-H)^(Rest[Pinky].GetLocation()-H));
    }
    if(Bones.IsEmpty())return false;
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();if(Pose.Num()!=Rest.Num())return false;
    Source=Pose;Goal=Pose;
    const FTransform MW=Mesh.GetComponentTransform(),CW=Camera->GetComponentTransform();
    const auto ToMesh=[&](const FVector& V){return MW.InverseTransformPosition(CW.TransformPosition(V));};
    const FQuat CToM=MW.GetRotation().Inverse()*CW.GetRotation();
    const FTransform Palm=Motion.PalmAt(Age);
    const FVector RU=Rest[Lower].GetLocation()-Rest[Upper].GetLocation(),RL=Rest[Hand].GetLocation()-Rest[Lower].GetLocation();
    FVector A=ToMesh(Motion.Shoulder),Target=ToMesh(Palm.GetLocation());
    const FVector Reach=Target-A;const float Limit=(RU.Size()+RL.Size())*.93f;
    if(Reach.Size()>Limit)A+=Reach.GetSafeNormal()*(Reach.Size()-Limit);
    FVector E,H;AnimationCore::SolveTwoBoneIK(A,A+RU,A+RU+RL,ToMesh(Motion.Pole),Target,E,H,RU.Size(),RL.Size(),false,1.,1.);
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
                const int32 Next=Mesh.GetBoneIndex(FName(*FString::Printf(TEXT("%s_%02d_l"),*Digit.Key.ToString(),Segment+2)));
                const FVector Direction=Next>=0?Rest[Next].GetLocation()-Rest[I].GetLocation():
                    Rest[I].GetRotation().RotateVector(Rest[P].GetRotation().UnrotateVector(Rest[I].GetLocation()-Rest[P].GetLocation()));
                float Closure=Closed;
                if(Digit.Key==TEXT("thumb"))
                {
                    // Thumb lifts the stopper while the four fingers keep their hold.
                    const float Pop=FPotionUseMotion::Ease((Age-.47f)/.12f)*(1.f-FPotionUseMotion::Ease((Age-Motion.Uncap)/.13f));
                    Closure*=1.f-.72f*Pop;
                }
                const float Flex=FMath::DegreesToRadians(FMath::Lerp(8.f+Segment*4.f,float(Digit.Value.Flex[Segment]),Closure));
                const float Spread=FMath::DegreesToRadians(Digit.Value.Spread[Segment]);
                const FQuat Neutral=DesiredPalm*FQuat(FVector::UpVector,Spread);
                const FQuat Curled=Neutral*FQuat(FVector::RightVector,-Flex);
                Goal[I].SetRotation((Curled*Frame(Direction,PalmReference.GetAxisZ()).Inverse()*Rest[I].GetRotation()).GetNormalized());
                break;
            }
        }
    }
    const float Weight=Motion.Layer(Age);
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
