#include "ColdSteelProfileTransfer.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Misc/Compression.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "UObject/UnrealType.h"

namespace ColdSteelProfileTransfer
{
    // Tagged-property archives read container counts before validating them.
    // A hostile blob could ask for billions of items and make EmptyAndAddValues
    // allocate before any post-deserialize check runs. Clamp the count at the
    // archive boundary and fail the whole transfer if a clamp was needed.
    class FProfileReadArchive final : public FObjectAndNameAsStringProxyArchive
    {
    public:
        explicit FProfileReadArchive(FArchive& InInnerArchive)
            : FObjectAndNameAsStringProxyArchive(InInnerArchive,true)
        {
        }
        bool bLimitHit=false;
        static constexpr int32 MaxElements=10000;
        static constexpr int32 MaxStringChars=65536;
        virtual void Serialize(void* Data,int64 Num) override
        {
            if(!IsLoading()||!Data||Num!=sizeof(int32))
            {
                FObjectAndNameAsStringProxyArchive::Serialize(Data,Num);
                return;
            }
            const FProperty* Property=GetSerializedProperty();
            if(!Property)
            {
                FObjectAndNameAsStringProxyArchive::Serialize(Data,Num);
                return;
            }
            const bool bArray=Property->IsA<FArrayProperty>();
            const bool bMap=Property->IsA<FMapProperty>();
            const bool bSet=Property->IsA<FSetProperty>();
            const bool bString=Property->IsA<FStrProperty>();
            if(!bArray&&!bMap&&!bSet&&!bString)
            {
                FObjectAndNameAsStringProxyArchive::Serialize(Data,Num);
                return;
            }
            int32 Count=0;
            InnerArchive.Serialize(&Count,sizeof(int32));
            if(IsError())
            {
                FMemory::Memcpy(Data,&Count,sizeof(int32));
                return;
            }
            if(bString)
            {
                // FString stores a positive character count or a negative
                // UTF-16 count. Bound both before the following char payload.
                const int64 Magnitude=int64(Count)<0?-int64(Count):int64(Count);
                if(Magnitude>MaxStringChars)
                {
                    Count=Count<0?-MaxStringChars:MaxStringChars;
                    bLimitHit=true;
                }
            }
            else
            {
                // Woodworking masks are byte arrays bounded by the 4 MB blob
                // itself; other containers are bounded by element count.
                const int32 Limit=Property->GetName()==FName(TEXT("Mask"))?MaxRawBytes:MaxElements;
                if(Count>Limit)
                {
                    Count=Limit;
                    bLimitHit=true;
                }
                else if(Count<0)
                {
                    Count=0;
                    bLimitHit=true;
                }
            }
            FMemory::Memcpy(Data,&Count,sizeof(int32));
        }
    };

    class FProfileWriteArchive final : public FObjectAndNameAsStringProxyArchive
    {
    public:
        explicit FProfileWriteArchive(FArchive& InInnerArchive)
            : FObjectAndNameAsStringProxyArchive(InInnerArchive,true)
        {
        }
    };
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
        FProfileWriteArchive Ar(Writer);
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
        FProfileReadArchive Ar(Reader);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
        if(Ar.bLimitHit)
        {
            UE_LOG(LogTemp,Warning,TEXT("ColdSteel profile blob rejected: container/string limit exceeded"));
            return false;
        }
        return !Ar.IsError();
    }

    UColdSteelProfileSave* BlobToSave(const TArray<uint8>& Blob)
    {
        auto* Save = NewObject<UColdSteelProfileSave>();
        return BlobToSaveObject(Blob, Save) ? Save : nullptr;
    }
}
