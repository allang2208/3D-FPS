#include "ColdSteelWorldInteraction.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/ColdSteelDoorInteraction.h"
#include "../Building/ColdSteelFountain.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Items/FPSPotionUseComponent.h"
#include "ColdSteelStatusModel.h"
#include "Kismet/GameplayStatics.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelSceneContainer.h"
#include "ColdSteelPickup.h"
#include "../Weapons/Bow/BowArrow.h"
#include "ColdSteelDungeonLoot.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelHUDWidget.h"
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
    if(!IsValid(PC)||!PC->GetPawn()||PC->bShowMouseCursor||PC->GetNetMode()==NM_Client)return nullptr;
    FVector Eye;FRotator View;GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelUse),false,PC->GetPawn());
    TArray<FHitResult> Hits;
    // Includes arrow overlap shapes up to the first blocking surface. Arrows
    // stay nonblocking to combat traces; walls still limit interaction reach.
    PC->GetWorld()->LineTraceMultiByChannel(Hits,Eye,Eye+View.Vector()*Reach,ECC_Visibility,Query);
    for (const FHitResult& Hit : Hits)
    {
        if (const auto* Arrow = Cast<ABowArrow>(Hit.GetActor()); Arrow && Arrow->CanRecover()) return Hit.GetActor();
        if (Hit.bBlockingHit) return Hit.GetActor();
    }
    return nullptr;
}
bool ColdSteelWorldInteraction::IsFocused(const APawn* Pawn,const AActor* Target,float Reach)
{
    return IsValid(Pawn)&&IsValid(Target)&&Pawn->GetWorld()==Target->GetWorld()&&TraceTarget(Cast<APlayerController>(Pawn->GetController()),Reach)==Target;
}
AColdSteelSceneContainer* ColdSteelWorldInteraction::FocusedSceneContainer(const APlayerController* PC)
{
    if(!IsValid(PC)||!PC->GetPawn()||PC->bShowMouseCursor||PC->GetNetMode()==NM_Client)return nullptr;
    if(auto* Exact=Cast<AColdSteelSceneContainer>(TraceTarget(PC)))return Exact;
    FVector Eye;FRotator View;GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelContainerFocus),false,PC->GetPawn());
    FHitResult Hit;
    // A narrow aim corridor catches open shelving gaps and the immediate rim.
    // First blocking surface wins; furniture behind a wall never receives focus.
    if(!PC->GetWorld()->SweepSingleByChannel(Hit,Eye,Eye+View.Vector()*250.f,FQuat::Identity,
        ECC_Visibility,FCollisionShape::MakeSphere(18.f),Query))return nullptr;
    auto* Container=Cast<AColdSteelSceneContainer>(Hit.GetActor());
    if(Container&&FVector::Dist(PC->GetPawn()->GetActorLocation(),Container->GetActorLocation()+FVector(0,0,70))<=240.f)
        return Container;
    return nullptr;
}

AColdSteelSceneContainer* ColdSteelWorldInteraction::UpdateSceneContainerHighlight(const APlayerController* PC,bool bAllowed)
{
    // Standalone local HUD owns the single focus. No actor idle ticks or world scans.
    static TWeakObjectPtr<const APlayerController> Owner;
    static TWeakObjectPtr<AColdSteelSceneContainer> Previous;
    static double LastUpdate=-1.;
    const double Now=IsValid(PC)&&PC->GetWorld()?PC->GetWorld()->GetTimeSeconds():0.;
    if(Owner.Get()!=PC||!bAllowed||Now<LastUpdate)
    {
        if(Previous.IsValid())Previous->SetViewHighlighted(false);
        Previous.Reset();Owner=PC;LastUpdate=-1.;
    }
    if(!bAllowed)return nullptr;
    if(LastUpdate>=0.&&Now-LastUpdate<.06)return Previous.Get();
    LastUpdate=Now;
    auto* Next=FocusedSceneContainer(PC);
    if(Next!=Previous.Get())
    {
        if(Previous.IsValid())Previous->SetViewHighlighted(false);
        Previous=Next;
        if(Next)Next->SetViewHighlighted(true);
    }
    return Next;
}
bool ColdSteelWorldInteraction::IsExpeditionAltar(const AActor* Target)
{
    static const FName AltarTag(TEXT("ColdSteel.ExpeditionAltar"));
    return IsValid(Target) && Target->ActorHasTag(AltarTag);
}

bool ColdSteelWorldInteraction::IsBlessingFountain(const AActor* Target)
{
    return IsValid(Target)&&Cast<AColdSteelFountain>(Target)
        &&UGameplayStatics::GetCurrentLevelName(Target,true)==TEXT("DayNight_Lighting");
}

