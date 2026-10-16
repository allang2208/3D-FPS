#pragma once
#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"
namespace AlchemyManualArtwork {
inline FSoftObjectPath Texture(const FString& Name) {const FString N=TEXT("T_Manual")+Name;return FSoftObjectPath(TEXT("/Game/Building/PotionWorkbench20261015/ManualV5/Textures/")+N+TEXT(".")+N);}
inline void Gather(TArray<FSoftObjectPath>& Paths) {
Paths.Add(Texture(TEXT("Paper")));
Paths.Add(Texture(TEXT("_alchemy_active_catalyst")));
Paths.Add(Texture(TEXT("_alchemy_bluemarrow_crystals")));
Paths.Add(Texture(TEXT("_alchemy_pure_base_fluid")));
Paths.Add(Texture(TEXT("_alchemy_redvein_extract")));
Paths.Add(Texture(TEXT("_hp_potion")));
Paths.Add(Texture(TEXT("_hp_potion_high")));
Paths.Add(Texture(TEXT("_hp_potion_medium")));
Paths.Add(Texture(TEXT("_hp_potion_special")));
Paths.Add(Texture(TEXT("_mp_potion")));
Paths.Add(Texture(TEXT("_mp_potion_high")));
Paths.Add(Texture(TEXT("_mp_potion_medium")));
Paths.Add(Texture(TEXT("_mp_potion_special")));
}
}
