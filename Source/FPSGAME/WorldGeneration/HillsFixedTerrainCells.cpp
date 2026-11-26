#include "HillsFixedTerrainCells.h"
#include "EastRiverRoad.h"
#include "TemperateVillageGround.h"
#include "TemperateHillsStreamingPrivate.h"
#include "HAL/FileManager.h"
#include "Misc/Compression.h"
#include "Misc/Crc.h"
#include "Misc/Paths.h"
#include "Serialization/CustomVersion.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#if WITH_EDITOR
#include "Async/ParallelFor.h"
#include "Misc/ScopeExit.h"
#endif

namespace HillsFixedTerrainCells
{
namespace
{
constexpr uint32 Magic = 0x43544846;
constexpr int32 Format = 1;
using FMesh = UE::Geometry::FDynamicMesh3;

FString TerrainPath()
{
    return FPaths::ProjectContentDir() / TEXT("WorldGeneration/TemperateHills/FixedTerrain/Hills.terrain");
}

// This profile consists entirely of doubles and nested groups of doubles.
// Include it because the same authored heights may have different ground layers.
uint32 EcologyKey(const TemperateEcology::FProfile& Profile)
{
    return FCrc::MemCrc32(&Profile, sizeof(Profile));
}

struct FHeader
{
    uint32 Tag = Magic;
    int32 Schema = Format, Seed = 0, Version = 0, Width = 0;
    double Half = 0., CellSize = HillsStreaming::CellSize;
    uint32 Layout = 0, Ecology = 0;

    void Serialize(FArchive& Ar)
    {
        Ar << Tag << Schema << Seed << Version << Width << Half << CellSize << Layout << Ecology;
    }
};

struct FBlock
{
    int64 Offset = 0;
    int32 Bytes = 0, RawBytes = 0;
    uint32 Crc = 0;

    void Serialize(FArchive& Ar) { Ar << Offset << Bytes << RawBytes << Crc; }
};

struct FCell
{
    FBlock NearGround, FarGround, Water;
    // Serialized scalar widths, independent of compiler alignment.
    static constexpr int64 IndexStride = 3 * (sizeof(int64) + 3 * sizeof(uint32));

