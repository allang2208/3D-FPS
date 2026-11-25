#include "StableManeComponent.h"
#include "../FPSWeatherManager.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

UStableManeComponent::UStableManeComponent()
{
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);
    SetCanEverAffectNavigation(false);
    BoundsScale=1.12f;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Crop(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/AppearanceR30/SK_Hair_Crop"));
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Sweep(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/AppearanceR30/SK_Hair_Sweep"));
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Parted(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/AppearanceR30/SK_Hair_Parted"));
    Styles={Crop.Object,Sweep.Object,Parted.Object};
    if(Sweep.Succeeded())SetSkeletalMeshAsset(Sweep.Object);
}

void UStableManeComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Body=Cast<USkeletalMeshComponent>(GetAttachParent()))
    {
        SetLeaderPoseComponent(Body);
        if(!HairMaterial)HairMaterial=CreateDynamicMaterialInstance(0);
    }
}

void UStableManeComponent::SetHairStyle(uint8 Style)
{
    if(!Styles.IsValidIndex(Style)||!Styles[Style])return;
    if(GetSkeletalMeshAsset()!=Styles[Style])
    {
        SetMaterial(0,nullptr);
        SetSkeletalMeshAsset(Styles[Style]);
        if(auto* Body=Cast<USkeletalMeshComponent>(GetAttachParent()))SetLeaderPoseComponent(Body,true);
        HairMaterial=nullptr;
        bSampled=false;
    }
    if(!HairMaterial)HairMaterial=CreateDynamicMaterialInstance(0);
}

void UStableManeComponent::UpdateMotion(float Dt)
{
    auto* Body=Cast<USkeletalMeshComponent>(GetAttachParent());
    if(!HairMaterial||!Body||!Body->WasRecentlyRendered(.4f)||Dt<=SMALL_NUMBER)
    {bSampled=false;return;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(!Weather.IsValid()&&Now>=NextWeatherLookup)
    {
        NextWeatherLookup=Now+4.;
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){Weather=*It;break;}
    }
    const FVector Crest=Body->GetSocketLocation(TEXT("neck_03"));
    const FVector Delta=Crest-LastRoot;
    const bool Continuous=bSampled&&Dt<.12f&&Delta.SizeSquared()<FMath::Square(85.);
    const FVector RootVelocity=Continuous ? Delta/Dt : GetOwner()->GetVelocity();
    if(!Continuous){Velocity=FVector::ZeroVector;Offset=FVector::ZeroVector;}
    bSampled=true;LastRoot=Crest;
    const FVector Wind=Weather.IsValid()?Weather->GetWeatherWind():FVector::ZeroVector;
    const FVector Target=((Wind-RootVelocity)*AirDrag).GetClampedToMaxSize(MaximumTipTravelCm);
    const float W=2.f*PI*FMath::Clamp(FrequencyHz,.5f,10.f);
    const float Duration=FMath::Min(Dt,.0833f);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*120.f));
    const float Step=Duration/Steps;
    for(int32 I=0;I<Steps;++I)
    {
        Velocity+=((Target-Offset)*FMath::Square(W)-Velocity*(2.f*W*DampingRatio))*Step;
        Offset=(Offset+Velocity*Step).GetClampedToMaxSize(MaximumTipTravelCm);
    }
    const FVector Axis=Body->GetComponentQuat().GetAxisX();
    HairMaterial->SetVectorParameterValue(TEXT("ManeDisplacement"),FLinearColor(Offset.X,Offset.Y,Offset.Z));
    HairMaterial->SetVectorParameterValue(TEXT("ManeSideAxis"),FLinearColor(Axis.X,Axis.Y,Axis.Z));
}
