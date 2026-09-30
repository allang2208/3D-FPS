#include "ProductionToolAppearance.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInterface.h"

/**
 * 采集工具强化的外观落地。
 *
 * 按**槽名**找材质索引（`GetMaterialIndex`），不按固定索引：阶段 2 拆槽会改变槽数与
 * 槽序，写死索引会在重导出后换错材质。找不到槽＝资产尚未拆槽，保持现状。
 *
 * 三条降级路径都只 log 一次（各自的 `static bool`），且都不改变网格的任何其他槽、
 * 不改变可见性与变换，因此在「资源还没加载完就被调用」时也是安全的空操作。
 */

namespace
{
    /** `Metal` 槽索引；没有该槽返回 INDEX_NONE。 */
    int32 FindMetalSlot(const UStaticMesh* Asset)
    {
        return Asset?Asset->GetMaterialIndex(FName(*ColdSteelToolEnhance::MetalSlotName())):INDEX_NONE;
    }

    int32 FindMetalSlot(const USkeletalMesh* Asset)
    {
        if(!Asset)return INDEX_NONE;
        // 骨骼网格没有 GetMaterialIndex：按 `FSkeletalMaterial::MaterialSlotName` 自己找。
        const FName Wanted(*ColdSteelToolEnhance::MetalSlotName());
        const TArray<FSkeletalMaterial>& Slots=Asset->GetMaterials();
        for(int32 Index=0;Index<Slots.Num();++Index)
            if(Slots[Index].MaterialSlotName==Wanted)return Index;
        return INDEX_NONE;
    }

    /**
     * 加载等级对应的金属材质实例。
     * 路径为空（未登记的工具，如铁铲）＝静默保持现状；路径存在但资产未制作时只 log 一次。
     */
    UMaterialInterface* LoadMetalMaterial(const FColdSteelItem& Item,int32 LevelOverride)
    {
        const FString Path=ColdSteelToolEnhance::MetalMaterialPath(Item,LevelOverride);
        if(Path.IsEmpty())return nullptr;
        UMaterialInterface* Loaded=LoadObject<UMaterialInterface>(nullptr,*Path);
        if(!Loaded)
        {
            // 阶段 2 之前 Enhance20260925 下的 MI 都不存在，这里必然走到：只提示一次，不刷屏。
            static bool bLoggedMissing=false;
            if(!bLoggedMissing)
            {
                bLoggedMissing=true;
                UE_LOG(LogTemp,Warning,TEXT("Tool enhance material not authored yet, keeping current: %s"),*Path);
            }
        }
        return Loaded;
    }

    /** 找不到 `Metal` 槽（世界网格与视模当前仍是单槽）时提示一次。 */
    void LogMissingSlotOnce()
    {
        static bool bLogged=false;
        if(bLogged)return;
        bLogged=true;
        UE_LOG(LogTemp,Warning,TEXT("Tool enhance slot '%s' not found, keeping current materials"),
           *ColdSteelToolEnhance::MetalSlotName());
    }
}

void ProductionToolAppearance::ApplyLevel(UStaticMeshComponent* Mesh,const FColdSteelItem& Item,int32 LevelOverride)
{
    if(!Mesh)return;
    UMaterialInterface* Material=LoadMetalMaterial(Item,LevelOverride);
    if(!Material)return;
    const int32 Slot=FindMetalSlot(Mesh->GetStaticMesh());
    if(Slot==INDEX_NONE){LogMissingSlotOnce();return;}
    Mesh->SetMaterial(Slot,Material);
}

void ProductionToolAppearance::ApplyLevel(USkeletalMeshComponent* Mesh,const FColdSteelItem& Item,int32 LevelOverride)
{
    if(!Mesh)return;
    UMaterialInterface* Material=LoadMetalMaterial(Item,LevelOverride);
    if(!Material)return;
    // 视模可能在资源异步加载完成前被调用：此时资产为空，等同于「找不到槽」，保持现状。
    const int32 Slot=FindMetalSlot(Mesh->GetSkeletalMeshAsset());
    if(Slot==INDEX_NONE){LogMissingSlotOnce();return;}
    Mesh->SetMaterial(Slot,Material);
}