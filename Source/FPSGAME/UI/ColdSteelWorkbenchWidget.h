#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelWorkbenchWidget.generated.h"

class UBackgroundBlur;
class UBorder;
class UButton;
class UCanvasPanel;
class UCanvasPanelSlot;
class UComboBoxString;
class UGridPanel;
class UGridSlot;
class UHorizontalBox;
class UImage;
class UScaleBox;
class UScrollBox;
class USizeBox;
class UTextBlock;
class UTexture2D;
class UVerticalBox;
class UVerticalBoxSlot;
class UHorizontalBoxSlot;
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UColdSteelCraftingSystem;
class UColdSteelWorkbenchRowProxy;
class UColdSteelGunRecipeOptionWidget;
struct FColdSteelCraftingRecipe;
class AVoxelBuildWorld;

/**
 * 工作台制作面板（Docs/UI/workbench-panel-plan-20260924.md ＋
 * Docs/UI/workbench-crafting-system-plan-20260925.md 制造系统接入轮）：由工作台 E 交互打开。
 * 2026-09-28 复制升级：版面与规格**逐参数对齐打铁栏/枪械装配栏**（Docs/UI/forging-panel-plan-20260926.md
 * ＋ gun-assembly-catalog-and-desktop-20260928.md）——全宽抽屉（与背包等宽、零缝拼接、上下 12px）、
 * 磨砂外壳、20px 标题、16px 分区标题、14px 正文、12px 辅助、36px 按钮、材料三列表格；
 * 配方选择由行卡列表改为打铁同款 ComboBox，成品预览＝图标＋参数双列（读浮窗摘要口径），
 * 卡片列在 ScrollBox 内滚动，批量/状态/主操作固定页脚（HeaderTint 带）。
 * 左缘「升级」页签＋同尺寸弹层沿用冶炼 v10-v12b 结构不动；枪械工作台模式已由
 * UColdSteelGunAssemblyWidget 接管，本面板的枪械分支（ColdSteelGunWorkbench.cpp）随本轮删除。
 * 与冶炼面板共用背包抽屉左缘的贴位，二者互斥（HUD 开一收另一）。
 */
UCLASS()
class FPSGAME_API UColdSteelWorkbenchWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    /** 指向一座已放置的工作台（20 cm 建造格锚格）。 */
    void SetWorkbench(AVoxelBuildWorld* InWorld,FIntVector InCell);
    /** 抽屉布局推送面板宽度（像素），弹层与面板同宽按它折算。 */
    void SetLayoutWidth(float PixelsX);
    /** 主题层推送面板左缘的屏幕像素 X（页签/弹层贴缝钳制的唯一可信坐标源，
     *  继承冶炼 §7.7：Slate 缓存几何在本层级带固定偏移，不可反推）。 */
    void SetPanelScreenX(float Px);
    void SetInputReady(bool bReady);
    /** 升级页签选择：同样走点击代理（UButton::OnClicked 动态委托带不了参数——工程先例）。
     *  公开供代理回调，与冶炼 SelectUpgradeAxis 同构。 */
    void SelectUpgradeAxis(int32 Axis);
    /** 审计取证（同冶炼 v10c）：广播页签真实委托链＋读选中轴——直接调 handler 测不到代理失效。 */
    void DebugClickUpgradeTab(int32 Axis);
    int32 DebugUpgradeSel() const{return UpgSel;}
    // 批量/制作交互入口（面板按钮与审计脚本共用；审计直接调用它们截图取证）。
    UFUNCTION() void HandleBatchMinus();
    UFUNCTION() void HandleBatchPlus();
    UFUNCTION() void HandleUpgradeToggled();
    UFUNCTION() void HandleUpgradeClose();
    UFUNCTION() void HandleUpgradeClicked();   // 详情带升级钮：占位（工作台升级事务后续设计）

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& MyGeometry,float InDeltaTime) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event) override;

