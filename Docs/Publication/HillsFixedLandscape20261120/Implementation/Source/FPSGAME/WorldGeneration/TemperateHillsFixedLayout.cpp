#include "TemperateHillsFixedLayout.h"

#include "HAL/FileManager.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"

namespace TemperateHillsFixedLayout
{
namespace
{
constexpr uint32 LayoutMagic = 0x48494C4C;
constexpr int32 FormatVersion = 2;

FString LayoutPath()
{
    return FPaths::ProjectContentDir() / TEXT("WorldGeneration/TemperateHills/FixedLayout/Hills.layout");
}

template<typename T, typename Fn>
void Entries(FArchive& Ar, TArray<T>& Values, Fn Visit)
{
    int32 Count = Values.Num();
    Ar << Count;
    if (Count < 0 || (Ar.IsLoading() && Count > Ar.TotalSize() - Ar.Tell()))
    {
        Ar.SetError();
        return;
    }
    if (Ar.IsLoading()) Values.SetNum(Count);
    for (T& Value : Values) Visit(Value);
}

// The shared plans are immutable once published. Only the reader constructs a
// new object; the writer archives fields in place without copying the grids.
template<typename T, typename Fn>
void PlanObject(FArchive& Ar, TSharedPtr<const T, ESPMode::ThreadSafe>& Ptr, Fn Visit)
{
    if (Ar.IsLoading())
    {
        auto NewPlan = MakeShared<T, ESPMode::ThreadSafe>();
        Visit(*NewPlan);
        Ptr = MoveTemp(NewPlan);
    }
    else Visit(*ConstCastSharedPtr<T>(Ptr));
}

void River(FArchive& Ar, TemperateRiver::FPlan& R, const TemperateEcology::FProfile& Ecology)
{
    Ar << R.GenerationVersion << R.BankReliefCm << R.WorldHalf << R.bRiverLake;
    Ar << R.ProtectedSize << R.ProtectedLand << R.UplandReliefCm;
    Ar << R.ForestGridSize << R.ForestHalfSize << R.ForestAnchor << R.bVillageRainforest << R.RainforestMask;
    Entries(Ar, R.Points, [&](TemperateRiver::FPoint& P)
    {
        Ar << P.XY << P.Side << P.WaterZ << P.HalfWidth << P.Depth << P.Distance;
        Ar << P.LeftWidth << P.RightWidth << P.Bend << P.Speed;
    });
    Ar << R.Buckets;

    auto& Lake = R.Lake;
    Ar << Lake.Valid << Lake.bNaturalShore << Lake.LandformSeed << Lake.Center << Lake.Axis;
    Ar << Lake.RadiusX << Lake.RadiusY << Lake.WaterZ << Lake.Depth << Lake.Phase << Lake.Along << Lake.RiverMouths;
    Entries(Ar, Lake.BankPatches, [&](TemperateRiver::FPlan::FLake::FBankPatch& P)
    {
        Ar << P.Frame.Anchor << P.Frame.Inland << P.HalfLength << P.HalfDepth << P.CrossScale;
        Ar << P.Hand << P.Strength << P.StoneYaw;
        uint8 Form = static_cast<uint8>(P.Form);
        Ar << Form;
        if (Ar.IsLoading()) P.Form = static_cast<TemperateRiver::FPlan::FLake::EBankForm>(Form);
    });
    Ar << Lake.BankTiles;

    auto& Cliff = R.WhiteCliffs;
    Ar << Cliff.Valid << Cliff.Center << Cliff.Axis << Cliff.FloorZ;
    auto& Slope = R.QuarryLakeSlope;
    Ar << Slope.Origin << Slope.Across << Slope.MinY << Slope.Rows << Slope.Outcrops;
    Entries(Ar, Slope.Cells, [&](TemperateQuarryLakeSlope::FField::FCell& C)
    {
        Ar << C.HeightCm << C.Coverage << C.Gully << C.Gravel << C.Ledge << C.Turf << C.Damp;
    });

    bool HasBaseline = R.SettlementBaseline.IsValid();
    Ar << HasBaseline;
    if (HasBaseline && !Ar.IsError())
        PlanObject(Ar, R.SettlementBaseline, [&](TemperateRiver::FPlan& B){ River(Ar, B, Ecology); });
    if (Ar.IsLoading()) R.Ecology = Ecology;
}

void ForestWater(FArchive& Ar, TemperateForestWater::FPlan& W)
{
    Ar << W.Origin << W.Width << W.Height << W.Ground << W.ShoreMoisture;
    Entries(Ar, W.Pools, [&](TemperateForestWater::FPool& P)
    {
        Ar << P.WaterZ << P.AreaM2 << P.MaxDepth << P.Bounds << P.Cells;
    });
    Entries(Ar, W.Basins, [&](TemperateForestWater::FBasin& B)
    {
        Ar << B.Center << B.Radius << B.WaterZ << B.Depth;
    });
    Entries(Ar, W.Patches, [&](TemperateForestWater::FPlanPtr& Patch)
    {
        PlanObject(Ar, Patch, [&](TemperateForestWater::FPlan& P){ ForestWater(Ar, P); });
    });
}

void LayoutFields(FArchive& Ar, FLayout& Layout, const TemperateEcology::FProfile& Ecology)
{
    auto& V = Layout.Village;
    Ar << V.Ground << V.Axis << V.Shoulder << V.PadHalfX << V.PadHalfY;
    Ar << V.bHilltop << V.bPlaced << V.bSideLane << V.FeederLength << V.JunctionZ;
    PlanObject(Ar, Layout.River, [&](TemperateRiver::FPlan& R){ River(Ar, R, Ecology); });
    PlanObject(Ar, Layout.Water, [&](TemperateForestWater::FPlan& W){ ForestWater(Ar, W); });
}

struct FHeader
{
    uint32 Magic = LayoutMagic;
    int32 Format = FormatVersion;
    int32 Seed = 0, Generation = 0;
    double HalfSize = 0.;
    FVector2D Anchor = FVector2D::ZeroVector;
    uint32 Checksum = 0;

