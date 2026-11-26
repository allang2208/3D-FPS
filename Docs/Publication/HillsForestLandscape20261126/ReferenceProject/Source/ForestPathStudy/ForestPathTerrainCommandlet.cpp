#include "ForestPathTerrainCommandlet.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SplineComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "Landscape.h"
#include "LandscapeLayerInfoObject.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "LandscapeEditorModule.h"
#include "LandscapeFileFormatInterface.h"
#include "LandscapeImportHelper.h"
#include "Modules/ModuleManager.h"

// The artist draws the path by hand. Both the editable guide and the paint mask
// use this same reconstructed route, with the 28:55 mannequin as a survey point.
static USplineComponent* PlaceRoadGuide(UWorld* World, bool bCameraRoute)
{
    UClass* RoadClass = LoadClass<AActor>(nullptr,
        TEXT("/Game/ForestPathStudy/PCG/BP_ForestPathSpline.BP_ForestPathSpline_C"));
    if (!RoadClass) return nullptr;
    AActor* Road = World->SpawnActor<AActor>(RoadClass, FVector(-10610.,23580.,-600.), FRotator::ZeroRotator);
    if (!Road) return nullptr;
    Road->SetActorLabel(TEXT("Forest path - reconstructed centreline"));
    USplineComponent* Spline = Road->FindComponentByClass<USplineComponent>();
    if (!Spline) return nullptr;
    TArray<FVector> Points{
        {-10460.,-6080.,0.}, {-7180.,-4510.,0.}, {-4200.,-1780.,0.},
        {-1710.,-650.,0.}, {0.,0.,0.}, {1700.,405.,0.}
    };
    if (bCameraRoute)
    {
        // The 38:12 camera looks south from (-10502.6, 23732.5). At 81:02
        // it has advanced to (-10152.1, 21975.6). Match this photographed stretch first.
        Points = {{-165.,1550.,0.},{108.,150.,0.},{237.,-630.,0.},{458.,-1604.,0.},
            {1060.,-2620.,0.},{1480.,-3660.,0.},{2890.,-4770.,0.},{3590.,-6720.,0.}};
    }
    Spline->SetSplinePoints(Points, ESplineCoordinateSpace::Local, true);
    Spline->bSplineHasBeenEdited = true;
    return Spline;
}

static bool PaintAndSculptRoad(USplineComponent* Road, TArray<uint16>& Heights,
    TArray<FLandscapeImportLayerInfo>& Paint)
{
    for (const TCHAR* Layer : {TEXT("AutoMaterial"), TEXT("C")})
    {
        const FString Asset = FString::Printf(TEXT("/Game/Example/Maps/NaniteExample_sharedassets/%s_LayerInfo.%s_LayerInfo"), Layer, Layer);
        ULandscapeLayerInfoObject* Info = LoadObject<ULandscapeLayerInfoObject>(nullptr, *Asset);
        if (!Info) return false;
        FLandscapeImportLayerInfo& Entry = Paint.Emplace_GetRef(Info->GetLayerName());
        Entry.LayerInfo = Info;
        Entry.LayerData.SetNumUninitialized(505 * 505);
    }
    // Distances are measured in XY so path paint follows the projected spline.
    TArray<FVector2D> Route;
    const float Length = Road->GetSplineLength();
    for (int32 I = 0; I <= FMath::CeilToInt(Length / 50.f); ++I)
        Route.Emplace(Road->GetLocationAtDistanceAlongSpline(FMath::Min(Length, I * 50.f), ESplineCoordinateSpace::World));
    FBox2D Bounds(ForceInit);
    for (const auto& P : Route) Bounds += P;
    Bounds = Bounds.ExpandBy(350.);
    for (int32 Y = 0; Y < 505; ++Y)
    {
        for (int32 X = 0; X < 505; ++X)
        {
            const FVector2D P(-25200. + 100. * X, -25200. + 100. * Y);
            double Distance = 10000.;
            if (Bounds.IsInside(P))
            {
                for (int32 I = 1; I < Route.Num(); ++I)
                {
                    const FVector2D Delta = Route[I] - Route[I - 1];
                    const double T = FMath::Clamp(FVector2D::DotProduct(P - Route[I - 1], Delta) / FMath::Max(1., Delta.SizeSquared()), 0., 1.);
                    Distance = FMath::Min(Distance, (P - Route[I - 1] - T * Delta).Size());
                }
            }
            const int32 Index = Y * 505 + X;
            const double Verge = 170. + 26. * FMath::PerlinNoise2D(P / 430.);
            const double Mask = 1. - FMath::SmoothStep(Verge - 65., Verge + 70., Distance);
            Paint[1].LayerData[Index] = FMath::RoundToInt(255. * Mask);
            Paint[0].LayerData[Index] = 255 - Paint[1].LayerData[Index];
            // The video shows a shallow, smooth tread. Its depth is not shown numerically.
            const double Depth = 16. * (1. - FMath::SmoothStep(0., Verge + 65., Distance));
            Heights[Index] = static_cast<uint16>(FMath::Max(0, Heights[Index] - FMath::RoundToInt(Depth * 128. / 10.)));
        }
    }
    return true;
}