bool ColdSteelWorldInteraction::DrinkFromFountain(const APlayerController* PC,AActor* Target)
{
    // The existing use trace enforces cursor mode, walls and eye reach. Never use actor-centre distance:
    // the basin itself is almost ten metres wide and is approached at its rim.
    if(!IsBlessingFountain(Target)||TraceTarget(PC)!=Target)return false;
    APawn* Pawn=PC->GetPawn();
    if(!Pawn||!Pawn->HasAuthority())return false;
    auto* Survival=Pawn->FindComponentByClass<UFPSSurvivalComponent>();
    if(!Survival||!Survival->DrinkBlessedWater())return false;
    if(auto* Consumable=Pawn->FindComponentByClass<UFPSPotionUseComponent>())Consumable->PlayHydrationAudio();
    if(auto* Game=PC->GetGameInstance())if(auto* Profile=Game->GetSubsystem<UColdSteelStatusModel>())
    {
        // SaveNow captures the live resources and blessing before publishing the profile.
        Profile->SaveNow();
        Profile->PostNotice(TEXT("清泉赐福"),TEXT("缺水度已补满 · 12 分钟内饥饿、缺水消耗减慢 10%"),TEXT("💧"));
    }
    return true;
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
        if(Target->ActorHasTag(TreasureOpenedTag))return TEXT("最终宝箱 · 打开战利品");
        return TEXT("最终宝箱 · 开启");
    }
    if(Target->ActorHasTag(TreasureOpeningTag))return TEXT("探险宝箱 · 开启中");
    if(Target->ActorHasTag(TreasureOpenedTag))return TEXT("探险宝箱 · 打开战利品");
    return TEXT("探险宝箱 · 开启");
}

bool ColdSteelWorldInteraction::IsSmeltingFurnace(const AActor* Target)
{
    // 高炉是普通静态构件（调色板 `blast_furnace`，无逻辑件）：命中 Actor 就是占位记录本身。
    // 落体件（BeginFall 后）已不在构件记录里，不再可交互——与门对 `VoxelDetached` 的免疫同一口径。
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Target);
    return Piece&&(Piece->PrefabId()==VoxelSmeltingFurnaceId||Piece->PrefabId()==VoxelCastingStationId)&&!Piece->IsFalling();
}

bool ColdSteelWorldInteraction::IsForgingStation(const AActor* Target)
{
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Target);
    return Piece&&Piece->PrefabId()==VoxelCastingStationId&&!Piece->IsFalling();
}

FString ColdSteelWorldInteraction::SmeltingFurnacePrompt(const AActor* Target)
{
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Target);
    if(!IsSmeltingFurnace(Target))return FString();
    const auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    FIntVector Cell=Piece->AnchorCell();
    const bool bTable=Piece->PrefabId()==VoxelCastingStationId;
    if(bTable&&(!World||!World->FindCastingFurnace(Cell,Cell)))
        return TEXT("铸造台 · 在附近高炉投料后使用");
    if(World)if(const FVoxelSmeltingJob* Job=World->FindSmelting(Cell))
    {
        (void)Job;   // 任务存在性判定；状态读取走系统的 (World,Cell) 口径
        auto* Game=World->GetWorld()?World->GetWorld()->GetGameInstance():nullptr;
        auto* System=Game?Game->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
        if(Job->bCasting)
        {
            const int64 Stored=UColdSteelSmeltingSystem::CastingStored(*Job);
            if(Stored>=UColdSteelSmeltingSystem::CastingCapacity)return TEXT("成品架已满 · 领取后继续冶炼");
            return FString::Printf(TEXT("%s · 成品 %lld / 60 · 打开队列"),bTable?TEXT("铸造台"):TEXT("冶炼高炉"),Stored);
        }
        if(System&&System->IsDone(World,Cell))return TEXT("冶炼高炉 · 取出矿锭");
        if(System&&System->IsBurning(World,Cell))return TEXT("冶炼高炉 · 冶炼中");
        return TEXT("冶炼高炉 · 等待燃料");   // 停炉：有任务、未烧完、火已熄
    }
    return TEXT("冶炼高炉 · 打开冶炼面板");
}

bool ColdSteelWorldInteraction::IsWorkbench(const AActor* Target)
{
    // 工作台与高炉同一口径：普通静态构件（调色板 `workbench_table`，无逻辑件），
    // 命中 Actor 就是占位记录本身；落体件不再可交互。
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Target);
    return Piece&&(Piece->PrefabId()==VoxelWorkbenchId||Piece->PrefabId()==VoxelGunWorkbenchId)&&!Piece->IsFalling();
}

FString ColdSteelWorldInteraction::WorkbenchPrompt(const AActor* Target)
{
    if(!IsWorkbench(Target))return FString();
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Target);
    return Piece->PrefabId()==VoxelGunWorkbenchId?TEXT("枪械工作台 · 打开拼装界面"):TEXT("工作台 · 打开制作面板");
}

