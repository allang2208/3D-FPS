#include "BakeTemperateHillsLayoutCommandlet.h"
#include "TemperateHillsFixedLayout.h"
#include "TemperateHillsMap.h"
#include "HillsFixedTerrainCells.h"
#include "TemperateHillsWorld.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "UObject/Package.h"

#if WITH_EDITOR
bool ATemperateHillsWorld::BakeFixedLayout()
{
    if (!Assets || Assets->RiverMaterial.IsNull()) return false;
    Seed = TemperateHillsMap::Seed;
    GeneratorVersion = TemperateHillsMap::GeneratorVersion;
    SizeMeters = FMath::Clamp(FMath::RoundToFloat(SizeMeters / 128.f) * 128.f, 512.f, 1024.f);
    bStartLocationCached = false;
    const double Half = SizeMeters * 50.;
    NetEcology.Profile = TemperateEcology::Get();
    const FVector2D Anchor(GetGenerationAnchor());
    const auto Original = TemperateRiver::Generate(Seed, Half, Anchor, Assets->RiverBankReliefCm,
        GeneratorVersion, TemperateEcology::Get());
    RiverPlan = Original;
    const auto SurveyWater = TemperateForestWater::Generate(Seed, Half, Original, {}, GeneratorVersion);
    PlanAbandonedVillage(SurveyWater);
    if (!VillageSite.bHilltop) return false;
    auto Updated = MakeShared<TemperateRiver::FPlan, ESPMode::ThreadSafe>(*Original);
    Updated->BuildVillageRainforest(Seed, Half, VillageSite, Anchor);
    Updated->BuildRiverLake(Seed, Half, VillageSite, Anchor, Original);
    if (!Updated->bRiverLake || !Updated->WhiteCliffs.Valid) return false;
    const auto Water = TemperateForestWater::Generate(Seed, Half, Updated, {}, GeneratorVersion);
    RiverPlan = Updated;
    ForestWaterPlan = Water;
    TemperateHillsFixedLayout::FLayout Layout{Updated, Water, VillageSite};
    return TemperateHillsFixedLayout::Write(Layout, Seed, GeneratorVersion, Half, Anchor)
        && BakeFixedQuarryDressing(Layout.Checksum)
        && HillsFixedTerrainCells::Bake(Half, Seed, GeneratorVersion, Updated, Water, ChapelSite, VillageSite, Layout.Checksum);
}
#endif

int32 UBakeTemperateHillsLayoutCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    // Read the actual map actor and its curated assets without playing or saving
    // the map, and without opening or writing a player's save.
    UPackage* Package = LoadPackage(nullptr, TEXT("/Game/GameMaps/L_TemperateHills_Initial"), LOAD_None);
    UWorld* World = Package ? UWorld::FindWorldInPackage(Package) : nullptr;
    if (World && World->PersistentLevel)
        for (AActor* Actor : World->PersistentLevel->Actors)
            if (auto* Hills = Cast<ATemperateHillsWorld>(Actor))
            {
                FString Directory;
                if (FParse::Value(*Params,TEXT("ExportQuarry="),Directory))
                    return Hills->ExportQuarrySurvey(Directory) ? 0 : 1;
                return Hills->BakeFixedLayout() ? 0 : 1;
            }
    UE_LOG(LogTemp, Error, TEXT("Cannot bake fixed hills: the authored hills world actor was not found."));
#endif
    return 1;
}
