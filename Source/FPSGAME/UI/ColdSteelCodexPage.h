#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelInventoryTypes.h"
#include "../Monsters/MonsterCoreStats.h"
#include "ColdSteelCodexPage.generated.h"
class UColdSteelStatusModel;
class UDevelopmentSpawnComponent;
struct FDevelopmentMonsterEntry;
class APawn;
class UTexture2D;
class SBox;
class SScrollBox;
class SButton;

/** 图鉴（武器／怪物）档案页：只读展示，挂在既有右侧抽屉的第 4 页。
 *  数据来源与运行时同一入口——武器走 UColdSteelStatusModel 的物品目录与物品 Data，
 *  怪物走 UDevelopmentSpawnComponent::GetMonsters() 与 MonsterCoreStats。本页不写存档、
 *  不改战斗公式，也不复制第二套数值口径。参考原项目 src/ui/codex-manager.js 的分类与详情结构。 */
UCLASS()
class FPSGAME_API UColdSteelCodexPage : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetHUD(class UColdSteelHUDWidget* Owner);
    /** 抽屉实际内容宽度（像素）：决定网格／详情是并排还是纵排。 */
    void SetLayoutWidth(float Pixels);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeTick(const FGeometry& Geometry, float Delta) override;
private:
    /** 一条档案：武器与怪物共用一个条目形状，Selected 时按 Section 解释字段。 */
    struct FCodexEntry
    {
        FString Id;
        FString Name;
        FString Category;
        FString Subtitle;
        int32 CombatLevel = 0;
        int32 SortKey = 0;
    };

    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;

    TSharedPtr<SBox> Root;
    TSharedPtr<SScrollBox> GridScroll;
    TSharedPtr<SScrollBox> DetailScroll;
    TSharedPtr<SBox> GridHost;
    TSharedPtr<SBox> DetailHost;
    TArray<TSharedPtr<SButton>> CardButtons;
    TArray<TSharedPtr<SButton>> SectionButtons;
    TArray<TSharedPtr<SButton>> CategoryButtons;
    FButtonStyle ActionStyle;
    FButtonStyle ActionActiveStyle;
    FButtonStyle CardStyle;
    FButtonStyle CardActiveStyle;
    /** SBorder 的 BorderImage 取指针，故缓存分区卡画刷而不是每次构造临时值。 */
    FSlateBrush SectionBrush;

    /** 0 武器，1 怪物。 */
    int32 Section = 0;
    int32 Category = 0;
    FString SelectedId;

    /** 怪物登记表的求值结果缓存：身份与六维在运行期不变，避免每次重建都重新加载类与求值。
     *  键为 FDevelopmentMonsterEntry::Id，值为是否成功登记六维；未登记的条目也缓存，键存在即已求值。 */
    mutable TMap<FName, TPair<bool, FMonsterCoreStats>> MonsterStatsCache;

    float Scale = 1.f;
    float PageWidth = 720.f;

    void RefreshLayout();
    TSharedRef<SWidget> BuildPage();
    TSharedRef<SWidget> BuildTabs();
    TSharedRef<SWidget> BuildGrid();
    TSharedRef<SWidget> BuildDetail();
    TSharedRef<SWidget> Label(const FString& Value, float Pixels, const FLinearColor& Color, bool bNumeric = false, bool bMedium = false) const;
    /** 页签文字：单行不换行，避免等宽窄列把中文逐字竖排。 */
    TSharedRef<SWidget> TabLabel(const FString& Value, bool bActive) const;
    /** 卡片／列表内的左对齐单行文字。 */
    TSharedRef<SWidget> LeftLabel(const FString& Value, float Pixels, const FLinearColor& Color, bool bMedium = false) const;
    /** 数值／单位文字：JetBrains Mono，单行不换行。 */
    TSharedRef<SWidget> ValueLabel(const FString& Value, float Pixels, const FLinearColor& Color, bool bMedium = false) const;
    TSharedRef<SWidget> DetailRow(const FString& Caption, const FString& Value, const FLinearColor& ValueColor) const;
    TSharedRef<SWidget> SectionCard(const FString& Title, const TArray<TSharedRef<SWidget>>& Rows) const;

    /** 当前分类下的档案；网格与详情共用同一过滤，避免数量与内容不一致。 */
    TArray<FCodexEntry> Entries() const;
    TArray<FString> Categories() const;
    FString SectionLabel() const;
    /** 玩家身上的怪物生成登记表；未找到返回空指针（档案仍可列出名称）。 */
    const UDevelopmentSpawnComponent* ResolveSpawner() const;
    /** 按 Definition 从物品目录取显示名，用于过滤器已移除选中条目时的回退。 */
    FString CatalogName(const FString& Definition) const;
    /** 单件武器的栏目归属：all 表示不属于图鉴收录范围（弹药／材料／消耗品等）。 */
    FString WeaponCategoryOf(const FColdSteelItem& Item) const;

    /** 取某怪物身份的六维与品阶（带缓存）；返回 false 表示该身份未登记六维。 */
    bool MonsterStatsOf(const FDevelopmentMonsterEntry& Entry, FMonsterCoreStats& Out) const;

    /** 立绘：武器走背包同一图标工作室，怪物走图鉴专用立绘工作室。两者都是固定正交相机，
     *  朝向与视角统一。返回空表示尚未渲染完成（已排队）或该条目不支持出图。 */
    const FSlateBrush* PortraitBrush(bool bWeapon, const FString& Id) const;
    /** 详情头部的立绘控件：有图显示图，无图显示等宽透明占位（不留空洞、不画假图）。 */
    TSharedRef<SWidget> PortraitFrame(bool bWeapon, const FString& Id) const;
    /** 立绘就绪回调：命中当前选中项时重建详情。 */
    void HandlePortraitReady(const FString& Id);
    /** 请求某条目的立绘：武器走图标工作室，怪物走立绘工作室。 */
    void RequestPortrait(bool bWeapon, const FString& Id) const;

    FReply SelectSection(int32 Index);
    FReply SelectCategory(int32 Index);
    FReply SelectEntry(const FString& Id);
    FReply CloseDetail();

    /** 武器详情：字段直接读物品 Data，缺失显示「—」，不伪造数值。 */
    TArray<TSharedRef<SWidget>> WeaponDetailRows(const FString& Definition) const;
    /** 怪物详情：六维／战力／品阶奖励与运行时同一入口求值。 */
    TArray<TSharedRef<SWidget>> MonsterDetailRows(const FString& MonsterId) const;
};