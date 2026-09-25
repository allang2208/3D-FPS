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
    // Every definition ColdSteelWeaponIcons::Supports must appear here: a weapon missing from
    // this list has no catalog image, so an icon capture that exhausts its retry budget falls
    // back to a blank slot, or to artwork shot on another rig.
    // 生产材料（矿石／金属锭／石块）走 ColdSteelMaterialIcon.cpp 的拾取物通道；木材的
    // 目录图由 Tools/HarvestTimber/render_wood_log_icon.py 离线渲染成 1x2 竖幅，不在此列。
    const TArray<FString> Definitions=Requested.IsEmpty()?TArray<FString>{TEXT("ue_svd"),TEXT("ue_m1911"),TEXT("ue_akm"),TEXT("ue_a762"),TEXT("ue_m4a1"),TEXT("ue_m16a2"),TEXT("ue_ash12"),TEXT("ue_qbz191"),TEXT("ue_pkm_lowpoly"),TEXT("ue_dan_wesson715"),TEXT("ue_rune_sword"),TEXT("ue_frost_crystal_sword"),TEXT("ue_highland_claymore"),
        TEXT("stone"),TEXT("iron_ore"),TEXT("copper_ore"),TEXT("silver_ore"),TEXT("gold_ore"),TEXT("ironIngot"),TEXT("copperIngot"),TEXT("silverIngot"),TEXT("goldIngot")}:TArray<FString>{Requested};
    for(const FString& Definition:Definitions)
        if(!Icons->ExportCatalogIcon(Definition,Directory/(Definition+TEXT(".png"))))++Failures;
    FlushRenderingCommands();Icons->Deinitialize();
    UE_LOG(LogTemp,Display,TEXT("WeaponIconCatalog: COMPLETE failures=%d"),Failures);
    return Failures?1:0;
#else
    return 1;
#endif
}