int32 UForestPathTerrainCommandlet::Main(const FString& Params)
{
    FString Heightmap;
    if (!FParse::Value(*Params, TEXT("Heightmap="), Heightmap))
    {
        UE_LOG(LogTemp, Error, TEXT("Supply the author's PNG using -Heightmap=<filename>."));
        return 1;
    }
    auto& Module = FModuleManager::LoadModuleChecked<ILandscapeEditorModule>("LandscapeEditor");
    const ILandscapeHeightmapFileFormat* Reader = Module.GetHeightmapFormatByExtension(TEXT(".png"));
    if (!Reader) return 1;
    const auto Original = Reader->Import(*Heightmap, NAME_None, {1009, 1009});
    if (Original.ResultCode == ELandscapeImportResult::Error || Original.Data.Num() != 1009 * 1009)
    {
        UE_LOG(LogTemp, Error, TEXT("Heightmap import failed: %s"), *Original.ErrorMessage.ToString());
        return 1;
    }

    // Same centering operation as New Landscape / Import from File.
    TMap<FGuid, TArray<uint16>> Heights;
    FLandscapeImportHelper::TransformHeightmapImportData(Original.Data, Heights.Add(FGuid()),
        {1009, 1009}, {505, 505}, ELandscapeImportTransformType::ExpandCentered);
    TMap<FGuid, TArray<FLandscapeImportLayerInfo>> Layers;
    Layers.Add(FGuid());
    UWorld* World = UEditorLoadingAndSavingUtils::NewBlankMap(false);
    if (!World) return 1;
    ALandscape* Land = World->SpawnActor<ALandscape>(FVector(-25200., -25200., 100.), FRotator::ZeroRotator);
    if (!Land) return 1;
    Land->SetActorScale3D(FVector(100., 100., 10.));
    const bool bPainted = FParse::Param(*Params, TEXT("Painted"));
    if (bPainted)
    {
        Land->LandscapeMaterial = LoadObject<UMaterialInterface>(nullptr,
            TEXT("/Game/ForestPathStudy/Materials/MI_ForestPathLandscape.MI_ForestPathLandscape"));
        USplineComponent* Road = PlaceRoadGuide(World, FParse::Param(*Params, TEXT("CameraRoute")));
        if (!Land->LandscapeMaterial || !Road || !PaintAndSculptRoad(Road, Heights[FGuid()], Layers[FGuid()]))
        {
            UE_LOG(LogTemp, Error, TEXT("Landscape material, spline class or paint layers unavailable."));
            return 1;
        }
    }
    Land->Import(FGuid::NewGuid(), 0, 0, 504, 504, 1, 63, Heights, *Heightmap, Layers,
        ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
    Land->SetActorLabel(TEXT("Landscape"));
    for (const FLandscapeImportLayerInfo& Entry : Layers[FGuid()])
        Land->AddTargetLayer(Entry.LayerName, FLandscapeTargetLayerSettings(Entry.LayerInfo));
    // Initial environment rig only. The final lighting is adjusted by hand in the tutorial.
    ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0.,0.,500.), FRotator(-45.,-35.,0.));
    Sun->GetComponent()->SetAtmosphereSunLight(true);
    World->SpawnActor<ASkyAtmosphere>();
    World->SpawnActor<ASkyLight>();
    World->SpawnActor<AVolumetricCloud>();
    AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>();
    Fog->GetComponent()->bEnableVolumetricFog = true;
    const FString PackageName = FParse::Param(*Params, TEXT("CameraRoute"))
        ? TEXT("/Game/ForestPathStudy/Maps/L_ForestPathCameraRoute")
        : (bPainted ? TEXT("/Game/ForestPathStudy/Maps/L_ForestPathStudy") : TEXT("/Game/ForestPathStudy/Maps/L_ForestPathTerrain"));
    if (Land->LandscapeComponents.Num() != 64 || !UEditorLoadingAndSavingUtils::SaveMap(World, PackageName))
    {
        UE_LOG(LogTemp, Error, TEXT("Could not save the 8 by 8 component Landscape."));
        return 1;
    }
    UE_LOG(LogTemp, Display, TEXT("Saved %s from %s with %d components."), *PackageName, *Heightmap, Land->LandscapeComponents.Num());
    return 0;
}
