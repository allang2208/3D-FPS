#include "VillageDistantGlow.h"
#include "HillsBlacksmith.h"
#include "SmithYardLamp.h"
#include "TemperateHillsWorld.h"
#include "TemperateVillageSite.h"
#include "VillagePresentationView.h"
#include "VillageRoadLamp.h"
#include "../Building/BronzeTorch.h"
#include "../Building/ColdSteelWindow.h"
#include "../FPSWeatherManager.h"
#include "Components/ChildActorComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
int32 GDistantVillageGlow = 1;
FAutoConsoleVariableRef CVarDistantVillageGlow(
    TEXT("fps.Hills.DistantVillageGlow"),
    GDistantVillageGlow,
    TEXT("1 = enable single-batched ultra-far village night beacons & backlit valley glow (default), 0 = disable."),
    ECVF_Default);

int32 GDistantVillageWindows = 1;
FAutoConsoleVariableRef CVarDistantVillageWindows(
    TEXT("fps.Hills.DistantVillageWindows"),
    GDistantVillageWindows,
    TEXT("1 = enable warm glowing windows on repaired village buildings at distance (default), 0 = disable."),
    ECVF_Default);

struct FBeaconInstanceData
{
    FTransform Transform;
    float CustomData[5];
};

struct FWindowInstanceData
{
    FTransform Transform;
    float CustomData[6];
};

float ComputeNightFactor(float Hour)
{
    if (Hour >= 18.5f || Hour <= 4.5f)
    {
        return 1.0f;
    }
    if (Hour > 17.0f && Hour < 18.5f)
    {
        return FMath::SmoothStep(17.0f, 18.5f, Hour);
    }
    if (Hour > 4.5f && Hour < 6.0f)
    {
        return 1.0f - FMath::SmoothStep(4.5f, 6.0f, Hour);
    }
    return 0.0f;
}

uint32 DeterministicHash(const FVector& Pos)
{
    const int32 IX = FMath::RoundToInt(Pos.X * 0.1);
    const int32 IY = FMath::RoundToInt(Pos.Y * 0.1);
    const int32 IZ = FMath::RoundToInt(Pos.Z * 0.1);
    return HashCombineFast(HashCombineFast(GetTypeHash(IX), GetTypeHash(IY)), GetTypeHash(IZ));
}

float HashUnit(uint32 Seed)
{
    Seed ^= Seed >> 16;
    Seed *= 0x7feb352dU;
    Seed ^= Seed >> 15;
    Seed *= 0x846ca68bU;
    Seed ^= Seed >> 16;
    return float(Seed & 0xFFFFu) / 65535.0f;
}

int32 CountActiveVillageFixtures(UWorld* World)
{
    if (!World)
    {
        return 0;
    }
    int32 Count = 0;
    for (TActorIterator<ABronzeTorch> It(World); It; ++It)
    {
        if (!It->IsHidden())
        {
            ++Count;
        }
    }
    for (TActorIterator<AColdSteelWindow> It(World); It; ++It)
    {
        if (!It->IsHidden())
        {
            ++Count;
        }
    }
    return Count;
}
}

UVillageDistantGlowComponent::UVillageDistantGlowComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = 0.5f;
    PrimaryComponentTick.bAllowTickOnDedicatedServer = false;
}

void UVillageDistantGlowComponent::RequestAnchorRefresh()
{
    bAnchorsDirty = true;
}

