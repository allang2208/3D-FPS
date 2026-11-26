#include "TemperateQuarryFixedDressing.h"
#include "HAL/FileManager.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

namespace TemperateQuarryFixedDressing
{
namespace
{
constexpr uint32 Format = 0x51525901;

FString LayoutPath()
{
    return FPaths::ProjectContentDir() / TEXT("WorldGeneration/TemperateHills/FixedLayout/Quarry.dressing");
}
}

FArchive& operator<<(FArchive& Ar, FBlocker& Block)
{
    return Ar << Block.Bounds << Block.Item.Mesh << Block.Item.Transform << Block.Item.Key << Block.Item.CandidateId;
}

FLayoutPtr Load(uint32 TerrainLayout)
{
    TArray<uint8> Bytes;
    if (!FFileHelper::LoadFileToArray(Bytes, *LayoutPath())) return {};
    FMemoryReader Ar(Bytes, true);
    uint32 Version = 0, Parent = 0, Crc = 0;
    Ar << Version << Parent << Crc;
    if (Ar.IsError() || Version != Format || Parent != TerrainLayout || Ar.AtEnd()) return {};
    if (Crc != FCrc::MemCrc32(Bytes.GetData() + Ar.Tell(), Bytes.Num() - Ar.Tell())) return {};
    auto Data = MakeShared<FLayout, ESPMode::ThreadSafe>();
    FObjectAndNameAsStringProxyArchive Records(Ar, false);
    Records << Data->Groups << Data->Blockers;
    return !Records.IsError() && Ar.AtEnd() ? Data : FLayoutPtr{};
}

#if WITH_EDITOR
bool Write(uint32 TerrainLayout, FLayout& Layout)
{
    TArray<uint8> Bytes;
    FMemoryWriter Ar(Bytes, true);
    uint32 Version = Format, Crc = 0;
    Ar << Version << TerrainLayout;
    const int64 ChecksumAt = Ar.Tell();
    Ar << Crc;
    const int64 Start = Ar.Tell();
    FObjectAndNameAsStringProxyArchive Records(Ar, false);
    Records << Layout.Groups << Layout.Blockers;
    if (Records.IsError()) return false;
    Crc = FCrc::MemCrc32(Bytes.GetData() + Start, Bytes.Num() - Start);
    Ar.Seek(ChecksumAt);
    Ar << Crc;
    const FString Path = LayoutPath();
    const FString Temp = FPaths::CreateTempFilename(*FPaths::GetPath(Path), TEXT("quarry-"), TEXT(".tmp"));
    if (!FFileHelper::SaveArrayToFile(Bytes, *Temp) || !IFileManager::Get().Move(*Path, *Temp, true))
    {
        IFileManager::Get().Delete(*Temp);
        return false;
    }
    int32 Instances = 0;
    for (const auto& Group : Layout.Groups) Instances += Group.Value.Num();
    UE_LOG(LogTemp, Display, TEXT("HILLS_QUARRY_BAKED instances=%d mesh_groups=%d blockers=%d"), Instances, Layout.Groups.Num(), Layout.Blockers.Num());
    return true;
}
#endif
}