    void Serialize(FArchive& Ar) { NearGround.Serialize(Ar); FarGround.Serialize(Ar); Water.Serialize(Ar); }
};

bool ReadMeshes(FArchive& File, const FBlock& Block, FMesh& Mesh, FMesh* Other = nullptr)
{
    // A cell is at most 64 x 64 ground quads plus its skirt, or one tile of
    // clipped water surfaces. Reject corrupt lengths before allocating buffers.
    constexpr int32 MaxBlockBytes = 32 * 1024 * 1024;
    if (Block.Bytes <= 0 || Block.Bytes > MaxBlockBytes || Block.RawBytes <= 0 ||
        Block.RawBytes > MaxBlockBytes || Block.Offset < 0 || Block.Offset > File.TotalSize() - Block.Bytes)
        return false;
    File.Seek(Block.Offset);
    TArray<uint8> Packed, Raw;
    Packed.SetNumUninitialized(Block.Bytes);
    File.Serialize(Packed.GetData(), Packed.Num());
    if (File.IsError()) return false;
    Raw.SetNumUninitialized(Block.RawBytes);
    if (!FCompression::UncompressMemory(NAME_Zlib, Raw.GetData(), Raw.Num(), Packed.GetData(), Packed.Num()) ||
        FCrc::MemCrc32(Raw.GetData(), Raw.Num()) != Block.Crc) return false;

    FMemoryReader Reader(Raw);
    FCustomVersionContainer Versions;
    Versions.Serialize(Reader);
    Reader.SetCustomVersions(Versions);
    Reader << Mesh;
    if (Other) Reader << *Other;
    return !Reader.IsError() && Reader.AtEnd();
}

FCellPtr ReadCell(FIntPoint Key, bool Detailed, double Half, int32 Seed, int32 Version,
    uint32 Layout, uint32 Ecology)
{
    TUniquePtr<FArchive> File(IFileManager::Get().CreateFileReader(*TerrainPath()));
    if (!File) return {};
    FHeader Header;
    Header.Serialize(*File);
    const int32 Width = FMath::RoundToInt(2. * Half / HillsStreaming::CellSize);
    if (File->IsError() || Header.Tag != Magic || Header.Schema != Format || Header.Layout != Layout ||
        Header.Ecology != Ecology || Header.Seed != Seed || Header.Version != Version || Header.Half != Half ||
        Header.Width != Width || Header.CellSize != HillsStreaming::CellSize ||
        Key.X < 0 || Key.Y < 0 || Key.X >= Width || Key.Y >= Width) return {};

    const int64 Position = File->Tell() + FCell::IndexStride * (Key.Y * Width + Key.X);
    if (Position + FCell::IndexStride > File->TotalSize()) return {};
    File->Seek(Position);
    FCell Cell;
    Cell.Serialize(*File);
    auto Result = MakeShared<HillsStreaming::FMeshResult, ESPMode::ThreadSafe>();
    Result->Key = Key;
    Result->Detailed = Detailed;
    const auto& Ground = Detailed || Cell.FarGround.Bytes == 0 ? Cell.NearGround : Cell.FarGround;
    if (File->IsError() || !ReadMeshes(*File, Ground, Result->Mesh) ||
        (Cell.Water.Bytes != 0 && !ReadMeshes(*File, Cell.Water, Result->Water, &Result->Ponds))) return {};
    return Result;
}

bool EditsMayAffect(FIntPoint Key, double Half, const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,
    const TemperateForestWater::FPlan& Water)
{
    if (Edits.IsEmpty()) return false;
    const FVector2D Origin = FVector2D(Key) * HillsStreaming::CellSize - FVector2D(Half);
    const FBox2D Cell(Origin, Origin + FVector2D(HillsStreaming::CellSize));
    for (const auto& Edit : Edits)
    {
        const double Reach = TemperateHillsSurface::TerrainEditReach(Edit) + 110.;
        if (Cell.ExpandBy(Reach).IsInsideOrOn(FVector2D(Edit.X, Edit.Y))) return true;
    }
    // Filling one pond can change which ponds fit the global pool budget.
    // All edited water results live on these same surveyed forest patches.
    for (const auto& Patch : Water.Patches)
    {
        const FVector2D End = Patch->Origin + FVector2D(Patch->Width - 1, Patch->Height - 1) * TemperateForestWater::Step;
        if (Cell.Intersect(FBox2D(Patch->Origin, End))) return true;
    }
    return false;
}
}

FCellPtr LoadOrGenerate(FIntPoint Key, bool Detailed, double Half, int32 Seed, TemperateRiver::FPlanPtr River,
    const TArray<TemperateHillsSurface::FTerrainEdit>& Edits, int32 Version, TemperateForestWater::FPlanPtr Water,
    FTemperateChapelSite Chapel, FTemperateVillageSite Village, uint32 LayoutChecksum)
{
    FCellPtr Cell;
    const bool RoadCell=EastRiverRoad::Enabled(Seed,Version,Village) &&
        EastRiverRoad::TouchesCell(Key.X*HillsStreaming::CellSize-Half,Key.Y*HillsStreaming::CellSize-Half,HillsStreaming::CellSize);
    if (LayoutChecksum && River && Water && !RoadCell && !EditsMayAffect(Key, Half, Edits, *Water))
        Cell=ReadCell(Key, Detailed, Half, Seed, Version, LayoutChecksum, EcologyKey(River->Ecology));
    if (!Cell)
        Cell=HillsStreaming::MakeMesh(Key, Detailed, Half, Seed, River, Edits, Version, Water, Chapel, Village);
    if (Cell)
        TemperateVillageGround::ShapeCell(Village,FVector2D(Key)*HillsStreaming::CellSize-FVector2D(Half),
                                          HillsStreaming::CellSize,Cell->Mesh);
    return Cell;
}

#if WITH_EDITOR
namespace
{
struct FPackedBlock
{
    TArray<uint8> Bytes;
    int32 RawBytes = 0;
    uint32 Crc = 0;

