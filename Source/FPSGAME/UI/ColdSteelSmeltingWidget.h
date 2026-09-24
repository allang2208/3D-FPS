#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelSmeltingWidget.generated.h"

class UBackgroundBlur;
class UBorder;
class UButton;
class UCanvasPanel;
class UCanvasPanelSlot;
class UHorizontalBox;
class UImage;
class UOverlay;
class UProgressBar;
class UScrollBox;
class USizeBox;
class UTextBlock;
class UVerticalBox;
class UVerticalBoxSlot;
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UColdSteelSmeltingSystem;
class UColdSteelSmeltingRowProxy;
class AVoxelBuildWorld;

/**
 * 冶炼面板（Docs/UI/smelting-panel-plan-20260923.md）：只由高炉 E 交互打开的独立右侧面板，
 * 与背包互不连带（2026-09-23 追加需求）；背包同开时贴到抽屉左侧，背包关时贴视口右缘。
 * 上段＝冶炼（炉况卡＋可冶炼矿石＋开始冶炼），下段＝燃料卡（剩余燃料＋添加燃料）。
 * 只做展示与按钮转发：扣料、起炉、结算、写档全部在 UColdSteelSmeltingSystem +
 * UColdSteelStatusModel 的既有事务里（UI-WORKFLOW 第 5 节）。
 */
UCLASS()
class FPSGAME_API UColdSteelSmeltingWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    /** 指向一座已放置的高炉（20 cm 建造格锚格）；换炉子时清选择与状态行。 */
    void SetFurnace(AVoxelBuildWorld* InWorld,FIntVector InCell);
    /** 抽屉布局推送面板宽度（像素），进度条填充按它折算。 */
    void SetLayoutWidth(float PixelsX);
    /** 主题层推送面板左缘的屏幕像素 X（升级弹层贴屏钳制的唯一可信坐标源，2026-09-24 实测
     *  Slate 缓存几何在此层级带固定偏移，不可反推）。 */
    void SetPanelScreenX(float Px);
    /** 行点击代理转发进来的选择（UButton::OnClicked 是动态委托，带不了参数——走工程先例）。 */
    void SelectRecipe(FName Recipe);
    /** 升级页签选择（v10，2026-09-24 用户"三卡压缩成页签，下方详情带显示效果与材料"）：同样走点击代理。 */
    void SelectUpgradeAxis(int32 Axis);
    /** 审计取证：燃料读数行当前文本（倒计时是否真的在逐秒走，2026-09-24 用户"一直显示 10 秒"）。 */
    FString DebugFuelLineText() const;
    /** 审计取证（v10c，2026-09-24 用户"子选项不可切换"）：广播页签真实委托链＋读选中轴。
     *  直接调 handler 测不到代理 GC 失效——必须走 OnClicked→代理→SelectUpgradeAxis 这一整条。
     *  实现在 cpp：头文件里 UButton 只是前向声明，解引用需完整类型。 */
    void DebugClickUpgradeTab(int32 Axis);
    int32 DebugUpgradeSel() const{return UpgSel;}
    // 批量/升级交互入口（面板按钮与审计脚本共用；审计直接调用它们截图取证）。
    UFUNCTION() void HandleBatchMinus();
    UFUNCTION() void HandleBatchPlus();
    UFUNCTION() void HandleUpgradeToggled();
    UFUNCTION() void HandleUpgradeClose();
    UFUNCTION() void HandleUpgradeClicked();          // 速度轴（旧名保留：审计与既有调用）
    UFUNCTION() void HandleUpgradeFuelClicked();      // 燃料仓轴
    UFUNCTION() void HandleUpgradeBatchClicked();     // 每次投料轴

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& MyGeometry,float InDeltaTime) override;

