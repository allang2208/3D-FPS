#include "VillageBlacksmithResident.h"

#include "VillageArtisanAppearance.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace VillageBlacksmithAssets
{
const FVillageArtisanAppearance Appearance{
    FSoftObjectPath(TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Head.SK_Smith_Head")),
    FSoftObjectPath(TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit.SK_Smith_Outfit"))
};
}

TArray<FSoftObjectPath> AVillageBlacksmithResident::AppearancePaths()
{
    return VillageBlacksmithAssets::Appearance.Paths();
}

bool AVillageBlacksmithResident::IsAppearanceCompilationPending()
{
    return VillageBlacksmithAssets::Appearance.IsCompiling();
}

AVillageBlacksmithResident::AVillageBlacksmithResident()
{
    Head = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("SmithHead"));
    Outfit = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("SmithWorkClothes"));
    for (auto* Part : {Head.Get(), Outfit.Get()})
    {
        Part->SetupAttachment(Body);
    }
    for (auto* Part : {Body.Get(), Head.Get(), Outfit.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetVisibility(false);
    }
    Tags.Add(TEXT("NPC"));
    Tags.Add(TEXT("VillageBlacksmith"));
}

void AVillageBlacksmithResident::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() == NM_DedicatedServer)
    {
        return;
    }
    AppearanceLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(AppearancePaths(),
        FStreamableDelegate::CreateUObject(this, &AVillageBlacksmithResident::AssembleAppearance));
}

void AVillageBlacksmithResident::AssembleAppearance()
{
    // Package completion is earlier than skeletal compilation in an uncooked
    // game. SetSkeletalMeshAsset would synchronously join all three workers.
    if (IsAppearanceCompilationPending())
    {
        GetWorldTimerManager().SetTimer(AppearanceRetryTimer, this,
            &AVillageBlacksmithResident::AssembleAppearance, .05f, false);
        return;
    }
    VillageBlacksmithAssets::Appearance.Dress(*Body, *Head, *Outfit, ConversationFacing);
    OnDressed();
}

void AVillageBlacksmithResident::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(AppearanceRetryTimer);
    if (AppearanceLoad)
    {
        AppearanceLoad->CancelHandle();
        AppearanceLoad.Reset();
    }
    Super::EndPlay(Reason);
}