    bool Encode(FMesh& Mesh, FMesh* Other = nullptr)
    {
        // Persist only the versions the mesh writer actually used. The outer
        // stream compresses once per block instead of once per attribute.
        TArray<uint8> Geometry, Raw;
        FMemoryWriter MeshWriter(Geometry);
        MeshWriter.SetCustomVersions(FCustomVersionContainer());
        MeshWriter << Mesh;
        if (Other) MeshWriter << *Other;
        if (MeshWriter.IsError()) return false;
        FCustomVersionContainer Versions = MeshWriter.GetCustomVersions();
        FMemoryWriter Writer(Raw);
        Versions.Serialize(Writer);
        Writer.Serialize(Geometry.GetData(), Geometry.Num());
        if (Writer.IsError()) return false;
        RawBytes = Raw.Num();
        Crc = FCrc::MemCrc32(Raw.GetData(), RawBytes);
        int32 Size = FCompression::CompressMemoryBound(NAME_Zlib, RawBytes);
        if (Size <= 0) return false;
        Bytes.SetNumUninitialized(Size);
        if (!FCompression::CompressMemory(NAME_Zlib, Bytes.GetData(), Size, Raw.GetData(), RawBytes)) return false;
        Bytes.SetNum(Size, EAllowShrinking::No);
        return true;
    }

    FBlock Write(FArchive& Ar)
    {
        if (Bytes.IsEmpty()) return {};
        FBlock Block{Ar.Tell(), Bytes.Num(), RawBytes, Crc};
        Ar.Serialize(Bytes.GetData(), Bytes.Num());
        return Block;
    }
};
}

bool Bake(double Half, int32 Seed, int32 Version, TemperateRiver::FPlanPtr River, TemperateForestWater::FPlanPtr Water,
    FTemperateChapelSite Chapel, FTemperateVillageSite Village, uint32 LayoutChecksum)
{
    if (!River || !Water || !LayoutChecksum || Half <= 0. || Half > 51200.) return false;
    FHeader Header;
    Header.Seed = Seed;
    Header.Version = Version;
    Header.Width = FMath::RoundToInt(2. * Half / HillsStreaming::CellSize);
    Header.Half = Half;
    Header.Layout = LayoutChecksum;
    Header.Ecology = EcologyKey(River->Ecology);
    const FString Target = TerrainPath();
    const FString Folder = FPaths::GetPath(Target);
    IFileManager& Files = IFileManager::Get();
    if (!Files.MakeDirectory(*Folder, true)) return false;
    const FString Temp = FPaths::CreateTempFilename(*Folder, TEXT("Hills-"), TEXT(".tmp"));
    ON_SCOPE_EXIT { if (Files.FileExists(*Temp)) Files.Delete(*Temp); };
    TUniquePtr<FArchive> File(Files.CreateFileWriter(*Temp));
    if (!File) return false;
    Header.Serialize(*File);
    const int64 IndexStart = File->Tell();
    TArray<FCell> Index;
    Index.SetNum(Header.Width * Header.Width);
    for (auto& Cell : Index) Cell.Serialize(*File);

    struct FPackedCell { FPackedBlock Near, Far, Water; bool Ok = false; };
    for (int32 Y = 0; Y < Header.Width; ++Y)
    {
        // Keep only one row of compressed cells in memory, writing a stable
        // row-major file regardless of the order in which workers complete.
        TArray<FPackedCell> Row;
        Row.SetNum(Header.Width);
        ParallelFor(Header.Width, [&](int32 X)
        {
            FCellPtr Near, Far;
            BuildBakeCell({X, Y}, Half, Seed, Version, River, Water, Chapel, Village, Near, Far);
            auto& Out = Row[X];
            const bool HasWater = Near->Water.TriangleCount() || Near->Ponds.TriangleCount();
            Out.Ok = Out.Near.Encode(Near->Mesh) && (!Far || Out.Far.Encode(Far->Mesh)) &&
                (!HasWater || Out.Water.Encode(Near->Water, &Near->Ponds));
        });
        for (int32 X = 0; X < Header.Width; ++X)
        {
            auto& B = Row[X];
            if (!B.Ok) return false;
            Index[Y * Header.Width + X] = {B.Near.Write(*File), B.Far.Write(*File), B.Water.Write(*File)};
        }
        if (File->IsError()) return false;
    }
    const int64 TotalBytes = File->Tell();
    File->Seek(IndexStart);
    for (auto& Cell : Index) Cell.Serialize(*File);
    if (!File->Close() || File->IsError()) return false;
    File.Reset();
    if (!Files.Move(*Target, *Temp, true)) return false;
    UE_LOG(LogTemp, Display, TEXT("HILLS_FIXED_TERRAIN_BAKED seed=%d cells=%d bytes=%lld path=%s"),
        Seed, Index.Num(), TotalBytes, *Target);
    return true;
}
#endif
}