void UVillageDistantGlowComponent::InitializeForSite(
    const FTemperateVillageSite& Site,
    TFunctionRef<double(double, double)> TerrainHeightFn)
{
    if (bInitialized || !Site.bPlaced || GetNetMode() == NM_DedicatedServer)
    {
        return;
    }

    AActor* Owner = GetOwner();
    if (!Owner)
    {
        return;
    }

    CachedSite = Site;
    const FVector2D CenterXY = Site.World(0.0, 300.0);
    // Low interior bounce height keeps rooftops dark against the sky and horizon haze.
    TownCenterWorld = FVector(CenterXY, TerrainHeightFn(CenterXY.X, CenterXY.Y) + 650.0);

    // Tier 2: One unshadowed distant ambient bounce light (only active far away at night).
    TownGlowLight = NewObject<UPointLightComponent>(Owner, TEXT("VillageDistantTownGlow"));
    Owner->AddInstanceComponent(TownGlowLight);
    TownGlowLight->SetupAttachment(this);
    TownGlowLight->SetWorldLocation(TownCenterWorld);
    TownGlowLight->SetMobility(EComponentMobility::Movable);
    TownGlowLight->SetCastShadows(false);
    TownGlowLight->SetIntensityUnits(ELightUnits::Lumens);
    TownGlowLight->SetInverseExposureBlend(0.6f);
    TownGlowLight->SetAttenuationRadius(6800.0f);
    TownGlowLight->SetLightColor(FLinearColor(1.0f, 0.58f, 0.22f));
    TownGlowLight->SetMaxDrawDistance(140000.0f);
    TownGlowLight->SetMaxDistanceFadeRange(20000.0f);
    TownGlowLight->SetVolumetricScatteringIntensity(0.14f);
    TownGlowLight->SetSourceRadius(250.0f);
    TownGlowLight->SetSpecularScale(0.12f);
    TownGlowLight->SetIntensity(0.0f);
    TownGlowLight->SetVisibility(false);
    TownGlowLight->RegisterComponent();

    UStaticMesh* PlaneMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
    UMaterialInterface* BeaconBaseMat = LoadObject<UMaterialInterface>(
        nullptr, TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon.M_VillageDistantBeacon"));
    UMaterialInterface* WindowBaseMat = LoadObject<UMaterialInterface>(
        nullptr, TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageWarmWindow.M_VillageWarmWindow"));

    auto ConfigureISM = [Owner, this, PlaneMesh](const TCHAR* Name, UMaterialInterface* BaseMat, int32 NumCustomFloats, float BoundsScale, TObjectPtr<UMaterialInstanceDynamic>& OutMID) -> UInstancedStaticMeshComponent*
    {
        if (!PlaneMesh || !BaseMat)
        {
            return nullptr;
        }
        OutMID = UMaterialInstanceDynamic::Create(BaseMat, Owner);
        OutMID->SetScalarParameterValue(TEXT("NightIntensity"), 0.0f);

        auto* ISM = NewObject<UInstancedStaticMeshComponent>(Owner, Name);
        Owner->AddInstanceComponent(ISM);
        ISM->SetupAttachment(this);
        ISM->SetMobility(EComponentMobility::Movable);
        ISM->SetStaticMesh(PlaneMesh);
        ISM->SetMaterial(0, OutMID);
        ISM->SetNumCustomDataFloats(NumCustomFloats);
        ISM->SetCastShadow(false);
        ISM->bAffectDynamicIndirectLighting = false;
        ISM->bAffectDistanceFieldLighting = false;
        ISM->SetVisibleInRayTracing(false);
        ISM->SetReceivesDecals(false);
        ISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ISM->SetCanEverAffectNavigation(false);
        ISM->SetCullDistances(0, 150000);
        ISM->SetBoundsScale(BoundsScale);
        ISM->SetVisibility(false);
        ISM->RegisterComponent();
        return ISM;
    };

    BeaconISM = ConfigureISM(TEXT("VillageDistantBeaconISM"), BeaconBaseMat, 5, 12.0f, BeaconMID);
    WindowISM = ConfigureISM(TEXT("VillageWarmWindowISM"), WindowBaseMat, 6, 4.0f, WindowMID);

    bInitialized = true;
    bAnchorsDirty = true;
}

void UVillageDistantGlowComponent::RebuildAnchors()
{
    UWorld* World = GetWorld();
    ATemperateHillsWorld* HillsOwner = Cast<ATemperateHillsWorld>(GetOwner());
    if (!World || !HillsOwner || !CachedSite.bPlaced)
    {
        return;
    }

    auto SampleTerrainZ = [HillsOwner](double X, double Y) -> double
    {
        return HillsOwner->Height(X, Y);
    };

    auto ComputeTerrainNormal = [&SampleTerrainZ](double X, double Y) -> FVector
    {
        const double Step = 80.0;
        const double Zx0 = SampleTerrainZ(X - Step, Y);
        const double Zx1 = SampleTerrainZ(X + Step, Y);
        const double Zy0 = SampleTerrainZ(X, Y - Step);
        const double Zy1 = SampleTerrainZ(X, Y + Step);
        const FVector TX(2.0 * Step, 0.0, Zx1 - Zx0);
        const FVector TY(0.0, 2.0 * Step, Zy1 - Zy0);
        FVector N = FVector::CrossProduct(TX, TY).GetSafeNormal();
        if (N.Z < 0.0)
        {
            N = -N;
        }
        return N.IsNearlyZero() ? FVector::UpVector : N;
    };

    TArray<FBeaconInstanceData> Beacons;
    Beacons.Reserve(96);
    TArray<FVector> LampPositions;
    LampPositions.Reserve(48);

    auto AddLampWithSpill = [&](const FVector& LampWorld, float HaloRadiusCm, float HaloStrength, float Warmth, float HaloMinFadeCm, float SpillRadiusCm, float SpillStrength)
    {
        for (const FVector& Existing : LampPositions)
        {
            if (FVector::DistSquared(Existing, LampWorld) < FMath::Square(75.0))
            {
                return;
            }
        }
        LampPositions.Add(LampWorld);

        // Mode 0: Hooded lamp halo locked tightly to actual fixture center.
        {
            FBeaconInstanceData Entry;
            Entry.Transform = FTransform(FRotator::ZeroRotator, LampWorld, FVector::OneVector);
            Entry.CustomData[0] = HaloRadiusCm;
            Entry.CustomData[1] = HaloStrength;
            Entry.CustomData[2] = Warmth;
            Entry.CustomData[3] = HaloMinFadeCm;
            Entry.CustomData[4] = 0.0f;
            Beacons.Add(Entry);
        }

        // Mode 2: Horizontal terrain-seated warm ground spill pool beneath fixture.
        if (SpillStrength > 0.0f)
        {
            const double GroundZ = SampleTerrainZ(LampWorld.X, LampWorld.Y);
            if (LampWorld.Z - GroundZ < 600.0)
            {
                const FVector Normal = ComputeTerrainNormal(LampWorld.X, LampWorld.Y);
                const FQuat Rot = FQuat::FindBetweenNormals(FVector::UpVector, Normal);
                const FVector SpillLoc(LampWorld.X, LampWorld.Y, GroundZ + 14.0);
                const float S = SpillRadiusCm / 50.0f;
                FBeaconInstanceData Spill;
                Spill.Transform = FTransform(Rot, SpillLoc, FVector(S, S, 1.0f));
                Spill.CustomData[0] = SpillRadiusCm;
                Spill.CustomData[1] = SpillStrength;
                Spill.CustomData[2] = Warmth;
                Spill.CustomData[3] = HaloMinFadeCm - 300.0f;
                Spill.CustomData[4] = 2.0f;
                Beacons.Add(Spill);
            }
        }
    };

    // 1A. Real street lamps (spawned dynamically only after wall/tavern repairs).
    for (TActorIterator<AVillageRoadLamp> It(World); It; ++It)
    {
        const AVillageRoadLamp* Lamp = *It;
        if (!IsValid(Lamp) || Lamp->IsHidden())
        {
            continue;
        }
        const auto* Light = Lamp->FindComponentByClass<ULightComponent>();
        const FVector Loc = Light ? Light->GetComponentLocation() : (Lamp->GetActorLocation() + FVector(0.0, 0.0, 246.0));
        AddLampWithSpill(Loc, 56.0f, 1.15f, 0.65f, 4800.0f, 290.0f, 0.30f);
    }

    // 1B. Repaired exterior shop wall lanterns (exclude interior AlwaysLit & cold Unlit).
    for (TActorIterator<AVillageShopChainLamp> It(World); It; ++It)
    {
        const AVillageShopChainLamp* Lamp = *It;
        if (!IsValid(Lamp) || Lamp->IsHidden())
        {
            continue;
        }
        const UChildActorComponent* Parent = Lamp->GetParentComponent();
        if (Parent && (Parent->ComponentHasTag(AVillageShopChainLamp::Unlit) || Parent->ComponentHasTag(AVillageShopChainLamp::AlwaysLit)))
        {
            continue;
        }
        const auto* Light = Lamp->FindComponentByClass<ULightComponent>();
        const FVector Loc = Light ? Light->GetComponentLocation() : Lamp->GetActorLocation();
        if (!CachedSite.Near(Loc.X, Loc.Y, 2400.0))
        {
            continue;
        }
        AddLampWithSpill(Loc, 48.0f, 0.95f, 0.60f, 4400.0f, 230.0f, 0.24f);
    }

    // 1C. Exterior bronze torches (chapel entry, gates/bridges; exclude indoor NaveTorch & pawns).
    for (TActorIterator<ABronzeTorch> It(World); It; ++It)
    {
        const ABronzeTorch* Torch = *It;
        if (!IsValid(Torch) || Torch->IsHidden() || Torch->IsA<AVillageRoadLamp>() || Torch->IsA<AVillageShopChainLamp>())
        {
            continue;
        }
        if (Cast<APawn>(Torch->GetAttachParentActor()) || Cast<APawn>(Torch->GetOwner()))
        {
            continue;
        }
        if (const UChildActorComponent* Parent = Torch->GetParentComponent())
        {
            if (Parent->GetFName().ToString().Contains(TEXT("NaveTorch")))
            {
                continue;
            }
        }
        const auto* Light = Torch->FindComponentByClass<ULightComponent>();
        const FVector Loc = Light ? Light->GetComponentLocation() : Torch->GetActorLocation();
        if (!CachedSite.Near(Loc.X, Loc.Y, 2400.0))
        {
            continue;
        }
        AddLampWithSpill(Loc, 46.0f, 1.00f, 0.45f, 4400.0f, 210.0f, 0.22f);
    }

    // 1D. Static stable yard lanterns authored in L_AbandonedVillage.
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (!IsValid(*It) || It->GetClass() != AActor::StaticClass() || It->IsHidden())
        {
            continue;
        }
        if (!It->ActorHasTag(TEXT("VillageStable.GroundDetailR4")))
        {
            continue;
        }
        TInlineComponentArray<UPointLightComponent*> YardLights(*It);
        for (const UPointLightComponent* Light : YardLights)
        {
            if (!Light || !Light->IsVisible() || Light->Intensity <= 1.0f)
            {
                continue;
            }
            const FVector Loc = Light->GetComponentLocation();
            AddLampWithSpill(Loc, 48.0f, 0.90f, 0.58f, 4400.0f, 220.0f, 0.22f);
        }
    }

    // 2. Ground-hugging wide backlit valley haze domes (no floating high-altitude spheres).
    auto AddBacklitDome = [&](double LocalX, double LocalY, double BaseOffsetCm, float RadiusCm, float Strength, float Warmth, float MinFadeCm)
    {
        const FVector2D W = CachedSite.World(LocalX, LocalY);
        FBeaconInstanceData Dome;
        Dome.Transform = FTransform(FRotator::ZeroRotator, FVector(W.X, W.Y, SampleTerrainZ(W.X, W.Y) + BaseOffsetCm), FVector::OneVector);
        Dome.CustomData[0] = RadiusCm;
        Dome.CustomData[1] = Strength;
        Dome.CustomData[2] = Warmth;
        Dome.CustomData[3] = MinFadeCm;
        Dome.CustomData[4] = 1.0f;
        Beacons.Add(Dome);
    };
    AddBacklitDome(0.0, 200.0, 220.0, 5400.0f, 0.55f, 0.42f, 7800.0f);
    AddBacklitDome(1600.0, 900.0, 260.0, 6400.0f, 0.40f, 0.36f, 10500.0f);

    if (BeaconISM)
    {
        BeaconISM->ClearInstances();
        BeaconISM->PreAllocateInstancesMemory(Beacons.Num());
        for (int32 I = 0; I < Beacons.Num(); ++I)
        {
            const int32 Idx = BeaconISM->AddInstance(Beacons[I].Transform, true);
            BeaconISM->SetCustomData(Idx, MakeArrayView(Beacons[I].CustomData, 5), I == Beacons.Num() - 1);
        }
        BeaconISM->MarkRenderStateDirty();
    }

    // 3. Physically anchored glowing windows on repaired buildings.
    TArray<FWindowInstanceData> Windows;
    Windows.Reserve(64);
    TArray<FVector> WindowCenters;
    WindowCenters.Reserve(64);

    auto AddWindowQuad = [&](const FVector& CenterWorld, const FVector& RawRight, const FVector& RawUp, float HalfW, float HalfH, float ShapeType, float Warmth, float Strength, float MinFadeCm)
    {
        for (const FVector& Existing : WindowCenters)
        {
            if (FVector::DistSquared(Existing, CenterWorld) < FMath::Square(55.0))
            {
                return;
            }
        }
        const FVector X = RawRight.GetSafeNormal();
        const FVector Y = RawUp.GetSafeNormal();
        const FVector Z = FVector::CrossProduct(X, Y).GetSafeNormal();
        if (X.IsNearlyZero() || Y.IsNearlyZero() || Z.IsNearlyZero())
        {
            return;
        }
        WindowCenters.Add(CenterWorld);

        const FMatrix Basis(X * (HalfW / 50.0f), Y * (HalfH / 50.0f), Z, CenterWorld);
        FWindowInstanceData Win;
        Win.Transform = FTransform(Basis);
        Win.CustomData[0] = ShapeType;
        Win.CustomData[1] = Warmth;
        Win.CustomData[2] = Strength;
        Win.CustomData[3] = MinFadeCm;
        Win.CustomData[4] = HalfW;
        Win.CustomData[5] = HalfH;
        Windows.Add(Win);
    };

    auto OrientOutwardOffset = [&](const FVector& BaseCenter, const FVector& NormalCandidate, const FVector& InteriorRef, float OutwardOffsetCm) -> FVector
    {
        FVector Out = NormalCandidate.GetSafeNormal();
        if (Out.IsNearlyZero())
        {
            return BaseCenter;
        }
        if (FVector::DotProduct(Out, BaseCenter - InteriorRef) < 0.0)
        {
            Out = -Out;
        }
        return BaseCenter + Out * OutwardOffsetCm;
    };

    // 3A. Old Chapel (always assembled: Gothic lancet stained glass + west Rose Oculus).
    const FVector ChapelRef = CachedSite.ChapelLot().Ground + FVector(0.0, 0.0, 220.0);
    for (UActorComponent* Comp : HillsOwner->GetComponents())
    {
        auto* ISM = Cast<UInstancedStaticMeshComponent>(Comp);
        if (!ISM || !ISM->GetStaticMesh())
        {
            continue;
        }
        const FString Name = ISM->GetName();
        const bool bLancet = Name.Contains(TEXT("OldChapel_LancetGlass"));
        const bool bOculus = Name.Contains(TEXT("OldChapel_OculusGlass"));
        if (!bLancet && !bOculus)
        {
            continue;
        }
        const FBox Box = ISM->GetStaticMesh()->GetBoundingBox();
        const FVector BoxCenter = Box.GetCenter();
        const FVector BoxExt = Box.GetExtent();
        const float ShapeType = bOculus ? 2.0f : 1.0f;
        const float Warmth = bOculus ? 0.82f : 0.78f;
        const float Strength = bOculus ? 1.55f : 1.45f;

        for (int32 I = 0; I < ISM->GetInstanceCount(); ++I)
        {
            FTransform T;
            if (!ISM->GetInstanceTransform(I, T, true))
            {
                continue;
            }
            const FVector Scale = T.GetScale3D().GetAbs();
            const FVector WorldCenter = T.TransformPosition(BoxCenter);
            const FVector WorldX = T.TransformVectorNoScale(FVector::ForwardVector);
            const FVector WorldY = T.TransformVectorNoScale(FVector::RightVector);
            const FVector WorldZ = T.TransformVectorNoScale(FVector::UpVector);
            // Thin glass normal is the axis with smallest local extent.
            const bool bThinX = BoxExt.X <= BoxExt.Y;
            const FVector RightAxis = bThinX ? WorldY : WorldX;
            const FVector NormalAxis = bThinX ? WorldX : WorldY;
            const float HalfW = FMath::Max(22.0f, float((bThinX ? BoxExt.Y : BoxExt.X) * (bThinX ? Scale.Y : Scale.X)));
            const float HalfH = FMath::Max(28.0f, float(BoxExt.Z * Scale.Z));
            const FVector PlacedCenter = OrientOutwardOffset(WorldCenter, NormalAxis, ChapelRef, 4.0f);
            AddWindowQuad(PlacedCenter, RightAxis, WorldZ, HalfW, HalfH, ShapeType, Warmth, Strength, 3400.0f);
        }
    }

    // Collect known building centers so AColdSteelWindow quads always sit on the exterior face.
    TArray<FVector> BuildingCenters;
    BuildingCenters.Add(ChapelRef);
    const FVector2D TownMidXY = CachedSite.World(0.0, 200.0);
    const FVector TownFallbackRef(TownMidXY.X, TownMidXY.Y, SampleTerrainZ(TownMidXY.X, TownMidXY.Y));
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->ActorHasTag(TEXT("VillageBakery.Site")) || It->ActorHasTag(TEXT("VillageGunshop.Site"))
            || It->ActorHasTag(TEXT("VillageTavern.Site")) || It->IsA<AHillsBlacksmith>()
            || It->GetClass()->GetFName() == FName(TEXT("VillageWarehouseActor")))
        {
            BuildingCenters.Add(It->GetActorLocation());
        }
    }
    auto NearestBuildingRef = [&](const FVector& Pos) -> FVector
    {
        FVector Best = TownFallbackRef;
        double BestDistSq = DBL_MAX;
        for (const FVector& B : BuildingCenters)
        {
            const double DSq = FVector::DistSquared2D(Pos, B);
            if (DSq < BestDistSq)
            {
                BestDistSq = DSq;
                Best = B;
            }
        }
        return (BestDistSq < FMath::Square(1800.0)) ? Best : TownFallbackRef;
    };

    // 3B. Repaired interactive casement windows (AColdSteelWindow across Bakery, Gunshop, Blacksmith, Carpenter, Herbalist).
    for (TActorIterator<AColdSteelWindow> It(World); It; ++It)
    {
        const AColdSteelWindow* Win = *It;
        if (!IsValid(Win) || Win->IsHidden())
        {
            continue;
        }
        const FVector Loc = Win->GetActorLocation();
        if (!CachedSite.Near(Loc.X, Loc.Y, 2400.0))
        {
            continue;
        }
        const UStaticMeshComponent* FrameComp = nullptr;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Win);
        for (const UStaticMeshComponent* MeshComp : Meshes)
        {
            if (MeshComp->GetName() == TEXT("WindowFrame"))
            {
                FrameComp = MeshComp;
                break;
            }
        }
        if (!FrameComp || !FrameComp->GetStaticMesh())
        {
            continue;
        }
        const FBox Box = FrameComp->GetStaticMesh()->GetBoundingBox();
        const FVector Scale = FrameComp->GetComponentScale().GetAbs();
        const FVector BaseCenter = FrameComp->GetComponentTransform().TransformPosition(Box.GetCenter());
        const FVector RightDir = FrameComp->GetRightVector();
        const FVector UpDir = FrameComp->GetUpVector();
        const FVector ForwardDir = FrameComp->GetForwardVector();
        const float HalfW = FMath::Max(22.0f, float((Box.GetExtent().Y - 6.0) * Scale.Y));
        const float HalfH = FMath::Max(24.0f, float((Box.GetExtent().Z - 6.0) * Scale.Z));

        const uint32 H = DeterministicHash(BaseCenter);
        const float U = HashUnit(H);
        const float Warmth = 0.48f + 0.28f * U;
        const float Strength = 1.10f + 0.35f * HashUnit(H ^ 0x9E3779B9u);
        // Seat at +5.5 cm outside the 2 cm closed leaf panel, recessed inside the 10 cm outer stone frame.
        const FVector PlacedCenter = OrientOutwardOffset(BaseCenter, ForwardDir, NearestBuildingRef(BaseCenter), 5.5f);
        AddWindowQuad(PlacedCenter, RightDir, UpDir, HalfW, HalfH, 0.0f, Warmth, Strength, 3200.0f);
    }

    // 3C. 3-Storey Tavern windows when repaired (exact inn_geometry.py 2F/3F bays + 1F taproom scans).
    AActor* Tavern = HillsOwner->GetStreamedTavern();
    if (HillsOwner->IsTavernRepaired() && IsValid(Tavern))
    {
        const FTransform TavernT = Tavern->GetActorTransform();
        const FVector TavernCenter = TavernT.TransformPosition(FVector(-40.0, 200.0, 500.0));
        auto AddTavernBay = [&](double LX, double LY, double LZ, const FVector& LocalRight, float MinStren, float MaxStren)
        {
            const FVector CenterW = TavernT.TransformPosition(FVector(LX, LY, LZ));
            const FVector RightW = TavernT.TransformVectorNoScale(LocalRight);
            const FVector UpW = TavernT.TransformVectorNoScale(FVector::UpVector);
            const uint32 H = DeterministicHash(CenterW);
            const bool bLitRoom = HashUnit(H) > 0.22f;
            const float Strength = bLitRoom ? FMath::Lerp(MinStren, MaxStren, HashUnit(H ^ 0xA511E9B3u)) : 0.28f;
            const float Warmth = 0.50f + 0.24f * HashUnit(H ^ 0x517CC1B7u);
            AddWindowQuad(CenterW, RightW, UpW, 50.0f, 59.0f, 0.0f, Warmth, Strength, 3200.0f);
        };

        const double ZFloors[2] = { 340.0 + 155.0, 642.0 + 155.0 };
        const double FrontXs[2][4] = { {-520.0, -138.0, 320.0, 525.0}, {-512.0, -175.0, 214.0, 494.0} };
        const double BackXs[2][4] = { {-466.0, -115.0, 300.0, 504.0}, {-510.0, -162.0, 182.0, 433.0} };
        const double WestYs[3] = { -200.0, 185.0, 633.0 };
        const double EastYs[3] = { -240.0, 244.0, 633.0 };

        for (int32 F = 0; F < 2; ++F)
        {
            const float MinS = (F == 0) ? 0.95f : 0.80f;
            const float MaxS = (F == 0) ? 1.35f : 1.15f;
            for (double X : FrontXs[F]) AddTavernBay(X, -424.0, ZFloors[F], FVector::ForwardVector, MinS, MaxS);
            for (double X : BackXs[F]) AddTavernBay(X, 826.0, ZFloors[F], FVector::ForwardVector, MinS, MaxS);
            for (double Y : WestYs) AddTavernBay(-722.0, Y, ZFloors[F], FVector::RightVector, MinS, MaxS);
            for (double Y : EastYs) AddTavernBay(642.0, Y, ZFloors[F], FVector::RightVector, MinS, MaxS);
        }

        TInlineComponentArray<UStaticMeshComponent*> TavernMeshes(Tavern);
        for (const UStaticMeshComponent* Comp : TavernMeshes)
        {
            if (!Comp->IsVisible() || !Comp->GetStaticMesh())
            {
                continue;
            }
            const FString MeshName = Comp->GetStaticMesh()->GetName();
            if (!MeshName.StartsWith(TEXT("SM_InnWindowFrame")) && !MeshName.StartsWith(TEXT("SM_Window_")))
            {
                continue;
            }
            const FBox Box = Comp->GetStaticMesh()->GetBoundingBox();
            const FVector Ext = Box.GetExtent();
            const bool bThinX = Ext.X <= Ext.Y;
            auto AddFromTransform = [&](const FTransform& T)
            {
                const FVector Scale = T.GetScale3D().GetAbs();
                const FVector CenterW = T.TransformPosition(Box.GetCenter());
                const FVector WX = T.TransformVectorNoScale(FVector::ForwardVector);
                const FVector WY = T.TransformVectorNoScale(FVector::RightVector);
                const FVector WZ = T.TransformVectorNoScale(FVector::UpVector);
                const FVector RightW = bThinX ? WY : WX;
                const FVector NormW = bThinX ? WX : WY;
                const float HalfW = FMath::Max(22.0f, float((bThinX ? Ext.Y : Ext.X) * (bThinX ? Scale.Y : Scale.X)));
                const float HalfH = FMath::Max(24.0f, float(Ext.Z * Scale.Z));
                const FVector Placed = OrientOutwardOffset(CenterW, NormW, TavernCenter, 3.0f);
                AddWindowQuad(Placed, RightW, WZ, HalfW, HalfH, 0.0f, 0.66f, 1.45f, 3200.0f);
            };
            if (const auto* ISM = Cast<UInstancedStaticMeshComponent>(Comp))
            {
                for (int32 I = 0; I < ISM->GetInstanceCount(); ++I)
                {
                    FTransform T;
                    if (ISM->GetInstanceTransform(I, T, true)) AddFromTransform(T);
                }
            }
            else
            {
                AddFromTransform(Comp->GetComponentTransform());
            }
        }
    }

    // 3D. Warehouse & Blacksmith loft windows (SM_SmithLoft_WindowMount_R7b).
    auto CollectMountWindows = [&](const AActor* Building)
    {
        if (!IsValid(Building) || Building->IsHidden())
        {
            return;
        }
        const FVector BuildingCenter = Building->GetActorLocation() + FVector(0.0, 0.0, 300.0);
        TInlineComponentArray<UStaticMeshComponent*> Parts(Building);
        for (const UStaticMeshComponent* Comp : Parts)
        {
            if (!Comp->IsVisible() || !Comp->GetStaticMesh())
            {
                continue;
            }
            if (!Comp->GetStaticMesh()->GetName().Contains(TEXT("SM_SmithLoft_WindowMount")))
            {
                continue;
            }
            const FBox Box = Comp->GetStaticMesh()->GetBoundingBox();
            const FVector Ext = Box.GetExtent();
            const bool bThinX = Ext.X <= Ext.Y;
            const FTransform& T = Comp->GetComponentTransform();
            const FVector Scale = T.GetScale3D().GetAbs();
            const FVector CenterW = T.TransformPosition(Box.GetCenter());
            const FVector WX = T.TransformVectorNoScale(FVector::ForwardVector);
            const FVector WY = T.TransformVectorNoScale(FVector::RightVector);
            const FVector WZ = T.TransformVectorNoScale(FVector::UpVector);
            const FVector RightW = bThinX ? WY : WX;
            const FVector NormW = bThinX ? WX : WY;
            const float HalfW = FMath::Max(24.0f, float((bThinX ? Ext.Y : Ext.X) * (bThinX ? Scale.Y : Scale.X) - 6.0));
            const float HalfH = FMath::Max(26.0f, float(Ext.Z * Scale.Z - 6.0));
            const FVector Placed = OrientOutwardOffset(CenterW, NormW, BuildingCenter, 5.0f);
            AddWindowQuad(Placed, RightW, WZ, HalfW, HalfH, 0.0f, 0.56f, 1.20f, 3200.0f);
        }
    };
    if (HillsOwner->IsVillageWallRepaired())
    {
        for (TActorIterator<AActor> It(World); It; ++It) if (It->GetClass()->GetFName() == FName(TEXT("VillageWarehouseActor"))) CollectMountWindows(*It);
    }
    if (HillsOwner->IsVillageBlacksmithRepaired())
    {
        for (TActorIterator<AHillsBlacksmith> It(World); It; ++It) CollectMountWindows(*It);
    }

    if (WindowISM)
    {
        WindowISM->ClearInstances();
        WindowISM->PreAllocateInstancesMemory(Windows.Num());
        for (int32 I = 0; I < Windows.Num(); ++I)
        {
            const int32 Idx = WindowISM->AddInstance(Windows[I].Transform, true);
            WindowISM->SetCustomData(Idx, MakeArrayView(Windows[I].CustomData, 6), I == Windows.Num() - 1);
        }
        WindowISM->MarkRenderStateDirty();
    }

    LastSyncedRevision = HillsOwner->GetMapSurfaceRevision();
    LastSyncedFixtureCount = CountActiveVillageFixtures(World);
    bAnchorsDirty = false;
    NextFixtureCheckTime = World->GetTimeSeconds() + 3.0;

    UE_LOG(LogTemp, Display, TEXT("HILLS_DISTANT_GLOW rebuilt beacons=%d windows=%d"), Beacons.Num(), Windows.Num());
}

