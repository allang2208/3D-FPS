#include "ProductionToolMeshComponent.h"
#include "WarhammerHeadMarker.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

void UProductionToolMeshComponent::FinalizeBoneTransform()
{
    auto* Asset=GetSkeletalMeshAsset();auto& Pose=GetEditableComponentSpaceTransforms();
    const int32 Weapon=GetBoneIndex(TEXT("WPN_root"));
    if(Asset&&FloorWeight>0.f&&Pose.IsValidIndex(Weapon))
    {
        const auto& Ref=Asset->GetRefSkeleton();const TArray<FTransform> Source=Pose;
        // Authored hammer-head bottom marker in the unchanged native WPN frame.
        const FVector Head=Source[Weapon].TransformPosition(WarhammerHeavy::HeadMarker);
        const FVector Target=GetComponentTransform().InverseTransformPosition(FloorPoint);
        const FVector Delta=(Target-Head)*FMath::Clamp(FloorWeight,0.f,1.f);
        for(int32 I=0;I<Pose.Num();++I)
            if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))Pose[I].AddToTranslation(Delta);
        for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
        {
            const auto Index=[&](const TCHAR* Stem){return GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
            const int32 C=Index(TEXT("clavicle")),U=Index(TEXT("upperarm")),L=Index(TEXT("lowerarm")),H=Index(TEXT("hand"));
            if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
            const FVector OldA=Source[U].GetLocation(),OldE=Source[L].GetLocation(),OldH=Source[H].GetLocation();
            const double Upper=(OldE-OldA).Size(),Lower=(OldH-OldE).Size();
            const FVector Goal=OldH+Delta,Reach=Goal-OldA;
            const FVector Shift=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-(Upper+Lower)*.985);
            FVector E,Hand;
            AnimationCore::SolveTwoBoneIK(OldA+Shift,OldE+Shift,OldH+Shift,OldE+Shift,Goal,E,Hand,Upper,Lower,false,1.,1.);
            const FQuat LowerTurn=FQuat::FindBetweenNormals((OldH-OldE).GetSafeNormal(),(Hand-E).GetSafeNormal());
            const FQuat UpperTurn=FQuat::FindBetweenNormals(LowerTurn.RotateVector((OldE-OldA).GetSafeNormal()),(E-OldA-Shift).GetSafeNormal())*LowerTurn;
            FTransform A=Source[U],B=Source[L],W=Source[H];
            A.SetLocation(OldA+Shift);A.SetRotation((UpperTurn*A.GetRotation()).GetNormalized());
            B.SetLocation(E);B.SetRotation((LowerTurn*B.GetRotation()).GetNormalized());W.SetLocation(Hand);
            for(int32 I=C;I<Pose.Num();++I)
            {
                if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))continue;
                if(I==C)Pose[I].AddToTranslation(Shift);
                else if(I==U)Pose[I]=A;
                else if(I==L)Pose[I]=B;
                else if(I==H)Pose[I]=W;
                else if(Ref.BoneIsChildOf(I,C))
                {
                    const int32 Parent=Ref.GetParentIndex(I);
                    Pose[I]=Source[I].GetRelativeTransform(Source[Parent])*Pose[Parent];
                }
            }
        }
    }
    Super::FinalizeBoneTransform();
}
