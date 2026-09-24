#include "ColdSteelWorldInteraction.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"

namespace
{
    const FName TreasureOpeningTag(TEXT("DungeonTreasure.Opening"));
    const FName TreasureOpenedTag(TEXT("DungeonTreasure.Opened"));
}
void ColdSteelWorldInteraction::GetReachViewPoint(const APlayerController* PC,FVector& Eye,FRotator& View)
{
    PC->GetPlayerViewPoint(Eye,View);
    if(const APawn* Pawn=PC->GetPawn())
        if(const auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>()) Body->ApplyInteractionView(Eye,View);
}
AActor* ColdSteelWorldInteraction::TraceTarget(const APlayerController* PC,float Reach)
{
    if(!IsValid(PC)||!PC->GetPawn()||PC->bShowMouseCursor||PC->GetNetMode()!=NM_Standalone)return nullptr;
    FVector Eye;FRotator View;GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelUse),false,PC->GetPawn());FHitResult Hit;
    return PC->GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*Reach,ECC_Visibility,Query)?Hit.GetActor():nullptr;
}
bool ColdSteelWorldInteraction::IsFocused(const APawn* Pawn,const AActor* Target,float Reach)
{
    return IsValid(Pawn)&&IsValid(Target)&&Pawn->GetWorld()==Target->GetWorld()&&TraceTarget(Cast<APlayerController>(Pawn->GetController()),Reach)==Target;
}

bool ColdSteelWorldInteraction::IsTreasureChest(const AActor* Target)
{
    return IsValid(Target)&&Target->ActorHasTag(TEXT("DungeonTreasureChest"));
}

bool ColdSteelWorldInteraction::IsTreasureChestActivated(const AActor* Target)
{
    return IsTreasureChest(Target)&&(Target->ActorHasTag(TreasureOpeningTag)||Target->ActorHasTag(TreasureOpenedTag));
}

FString ColdSteelWorldInteraction::TreasureChestPrompt(const AActor* Target)
{
    if(!IsTreasureChest(Target))return FString();
    if(Target->ActorHasTag(TEXT("DungeonReward.Locked")))return TEXT("最终宝箱 · 击败首领后解锁");
    if(Target->ActorHasTag(TEXT("DungeonFinalTreasure")))
    {
        if(Target->ActorHasTag(TreasureOpeningTag))return TEXT("最终宝箱 · 开启中");
        if(Target->ActorHasTag(TreasureOpenedTag))return TEXT("最终宝箱 · 已开启");
        return TEXT("最终宝箱 · 开启");
    }
    if(Target->ActorHasTag(TreasureOpeningTag))return TEXT("探险宝箱 · 开启中");
    if(Target->ActorHasTag(TreasureOpenedTag))return TEXT("探险宝箱 · 已开启");
    return TEXT("探险宝箱 · 开启");
}

bool ColdSteelWorldInteraction::OpenTreasureChest(const APlayerController* PC,AActor* Target)
{
    // TraceTarget also enforces standalone mode, cursor state, occlusion and 2.5 m eye reach.
    if(!IsTreasureChest(Target)||IsTreasureChestActivated(Target)||TraceTarget(PC)!=Target)return false;
    if(Target->ActorHasTag(TEXT("DungeonReward.Locked")))return false;
    auto* Mesh=Target->FindComponentByClass<USkeletalMeshComponent>();
    if(!Mesh||!Mesh->GetSkeletalMeshAsset())return false;
    FString JSON,Path;
    TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(JSON,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/treasure_chest_assets.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(JSON),Config)||!Config.IsValid()
        ||!Config->TryGetStringField(TEXT("opening"),Path))return false;
    auto* Clip=LoadObject<UAnimSequence>(nullptr,*Path);
    if(!Clip||Clip->GetPlayLength()<=0.f)
    {
        UE_LOG(LogTemp,Warning,TEXT("TreasureChest: opening clip unavailable: %s"),*Path);
        return false;
    }

    Target->Tags.AddUnique(TreasureOpeningTag);
    Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->ComponentTags.Remove(TEXT("DungeonClosedPoseFrozen"));
    Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Mesh->bEnableUpdateRateOptimizations=false;
    Mesh->SetComponentTickEnabled(true);
    Mesh->PlayAnimation(Clip,false);
    Mesh->SetPlayRate(1.f);
    Mesh->SetPosition(0.f,false);
    Mesh->TickAnimation(0.f,false);
    Mesh->RefreshBoneTransforms();

    const float Duration=Clip->GetPlayLength();
    const TWeakObjectPtr<USkeletalMeshComponent> WeakMesh=Mesh;
    FTimerHandle FinishTimer;
    Target->GetWorldTimerManager().SetTimer(FinishTimer,FTimerDelegate::CreateWeakLambda(Target,[Target,WeakMesh,Duration]()
    {
        if(auto* ChestMesh=WeakMesh.Get())
        {
            // Evaluate the last frame before freezing; looking away must not leave a half-open lid.
            ChestMesh->SetPosition(Duration,false);
            ChestMesh->SetPlayRate(0.f);
            ChestMesh->TickAnimation(0.f,false);
            ChestMesh->RefreshBoneTransforms();
            ChestMesh->SetComponentTickEnabled(false);
            ChestMesh->ComponentTags.AddUnique(TEXT("DungeonOpenPoseFrozen"));
        }
        Target->Tags.Remove(TreasureOpeningTag);
        Target->Tags.AddUnique(TreasureOpenedTag);
    }),Duration,false);
    return true;
}