    void Serialize(FArchive& Ar)
    {
        Ar << Magic << Format << Seed << Generation << HalfSize << Anchor << Checksum;
    }
};
}

FLayout Load(int32 Seed, int32 GeneratorVersion, double HalfSize, const FVector2D& Anchor,
    const TemperateEcology::FProfile& Ecology)
{
    TArray<uint8> Bytes;
    if (!FFileHelper::LoadFileToArray(Bytes, *LayoutPath())) return {};
    FMemoryReader Ar(Bytes, true);
    FHeader Header;
    Header.Serialize(Ar);
    if (Ar.IsError() || Header.Magic != LayoutMagic || (Header.Format != 1 && Header.Format != FormatVersion) ||
        Header.Seed != Seed || Header.Generation != GeneratorVersion || Header.HalfSize != HalfSize ||
        !Header.Anchor.Equals(Anchor, .01) || Ar.Tell() >= Bytes.Num()) return {};
    if (Header.Checksum != FCrc::MemCrc32(Bytes.GetData() + Ar.Tell(), Bytes.Num() - Ar.Tell())) return {};
    FLayout Layout;
    LayoutFields(Ar, Layout, Ecology);
    Layout.Checksum = Header.Checksum;
    return !Ar.IsError() && Ar.AtEnd() ? Layout : FLayout{};
}

#if WITH_EDITOR
bool Write(FLayout& Layout, int32 Seed, int32 GeneratorVersion, double HalfSize, const FVector2D& Anchor)
{
    FHeader Header;
    Header.Seed = Seed;
    Header.Generation = GeneratorVersion;
    Header.HalfSize = HalfSize;
    Header.Anchor = Anchor;
    TArray<uint8> Bytes;
    FMemoryWriter Ar(Bytes, true);
    Header.Serialize(Ar);
    const int64 Start = Ar.Tell();
    LayoutFields(Ar, Layout, Layout.River->Ecology);
    if (Ar.IsError()) return false;
    Header.Checksum = FCrc::MemCrc32(Bytes.GetData() + Start, Bytes.Num() - Start);
    Ar.Seek(0);
    Header.Serialize(Ar);

    const FString Path = LayoutPath();
    const FString Temp = FPaths::CreateTempFilename(*FPaths::GetPath(Path), TEXT("Hills-"), TEXT(".tmp"));
    IFileManager& Files = IFileManager::Get();
    if (!Files.MakeDirectory(*FPaths::GetPath(Path), true)) return false;
    if (!FFileHelper::SaveArrayToFile(Bytes, *Temp) || !Files.Move(*Path, *Temp, true))
    {
        Files.Delete(*Temp);
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("HILLS_LAYOUT_BAKED seed=%d size_m=%.0f river_samples=%d shore_sections=%d pools=%d bytes=%d path=%s"),
        Seed, HalfSize / 50., Layout.River->Points.Num(), Layout.River->Lake.BankPatches.Num(), Layout.Water->Pools.Num(), Bytes.Num(), *Path);
    Layout.Checksum = Header.Checksum;
    return true;
}
#endif
}
