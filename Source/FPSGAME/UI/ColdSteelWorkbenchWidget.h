#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelWorkbenchWidget.generated.h"

class UBackgroundBlur;
class UBorder;
class UButton;
class UCanvasPanel;
class UCanvasPanelSlot;
class UHorizontalBox;
class UImage;
class UScrollBox;
class USizeBox;
class UTextBlock;
class UVerticalBox;
class UVerticalBoxSlot;
class UColdSteelHUDWidget;
class UColdSteelWorkbenchRowProxy;
class AVoxelBuildWorld;

/**
 * 工作台制作面板（Docs/UI/workbench-panel-plan-20260924.md）：由工作台 E 交互打开，
 * 外壳、尺寸、贴位与左缘「升级」页签＋同尺寸弹层**逐参数复刻** UColdSteelSmeltingWidget
 * 最新定稿格式（2026-09-24 v10 三轴页签＋下方详情带；v11 页签跟缝展开；v11c 竖排"升/收回"
 * 居中；v10c 页签代理与行缓存分家）。动画构建同款：FlyMotion 4.0/s＋EaseSmooth 右缘钉缝
 * 横展、方片逐帧随弹层左缘、数据侧 0.1s 节流与每帧动画解耦。
 * 本次只有外壳与占位内容：制作列表区恒空态、开始按钮禁用、升级页签/详情带为同构占位——
 * 升级轴名、数值、材料与事务后续设计时按注释处接入；面板不做任何业务（UI-WORKFLOW 第 5 节）。
 * 与冶炼面板共用背包抽屉左缘的贴位，二者互斥（HUD 开一收另一）。
 */
UCLASS()
class FPSGAME_API UColdSteelWorkbenchWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    /** 指向一座已放置的工作台（20 cm 建造格锚格）；换台时收起升级弹层并归零页签选择（同冶炼换炉口径）。 */
    void SetWorkbench(AVoxelBuildWorld* InWorld,FIntVector InCell);
    /** 抽屉布局推送面板宽度（像素），弹层与面板同宽按它折算。 */
    void SetLayoutWidth(float PixelsX);
    /** 主题层推送面板左缘的屏幕像素 X（页签/弹层贴缝钳制的唯一可信坐标源，
     *  继承冶炼 §7.7：Slate 缓存几何在本层级带固定偏移，不可反推）。 */
    void SetPanelScreenX(float Px);
    /** 升级页签选择：同样走点击代理（UButton::OnClicked 动态委托带不了参数——工程先例）。
     *  公开供代理回调，与冶炼 SelectUpgradeAxis 同构。 */
    void SelectUpgradeAxis(int32 Axis);
    /** 审计取证（同冶炼 v10c）：广播页签真实委托链＋读选中轴——直接调 handler 测不到代理失效。 */
    void DebugClickUpgradeTab(int32 Axis);
    int32 DebugUpgradeSel() const{return UpgSel;}
    UFUNCTION() void HandleUpgradeToggled();
    UFUNCTION() void HandleUpgradeClose();
    UFUNCTION() void HandleUpgradeClicked();   // 详情带升级钮：占位（工作台升级事务后续设计）

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& MyGeometry,float InDeltaTime) override;

private:
    UFUNCTION() void HandleClose();
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    /** bWrap：正文/说明行一律允许换行（冷钢正式规则 §3：超长文本换行，不缩字号、不靠裁剪）。 */
    UTextBlock* Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false,bool bWrap=false);
    UButton* Action(const FString& Caption);
    void UpdateScale();
    /** 按主题层推送的屏幕像素重排 Shell/页签/弹层（命中区已扩为全宽画布，坐标全部非负）。 */
    void ApplyScreenLayout();
    /** 升级入口方片的横向摆位（冶炼 v11 同款）：收起态右缘压面板左缘缝 2px，
     *  展开态随 FlyMotion 同曲线贴弹层左缘推到最左（左不过屏幕边）。 */
    void LayoutUpgradeTab();
    /** 升级页签/详情带刷新（占位数据版）：页签高亮、"升/收回"文案与详情带文案统一从这里走，
     *  与冶炼同一入口口径（升级轴上线时替换轴名/Lv/效果/材料四处即可）。 */
    void RefreshUpgrade();

    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    TWeakObjectPtr<AVoxelBuildWorld> World;
    FIntVector Cell=FIntVector::ZeroValue;
    float Scale=1.f;
    float LayoutWidth=-1.f;      // 主题层推送的屏幕像素（＝冶炼面板同款宽）
    float PanelScreenPx=-1.f;    // 面板左缘屏幕像素（ApplyScreenLayout 的唯一坐标源）
    bool bUpgradeOpen=false;
    float FlyMotion=0.f;         // 弹层展开进度（与冶炼同款 4.0/s＋EaseSmooth，右缘钉缝）
    float RefreshAccum=0.f;      // 数据侧 0.1s 节流（与每帧动画解耦，冶炼同构）
    int32 UpgSel=0;              // 当前选中页签（占位三轴下标，后续设计定默认轴）

    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> RootCanvas;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ShellSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeTabSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeFlySlot;
    UPROPERTY(Transient) TObjectPtr<UBorder> Shell;
    UPROPERTY(Transient) TObjectPtr<UBorder> HeaderSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> StatusCard;
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeTab;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> UpgradeTabText;   // 竖排"升/级"⇄"收/回"（冶炼 v11c 同款）
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeFlyout;
    UPROPERTY(Transient) TObjectPtr<UBorder> FlyHeadSurf;
    UPROPERTY(Transient) TObjectPtr<USizeBox> HeaderSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyHeadSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> IconSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> StartSize;
    UPROPERTY(Transient) TObjectPtr<UImage> IconImage;   // 状态卡图标位（内容后续设计，先收起占位）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RowsEmpty;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLine;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Footer;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> RowsScroll;
    UPROPERTY(Transient) TObjectPtr<UButton> StartButton;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> BodySlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> StartSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> StatusSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> FooterSlot;
    // —— 升级页签行＋详情带（冶炼 v10 同构，占位内容）——
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> UpgTabs;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> UpgTabSurfs;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabNames;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabLv;
    // 页签代理与（未来的）行缓存分家常驻引用——冶炼 v10c 教训：混存会被列表重建 Reset 掉
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
    friend class UColdSteelWorkbenchRowProxy;
};

/** 升级页签点击代理（冶炼 UColdSteelSmeltingRowProxy 同款小 UObject）：OnClicked 是动态无参委托，
 *  用它携带"这行选哪个升级页签"转发回面板。工作台升级轴上线前保持占位可切换。 */
UCLASS()
class UColdSteelWorkbenchRowProxy : public UObject
{
    GENERATED_BODY()
public:
    UFUNCTION() void AxisClicked();
    TWeakObjectPtr<UColdSteelWorkbenchWidget> Panel;
    int32 Axis=0;
};