private:
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    /** bWrap：正文/说明行一律允许换行（冷钢正式规则 §3：超长文本换行，不缩字号、不靠裁剪）。 */
    UTextBlock* Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false,bool bWrap=false);
    UButton* Action(const FString& Caption);
    void UpdateScale();
    /** 按主题层推送的屏幕像素重排 Shell/页签/弹层（命中区已扩为全宽画布，坐标全部非负）。 */
    void ApplyScreenLayout();
    /** 升级入口方片的横向摆位（v11，2026-09-24 用户"贴紧零缝＋跟随弹层左缘推到最左"）：
     *  收起态右缘压面板左缘线，展开态随 FlyMotion 同步贴到弹层左缘（左不过屏幕边）。 */
    void LayoutUpgradeTab();
    /** v12（2026-09-24 用户"取消方片与冶炼栏/升级栏的边界，做成其一部分，保留功能"）：
     *  无描边直角填充，颜色跟随所贴主体（收起=冶炼栏 GlassTint，展开=升级栏 Content），钮只留 hover/pressed 反馈。 */
    void ApplyUpgradeTabVisual();
    void RefreshRows();
    void RefreshJob();
    /** 燃料读数行实时化（2026-09-24 用户"下方剩余时间没有实时更新，要性能友好的实时方案"）：
     *  10Hz 的 RefreshJob 只更新锚点（存料/还需烧/挂钟戳），本函数每帧按挂钟外推，
     *  显示整数秒没变就一个字节都不写——每秒至多一次 SetText，稳态零分配零无效化。 */
    void PaintFuelLine();
    /** 升级卡按钮转发：按轴升级这座炉（三轴共用一套卡，2026-09-24 v9）。 */
    void UpgradeAxis(int32 Axis);
    /** 某轴某等级的效果读数文案（"30 分钟"/"×15"/"+50%"）：页签、详情带共用一个口径。 */
    void AxisValueText(int32 Axis,int32 Level,FString& Out) const;
    void RefreshSelection();
    void SetStatus(const FString& Line,bool bError=false);
    const FSlateBrush* IconFor(const FString& Definition);
    UFUNCTION() void HandleStart();
    UFUNCTION() void HandleCollect();
    UFUNCTION() void HandleAddFuel();
    UFUNCTION() void HandleClose();
    /** 每帧动画：冶炼条脉冲亮度＋前沿亮头，燃料条火星粒子（数据刷新仍是 0.1s 节流，动画独立）。 */
    void AnimateBars(float DeltaSeconds);

    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UColdSteelSmeltingSystem> System;
    TWeakObjectPtr<AVoxelBuildWorld> World;
    FIntVector Cell=FIntVector::ZeroValue;
    FDelegateHandle ChangedHandle;

    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<UBorder> HeaderSurface;
    UPROPERTY(Transient) TObjectPtr<USizeBox> HeaderSize;
    UPROPERTY(Transient) TObjectPtr<UBorder> JobCard;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JobTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JobDetail;
    // 上＝冶炼进度（JobCard 内通栏，脉冲），下＝燃料卡（面板底部，火星粒子）；两卡各自通栏。
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> SmeltSection;
    UPROPERTY(Transient) TObjectPtr<UBorder> FuelCard;
    UPROPERTY(Transient) TObjectPtr<USizeBox> BarSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FuelBarSize;
    UPROPERTY(Transient) TObjectPtr<UOverlay> SmeltOverlay;
    UPROPERTY(Transient) TObjectPtr<UOverlay> FuelOverlay;
    // 条＝与 HUD 状态条同款 UProgressBar：轨道与填充共用同一几何，天然贴合、无黑边，
    // 宽度恒＝percent×控件宽，不会溢出卡片（2026-09-24 用户"黑边/燃料条通栏"整改）。
    UPROPERTY(Transient) TObjectPtr<UProgressBar> SmeltBar;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> SmeltCanvas;
    UPROPERTY(Transient) TObjectPtr<UImage> Head;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> FuelBar;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> FuelCanvas;
    // —— 第一批美术升级（2026-09-24 用户选定 A＋B1＋B2＋C）：全部纯装饰绘制，不驱动数据。——
    // A 炉况视觉区：任务中占据列表区（图标→产物＋呼吸光环），补掉中部空窗。
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> Showcase;
    UPROPERTY(Transient) TObjectPtr<USizeBox> ShowInSize;
    UPROPERTY(Transient) TObjectPtr<UImage> ShowInIcon;
    UPROPERTY(Transient) TObjectPtr<USizeBox> ShowOutSize;
    UPROPERTY(Transient) TObjectPtr<UBorder> ShowRing;
    UPROPERTY(Transient) TObjectPtr<UImage> ShowOutIcon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ShowCaption;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SectionTitle;   // "可冶炼矿石"标题（任务中随列表一起收起）
    // B1 流动高光（3 段亮带在填充内往返）＋ B2 完成闪光（一次性亮带扫过）。
    UPROPERTY(Transient) TObjectPtr<UImage> SweepA;
    UPROPERTY(Transient) TObjectPtr<UImage> SweepB;
    UPROPERTY(Transient) TObjectPtr<UImage> SweepC;
    UPROPERTY(Transient) TObjectPtr<UImage> FlashBand;
    // 第二批（2026-09-24 用户"按你建议优化"）：B3 亮头辉光软带＋B4 轨道 25/50/75% 刻度线。
    UPROPERTY(Transient) TObjectPtr<UImage> HeadGlow;
    UPROPERTY(Transient) TArray<TObjectPtr<UImage>> BarTicks;
    // C 锚点：炉况卡图标、燃料卡木材图标、取出按钮绿色呼吸描边。
    UPROPERTY(Transient) TObjectPtr<USizeBox> JobIconSize;
    UPROPERTY(Transient) TObjectPtr<UImage> JobIcon;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FuelIconSize;
    UPROPERTY(Transient) TObjectPtr<UImage> FuelIcon;
    UPROPERTY(Transient) TObjectPtr<UBorder> CollectGlow;
    UPROPERTY(Transient) TArray<TObjectPtr<UImage>> EmberImages;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JobTime;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FuelTime;
    UPROPERTY(Transient) TObjectPtr<UButton> AddFuelButton;
    UPROPERTY(Transient) TObjectPtr<USizeBox> AddFuelSize;
    UPROPERTY(Transient) TObjectPtr<UButton> CollectButton;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> RowsScroll;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> RowsBox;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RowsEmpty;
    UPROPERTY(Transient) TObjectPtr<UButton> StartButton;
    UPROPERTY(Transient) TObjectPtr<USizeBox> StartSize;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLine;
    // 留白归属这些槽：DPI/视口变化时在 UpdateScale 里统一重算（§3 分区留白条款）。
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> BodySlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> StartSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> StatusSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> FuelSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> FooterSlot;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> IconTextures;
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelSmeltingRowProxy>> RowProxies;
    // 升级页签代理：必须与配方行缓存分家——RowProxies 每次 RefreshRows 重建会 Reset，
    // 混存会让页签代理被 GC 收掉、AddDynamic 静默失效（2026-09-24 用户"子选项不可切换"）。
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelSmeltingRowProxy>> UpgProxies;

    FName SelectedRecipe;
    float Scale=1.f,LayoutWidth=0.f,RefreshAccum=0.f;
    // —— 每帧动画缓存：数据侧 0.1s 节流写这里，AnimateBars 每帧读（刷新与动画解耦）。——
    float AnimTime=0.f;                                   // 动画秒表（面板打开期间单调递增）
    float AnimSmeltT=0.f,AnimFuelRatio=0.f;               // 0..1 进度/燃料占比
    float SmeltFillPx=0.f,FuelFillPx=0.f;   // 亮头/火星参照宽（AnimateBars 按缓存几何算，单位系）
    bool bBurning=false,bFuelAlive=false;                 // 脉冲/火星的开关（停炉与空燃料不画动效）
    float FlashT=-1.f;                                    // 完成闪光进度 0..1（<0＝未触发）
    bool bWasDone=false;                                  // 完成沿检测（只在"转完成"那一拍触发闪光）
    // —— 燃料行倒计时锚点（PaintFuelLine）：RefreshJob 每 0.1s 校准，帧间纯挂钟外推。——
    double CdFuel=0.0,CdNeed=0.0,CdStamp=0.0;             // 存料秒/还需烧秒/取样挂钟秒
    bool bCdBurning=false,bCdRunning=false;               // 烧燃中才外推；任务态决定文案分支
    int32 CdLastBranch=-1,CdLastFuelSec=-1,CdLastNeedSec=-1;   // 变化门控（-1＝强制重绘）
    // —— 批量冶炼＋炉体升级（2026-09-24 用户"是否有批量冶炼功能…升级二字小方块…左方弹出升级界面"）——
    int64 Batch=1;                                        // 面板暂存的批量数（随持有量夹取，投料成功后保留）
    bool bUpgradeOpen=false;
    float FlyMotion=0.f;                                  // 升级弹层滑入进度（同款 4.0/s，NativeTick 驱动）
    float PanelScreenPx=-1.f;                             // 面板左缘屏幕像素（主题层推送）
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> BatchRow;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BatchText;
    UPROPERTY(Transient) TObjectPtr<UButton> BatchMinus;
    UPROPERTY(Transient) TObjectPtr<UButton> BatchPlus;
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeTab;   // 左缘竖排页签（36×60，"升/级"）
    UPROPERTY(Transient) TObjectPtr<UButton> UpgradeTabBtn;// v12：页签本体钮（无描边样式随状态/Scale 重建）
    bool bTabVisualOpen=false;                             // 已应用外观的展开态（变化才重建画刷）
    UPROPERTY(Transient) TObjectPtr<UBorder> UpgradeFlyout;// 独立升级页（与冶炼栏同尺寸，右缘钉缝展开）
    UPROPERTY(Transient) TObjectPtr<UBorder> FlyHeadSurf;  // 升级页头部底色（与面板 HeaderSurface 同款）
    // 三轴页签＋下方详情带（v10，下标＝VoxelFurnaceAxis*；2026-09-24 用户定案）：
    // 页签＝整行可选（名称 14，选中 Medium＋Accent 描边同款配方行），效果/材料移到卡列下方的详情带。
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> UpgTabs;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> UpgTabSurfs;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabNames;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> UpgTabLv;
    // 面板左缘的升级入口小方片（2026-09-24 用户"两个字居中放进方片、贴紧冶炼栏零缝；
    // 展开后跟随弹层左缘推到最左、文案换收回，点击收回＝关闭升级栏"）。
    UPROPERTY(Transient) TObjectPtr<UTextBlock> UpgradeTabText;
    UPROPERTY(Transient) TObjectPtr<UBorder> FlyDetail;        // 详情带卡面（StatusCard 同款）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyDetailName; // 轴名 16 Medium
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyDetailLv;   // Lv.N / Max 12
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyRuleSize;     // 细线分区（1px）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyFx;         // 升级效果"当前→下一级" 16 NumberFont
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> FlyMatRow; // 所需材料行（图标＋名称＋需＋持有/差额）
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyMatIconSize;  // 材料图标 28²（与任务图标同档）
    UPROPERTY(Transient) TObjectPtr<UImage> FlyMatIcon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyMatValue;   // "×N" 16 NumberFont（不足标 Warning）
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyMatOwned;   // "持有 M · 还差 D" 12
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyNoMat;      // 满级时替代材料行的提示
    UPROPERTY(Transient) TObjectPtr<UButton> FlyBtn;           // 详情带底部的标准 36px 升级钮
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FlyBtnText;
    UPROPERTY(Transient) TObjectPtr<USizeBox> FlyBtnSize;
    int32 UpgSel=0;                                             // 当前选中轴（默认＝冶炼速度）
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeTabSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> UpgradeFlySlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ShellSlot;
    struct FEmber{float Phase=0.f,Speed=0.f,Seed=0.f,Size=3.f;};   // 粒子：沿填充区漂流参数
    TArray<FEmber> Embers;
    FString RowsSignature;
    struct FRow {TWeakObjectPtr<UButton> Button;TWeakObjectPtr<UBorder> Card;FName Recipe;};
    TArray<FRow> Rows;
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UButton>> StyledButtons;
    TMap<FString,FSlateBrush> IconBrushes;
    TSet<FString> FailedIcons;
    friend class UColdSteelSmeltingRowProxy;
};

/** 行点击代理：UButton::OnClicked 是动态无参委托，按工程先例（UVoxelBuildCardProxy）
 *  用一个小 UObject 携带"这行选哪个配方"，点击时转发回面板。 */
UCLASS()
class UColdSteelSmeltingRowProxy : public UObject
{
    GENERATED_BODY()
public:
    UFUNCTION() void Clicked();
    UFUNCTION() void AxisClicked();   // 升级页签（v10）：Axis 携带"这行选哪条轴"
    TWeakObjectPtr<UColdSteelSmeltingWidget> Panel;
    int32 Axis=0;
    FName Recipe;
};
