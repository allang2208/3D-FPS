#include "VillageCarpenterResident.h"

#include "ResidentConversation.h"
#include "VillageArtisanAppearance.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "TimerManager.h"

namespace VillageCarpenterAssets
{
    const FVillageArtisanAppearance Appearance{
        FSoftObjectPath(TEXT("/Game/Characters/VillageCarpenterNPC/Head/SK_Carpenter_Head.SK_Carpenter_Head")),
        FSoftObjectPath(TEXT("/Game/Characters/VillageCarpenterNPC/Outfit/SK_Carpenter_Workwear.SK_Carpenter_Workwear"))
    };
}

TArray<FSoftObjectPath> AVillageCarpenterResident::AppearancePaths()
{
    return VillageCarpenterAssets::Appearance.Paths();
}

bool AVillageCarpenterResident::IsAppearanceCompilationPending()
{
    return VillageCarpenterAssets::Appearance.IsCompiling();
}

AVillageCarpenterResident::AVillageCarpenterResident()
{
    bCarpenter = true;

    Head = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CarpenterHead"));
    Workwear = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CarpenterWorkwear"));
    Head->SetupAttachment(Body);
    Workwear->SetupAttachment(Body);
    for (USkeletalMeshComponent* Part : {Body.Get(), Head.Get(), Workwear.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetVisibility(false);
    }
    Tags.Add(TEXT("NPC"));
    Tags.Add(TEXT("VillageCarpenter"));
}

void AVillageCarpenterResident::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() != NM_DedicatedServer)
        AppearanceLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(AppearancePaths(),
            FStreamableDelegate::CreateUObject(this, &AVillageCarpenterResident::AssembleAppearance));
}

void AVillageCarpenterResident::AssembleAppearance()
{
    if (IsAppearanceCompilationPending())
    {
        GetWorldTimerManager().SetTimer(AppearanceRetryTimer, this, &AVillageCarpenterResident::AssembleAppearance, .05f, false);
        return;
    }
    VillageCarpenterAssets::Appearance.Dress(*Body, *Head, *Workwear, ConversationFacing);
}

void AVillageCarpenterResident::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(AppearanceRetryTimer);
    if (AppearanceLoad)
    {
        AppearanceLoad->CancelHandle();
        AppearanceLoad.Reset();
    }
    Super::EndPlay(Reason);
}
