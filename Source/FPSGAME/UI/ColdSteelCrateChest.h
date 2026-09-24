#pragma once
#include "CoreMinimal.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelCrateChest.generated.h"

/** 五档储物箱档位：与 /Game/Props/WarehouseCrateTiers20260924/Skeletal 下的
 *  SK_WarehouseCrate_T1..T5 骨骼变体一一对应（共用仓库宝箱的骨架与开合片段）。 */
UENUM(BlueprintType)
enum class EColdSteelCrateTier : uint8
{
    Wood       UMETA(DisplayName="T1 木质储物箱"),
    StoneWood  UMETA(DisplayName="T2 石木储物箱"),
    Iron       UMETA(DisplayName="T3 铁质储物箱"),
    IronGold   UMETA(DisplayName="T4 鎏金储物箱"),
    SilverGem  UMETA(DisplayName="T5 银华储物箱"),
};

/**
 * 可交互储物箱：按 E 打开与武器仓库同一套面板，但绑定自己独立的格空间——
 * 容量按档位递增（1..5 页，一页 18x12=216 格），内容随玩家档案持久化
 * （物品平铺在 Items 数组内，以 FColdSteelItem::Container 归属区分）。
 * 开盖/关盖复用 warehouse_chest 骨架的 Open/Close 片段（片段绑骨架不绑网格）。
 */
UCLASS()
class FPSGAME_API AColdSteelCrateChest : public AColdSteelWarehouseChest
{
    GENERATED_BODY()
public:
    AColdSteelCrateChest();
    /** 关卡里直接摆放本 Actor 并选档位；同一档位默认共用一个容器键，
     *  需要多只独立箱子时给 StorageKeyOverride 填互不相同的稳定字符串。 */
    UPROPERTY(EditAnywhere,Category="Crate") EColdSteelCrateTier Tier=EColdSteelCrateTier::Wood;
    UPROPERTY(EditAnywhere,Category="Crate") FString StorageKeyOverride;
    static FString TierKey(EColdSteelCrateTier Tier);
    static FString TierCaption(EColdSteelCrateTier Tier);
    static int32 TierPages(EColdSteelCrateTier Tier);
    /** 在锚点 Actor（武器仓库宝箱）右侧成排生成一只储物箱；地面线迹被挡时跳过并告警。 */
    static AColdSteelCrateChest* SpawnBeside(UWorld* World,const AActor* Anchor,EColdSteelCrateTier Tier,float LateralOffset,float AlongOffset);
protected:
    virtual void BeginPlay() override;
    virtual FString GetStorageKey()const override;
    virtual int32 GetStoragePages()const override;
    virtual FString GetStorageCaption()const override;
    virtual FString GetPromptLabel()const override;
};
