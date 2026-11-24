#include "SmithYardLamp.h"
#include "VillageInteriorLighting.h"
#include "../Weapons/Staff/StaffIlluminationProfile.h"
#include "Components/ChildActorComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

const FName AVillageShopChainLamp::AlwaysLit(TEXT("VillageShop.ChainLamp.Lit"));
const FName AVillageShopChainLamp::Unlit(TEXT("VillageShop.ChainLamp.Cold"));

AVillageShopChainLamp::AVillageShopChainLamp()
{
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Lantern(TEXT("/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Chain(TEXT("/Game/UndergroundTunnel/Meshes/Props/SM_ChainLink01a"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Bar(TEXT("/Engine/BasicShapes/Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> WickMaterial(TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/MI_StaffLampWick"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Iron(TEXT("/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron"));

    auto MakeIronwork=[&](FName Name,UStaticMesh* Mesh)
    {
        auto* Part=CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
        Part->SetupAttachment(SceneRoot);
        Part->SetStaticMesh(Mesh);
        Part->SetMaterial(0,Iron.Object);
        Part->SetCollisionProfileName(TEXT("NoCollision"));
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
        Part->SetReceivesDecals(false);
        Part->SetCastShadow(false);
        Part->SetCullDistances(0,2600);
        return Part;
    };
    auto* Bracket=MakeIronwork(TEXT("RivetedBracket"),Bar.Object);
    auto Rod=[&](FVector A,FVector B,double Diameter)
    {
        const FVector Axis=B-A;
        Bracket->AddInstance(FTransform(FQuat::FindBetweenNormals(FVector::UpVector,Axis.GetSafeNormal()),
            (A+B)*.5,FVector(Diameter,Diameter,Axis.Size())*.01));
    };
    Rod({-2,0,0},{3,0,0},12.);
    Rod({2,0,-4},{4,0,-4},1.7);
    Rod({2,0,4},{4,0,4},1.7);
    Rod({0,0,0},{41,0,0},3.);
    Rod({0,0,-16},{32,0,0},2.4);
    auto* Links=MakeIronwork(TEXT("HangingChain"),Chain.Object);
    if (Chain.Object)
    {
        const FBox Box=Chain.Object->GetBoundingBox();
        const double Scale=13./FMath::Max(1.,Box.GetSize().X);
        const FQuat Plumb=FRotator(90,0,0).Quaternion();
        for (int32 I=0;I<3;++I)
        {
            const FVector Mid(39,0,-6.-I*12.);
            const FQuat Hang=FQuat(FVector::UpVector,(I%2)*HALF_PI)*Plumb;
            Links->AddInstance(FTransform(Hang,Mid-Hang.RotateVector(Box.GetCenter()*Scale),FVector(Scale)));
        }
    }

    BodyMesh=Lantern.Object;
    BodyMaterial=WickMaterial.Object;
    TorchBody->SetStaticMesh(BodyMesh);
    TorchBody->SetMaterial(0,BodyMaterial);
    TorchBody->SetCollisionProfileName(TEXT("NoCollision"));
    TorchBody->SetGenerateOverlapEvents(false);
    TorchBody->SetReceivesDecals(false);
    TorchBody->SetCastShadow(false);
    TorchBody->SetCullDistance(2600.f);
    if (BodyMesh)
    {
        const FBox Box=BodyMesh->GetBoundingBox();
        const double Scale=32./FMath::Max(1.,Box.GetSize().Z);
        const FVector Top(Box.GetCenter().X,Box.GetCenter().Y,Box.Max.Z);
        TorchBody->SetRelativeTransform(FTransform(FQuat::Identity,FVector(39,0,-36)-Top*Scale,FVector(Scale)));
    }
    FlameSystem=nullptr;
    bEnableFlame=false;
    LightOffset=FVector(39,0,-68.+.46*32.);
    LightLumens=UVillageInteriorLighting::FullLumens();
    LightColor=UVillageInteriorLighting::GlowTint();
    LightRadiusCm=UStaffIlluminationProfile::RadiusCm;
    bLightCastsShadows=true;
    FlickerAmplitude=0.f;
    PrimaryActorTick.TickInterval=.1f;
    TorchLight->SetMaxDrawDistance(2400.f);
    TorchLight->SetMaxDistanceFadeRange(450.f);
}

void AVillageShopChainLamp::BeginPlay()
{
    const UChildActorComponent* Mount=GetParentComponent();
    const bool FixedOn=Mount && Mount->ComponentHasTag(AlwaysLit);
    const bool FixedOff=Mount && Mount->ComponentHasTag(Unlit);
    if (FixedOn || FixedOff) SetLit(FixedOn);
    else EnableExteriorClockSleep();
    Super::BeginPlay();
    UVillageInteriorLighting::Configure(TorchLight,GetIgnitionAmount());
    Wick=TorchBody->CreateDynamicMaterialInstance(0);
    UpdateWick();
    if (FixedOn || FixedOff) SetActorTickEnabled(false);
}

void AVillageShopChainLamp::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateWick();
}

void AVillageShopChainLamp::UpdateWick()
{
    const float Level=GetIgnitionAmount();
    if (Wick && Level!=LastIgnition)
    {
        Wick->SetScalarParameterValue(TEXT("StaffLightAmount"),UVillageInteriorLighting::GetEmissionStrength()*Level);
        LastIgnition=Level;
    }
}
