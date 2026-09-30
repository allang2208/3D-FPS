#include "FPSOutfitSecondaryMotion.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<float> CVarChainmailSway(TEXT("fps.Outfit.ChainmailSway"),1.f,
    TEXT("Shared chainmail/lining cuff inertia strength, 0..1. No cloth simulation."),ECVF_Default);
constexpr float MaximumOffsetCm=.12f;
constexpr float Frequency=2.f*UE_PI*6.5f;
constexpr float Damping=.85f;
const FName Parameters[]={TEXT("CuffLagLeft"),TEXT("CuffLagRight"),TEXT("CuffLagPreviousLeft"),TEXT("CuffLagPreviousRight")};

void ConfigureCameraRegion(USkeletalMeshComponent& Garment,
    const TArray<TWeakObjectPtr<UMaterialInstanceDynamic>>& Materials,bool bFirstPerson)
{
    const auto* Mesh=Garment.GetSkeletalMeshAsset();if(!Mesh)return;
    const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
    TArray<FTransform> Rest=Ref.GetRefBonePose();
    for(int32 I=0;I<Rest.Num();++I)
        if(const int32 Parent=Ref.GetParentIndex(I);Parent!=INDEX_NONE)Rest[I]=Rest[I]*Rest[Parent];
    for(int32 Side=0;Side<2;++Side)
    {
        const TCHAR* Suffix=Side==0?TEXT("l"):TEXT("r");
        const TCHAR* Label=Side==0?TEXT("Left"):TEXT("Right");
        const TCHAR* Bones[]={TEXT("upperarm"),TEXT("lowerarm"),TEXT("hand")};
        const TCHAR* Points[]={TEXT("Shoulder"),TEXT("Elbow"),TEXT("Wrist")};
        int32 Indices[3];bool bValid=true;
        for(int32 I=0;I<3;++I)
        {
            Indices[I]=Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%s_%s"),Bones[I],Suffix)));
            bValid&=Rest.IsValidIndex(Indices[I]);
        }
        for(int32 I=0;I<3;++I)
        {
            const FVector P=bValid?Rest[Indices[I]].GetLocation():FVector::ZeroVector;
            const FName Name(*FString::Printf(TEXT("OutfitFade%s%s"),Points[I],Label));
            for(const auto& Weak:Materials)if(auto* Material=Weak.Get())
                Material->SetVectorParameterValue(Name,FLinearColor(P.X,P.Y,P.Z,bValid?1.f:0.f));
        }
    }
    for(const auto& Weak:Materials)if(auto* Material=Weak.Get())
        Material->SetScalarParameterValue(TEXT("OutfitCameraFadeEnabled"),bFirstPerson?1.f:0.f);
}
}

void FFPSOutfitSecondaryMotion::Initialize(USkeletalMeshComponent* InSource,USkeletalMeshComponent* InShirt)
{
    Source=InSource;Shirt=InShirt;
    Hands[0].Bone=InSource->GetBoneIndex(TEXT("hand_l"));
    Hands[1].Bone=InSource->GetBoneIndex(TEXT("hand_r"));
    // The new mesh has no clothing assets. Keep the ordinary leader-pose
    // follower asleep; only two spring states update in the outfit manager.
    InShirt->SetComponentTickEnabled(false);
    for(int32 I=0;I<InShirt->GetNumMaterials();++I)
        if(auto* Material=InShirt->CreateAndSetMaterialInstanceDynamic(I))Materials.Add(Material);
    // Reference-space anatomy is set once, including on single-arm rigs.
    // Camera distance is evaluated by the material each view; no extra Tick,
    // bone edits or dependency on the cuff-sway enable/disable setting.
    ConfigureCameraRegion(*InShirt,Materials,InSource->bOnlyOwnerSee);
    Reset();
}

