#include "ColdSteelCrateChest.h"
#include "Components/BoxComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Animation/AnimSequence.h"
#include "EngineUtils.h"

namespace
{
    const TCHAR* TierMeshPaths[] =
    {
        TEXT("/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood.SK_WarehouseCrate_T1_Wood"),
        TEXT("/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T2_StoneWood.SK_WarehouseCrate_T2_StoneWood"),
        TEXT("/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T3_Iron.SK_WarehouseCrate_T3_Iron"),
        TEXT("/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T4_IronGold.SK_WarehouseCrate_T4_IronGold"),
        TEXT("/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T5_SilverGem.SK_WarehouseCrate_T5_SilverGem"),
    };
    // 开合片段绑定在仓库宝箱的共享骨架上；五档骨骼网格都是该骨架的复制变体，可直接播放。
    const TCHAR* SharedOpenClip  = TEXT("/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidOpen.warehouse_chest_rigidOpen");
    const TCHAR* SharedCloseClip = TEXT("/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidClose.warehouse_chest_rigidClose");
    const TCHAR* TierKeys[]     = {TEXT("crate.wood"),TEXT("crate.stonewood"),TEXT("crate.iron"),TEXT("crate.irongold"),TEXT("crate.silvergem")};
    const TCHAR* TierCaptions[] = {TEXT("木质储物箱"),TEXT("石木储物箱"),TEXT("铁质储物箱"),TEXT("鎏金储物箱"),TEXT("银华储物箱")};
    const int32 TierPageCounts[] = {1,2,3,4,5}; // 一页 216 格：随档位 216/432/648/864/1080（勿与成员函数 TierPages 同名，类域会遮蔽）
    int32 TierIndex(EColdSteelCrateTier Tier){return FMath::Clamp(static_cast<int32>(Tier),0,4);}
}

FString AColdSteelCrateChest::TierKey(EColdSteelCrateTier Tier){return TierKeys[TierIndex(Tier)];}
FString AColdSteelCrateChest::TierCaption(EColdSteelCrateTier Tier){return TierCaptions[TierIndex(Tier)];}
int32 AColdSteelCrateChest::TierPages(EColdSteelCrateTier Tier){return TierPageCounts[TierIndex(Tier)];}

AColdSteelCrateChest::AColdSteelCrateChest()
{
    // 交互碰撞体贴合箱体（源宝箱 151.2×123.3cm、盖下沿起算）；提示板沿用基类高度。
    Collision->SetBoxExtent(FVector(62,78,60));Collision->SetRelativeLocation(FVector(0,0,60));
}

void AColdSteelCrateChest::BeginPlay()
{
    // 基类 BeginPlay 只在槽位为空时才回读 json 配置，因此先按档位装填网格与共享开合片段。
    const int32 Index=TierIndex(Tier);
    if(!ChestAsset)ChestAsset=LoadObject<USkeletalMesh>(nullptr,TierMeshPaths[Index]);
    if(!OpenClip)OpenClip=LoadObject<UAnimSequence>(nullptr,SharedOpenClip);
    if(!CloseClip)CloseClip=LoadObject<UAnimSequence>(nullptr,SharedCloseClip);
    Super::BeginPlay();
}

FString AColdSteelCrateChest::GetStorageKey()const
{
    return StorageKeyOverride.IsEmpty()?TierKeys[TierIndex(Tier)]:StorageKeyOverride;
}
int32 AColdSteelCrateChest::GetStoragePages()const
{
    return TierPages(Tier);
}
FString AColdSteelCrateChest::GetStorageCaption()const
{
    return TierCaptions[TierIndex(Tier)];
}
FString AColdSteelCrateChest::GetPromptLabel()const
{
    return GetStorageCaption()+FString(TEXT(" · 打开储物面板")); // 准星小浮窗正文；E 徽标由浮窗自绘
}

AColdSteelCrateChest* AColdSteelCrateChest::SpawnBeside(UWorld* World,const AActor* Anchor,EColdSteelCrateTier Tier,float LateralOffset,float AlongOffset)
{
    if(!World||!Anchor)return nullptr;
    const FTransform Base=Anchor->GetActorTransform();
    // 锚点局部系：X 前 / Y 右 / Z 上，与宝箱 ResolveFixedSpawn 的偏移口径一致。
    const FVector Probe=Base.TransformPosition(FVector(LateralOffset,AlongOffset,0));
    FHitResult Floor;FCollisionQueryParams Query(SCENE_QUERY_STAT(CrateRow),false,Anchor);
    if(!World->LineTraceSingleByChannel(Floor,Probe+FVector(0,0,120),Probe-FVector(0,0,200),ECC_Visibility,Query)
        ||Floor.bStartPenetrating||Floor.ImpactNormal.Z<.8f)
    {
        UE_LOG(LogTemp,Warning,TEXT("CrateChest: no floor at %s offset (%.0f,%.0f); slot skipped"),*Anchor->GetName(),LateralOffset,AlongOffset);
        return nullptr;
    }
    const FTransform Spawn(Base.GetRotation(),Floor.ImpactPoint+FVector(0,0,2));
    auto* Crate=World->SpawnActorDeferred<AColdSteelCrateChest>(AColdSteelCrateChest::StaticClass(),Spawn,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
    if(!Crate)return nullptr;
    Crate->Tier=Tier; // BeginPlay 在 FinishSpawning 内触发，装填前档位必须就位
    Crate->FinishSpawning(Spawn);
    return Crate;
}
