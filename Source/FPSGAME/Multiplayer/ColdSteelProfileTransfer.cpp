#include "ColdSteelProfileTransfer.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Misc/Compression.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

namespace ColdSteelProfileTransfer
{
    constexpr uint32 EnvelopeMagic = 0x43535031; // CSP1: zlib profile, version 1.
    constexpr int32 HeaderBytes = sizeof(uint32) + sizeof(int32);

    bool SaveToBlob(USaveGame* Save, TArray<uint8>& OutBlob)
    {
        OutBlob.Reset();
        if (!Save) return false;
        if(auto* ProfileSave=Cast<UColdSteelProfileSave>(Save))
            if(ProfileSave->Profile.Items.ContainsByPredicate([](const auto& I){return I.Container.StartsWith(TEXT("NetView."));}))
            {
                auto* Clean=NewObject<UColdSteelProfileSave>();Clean->Profile=ProfileSave->Profile;
                UColdSteelStatusModel::StripNetworkContainerView(Clean->Profile);Save=Clean;
            }
        TArray<uint8> Raw;
        FMemoryWriter Writer(Raw);
        FObjectAndNameAsStringProxyArchive Ar(Writer, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
        if (Ar.IsError() || Raw.IsEmpty() || Raw.Num() > MaxRawBytes) return false;

        int32 CompressedSize = FCompression::CompressMemoryBound(NAME_Zlib, Raw.Num());
        OutBlob.SetNumUninitialized(HeaderBytes + CompressedSize);
        if (!FCompression::CompressMemory(NAME_Zlib, OutBlob.GetData() + HeaderBytes,
            CompressedSize, Raw.GetData(), Raw.Num()) || HeaderBytes + CompressedSize > ChunkSize * MaxChunks)
        {
            OutBlob.Reset();
            return false;
        }
        OutBlob.SetNum(HeaderBytes + CompressedSize);
        FMemoryWriter Header(OutBlob);
        uint32 Magic = EnvelopeMagic;
        int32 RawSize = Raw.Num();
        Header << Magic << RawSize;
        return true;
    }

    bool BlobToSaveObject(const TArray<uint8>& Blob, USaveGame* Save)
    {
        if (!Save || Blob.Num() <= HeaderBytes || Blob.Num() > ChunkSize * MaxChunks) return false;
        FMemoryReader Header(Blob);
        uint32 Magic = 0;
        int32 RawSize = 0;
        Header << Magic << RawSize;
        if (Magic != EnvelopeMagic || RawSize <= 0 || RawSize > MaxRawBytes) return false;
        TArray<uint8> Raw;
        Raw.SetNumUninitialized(RawSize);
        if (!FCompression::UncompressMemory(NAME_Zlib, Raw.GetData(), RawSize,
            Blob.GetData() + HeaderBytes, Blob.Num() - HeaderBytes)) return false;

        FMemoryReader Reader(Raw);
        FObjectAndNameAsStringProxyArchive Ar(Reader, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
        return !Ar.IsError();
    }

    UColdSteelProfileSave* BlobToSave(const TArray<uint8>& Blob)
    {
        auto* Save = NewObject<UColdSteelProfileSave>();
        return BlobToSaveObject(Blob, Save) ? Save : nullptr;
    }
}
