#pragma once

#include "CoreMinimal.h"

class USaveGame;
class UColdSteelProfileSave;

namespace ColdSteelProfileTransfer
{
    // These limits apply to the network envelope, not the disk save format.
    constexpr int32 ChunkSize = 1024;
    constexpr int32 MaxChunks = 512;
    constexpr int32 MaxRawBytes = 4 * 1024 * 1024;
    bool SaveToBlob(USaveGame* Save, TArray<uint8>& OutBlob);
    bool BlobToSaveObject(const TArray<uint8>& Blob, USaveGame* Save);
    UColdSteelProfileSave* BlobToSave(const TArray<uint8>& Blob);
}
