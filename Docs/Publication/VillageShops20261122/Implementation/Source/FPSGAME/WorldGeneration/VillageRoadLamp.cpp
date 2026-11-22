#include "VillageRoadLamp.h"
#include "VillageShopTorches.h"
#include "Components/SpotLightComponent.h"
#include "Components/ChildActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
const FName FixedSupport(TEXT("VillageRoadLamp.FixedSupport"));
}

AVillageRoadLamp::AVillageRoadLamp(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<USpotLightComponent>(TEXT("TorchLight")))
{
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Oak(TEXT("/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_01A.SM_HW_Plank_01A"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Lamp(TEXT("/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A.SM_Props_Lantern_02A"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Rod(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Iron(TEXT("/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron.MI_DarkForgedIron"));

    auto AddPart = [this](FName Name, UStaticMesh* Mesh)
    {
        auto* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Part->ComponentTags.Add(FixedSupport);
        Part->SetupAttachment(SceneRoot);
        Part->SetMobility(EComponentMobility::Movable);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
        Part->SetReceivesDecals(false);
        Part->SetStaticMesh(Mesh);
        Part->SetCullDistance(8500.f);
        return Part;
    };
    // Fit each hewn member along its original longitudinal grain, accounting for the irregular pivot.
    auto Timber = [&](FName Name, FVector Start, FVector End, double Width, double Depth)
    {
        auto* Part = AddPart(Name,Oak.Object);
        if (!Oak.Object) return;
        const FBox Bounds = Oak.Object->GetBoundingBox();
        const FVector Size = Bounds.GetSize();
        const FVector Scale((End-Start).Size()/Size.X,Width/Size.Y,Depth/Size.Z);
        const FQuat Rotation = (End-Start).Rotation().Quaternion();
        Part->SetRelativeTransform(FTransform(Rotation,(Start+End)*.5-Rotation.RotateVector(Bounds.GetCenter()*Scale),Scale));
    };
    Timber(TEXT("HewnUpright"),{0,0,-8},{0,0,303},18.,19.);
    Timber(TEXT("LanternArm"),{-14,0,286},{94,0,286},14.,15.);
    Timber(TEXT("ArmBrace"),{1,0,224},{61,0,285},10.,12.);

    // The bail forks from a single fixing under the cantilever onto either side of the iron cap.
    auto Bail = [&](FName Name, double Side)
    {
        const FVector Top(78,0,283), Bottom(78,Side*6.5,267);
        auto* Part = AddPart(Name,Rod.Object);
        Part->SetRelativeTransform(FTransform(FQuat::FindBetweenNormals(FVector::UpVector,(Top-Bottom).GetSafeNormal()),
            (Top+Bottom)*.5,FVector(.016,.016,(Top-Bottom).Size()/100.)));
        if (Iron.Object) Part->SetMaterial(0,Iron.Object);
    };
    Bail(TEXT("BailLeft"),-1.);
    Bail(TEXT("BailRight"),1.);

    BodyMesh = Lamp.Object;
    BodyMaterial = nullptr;
    TorchBody->SetStaticMesh(BodyMesh);
    TorchBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TorchBody->SetGenerateOverlapEvents(false);
    TorchBody->SetReceivesDecals(false);
    // The globe encloses its light. Preserve shadows from the post and nearby buildings.
    TorchBody->SetCastShadow(false);
    TorchBody->SetCullDistance(8500.f);
    constexpr double Height = 44.;
    const FVector Cap(78,0,271);
    if (Lamp.Object)
    {
        const FBox Bounds = Lamp.Object->GetBoundingBox();
        const double Scale = Height/Bounds.GetSize().Z;
        const FVector PivotToCap(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Max.Z);
        TorchBody->SetRelativeTransform(FTransform(FQuat::Identity,Cap-PivotToCap*Scale,FVector(Scale)));
    }
    // The lantern mesh carries a masked wick. Its own flame fits inside the glass.
    bEnableFlame = false;
    FlameSystem = nullptr;
    FlameOffset = Cap-FVector(0,0,Height*.56);
    LightOffset = FlameOffset;
    LightLumens = 580.f;
    LightRadiusCm = 1100.f;
    LightColor = FLinearColor::White;
    FlickerAmplitude = .018f;
    bLightCastsShadows = true;
    // The globe is 2.46 m above grade. Feather the pool along the pavement
    // and tip it slightly inwards under the projecting arm.
    auto* Pool = CastChecked<USpotLightComponent>(TorchLight);
    Pool->SetRelativeRotation(FRotator(-82.f,0.f,0.f));
    Pool->SetOuterConeAngle(77.f);
    Pool->SetInnerConeAngle(54.f);
    Pool->SetUseTemperature(true);
    Pool->SetTemperature(2850.f);
    Pool->SetMaxDrawDistance(5000.f);
    Pool->SetMaxDistanceFadeRange(1000.f);
    PrimaryActorTick.TickInterval = .1f;
    EnableExteriorClockSleep();
}

void AVillageRoadLamp::PreRegisterAllComponents()
{
    // A streamed street is placed before these lamps spawn. Only its rigid hardware
    // follows the mount's mobility; the bulb still changes intensity throughout the night.
    if (const auto* Mount = GetParentComponent())
    {
        const auto Mobility = Mount->Mobility.GetValue();
        SceneRoot->SetMobility(Mobility);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
        for (auto* Mesh : Meshes)
            if (Mesh->ComponentHasTag(FixedSupport)) Mesh->SetMobility(Mobility);
    }
    Super::PreRegisterAllComponents();
}

void AVillageRoadLamp::BeginPlay()
{
    Super::BeginPlay();
    SetSceneSpecularScale(VillageShopTorches::FixtureSpecular);
    Wick = TorchBody->CreateDynamicMaterialInstance(0);
    UpdateWick();
}

void AVillageRoadLamp::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateWick();
}

void AVillageRoadLamp::UpdateWick()
{
    const float Ignition = GetIgnitionAmount();
    if (Wick && Ignition!=LastIgnition)
    {
        // The depot lantern defaults to 20,000 emissive. The village indoor wick uses 15.
        Wick->SetScalarParameterValue(TEXT("TS00_Emissive_Multiplier"),5.f*Ignition);
        LastIgnition = Ignition;
    }
}