namespace
{
    /** 已开启宝箱的战利品面板：与仓库宝箱同款 UI，绑定 DungeonChest.<领取键> 容器（一页）。
     *  开启动画结束与重复按 E 两条路共用；无运行上下文时静默不打开。 */
    void OpenChestLootPanel(const APlayerController* PC,AActor* Chest)
    {
        const auto* Impl=Cast<AFPSGAMEPlayerController>(PC);
        auto* HUD=Impl?Impl->GetColdSteelHUD():nullptr;
        if(!HUD||!Chest)return;
        const FString Key=FColdSteelDungeonLoot::ChestStorageKey(Chest);
        if(Key.IsEmpty())return;
        HUD->OpenChestLootStorage(Chest,Key,1,TEXT("宝箱战利品"));
    }
}

bool ColdSteelWorldInteraction::OpenTreasureChest(const APlayerController* PC,AActor* Target)
{
    // TraceTarget also enforces standalone mode, cursor state, occlusion and 2.5 m eye reach.
    if(!IsTreasureChest(Target)||TraceTarget(PC)!=Target)return false;
    if(Target->ActorHasTag(TreasureOpeningTag))return false;
    if(Target->ActorHasTag(TreasureOpenedTag)){OpenChestLootPanel(PC,Target);return true;} // 重复按 E＝重开面板
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
    TWeakObjectPtr<const APlayerController> WeakPC=PC;
    FTimerHandle FinishTimer;
    Target->GetWorldTimerManager().SetTimer(FinishTimer,FTimerDelegate::CreateWeakLambda(Target,[Target,WeakMesh,WeakPC,Duration]()
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
        // 2026-10-02 仓库式取物：roll 写进宝箱容器（不直接发放、不播报），成功后弹出仓库同款面板。
        FString StorageKey;
        if(!FColdSteelDungeonLoot::StoreFromChest(Target,StorageKey))
            Target->Tags.Remove(TreasureOpenedTag); // 写入失败＝未领取，保持可重试
        else if(!StorageKey.IsEmpty())
            OpenChestLootPanel(WeakPC.Get(),Target);
    }),Duration,false);
    return true;
}

ColdSteelWorldInteraction::FInteractionHint ColdSteelWorldInteraction::ResolveInteractionHint(const AActor* Target)
{
    // 准星统一小浮窗的唯一文案来源（2026-09-24 用户指令：一切 E 交互走小浮窗，模型上方不再挂名牌）。
    // 分派顺序与 PlayerController 的 E 键处理一致：先特异后泛化；空文本＝不显示浮窗。
    FInteractionHint Hint;
    if(!IsValid(Target))return Hint;
    if(IsExpeditionAltar(Target)){Hint.Text=TEXT("祭坛 · 打开出征面板");return Hint;}
    if(IsBlessingFountain(Target)){Hint.Text=TEXT("喷泉 · 补满水分并获得 12 分钟赐福");return Hint;}
    if(const auto* Run=UDungeonRunSubsystem::Get(Target->GetWorld());Run&&Run->IsShrine(Target))
    {Hint.Text=Run->ShrinePrompt();Hint.bAction=Run->CanClaimShrine();return Hint;}
    if(IsTreasureChest(Target))
    {
        Hint.Text=TreasureChestPrompt(Target);
        // 已开启的宝箱保持可交互：E 重开战利品面板（2026-10-02 仓库式取物）。
        Hint.bAction=!Target->ActorHasTag(TreasureOpeningTag)&&!Target->ActorHasTag(FName(TEXT("DungeonReward.Locked")));
        return Hint;
    }
    if(const auto* Container=Cast<AColdSteelSceneContainer>(Target))
    {Hint.Text=Container->GetPromptLabel();Hint.bAction=!Container->IsOpening();return Hint;}
    if(const auto* Chest=Cast<AColdSteelWarehouseChest>(Target)){Hint.Text=Chest->GetPromptLabel();return Hint;}
    if(const auto* Pickup=Cast<AColdSteelPickup>(Target)){Hint.Text=Pickup->GetPromptText();return Hint;}
    if(const auto* Arrow=Cast<ABowArrow>(Target)){Hint.Text=Arrow->RecoveryPrompt();Hint.bAction=Arrow->CanRecover();return Hint;}
    if(IsForgingStation(Target)){Hint.Text=TEXT("铸造台 · 锻造 / 冶炼领锭");return Hint;}
    if(IsSmeltingFurnace(Target)){Hint.Text=SmeltingFurnacePrompt(Target);return Hint;}
    if(IsWorkbench(Target)){Hint.Text=WorkbenchPrompt(Target);return Hint;}
    if(UColdSteelDoorInteraction::IsDoor(Target)){Hint.Text=TEXT("门 · 开／关");return Hint;}
    return Hint;
}
