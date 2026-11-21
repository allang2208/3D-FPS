// Source/FPSGAME/WorldGeneration/TemperateVillageCheckCommandlet.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 12-12 | int32 UTemperateVillageCheckCommandlet::Main(const FString& Params)
    if(FParse::Param(*Params,TEXT("DefenseBlocks")))return CheckDefenseBlocks(Params);