void FFPSOutfitSecondaryMotion::Push(const FVector& Left,const FVector& Right,const FVector& PreviousLeft,const FVector& PreviousRight)
{
    const FVector Values[]={Left,Right,PreviousLeft,PreviousRight};
    for(int32 I=0;I<4;++I)
    {
        if(bHaveParameters&&LastSent[I].Equals(Values[I],.00001))continue;
        const FVector& V=Values[I];
        for(auto& Weak:Materials)if(auto* Material=Weak.Get())
            Material->SetVectorParameterValue(Parameters[I],FLinearColor(V.X,V.Y,V.Z,0.f));
        LastSent[I]=V;
    }
    bHaveParameters=true;
}

void FFPSOutfitSecondaryMotion::Reset()
{
    for(auto& Hand:Hands)
    {
        Hand.Offset=Hand.Velocity=Hand.AnchorVelocity=FVector::ZeroVector;
        Hand.bInitialized=false;
    }
    Push(FVector::ZeroVector,FVector::ZeroVector,FVector::ZeroVector,FVector::ZeroVector);
}

void FFPSOutfitSecondaryMotion::Tick(float Delta)
{
    auto* Leader=Source.Get();auto* Garment=Shirt.Get();if(!Leader||!Garment)return;
    const float Strength=FMath::Clamp(CVarChainmailSway.GetValueOnGameThread(),0.f,1.f);
    const bool bVisible=Leader->IsVisible()&&!Leader->bHiddenInGame&&!Leader->bOwnerNoSee
        &&Garment->IsVisible()&&!Garment->bHiddenInGame&&Strength>0.f;
    if(!bVisible){if(bActive)Reset();bActive=false;return;}
    if(!bActive||Delta>.1f)Reset();
    bActive=true;
    if(Delta<=UE_SMALL_NUMBER||Delta>.1f)return;
    FVector Previous[]={Hands[0].Offset*Strength,Hands[1].Offset*Strength};
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta*120.f),1,12);
    const float Dt=Delta/Steps;
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Hands[Side];if(H.Bone==INDEX_NONE)continue;
        const FTransform Hand=Leader->GetBoneTransform(H.Bone);
        const FVector Anchor=Hand.GetLocation()+Hand.GetRotation().RotateVector(FVector(0,2.5,0));
        if(!H.bInitialized||FVector::DistSquared(Anchor,H.PreviousAnchor)>35.f*35.f)
        {
            H.PreviousAnchor=Anchor;H.AnchorVelocity=H.Offset=H.Velocity=FVector::ZeroVector;
            H.bInitialized=true;Previous[Side]=FVector::ZeroVector;continue;
        }
        const FVector Raw=((Anchor-H.PreviousAnchor)/Delta).GetClampedToMaxSize(1000.f);
        const FVector Filtered=FMath::Lerp(H.AnchorVelocity,Raw,1.f-FMath::Exp(-30.f*Delta));
        const FVector Force=(-.4f*(Filtered-H.AnchorVelocity)/Delta).GetClampedToMaxSize(650.f);
        H.PreviousAnchor=Anchor;H.AnchorVelocity=Filtered;
        for(int32 Step=0;Step<Steps;++Step)
        {
            H.Velocity+=(Force-Frequency*Frequency*H.Offset-2.f*Damping*Frequency*H.Velocity)*Dt;
            H.Offset+=H.Velocity*Dt;
            if(H.Offset.SizeSquared()>MaximumOffsetCm*MaximumOffsetCm)
            {
                H.Offset=H.Offset.GetClampedToMaxSize(MaximumOffsetCm);
                const FVector Direction=H.Offset.GetSafeNormal();
                H.Velocity-=Direction*FMath::Max(0.,FVector::DotProduct(H.Velocity,Direction));
            }
            if(H.Offset.SizeSquared()<1.e-10&&H.Velocity.SizeSquared()<1.e-8&&Force.SizeSquared()<1.e-8)
                H.Offset=H.Velocity=FVector::ZeroVector;
        }
    }
    Push(Hands[0].Offset*Strength,Hands[1].Offset*Strength,Previous[0],Previous[1]);
}
