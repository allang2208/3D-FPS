#include "ColdSteelSharedChestVisual.h"
#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "TimerManager.h"

void AColdSteelPlayerState::MulticastSharedChestOpened_Implementation(AActor* Target)
{ColdSteelSharedChest::Open(Target);}

bool ColdSteelSharedChest::Open(AActor* Target,bool bInstant)
{
    if(!IsValid(Target)||!ColdSteelWorldInteraction::IsTreasureChest(Target))return false;
    if(Target->ActorHasTag(TEXT("DungeonTreasure.Opening")))return true;
    const bool AlreadyOpened=Target->ActorHasTag(TEXT("DungeonTreasure.Opened"));
    auto* Mesh=Target->FindComponentByClass<USkeletalMeshComponent>();
    FString Json,Path;TSharedPtr<FJsonObject> Config;
    UAnimSequence* Clip=nullptr;
    if(Mesh&&FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/treasure_chest_assets.json")))
        &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Config)&&Config
        &&Config->TryGetStringField(TEXT("opening"),Path))Clip=LoadObject<UAnimSequence>(nullptr,*Path);
    // Replicated/dynamically assembled components can arrive after the scene
    // snapshot. Do not mark the visual complete until it can actually be posed.
    if(!Mesh||!Mesh->GetSkeletalMeshAsset()||!Clip)return false;
    Target->Tags.AddUnique(TEXT("DungeonTreasure.Opened"));
    Target->Tags.AddUnique(TEXT("DungeonTreasure.Opening"));
    Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->ComponentTags.Remove(TEXT("DungeonClosedPoseFrozen"));
    Mesh->SetComponentTickEnabled(true);Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Mesh->PlayAnimation(Clip,false);Mesh->SetPlayRate(1.f);Mesh->SetPosition(0.f,false);
    const float Duration=Clip->GetPlayLength();TWeakObjectPtr<USkeletalMeshComponent> WeakMesh=Mesh;
    if(AlreadyOpened||bInstant)
    {
        Mesh->SetPosition(Duration,false);Mesh->SetPlayRate(0.f);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
        Mesh->SetComponentTickEnabled(false);Target->Tags.Remove(TEXT("DungeonTreasure.Opening"));return true;
    }
    FTimerHandle Timer;
    Target->GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(Target,[Target,WeakMesh,Duration]()
    {
        Target->Tags.Remove(TEXT("DungeonTreasure.Opening"));
        if(auto* Live=WeakMesh.Get())
        {Live->SetPosition(Duration,false);Live->SetPlayRate(0.f);Live->TickAnimation(0.f,false);Live->RefreshBoneTransforms();Live->SetComponentTickEnabled(false);}
    }),FMath::Max(.01f,Duration),false);
    return true;
}
