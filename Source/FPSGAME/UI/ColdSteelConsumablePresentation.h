#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;
class FJsonObject;
class UColdSteelStatusModel;

/**
 * 消耗品（食物／饮料／药水）浮窗标准。
 *
 * 简略浮窗与详细浮窗共用这里的行序；目录只填 useEffect / spoilDays /
 * useDuration / useCooldown / maxUses / remainingUses / buffs，
 * 不在 UI 里写单件物品分支。字段契约见
 * Docs/Items/consumable-tooltip-standard-20261018.md。
 */
namespace ColdSteelConsumable
{
    struct FRow
    {
        FString Label,Value,Note;
        /** 1 正向，-1 负向，0 中性；UI 只把它映射成颜色。 */
        int32 Tone=0;
        bool bSection=false;
    };

    /** category=consumable，或带 spoilDays 的可腐败食材（生肉等）。 */
    bool IsConsumable(const FJsonObject* Data);
    /** Shared freshness text/tone; refresh uses the already sampled lifetime. */
    void FormatFreshness(double Remaining,double Lifetime,FString& Value,int32& Tone);
    /** 简略与详细浮窗共用的数值口径说明。 */
    FString ValueScope(const FColdSteelItem& Item,const FJsonObject* Data);
    /** 详细浮窗主卡片：使用效果 → 持续增益 → 新鲜度 → 使用。 */
    void BuildDetailRows(const FColdSteelItem& Item,UColdSteelStatusModel* Model,const FJsonObject* Data,TArray<FRow>& Out);
    /** 简略浮窗核心行，按消耗品类型取前 MaxRows 条。 */
    void BuildSummaryRows(const FColdSteelItem& Item,UColdSteelStatusModel* Model,const FJsonObject* Data,TArray<FRow>& Out,int32 MaxRows=4);
}
