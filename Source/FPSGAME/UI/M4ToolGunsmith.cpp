#include "ColdSteelWeaponText.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionToolAppearance.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"

/**
 * 采集工具工作台（伐木斧、矿镐）。
 *
 * 布局、图标与独立预览沿用近战工作台那套结构（`IsStandaloneWorkbench`），
 * 但数值口径走工具自己的评估入口，不套用剑类连击／格挡／精通行。
 */
bool UM4GunsmithWidget::IsToolWorkbench() const
{
    return Model()->IsTool(Model()->Definition());
}

bool UM4GunsmithWidget::IsStandaloneWorkbench() const
{
    return IsStaffWorkbench()||IsMeleeWorkbench()||IsToolWorkbench()||IsBowWorkbench();
}

void UM4GunsmithWidget::AppendToolOverview(const FColdSteelItem& Item)
{
    const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto Parts=bCompareFactory?FGunsmithParts():Model()->Installed(Item);
    const auto Before=ColdSteelTool::Evaluate(Item,Profile,&Parts);
    const auto After=ColdSteelTool::Evaluate(Item,Profile,&Model()->Draft());
    auto Row=[this](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double Delta=Final-Base;const bool Same=FMath::Abs(Delta)<.00001;
        Overview.Add({Name,FString::Printf(TEXT("%.*f%s"),Digits,Base,Unit),FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit),
            Same?TEXT("—"):FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit),Same?0:((Delta>0)!=Lower?1:-1)});
    };
    Overview.Add({TEXT("采集"),TEXT(""),TEXT(""),TEXT(""),0});
    Row(TEXT("采集产出倍率"),Before.HarvestYield,After.HarvestYield,2,TEXT("×"));
    Row(TEXT("采集伤害"),ProductionTreeHealth::StrikeDamage(Before),
        ProductionTreeHealth::StrikeDamage(After),1,TEXT(" / 挥"));
    Row(TEXT("采集距离"),Before.HarvestReachCM/100,After.HarvestReachCM/100,2,TEXT(" m"));
    Row(TEXT("命中宽容半径"),Before.HarvestRadiusCM,After.HarvestRadiusCM,0,TEXT(" cm"));
    Row(TEXT("额外产出几率"),Before.BonusHarvestChance*100,After.BonusHarvestChance*100,0,TEXT(" %"));
    // 每次挥动只扣一次体力，采集与自卫共用，因此只列一行。
    Row(ColdSteelWeaponText::StaminaCost,Before.StaminaCost,After.StaminaCost,2,TEXT(""),true);
    Overview.Add({TEXT("战斗"),TEXT(""),TEXT(""),TEXT(""),0});
    Row(ColdSteelWeaponText::TotalDamage,Before.Damage.Total(),After.Damage.Total(),2,TEXT(""));
    Row(ColdSteelWeaponText::BasePhysical,Before.Damage.BasePhysical,After.Damage.BasePhysical,2,TEXT(""));
    Row(ColdSteelWeaponText::AddedPhysical,Before.Damage.AddedPhysical,After.Damage.AddedPhysical,2,TEXT(""));
    Row(ColdSteelWeaponText::AddedMagic,Before.Damage.AddedMagic,After.Damage.AddedMagic,2,TEXT(""));
    Row(TEXT("暴击率"),Before.CriticalChanceAdd,After.CriticalChanceAdd,0,TEXT(" %"));
    Row(TEXT("韧性伤害倍率"),Before.ToughnessDamage,After.ToughnessDamage,2,TEXT("×"));
    Row(ColdSteelWeaponText::AttackInterval,Before.SwingSeconds*1000,After.SwingSeconds*1000,0,TEXT(" ms"),true);
    Row(TEXT("接触时刻"),Before.ContactSeconds,After.ContactSeconds,2,TEXT(" s"),true);
    Row(ColdSteelWeaponText::AttackDistance,Before.CombatReachCM/100,After.CombatReachCM/100,2,TEXT(" m"));
    // 强化段排在「采集」「自卫」之后：等级与金属材质是外观档位，不是数值行。
    // 采集产出／所需有效命中／自卫总伤害的数字行保持原样不动，另加一行如实说明"强化不影响数值"。
    AppendToolEnhanceOverview(Item);
    Overview.Add({TEXT("握持"),TEXT("双手 · 占用副手"),TEXT("双手 · 占用副手"),TEXT("—"),0});
    // 四栏当前都是数值改造，外观如实说明沿用原装外形；接入实体模块后改读目录的 appearance 字段。
    Overview.Add({TEXT("外观"),TEXT("沿用原装外形"),TEXT("沿用原装外形"),TEXT("—"),0});
}

void UM4GunsmithWidget::SetStandaloneToolItem(const FColdSteelItem& Item,int32 LevelOverride)
{
    // 工具没有 world_mesh：工作台直接展示 production_tools.json 的 tool_mesh，
    // 与掉落物、第一人称视模同源，沿用近战独立预览的正交取景与轨道旋转。
    const FString Path=ColdSteelInventory::Text(Item,TEXT("tool_mesh"));
    // 草稿等级进 Key：只换材质也要重建一次，否则切档位时预览不会变。
    const FString Key=Item.InstanceId+TEXT("|tool|")+Path+FString::Printf(TEXT("|lv%d"),LevelOverride);
    if(StandaloneMelee&&StandaloneKey==Key)return;
    CloseStandalonePreview();
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset)return;
    InitializePreview();if(!Capture)return;
    StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StandaloneMelee->SetStaticMesh(Asset);StandaloneMelee->SetForcedLodModel(1);
    StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    // 网格设好之后再按等级换金属槽材质；资产未拆槽／未制作时保持现状，不报错。
    ProductionToolAppearance::ApplyLevel(StandaloneMelee,Item,LevelOverride);
    Studio->AddComponent(StandaloneMelee,FTransform::Identity);
    StandaloneKey=Key;bPreviewStreamingDirty=true;SetSidePreview(true);
}
