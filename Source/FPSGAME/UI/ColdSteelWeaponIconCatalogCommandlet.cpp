#include "ColdSteelWeaponIconCatalogCommandlet.h"
#include "ColdSteelWeaponIcons.h"
#include "Engine/GameInstance.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "RenderingThread.h"
#include "UObject/StrongObjectPtr.h"

int32 UColdSteelWeaponIconCatalogCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    // Deliberately do not call Init: this authoring task must not load or write a player profile.
    TStrongObjectPtr<UGameInstance> Owner(NewObject<UGameInstance>());
    TStrongObjectPtr<UColdSteelWeaponIcons> Icons(NewObject<UColdSteelWeaponIcons>(Owner.Get()));
    const FString Directory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons");
    IFileManager::Get().MakeDirectory(*Directory,true);
    int32 Failures=0;
    FString Requested;FParse::Value(*Params,TEXT("Definition="),Requested);
    const TArray<FString> Definitions=Requested.IsEmpty()?TArray<FString>{TEXT("ue_m1911"),TEXT("ue_akm"),TEXT("ue_m4a1"),TEXT("ue_dan_wesson715"),TEXT("ue_rune_sword")}:TArray<FString>{Requested};
    for(const FString& Definition:Definitions)
        if(!Icons->ExportCatalogIcon(Definition,Directory/(Definition+TEXT(".png"))))++Failures;
    FlushRenderingCommands();Icons->Deinitialize();
    UE_LOG(LogTemp,Display,TEXT("WeaponIconCatalog: COMPLETE failures=%d"),Failures);
    return Failures?1:0;
#else
    return 1;
#endif
}