private:
    UFUNCTION() void HandleClose();
    UFUNCTION() void HandleCraft();
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    /** bWrap：正文/说明行一律允许换行（冷钢正式规则 §3：超长文本换行，不缩字号、不靠裁剪）。 */
    UTextBlock* Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false,bool bWrap=false);
    UButton* Action(const FString& Caption);
    void UpdateScale();
    /** 按主题层推送的屏幕像素重排 Shell/页签/弹层（命中区已扩为全宽画布，坐标全部非负）。 */
    void ApplyScreenLayout();
    /** 升级入口方片的横向摆位（冶炼 v11 同款）：收起态右缘压面板左缘缝 1px（v12 无描边口径），
     *  展开态随 FlyMotion 同曲线贴弹层左缘推到最左（左不过屏幕边）。 */
    void LayoutUpgradeTab();
    /** v12（冶炼 §7.23 同款）：方片无描边直角填充，颜色跟随所贴主体
     *  （收起=制作栏 GlassTint，展开=升级栏 Content），钮只留 hover/pressed 反馈。 */
    void ApplyUpgradeTabVisual();
    /** 升级页签/详情带刷新（占位数据版）：页签高亮、"升/收回"文案与详情带文案统一从这里走，
     *  与冶炼同一入口口径（升级轴上线时替换轴名/Lv/效果/材料四处即可）。 */
    void RefreshUpgrade();
    void RefreshJob();
    /** 成品预览（打铁 RefreshProductPreview 同构）：产物浮窗摘要 → 双列参数表，配方切换时才重建。 */
    void RefreshPreview(const FColdSteelCraftingRecipe* Recipe);
    void SetStatus(const FString& Line,bool bError=false);
    const FSlateBrush* IconFor(const FString& Definition);
    FString DefinitionName(const FString& Definition) const;
    /** 材料读数"木材 ×1 · 石头 ×2"（状态行/结算行共用一个口径；InBatch 乘进计数）。 */
    FString InputsText(const FColdSteelCraftingRecipe& R,int64 InBatch) const;
    // —— 打铁/装配同款构件助手（打铁 ColdSteelForgingWidget 逐参数复刻）——
    UButton* Button(const FString& Caption,UTextBlock*& Label);
    UVerticalBox* Card(UVerticalBox* Parent);
    void Space(UVerticalBoxSlot* RowSlot,FMargin RowPadding);
    void AddMaterialCell(UWidget* Widget,int32 Row,int32 Column);
    void EnsureMaterialRows(int32 Count);
    UFUNCTION() void HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType);
    UFUNCTION() UWidget* GenerateRecipeOption(FString Option);
    void UpdatePreviewLayout();
    void RefreshActions();
    void RefreshDataChanged();

    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UColdSteelCraftingSystem> Crafting;
    TWeakObjectPtr<AVoxelBuildWorld> World;
    FIntVector Cell=FIntVector::ZeroValue;
    FDelegateHandle ChangedHandle;
    float Scale=1.f;
    float BoardHeight=0.f;       // 成品预览双列高度（随视口夹取，打铁同款公式）
    float LayoutWidth=-1.f;      // 主题层推送的屏幕像素（＝面板同宽）
    float PanelScreenPx=-1.f;    // 面板左缘屏幕像素（ApplyScreenLayout 的唯一坐标源）
    bool bUpgradeOpen=false;
    float FlyMotion=0.f;         // 弹层展开进度（与冶炼同款 4.0/s＋EaseSmooth，右缘钉缝）
    float RefreshAccum=0.f;      // 数据侧 0.1s 节流（与每帧动画解耦，冶炼同构）
    int32 UpgSel=0;              // 当前选中页签（占位三轴下标，后续设计定默认轴）
    FName SelectedRecipe;
    int64 Batch=1;               // 面板暂存的批量数（随可制作份数夹取，制作成功后保留）

    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> RootCanvas;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ShellSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeTabSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeFlySlot;
    UPROPERTY(Transient) TObjectPtr<UBorder> Shell;
    UPROPERTY(Transient) TObjectPtr<UBorder> HeaderSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeTab;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> UpgradeTabText;   // 竖排"升/级"⇄"收/回"（冶炼 v11c 同款）
    UPROPERTY(Transient) TObjectPtr<UButton> UpgradeTabBtn;       // v12：方片本体钮（无描边样式随状态/Scale 重建）
    bool bTabVisualOpen=false;                                    // 已应用外观的展开态（变化才重建画刷）
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeFlyout;
    UPROPERTY(Transient) TObjectPtr<UBorder> FlyHeadSurf;
    UPROPERTY(Transient) TObjectPtr<USizeBox> HeaderSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyHeadSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> StartSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> CloseSize;          // 打铁同款：关闭钮 36px 方钮
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLine;
    // —— 打铁/装配同款中段：Scroll → Body → 卡列（配方/状态/成品预览/操作说明）——
    UPROPERTY(Transient) TObjectPtr<UScrollBox> Scroll;
    UPROPERTY(Transient) TObjectPtr<UBorder> Body;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RecipeTitle;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> RecipeChoice;
    UPROPERTY(Transient) TObjectPtr<USizeBox> RecipeChoiceSize;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Materials;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> MaterialSource;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> MaterialGrid;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> MaterialQuantityHeader;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stats;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatLegend;
    UPROPERTY(Transient) TObjectPtr<USizeBox> BoardSize;          // 成品预览双列容器（高度随视口夹取）
    UPROPERTY(Transient) TObjectPtr<UBorder> PreviewParameterCard;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> PreviewParameterSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewStage;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> PreviewParameterGrid;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewScope;
    UPROPERTY(Transient) TObjectPtr<USizeBox> IconFrameSize;      // 左列产物图标（ScaleToFit 等比居中）
    UPROPERTY(Transient) TObjectPtr<UBorder> IconFrameBorder;     // 左列载体（右缝 4px 随 Scale 重排）
    UPROPERTY(Transient) TObjectPtr<UScaleBox> IconScale;
    UPROPERTY(Transient) TObjectPtr<UImage> PreviewIcon;
    UPROPERTY(Transient) TObjectPtr<UBorder> FooterBand;          // HeaderTint 页脚带：状态＋批量＋主操作
    UPROPERTY(Transient) TObjectPtr<UButton> StartButton;
    // 居中批量步进行（2026-09-25）：[−][读数][＋] 整体 HAlign_Center，进页脚带。
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> BatchRow;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> BatchRowSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BatchText;
    UPROPERTY(Transient) TObjectPtr<UButton> BatchMinus;
    UPROPERTY(Transient) TObjectPtr<UButton> BatchPlus;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> BodySlot;
    // —— 升级页签行＋详情带（冶炼 v10 同构，占位内容）——
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> UpgTabs;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> UpgTabSurfs;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabNames;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabLv;
    // 页签代理与行缓存分家常驻引用——冶炼 v10c 教训：混存会被列表重建 Reset 掉
    // 代理引用、AddDynamic 静默失效（"子选项不可切换"的根因）。
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelWorkbenchRowProxy>> UpgProxies;
    UPROPERTY(Transient) TObjectPtr<UBorder> FlyDetail;        // 详情带卡面（StatusCard 同款）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyDetailName; // 轴名 16 Medium
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyDetailLv;   // Lv.N / Max 12
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyRuleSize;     // 细线分区（1px）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyFx;         // 升级效果"当前→下一级" 16 NumberFont
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> FlyMatRow; // 所需材料行（图标＋名称＋需＋持有/差额）
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyMatIconSize;  // 材料图标 28²
    UPROPERTY(Transient) TObjectPtr<UImage> FlyMatIcon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyMatValue;   // "×N" 16 NumberFont
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyMatOwned;   // "持有 M · 还差 D" 12
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyNoMat;      // 占位说明（替代材料行，内容后续设计）
    UPROPERTY(Transient) TObjectPtr<UButton> FlyBtn;           // 详情带底部的标准 36px 升级钮
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyBtnText;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyBtnSize;
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UButton>> StyledButtons;
    // —— 打铁/装配同款缓存数组：UpdateScale 统一按 Scale 重排 ——
    TArray<TWeakObjectPtr<UBorder>> Cards;                                    // StatusCard 卡面（12px 内沿）
    TArray<TWeakObjectPtr<UButton>> Buttons;                                  // 标准钮（样式＋内容 padding 12/4）
    UPROPERTY(Transient) TArray<TObjectPtr<USizeBox>> ButtonSizes;            // 36px 动作高度
    struct FRowSpacing {TWeakObjectPtr<UVerticalBoxSlot> Slot;FMargin Padding;};
    TArray<FRowSpacing> RowSpacings;                                          // 卡内行距缓存
    struct FMaterialRow
    {
        TWeakObjectPtr<UTextBlock> Name;
        TWeakObjectPtr<UHorizontalBox> Amount;
        TWeakObjectPtr<UTextBlock> Owned,Separator,Required,State;
    };
    TArray<FMaterialRow> MaterialRows;                                        // 材料三列表（打铁同款）
    UPROPERTY(Transient) TArray<TObjectPtr<UGridSlot>> MaterialCellSlots;
    UPROPERTY(Transient) TArray<TObjectPtr<UGridSlot>> PreviewCellSlots;      // 参数两列表（打铁同款）
    struct FPreviewRow {TWeakObjectPtr<UTextBlock> Name,Value;};
    TArray<FPreviewRow> PreviewRows;
    FString PreviewRecipe;                                                    // 预览签名：配方没换不重建
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> IconTextures;
    TMap<FString,FSlateBrush> IconBrushes;
    TSet<FString> FailedIcons;
    friend class UColdSteelWorkbenchRowProxy;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PanelTitle;
    // Append layout members: other HUD translation units retain the existing field offsets.
    UPROPERTY(Transient) TObjectPtr<UBorder> ShellOutline;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> PreviewLayout;
    UPROPERTY(Transient) TObjectPtr<UGridSlot> PreviewIconSlot;
    UPROPERTY(Transient) TObjectPtr<UGridSlot> PreviewDetailsSlot;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> PreviewScroll;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewEmpty;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BatchStat;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OutputStat;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CraftHint;
    TArray<TWeakObjectPtr<UColdSteelGunRecipeOptionWidget>> RecipeOptionWidgets;
    bool bInputReady=false,bDataDirty=true,bPreviewDirty=true,bCanCraft=false;
    bool bPreviewStacked=false;
    int64 MaxBatch=0;
    FString CraftReason;
};

/** 页签点击代理（冶炼 UColdSteelSmeltingRowProxy 同款小 UObject）：OnClicked 是动态无参委托，
 *  用它携带"这条升级页签是哪一轴"转发回面板。 */
UCLASS()
class UColdSteelWorkbenchRowProxy : public UObject
{
    GENERATED_BODY()
public:
    UFUNCTION() void AxisClicked();
    TWeakObjectPtr<UColdSteelWorkbenchWidget> Panel;
    int32 Axis=0;
};