void UVillageDistantGlowComponent::TickComponent(
    float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!bInitialized || GetNetMode() == NM_DedicatedServer)
    {
        return;
    }

    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    if (!Weather.IsValid())
    {
        for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
        {
            Weather = *It;
            break;
        }
    }

    const float Hour = Weather.IsValid() ? FMath::Frac(Weather->NormalizedDayTime) * 24.0f : 12.0f;
    const float NightFactor = (GDistantVillageGlow != 0) ? ComputeNightFactor(Hour) : 0.0f;

    if (NightFactor <= 0.002f)
    {
        if (BeaconISM && BeaconISM->IsVisible())
        {
            BeaconISM->SetVisibility(false);
        }
        if (WindowISM && WindowISM->IsVisible())
        {
            WindowISM->SetVisibility(false);
        }
        if (TownGlowLight && TownGlowLight->IsVisible())
        {
            TownGlowLight->SetVisibility(false);
        }
        LastNightIntensity = 0.0f;
        LastBounceIntensity = 0.0f;
        return;
    }

    const auto* HillsOwner = Cast<ATemperateHillsWorld>(GetOwner());
    const double Now = World->GetTimeSeconds();
    if (HillsOwner && (bAnchorsDirty || HillsOwner->GetMapSurfaceRevision() != LastSyncedRevision))
    {
        RebuildAnchors();
    }
    else if (Now >= NextFixtureCheckTime)
    {
        NextFixtureCheckTime = Now + 3.0;
        const int32 CurrentFixtures = CountActiveVillageFixtures(World);
        if (CurrentFixtures != LastSyncedFixtureCount)
        {
            RebuildAnchors();
        }
    }

    if (BeaconISM)
    {
        if (!BeaconISM->IsVisible())
        {
            BeaconISM->SetVisibility(true);
        }
        if (BeaconMID && FMath::Abs(NightFactor - LastNightIntensity) > 0.01f)
        {
            BeaconMID->SetScalarParameterValue(TEXT("NightIntensity"), NightFactor);
        }
    }

    const bool bShowWindows = (GDistantVillageWindows != 0) && WindowISM && WindowISM->GetInstanceCount() > 0;
    if (WindowISM)
    {
        if (WindowISM->IsVisible() != bShowWindows)
        {
            WindowISM->SetVisibility(bShowWindows);
        }
        if (bShowWindows && WindowMID && FMath::Abs(NightFactor - LastNightIntensity) > 0.01f)
        {
            WindowMID->SetScalarParameterValue(TEXT("NightIntensity"), NightFactor);
        }
    }

    if (FMath::Abs(NightFactor - LastNightIntensity) > 0.01f)
    {
        LastNightIntensity = NightFactor;
    }

    if (TownGlowLight)
    {
        bool bHasView = false;
        const double Dist = VillagePresentationView::Distance(*World, TownCenterWorld, 0.0, &bHasView);
        const float FarBounceFactor = bHasView ? float(FMath::SmoothStep(6500.0, 12000.0, Dist)) : 0.0f;
        const float BounceAlpha = NightFactor * FarBounceFactor;
        if (BounceAlpha <= 0.005f)
        {
            if (TownGlowLight->IsVisible())
            {
                TownGlowLight->SetVisibility(false);
            }
            LastBounceIntensity = 0.0f;
        }
        else
        {
            if (!TownGlowLight->IsVisible())
            {
                TownGlowLight->SetVisibility(true);
            }
            const float TargetLumens = 14000.0f * BounceAlpha;
            if (FMath::Abs(TargetLumens - LastBounceIntensity) > 50.0f)
            {
                TownGlowLight->SetIntensity(TargetLumens);
                LastBounceIntensity = TargetLumens;
            }
        }
    }
}
