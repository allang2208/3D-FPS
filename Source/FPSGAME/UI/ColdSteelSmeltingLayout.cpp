#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelCampfirePanel.h"
#include "ColdSteelSmeltingPresentation.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

#include "ColdSteelSmeltingLayoutPrivate.h"
using namespace ColdSteelSmeltingLayoutPrivate;
using namespace ColdSteelSmeltingPresentation;

void UColdSteelSmeltingWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Scale=ColdSteelUI::PixelScale(this);
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    System=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
    // 根＝Canvas：主题层把本 widget 槽位扩到屏幕左缘→面板右缘的全宽命中区（2026-09-24 修复：
    // 挂在父边界外的负坐标子控件能绘制但收不到点击，页签曾被点穿导致整套 UI 关闭），
    // Shell 用正偏移贴到面板位，页签/弹层坐标一律以屏幕像素折算、全部落在槽位内。
    auto* RootCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=RootCanvas;
    // 全宽命中区画布：本体必须 SelfHitTestInvisible——透明区放行世界点击、子控件照常命中。
    // （HitTestInvisible 会连整个子树一起屏蔽命中，2026-09-24 页签与全部按钮点不动的根因。）
    RootCanvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    // 外壳三段式（与仓库/背包同源）：描边 Border → 真实 UBackgroundBlur → 玻璃 Tint → 内容。
    auto* Shell=WidgetTree->ConstructWidget<UBorder>();
    Shell->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,GunsmithUI::Edge,1/Scale));
    Shell->SetPadding(FMargin(1/Scale));
    ShellSlot=RootCanvas->AddChildToCanvas(Shell);
    ShellSlot->SetAnchors(FAnchors(0,0,1,1));ShellSlot->SetOffsets(FMargin(0));
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetCornerRadius(FVector4(10,10,10,10));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    Shell->SetContent(Blur);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();
    Tint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));
    Tint->SetPadding(FMargin(0));Blur->SetContent(Tint);
    StationPanels=WidgetTree->ConstructWidget<UWidgetSwitcher>();Tint->SetContent(StationPanels);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();StationPanels->AddChild(Stack);

    HeaderSurface=WidgetTree->ConstructWidget<UBorder>();
    HeaderSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Stack->AddChildToVerticalBox(HeaderSurface);
    HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSurface->SetContent(HeaderSize);
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    // 顶栏＝标题（20px Medium 档）＋ × 关闭：面板独立于背包后需要自带出口（Esc 同效）。
    StationTitle=Text(TEXT("冶炼"),20,ColdSteelUI::TextPrimary,false,true);
    auto* TitleSlot=Heading->AddChildToHorizontalBox(StationTitle);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    auto* PanelClose=Action(TEXT("×"));
    PanelClose->OnClicked.AddDynamic(this,&ThisClass::HandleClose);
    Heading->AddChildToHorizontalBox(PanelClose)->SetVerticalAlignment(VAlign_Center);

    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();
    BodySlot=Stack->AddChildToVerticalBox(Body);BodySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    // —— 炉内状态卡（StatusCard 8px）——
    JobCard=WidgetTree->ConstructWidget<UBorder>();
    JobCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    Body->AddChildToVerticalBox(JobCard)->SetPadding(FMargin(0,0,0,10/Scale));
    auto* JobStack=WidgetTree->ConstructWidget<UVerticalBox>();JobCard->SetContent(JobStack);
    // C 锚点：标题左侧 28px 图标＝当前炉料（选中/在炼的输入矿），空炉无料时收起。
    auto* JobHeader=WidgetTree->ConstructWidget<UHorizontalBox>();
    JobStack->AddChildToVerticalBox(JobHeader)->SetPadding(FMargin(0,0,0,6/Scale));
    JobIconSize=WidgetTree->ConstructWidget<USizeBox>();
    JobIconSize->SetWidthOverride(28/Scale);JobIconSize->SetHeightOverride(28/Scale);
    JobHeader->AddChildToHorizontalBox(JobIconSize)->SetVerticalAlignment(VAlign_Center);
    JobIcon=WidgetTree->ConstructWidget<UImage>();JobIcon->SetVisibility(ESlateVisibility::Collapsed);
    JobIconSize->SetContent(JobIcon);
    JobTitle=Text(TEXT("炉内空闲"),16,ColdSteelUI::TextTertiary,false,true);
    auto* JobTitleSlot=JobHeader->AddChildToHorizontalBox(JobTitle);
    JobTitleSlot->SetPadding(FMargin(10/Scale,0,0,0));JobTitleSlot->SetVerticalAlignment(VAlign_Center);
    JobDetail=Text(TEXT("从下方选择原料投料"),12,ColdSteelUI::TextTertiary,false,false,true);
    JobStack->AddChildToVerticalBox(JobDetail)->SetPadding(FMargin(0,0,0,8/Scale));
    // —— 上段·冶炼进度条（通栏）：燃烧时脉冲提亮＋前沿亮头。5px 版用户反馈"太细不明显"，加粗到 12px。
    // 2026-09-23 拆分：燃料不再与它同排双列，移到面板底部的独立燃料卡（FuelCard）。
    SmeltSection=WidgetTree->ConstructWidget<UVerticalBox>();
    JobStack->AddChildToVerticalBox(SmeltSection)->SetPadding(FMargin(0,0,0,6/Scale));
    ProgressTitle=Text(TEXT("冶炼进度"),12,ColdSteelUI::TextTertiary);
    SmeltSection->AddChildToVerticalBox(ProgressTitle);
    BarSize=WidgetTree->ConstructWidget<USizeBox>();BarSize->SetHeightOverride(12/Scale);
    SmeltSection->AddChildToVerticalBox(BarSize)->SetPadding(FMargin(0,4/Scale,0,0));
    SmeltOverlay=WidgetTree->ConstructWidget<UOverlay>();SmeltOverlay->SetVisibility(ESlateVisibility::HitTestInvisible);
    BarSize->SetContent(SmeltOverlay);
    // 与 HUD 状态条（已验收）同款 UProgressBar：轨道/填充共用同一几何 → 无黑边；
    // percent 驱动宽度 → 不溢出。手拼 Border+SizeBox+Image 的旧结构实测填充塌高且越界。
    SmeltBar=WidgetTree->ConstructWidget<UProgressBar>();
    {
        FProgressBarStyle Style;
        Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6.f/Scale,FLinearColor::Transparent,0));
        Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,6.f/Scale,FLinearColor::Transparent,0));
        SmeltBar->SetWidgetStyle(Style);
    }
    SmeltBar->SetFillColorAndOpacity(SmeltingProgressColor(0.f));
    SmeltBar->SetPercent(0.f);SmeltBar->SetVisibility(ESlateVisibility::HitTestInvisible);
    // UOverlaySlot 默认 HAlign_Left/VAlign_Top：不显式 Fill 条就只有 brush desired 的 20px 小点。
    if(auto* BarSlot=SmeltOverlay->AddChildToOverlay(SmeltBar)){BarSlot->SetHorizontalAlignment(HAlign_Fill);BarSlot->SetVerticalAlignment(VAlign_Fill);}
    // 前沿亮头叠在画布上：AnimateBars 每帧挪位置、按正弦调透明度（脉冲的"读秒"部分）。
    SmeltCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();SmeltCanvas->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(auto* CanvasSlot=SmeltOverlay->AddChildToOverlay(SmeltCanvas)){CanvasSlot->SetHorizontalAlignment(HAlign_Fill);CanvasSlot->SetVerticalAlignment(VAlign_Fill);}
    Head=WidgetTree->ConstructWidget<UImage>();
    Head->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,3.f/Scale,FLinearColor::Transparent,0));
    Head->SetColorAndOpacity(FLinearColor(1,1,1,0));Head->SetVisibility(ESlateVisibility::Collapsed);
    if(auto* HeadSlot=SmeltCanvas->AddChildToCanvas(Head))HeadSlot->SetSize(FVector2D(7/Scale,12/Scale));
    // B1 三段亮带（8/20/8，α .06/.16/.06 假渐变）在填充区内往返；B2 完成闪光＝一条宽带扫全条。
    // 画布不裁剪，位置全部数学钳制在 [0, 填充宽-带宽]，永不越出条外。
    auto MakeBand=[&](float Alpha)->UImage*
    {
        auto* B=WidgetTree->ConstructWidget<UImage>();
        B->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,3.f/Scale,FLinearColor::Transparent,0));
        B->SetColorAndOpacity(FLinearColor(1,1,1,Alpha));B->SetVisibility(ESlateVisibility::Collapsed);
        SmeltCanvas->AddChildToCanvas(B);return B;
    };
    SweepA=MakeBand(.06f);SweepB=MakeBand(.16f);SweepC=MakeBand(.06f);FlashBand=MakeBand(0.f);
    // B3 亮头辉光：跟在 7px 亮头后的 16px 软带，透明度随脉冲呼吸（同画布同坐标系，天然在条内）。
    HeadGlow=MakeBand(0.f);
    // B4 轨道刻度：25/50/75% 三条 1px 低亮刻线，填充与空轨都可见，给进度一个"几分之几"的锚。
    auto MakeTick=[&]()->UImage*
    {
        auto* B=WidgetTree->ConstructWidget<UImage>();
        B->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,0.f,FLinearColor::Transparent,0));
        B->SetColorAndOpacity(FLinearColor(1,1,1,.10f));B->SetVisibility(ESlateVisibility::HitTestInvisible);
        SmeltCanvas->AddChildToCanvas(B);return B;
    };
    for(int32 i=0;i<3;++i)BarTicks.Add(MakeTick());
    JobTime=Text(TEXT(""),12,ColdSteelUI::TextSecondary,true);
    SmeltSection->AddChildToVerticalBox(JobTime)->SetPadding(FMargin(0,6/Scale,0,0));
    CollectButton=Action(TEXT("取出矿锭"));
    auto* CollectSize=WidgetTree->ConstructWidget<USizeBox>();CollectSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    CollectSize->SetContent(CollectButton);
    CollectGlow=WidgetTree->ConstructWidget<UBorder>();
    CollectGlow->SetPadding(FMargin(2/Scale));
    CollectGlow->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,(ColdSteelUI::CardRadius+2)/Scale,ColdSteelUI::Success,1.5f/Scale));
    CollectGlow->SetVisibility(ESlateVisibility::Collapsed);   // 完成态由 RefreshJob 打开，AnimateBars 呼吸
    JobStack->AddChildToVerticalBox(CollectGlow)->SetPadding(FMargin(0,8/Scale,0,0));
    CollectGlow->SetContent(CollectSize);
    CollectButton->SetVisibility(ESlateVisibility::Collapsed);
    CollectButton->OnClicked.AddDynamic(this,&ThisClass::HandleCollect);
    SmeltSection->SetVisibility(ESlateVisibility::Collapsed);   // 有高炉上下文时由 RefreshJob 打开

    // —— 可冶炼原料列表 ——
    SectionTitle=Text(TEXT("可冶炼原料"),16,ColdSteelUI::TextPrimary,false,true);
    Body->AddChildToVerticalBox(SectionTitle)->SetPadding(FMargin(0,0,0,8/Scale));
    RowsScroll=WidgetTree->ConstructWidget<UScrollBox>();RowsScroll->SetAllowOverscroll(false);
    Body->AddChildToVerticalBox(RowsScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    RowsBox=WidgetTree->ConstructWidget<UVerticalBox>();RowsScroll->AddChild(RowsBox);
    RowsEmpty=Text(TEXT("背包与仓库中没有可冶炼的原料"),12,ColdSteelUI::TextTertiary,false,false,true);
    RowsBox->AddChildToVerticalBox(RowsEmpty);
    RowsScroll->SetVisibility(ESlateVisibility::Collapsed);   // 有炉子上下文且空闲时由 RefreshJob 打开

    // —— A 炉况视觉区：任务进行中占据列表区（投料图标→产物图标＋呼吸光环＋状态小字），
    // 补掉"冶炼中/完成"时面板中部的大空窗；纯装饰，不新增信息负担。——
    Showcase=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* ShowSlot=Body->AddChildToVerticalBox(Showcase);
    ShowSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ShowRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    Showcase->AddChildToVerticalBox(ShowRow)->SetHorizontalAlignment(HAlign_Center);
    ShowInSize=WidgetTree->ConstructWidget<USizeBox>();
    ShowInSize->SetWidthOverride(48/Scale);ShowInSize->SetHeightOverride(48/Scale);
    ShowRow->AddChildToHorizontalBox(ShowInSize)->SetVerticalAlignment(VAlign_Center);
    ShowInIcon=WidgetTree->ConstructWidget<UImage>();ShowInSize->SetContent(ShowInIcon);
    auto* ShowArrow=Text(TEXT("→"),16,ColdSteelUI::TextTertiary);
    auto* ArrowSlot=ShowRow->AddChildToHorizontalBox(ShowArrow);
    ArrowSlot->SetPadding(FMargin(14/Scale,0,14/Scale,0));ArrowSlot->SetVerticalAlignment(VAlign_Center);
    ShowRing=WidgetTree->ConstructWidget<UBorder>();
    ShowRing->SetPadding(FMargin(6/Scale));
    ShowRing->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,12.f/Scale,ColdSteelUI::Border,1.5f/Scale));
    ShowRow->AddChildToHorizontalBox(ShowRing)->SetVerticalAlignment(VAlign_Center);
    ShowOutSize=WidgetTree->ConstructWidget<USizeBox>();
    ShowOutSize->SetWidthOverride(48/Scale);ShowOutSize->SetHeightOverride(48/Scale);
    ShowRing->SetContent(ShowOutSize);
    ShowOutIcon=WidgetTree->ConstructWidget<UImage>();ShowOutSize->SetContent(ShowOutIcon);
    ShowCaption=Text(TEXT(""),12,ColdSteelUI::TextTertiary,false,false,true);
    ShowCaption->SetJustification(ETextJustify::Center);
    Showcase->AddChildToVerticalBox(ShowCaption)->SetPadding(FMargin(0,10/Scale,0,0));
    Showcase->SetVisibility(ESlateVisibility::Collapsed);   // 任务中由 RefreshJob 打开

    // —— 批量冶炼步进行（2026-09-24）：炉内空闲时显示，−/+ 调批量（1..持有量，封顶 99）。——
    // 2026-09-25 居中修复（用户"加减号没有位于卡片中央"，截图像素实测 −/＋ 贴卡两端）：
    // 步进群 [−][读数][＋] 整体在卡宽内水平居中——旧版读数列 Fill 撑满把两钮顶到行两端＝贴卡边。
    // 读数改 Auto 宽＋两侧 8px 间隔；两钮等宽等间隔，读数中线仍落卡中线（对称不破）。
    BatchRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    BatchRowSlot=Stack->AddChildToVerticalBox(BatchRow);
    BatchRowSlot->SetPadding(FMargin(16/Scale,4/Scale,16/Scale,6/Scale));
    BatchRowSlot->SetHorizontalAlignment(HAlign_Center);
    auto Small=[&](const FString& Caption)->UButton*
    {
        auto* B=WidgetTree->ConstructWidget<UButton>();
        B->SetContent(Text(Caption,14,ColdSteelUI::TextPrimary,false,true));
        StyledButtons.Add(B);
        auto* SZ=WidgetTree->ConstructWidget<USizeBox>();SZ->SetWidthOverride(30/Scale);SZ->SetHeightOverride(30/Scale);
        SZ->SetContent(B);
        BatchRow->AddChildToHorizontalBox(SZ)->SetVerticalAlignment(VAlign_Center);
        return B;
    };
    BatchMinus=Small(TEXT("−"));BatchMinus->OnClicked.AddDynamic(this,&ThisClass::HandleBatchMinus);
    BatchText=Text(TEXT("批量 ×1"),12,ColdSteelUI::TextSecondary);
    auto* BatchTextSlot=BatchRow->AddChildToHorizontalBox(BatchText);
    BatchTextSlot->SetPadding(FMargin(8/Scale,0,8/Scale,0));   // 与两钮的间隔；不再 Fill（Fill 把钮顶到卡边）
    BatchTextSlot->SetHorizontalAlignment(HAlign_Center);BatchTextSlot->SetVerticalAlignment(VAlign_Center);
    BatchPlus=Small(TEXT("+"));BatchPlus->OnClicked.AddDynamic(this,&ThisClass::HandleBatchPlus);
    BatchRow->SetVisibility(ESlateVisibility::Collapsed);   // 空闲且有炉子上下文时由 RefreshJob 打开

    // —— 底部操作与状态行 ——
    StartSize=WidgetTree->ConstructWidget<USizeBox>();StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    StartSlot=Stack->AddChildToVerticalBox(StartSize);
    StartButton=Action(TEXT("开始冶炼"));StartSize->SetContent(StartButton);
    StartButton->SetIsEnabled(false);
    StartButton->OnClicked.AddDynamic(this,&ThisClass::HandleStart);
    StatusLine=Text(TEXT(""),12,ColdSteelUI::TextTertiary,false,false,true);
    StatusSlot=Stack->AddChildToVerticalBox(StatusLine);

    // —— 下段·燃料卡（2026-09-23 拆分自炉况卡右列）：剩余燃料通栏条（火星粒子）＋添加燃料按钮。
    // 燃料＝木材，每件折算 FuelConfig().SecondsPerUnit 秒；空炉也能先添燃料（燃料独立于任务）。
    FuelCard=WidgetTree->ConstructWidget<UBorder>();
    FuelCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    FuelSlot=Stack->AddChildToVerticalBox(FuelCard);
    auto* FuelStack=WidgetTree->ConstructWidget<UVerticalBox>();FuelCard->SetContent(FuelStack);
    auto* FuelLabelRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    FuelStack->AddChildToVerticalBox(FuelLabelRow);
    FuelIconSize=WidgetTree->ConstructWidget<USizeBox>();
    FuelIconSize->SetWidthOverride(16/Scale);FuelIconSize->SetHeightOverride(16/Scale);
    FuelLabelRow->AddChildToHorizontalBox(FuelIconSize)->SetVerticalAlignment(VAlign_Center);
    FuelIcon=WidgetTree->ConstructWidget<UImage>();FuelIcon->SetVisibility(ESlateVisibility::Collapsed);
    FuelIconSize->SetContent(FuelIcon);
    auto* FuelLabel=Text(TEXT("剩余燃料 · 木材"),12,ColdSteelUI::TextTertiary);
    auto* FuelLabelSlot=FuelLabelRow->AddChildToHorizontalBox(FuelLabel);
    FuelLabelSlot->SetPadding(FMargin(6/Scale,0,0,0));FuelLabelSlot->SetVerticalAlignment(VAlign_Center);
    FuelBarSize=WidgetTree->ConstructWidget<USizeBox>();FuelBarSize->SetHeightOverride(12/Scale);
    FuelStack->AddChildToVerticalBox(FuelBarSize)->SetPadding(FMargin(0,4/Scale,0,0));
    FuelOverlay=WidgetTree->ConstructWidget<UOverlay>();FuelOverlay->SetVisibility(ESlateVisibility::HitTestInvisible);
    FuelBarSize->SetContent(FuelOverlay);
    // 燃料条＝通栏黑色背景条＋填充按存料占比增长（与上方冶炼条同构，2026-09-24 用户定稿）。
    FuelBar=WidgetTree->ConstructWidget<UProgressBar>();
    {
        FProgressBarStyle Style;
        Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6.f/Scale,FLinearColor::Transparent,0));
        Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,6.f/Scale,FLinearColor::Transparent,0));
        FuelBar->SetWidgetStyle(Style);
    }
    FuelBar->SetFillColorAndOpacity(FuelFillColor(0.f));
    FuelBar->SetPercent(0.f);FuelBar->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(auto* BarSlot=FuelOverlay->AddChildToOverlay(FuelBar)){BarSlot->SetHorizontalAlignment(HAlign_Fill);BarSlot->SetVerticalAlignment(VAlign_Fill);}
    // 火星：6 颗 2.5~4px 的暖色微粒沿填充区从左向右漂流、上下轻微摆动、闪烁冷却（AnimateBars 驱动）。
    FuelCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();FuelCanvas->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(auto* CanvasSlot=FuelOverlay->AddChildToOverlay(FuelCanvas)){CanvasSlot->SetHorizontalAlignment(HAlign_Fill);CanvasSlot->SetVerticalAlignment(VAlign_Fill);}
    for(int32 i=0;i<6;++i)
    {
        auto* Spark=WidgetTree->ConstructWidget<UImage>();
        Spark->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f/Scale,FLinearColor::Transparent,0));
        Spark->SetColorAndOpacity(FLinearColor(1,1,1,0));Spark->SetVisibility(ESlateVisibility::HitTestInvisible);
        if(auto* SparkSlot=FuelCanvas->AddChildToCanvas(Spark))SparkSlot->SetSize(FVector2D(3/Scale,3/Scale));
        EmberImages.Add(Spark);
        Embers.Add({FMath::FRand(),0.16f+0.26f*FMath::FRand(),FMath::FRand(),2.5f+1.5f*FMath::FRand()});
    }
    // 读数行与按钮各占一行（2026-09-24 截图实锤：任务中"存料 X · 还需烧 Y"与右侧按钮横向重叠）。
    // 按钮通栏＝与"开始冶炼/取出矿锭"同一动作规格；读数行永远有整卡宽度。
    FuelTime=Text(TEXT("0 秒"),12,ColdSteelUI::TextTertiary,true);
    FuelStack->AddChildToVerticalBox(FuelTime)->SetPadding(FMargin(0,6/Scale,0,0));
    AddFuelSize=WidgetTree->ConstructWidget<USizeBox>();AddFuelSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    FuelStack->AddChildToVerticalBox(AddFuelSize)->SetPadding(FMargin(0,6/Scale,0,0));
    AddFuelButton=Action(TEXT("添加燃料"));AddFuelSize->SetContent(AddFuelButton);
    AddFuelButton->SetIsEnabled(false);
    AddFuelButton->OnClicked.AddDynamic(this,&ThisClass::HandleAddFuel);
    FuelCard->SetVisibility(ESlateVisibility::Collapsed);   // 有高炉上下文时由 RefreshJob 打开

    // 页脚快捷键/语义说明（12px 辅助档，可换行）——与背包页脚同一位置语义；燃料语义写明"没油不推进"。
    StationFooter=Text(TEXT("Esc 或 × 关闭 · 存料持续燃烧（没矿也烧）· 有燃料才推进冶炼（关闭游戏也计入）"),12,ColdSteelUI::TextTertiary,false,false,true);
    FooterSlot=Stack->AddChildToVerticalBox(StationFooter);

    // —— 升级页签（2026-09-24 用户"在冶炼栏的左边添加一个类似事件进度栏的扩大箭头小方块，
    // 小箭头替换成升级二字，点击后左方弹出针对这个冶炼炉的升级界面"）：
    // 挂在面板左缘外（根 Canvas 允许负坐标外溢），弹出面板再往左开，只对这座炉生效。——
    UpgradeTab=WidgetTree->ConstructWidget<UBorder>();
    UpgradeTab->SetPadding(FMargin(0));   // v12：无描边并入主体，不再需要卡片内衬
    UpgradeTabBtn=WidgetTree->ConstructWidget<UButton>();
    // 2026-10-12：升级／收回使用横排，页签扩为 64 × 36。
    UpgradeTabText=Text(TEXT("升级"),14,ColdSteelUI::TextPrimary,false,true);
    UpgradeTabText->SetJustification(ETextJustify::Center);
    UpgradeTabText->SetAutoWrapText(false);UpgradeTabText->SetWrapTextAt(0); // 横向单行页签。
    UpgradeTabBtn->SetContent(UpgradeTabText);
    // v12：不进 StyledButtons（共享样式带描边），外观由 ApplyUpgradeTabVisual 统一给无描边样式。
    UpgradeTabBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeToggled);   // 收回态点击＝与关闭升级栏同一功能（互斥翻转）
    UpgradeTab->SetContent(UpgradeTabBtn);
    ApplyUpgradeTabVisual();
    UpgradeTabSlot=RootCanvas->AddChildToCanvas(UpgradeTab);
    // 页签＝36×60 竖排方块（字由上至下），大小随字收，右缘紧贴面板左缘零缝、垂直居中
    // 页签靠面板边缘，文字保持横向。
    UpgradeTabSlot->SetAnchors(FAnchors(0,.5f));UpgradeTabSlot->SetAlignment(FVector2D(0,.5f));
    UpgradeTabSlot->SetSize(FVector2D(64/Scale,36/Scale));
    UpgradeTabSlot->SetPosition(FVector2D(8/Scale,0.f));
    UpgradeTabSlot->SetZOrder(1);
    UpgradeTab->SetVisibility(ESlateVisibility::Collapsed);   // 有高炉上下文时由 RefreshJob 打开

    UpgradeFlyout=WidgetTree->ConstructWidget<UBorder>();
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10.f/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeFlyout->SetPadding(FMargin(0));   // v9：版面结构照抄面板（头部底色＋卡列各自内边距）
    UpgradeFlySlot=RootCanvas->AddChildToCanvas(UpgradeFlyout);
    // 弹层＝与冶炼面板同尺寸（2026-09-24 用户"直接复制尺寸和打开、收回的动画"）：槽铺满画布，
    // 左右留白由 ApplyScreenLayout 裁出［面板左缘−宽, 面板左缘］×全高；动画在 NativeTick 的 FlyMotion。
    // 独立页面动画的基准＝面板左缘那条边界线：右缘钉在缝上，横向缩放 0→1 向左展开/收回
    //（渲染枢轴在右中；不再从磨砂玻璃面板背后滑出——半透明会把"藏"漏成穿帮）。
    UpgradeFlySlot->SetAnchors(FAnchors(0,0,1,1));UpgradeFlySlot->SetAlignment(FVector2D::ZeroVector);
    UpgradeFlySlot->SetOffsets(FMargin(8/Scale,0.f,0.f,0.f));
    UpgradeFlyout->SetRenderTransformPivot(FVector2D(1.f,.5f));
    auto* FlyStack=WidgetTree->ConstructWidget<UVerticalBox>();UpgradeFlyout->SetContent(FlyStack);
    // 头部＝面板 HeaderSurface 同款：HeaderTint 底＋20px 标题＋Action("×")
    //（2026-09-24 用户"右上角的X就没有设计好"——旧版是裸文本小方块，现在与面板关闭钮同控件同规格）。
    FlyHeadSurf=WidgetTree->ConstructWidget<UBorder>();
    FlyHeadSurf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    FlyHeadSurf->SetPadding(FMargin(18/Scale,12/Scale));
    FlyStack->AddChildToVerticalBox(FlyHeadSurf);
    auto* FlyHeadSize=WidgetTree->ConstructWidget<USizeBox>();FlyHeadSize->SetHeightOverride(36/Scale);FlyHeadSurf->SetContent(FlyHeadSize);
    auto* FlyHead=WidgetTree->ConstructWidget<UHorizontalBox>();FlyHeadSize->SetContent(FlyHead);
    if(auto* TS=FlyHead->AddChildToHorizontalBox(Text(TEXT("高炉升级"),20,ColdSteelUI::TextPrimary,false,true)))
    {   TS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TS->SetVerticalAlignment(VAlign_Center);   }
    auto* FlyClose=Action(TEXT("×"));
    StyledButtons.Add(FlyClose);FlyClose->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeClose);
    if(auto* CS=FlyHead->AddChildToHorizontalBox(FlyClose))CS->SetVerticalAlignment(VAlign_Center);
    // 三轴页签（v10，2026-09-24 用户"三卡压缩成页签，下方详情带显示效果与材料"）：行＝轴名 14（选中
    // Medium）＋Lv 12，整行可点；选中/悬停视觉与配方行同款（§3 明度＋细边）。数据由 RefreshJob 统一刷。
    auto* FlyBody=WidgetTree->ConstructWidget<UVerticalBox>();
    if(auto* BS=FlyStack->AddChildToVerticalBox(FlyBody))
    {   BS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));BS->SetPadding(FMargin(12/Scale,10/Scale,12/Scale,0));   }
    for(int32 A=0;A<3;++A)
    {
        auto* Surf=WidgetTree->ConstructWidget<UBorder>();
        Surf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
        Surf->SetPadding(FMargin(12/Scale,8/Scale));
        if(auto* KS=FlyBody->AddChildToVerticalBox(Surf))KS->SetPadding(FMargin(0,0,0,6/Scale));
        auto* Tab=WidgetTree->ConstructWidget<UButton>();
        Tab->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));
        Surf->SetContent(Tab);
        auto* Content=WidgetTree->ConstructWidget<UHorizontalBox>();Tab->SetContent(Content);
        if(auto* CS=Cast<UButtonSlot>(Content->Slot))   // UButtonSlot 默认居中收缩（配方行 2026-09-23 的坑）：铺满才撑得开 Fill
            {CS->SetPadding(FMargin(0));CS->SetHorizontalAlignment(HAlign_Fill);CS->SetVerticalAlignment(VAlign_Center);}
        UpgTabs.Add(Tab);UpgTabSurfs.Add(Surf);
        auto* Name=Text(AxisNames[A],14,ColdSteelUI::TextPrimary,false,A==UpgSel);
        if(auto* NS=Content->AddChildToHorizontalBox(Name))
        {   NS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NS->SetVerticalAlignment(VAlign_Center);   }
        UpgTabNames.Add(Name);
        const FString Lv0=FString::Printf(TEXT("Lv.1 / %d"),VoxelFurnaceAxisMax(A));
        auto* Lv=Text(*Lv0,12,ColdSteelUI::TextSecondary,false,true);
        Content->AddChildToHorizontalBox(Lv)->SetVerticalAlignment(VAlign_Center);
        UpgTabLv.Add(Lv);
        auto* Proxy=NewObject<UColdSteelSmeltingRowProxy>(this);   // 点击代理：与配方行同款（ConstructWidget 只收 UWidget）
        Proxy->Panel=this;Proxy->Axis=A;
        Tab->OnClicked.AddDynamic(Proxy,&UColdSteelSmeltingRowProxy::AxisClicked);
        UpgProxies.Add(Proxy);   // 专用数组常驻引用（RowProxies 会被 RefreshRows 重清）
    }
    // —— 详情带（v10）：字号直接吃正式规则 §4 的四档——分区标题 16／正文 14／数值 16 NumberFont／辅助 12；
    // 关键信息不再挤旧卡列的 12px 辅助档（用户点名"字体大小做好规划"）。纯数字用等宽，混排文本用 UI 字体。——
    FlyDetail=WidgetTree->ConstructWidget<UBorder>();
    FlyDetail->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
    FlyDetail->SetPadding(FMargin(12/Scale));
    if(auto* DS=FlyStack->AddChildToVerticalBox(FlyDetail))DS->SetPadding(FMargin(12/Scale,2/Scale,12/Scale,0));
    auto* DCol=WidgetTree->ConstructWidget<UVerticalBox>();FlyDetail->SetContent(DCol);
    auto* DHead=WidgetTree->ConstructWidget<UHorizontalBox>();DCol->AddChildToVerticalBox(DHead);
    FlyDetailName=Text(AxisNames[0],16,ColdSteelUI::TextPrimary,false,true);
    DHead->AddChildToHorizontalBox(FlyDetailName)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    FlyDetailLv=Text(TEXT("Lv.1 / 5"),12,ColdSteelUI::TextSecondary,false,true);
    DHead->AddChildToHorizontalBox(FlyDetailLv)->SetVerticalAlignment(VAlign_Center);
    FlyRuleSize=WidgetTree->ConstructWidget<USizeBox>();FlyRuleSize->SetHeightOverride(1.f/Scale);
    if(auto* RS=DCol->AddChildToVerticalBox(FlyRuleSize))RS->SetPadding(FMargin(0,8/Scale,0,6/Scale));
    auto* Rule=WidgetTree->ConstructWidget<UImage>();
    Rule->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Border,0.f));FlyRuleSize->SetContent(Rule);   // §"细线分区"
    DCol->AddChildToVerticalBox(Text(TEXT("升级效果"),12,ColdSteelUI::TextTertiary));
    FlyFx=Text(TEXT(""),16,ColdSteelUI::Success,true,false);   // "30 分钟 → 40 分钟"：紧凑数值→JetBrains Mono
    if(auto* XS=DCol->AddChildToVerticalBox(FlyFx))XS->SetPadding(FMargin(0,2/Scale,0,8/Scale));
    DCol->AddChildToVerticalBox(Text(TEXT("所需材料"),12,ColdSteelUI::TextTertiary));
    FlyMatRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    if(auto* MS=DCol->AddChildToVerticalBox(FlyMatRow))MS->SetPadding(FMargin(0,2/Scale,0,0));
    FlyMatIconSize=WidgetTree->ConstructWidget<USizeBox>();
    FlyMatIconSize->SetWidthOverride(28/Scale);FlyMatIconSize->SetHeightOverride(28/Scale);
    FlyMatIcon=WidgetTree->ConstructWidget<UImage>();FlyMatIconSize->SetContent(FlyMatIcon);
    FlyMatIcon->SetVisibility(ESlateVisibility::Collapsed);
    FlyMatRow->AddChildToHorizontalBox(FlyMatIconSize)->SetVerticalAlignment(VAlign_Center);
    if(auto* NS=FlyMatRow->AddChildToHorizontalBox(Text(TEXT("铁锭"),14,ColdSteelUI::TextPrimary)))
        NS->SetPadding(FMargin(8/Scale,0,0,0));
    FlyMatValue=Text(TEXT("×10"),16,ColdSteelUI::TextPrimary,true,false);
    if(auto* VS=FlyMatRow->AddChildToHorizontalBox(FlyMatValue))
    {   VS->SetPadding(FMargin(8/Scale,0,0,0));VS->SetVerticalAlignment(VAlign_Center);   }
    FlyMatOwned=Text(TEXT(""),12,ColdSteelUI::TextSecondary,false,false,true);
    if(auto* OS=FlyMatRow->AddChildToHorizontalBox(FlyMatOwned))
    {   OS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));OS->SetPadding(FMargin(8/Scale,0,0,0));OS->SetVerticalAlignment(VAlign_Center);   }
    FlyNoMat=Text(TEXT("已满级，无需材料"),12,ColdSteelUI::TextTertiary);
    FlyNoMat->SetVisibility(ESlateVisibility::Collapsed);
    DCol->AddChildToVerticalBox(FlyNoMat);
    FlyBtnSize=WidgetTree->ConstructWidget<USizeBox>();FlyBtnSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    if(auto* SS=DCol->AddChildToVerticalBox(FlyBtnSize))SS->SetPadding(FMargin(0,10/Scale,0,0));
    FlyBtn=Action(TEXT("升级"));FlyBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeClicked);
    FlyBtnText=Cast<UTextBlock>(FlyBtn->GetContent());
    FlyBtnSize->SetContent(FlyBtn);
    if(auto* NS=FlyStack->AddChildToVerticalBox(Text(TEXT("升级只对这座炉生效 · 消耗铁锭"),12,ColdSteelUI::TextTertiary,false,false,true)))
        NS->SetPadding(FMargin(12/Scale,0,12/Scale,10/Scale));   // Body 占 Fill，说明行自然垫底＝面板页脚同一位置语义
    UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);
    UpdateScale();
}

void UColdSteelSmeltingWidget::UpdateScale()
{
    Scale=ColdSteelUI::PixelScale(this);
    HeaderSurface->SetPadding(FMargin(18/Scale,12/Scale));HeaderSize->SetHeightOverride(36/Scale);
    JobCard->SetPadding(FMargin(12/Scale));
    FuelCard->SetPadding(FMargin(12/Scale));
    BarSize->SetHeightOverride(12/Scale);   // 2026-09-23 用户反馈加粗：5px → 12px（燃料条同宽）
    FuelBarSize->SetHeightOverride(12/Scale);
    JobIconSize->SetWidthOverride(28/Scale);JobIconSize->SetHeightOverride(28/Scale);
    FuelIconSize->SetWidthOverride(16/Scale);FuelIconSize->SetHeightOverride(16/Scale);
    ShowInSize->SetWidthOverride(48/Scale);ShowInSize->SetHeightOverride(48/Scale);
    ShowOutSize->SetWidthOverride(48/Scale);ShowOutSize->SetHeightOverride(48/Scale);
    ShowRing->SetPadding(FMargin(6/Scale));
    // 批量/升级（2026-09-24）：页签、弹层与步进行的尺寸同样跟 Scale。
    // 2026-09-25：步进行居中归属槽位（HAlign_Center），读数间隔随 Scale 重算——与构建期同一口径。
    if(BatchRowSlot){BatchRowSlot->SetPadding(FMargin(16/Scale,4/Scale,16/Scale,6/Scale));BatchRowSlot->SetHorizontalAlignment(HAlign_Center);}
    if(auto* TS=Cast<UHorizontalBoxSlot>(BatchText->Slot))TS->SetPadding(FMargin(8/Scale,0,8/Scale,0));
    for(auto* B:{BatchMinus.Get(),BatchPlus.Get()})if(B)if(auto* SZ=Cast<USizeBox>(B->GetParent()))
        {SZ->SetWidthOverride(30/Scale);SZ->SetHeightOverride(30/Scale);}
    if(UpgradeTabSlot)UpgradeTabSlot->SetSize(FVector2D(64/Scale,36/Scale));
    ApplyScreenLayout();   // Shell/页签/弹层按新 Scale 重排（坐标源＝主题层推送的屏幕像素）
    ApplyUpgradeTabVisual();   // v12：hover/pressed 圆角随 Scale 重建
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10.f/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeFlyout->SetPadding(FMargin(0));   // v9 版面：头部底色与卡列各自带内边距（旧固定 220 宽一并作废）
    if(FlyHeadSurf)
    {   FlyHeadSurf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
        FlyHeadSurf->SetPadding(FMargin(18/Scale,12/Scale));
        if(auto* HS=Cast<USizeBox>(FlyHeadSurf->GetContent()))HS->SetHeightOverride(36/Scale);   }
    for(int32 A=0;A<UpgTabSurfs.Num();++A)
    {   if(UpgTabSurfs[A])UpgTabSurfs[A]->SetPadding(FMargin(12/Scale,8/Scale));   // 卡面刷（含选中态）由 RefreshJob 随 Scale 刷
        if(UpgTabs.IsValidIndex(A)&&UpgTabs[A])UpgTabs[A]->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));   }
    if(FlyDetail)
    {   FlyDetail->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
        FlyDetail->SetPadding(FMargin(12/Scale));   }
    if(FlyRuleSize)FlyRuleSize->SetHeightOverride(1.f/Scale);
    if(FlyMatIconSize){FlyMatIconSize->SetWidthOverride(28/Scale);FlyMatIconSize->SetHeightOverride(28/Scale);}
    if(FlyBtnSize)FlyBtnSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    {   // 条样式随 Scale 重建（圆角半径换算）；颜色/占比由 RefreshJob 复原。
        FProgressBarStyle Style;
        Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6.f/Scale,FLinearColor::Transparent,0));
        Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,6.f/Scale,FLinearColor::Transparent,0));
        SmeltBar->SetWidgetStyle(Style);FuelBar->SetWidgetStyle(Style);
    }
    AddFuelSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    RowsScroll->SetScrollbarThickness(FVector2D(6/Scale));   // 正式规则 §3：中性灰约 6px 滚动条
    // 分区留白（§3"明度、细边、留白建立层级"）：正文/按钮/状态行/页脚与玻璃边缘保持 16px，
    // 之前贴边——卡片和文字直接压在圆角玻璃上，是"不达标"观感的主因之一。
    BodySlot->SetPadding(FMargin(16/Scale,12/Scale,16/Scale,0));
    StartSlot->SetPadding(FMargin(16/Scale,2/Scale,16/Scale,4/Scale));
    StatusSlot->SetPadding(FMargin(16/Scale,2/Scale,16/Scale,2/Scale));
    FuelSlot->SetPadding(FMargin(16/Scale,4/Scale,16/Scale,8/Scale));
    FooterSlot->SetPadding(FMargin(16/Scale,0,16/Scale,8/Scale));
    for(const auto& L:Labels)if(auto* Label=L.Widget.Get())
        Label->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    const FButtonStyle Style=ColdSteelUI::ButtonStyle(Scale);
    for(const auto& Weak:StyledButtons)if(auto* B=Weak.Get())
    {
        B->SetStyle(Style);
        if(auto* Content=B->GetContent())if(auto* ContentSlot=Cast<UButtonSlot>(Content->Slot))ContentSlot->SetPadding(FMargin(10/Scale,8/Scale));
    }
    RefreshSelection();RefreshJob();
}

void UColdSteelSmeltingWidget::ApplyScreenLayout()
{
    if(PanelScreenPx<0.f||Scale<=0.f)return;
    // 槽位原点＝屏幕 x=0（主题层把 widget 扩为全宽命中区），偏移×Scale 即屏幕像素，无需任何几何反推。
    const float P=PanelScreenPx/Scale;
    if(ShellSlot)ShellSlot->SetOffsets(FMargin(P,0.f,0.f,0.f));
    if(UpgradeTabSlot)LayoutUpgradeTab();   // v11：摆位收敛到一个函数（收起贴缝/展开随弹层，见下）
    if(UpgradeFlySlot)
    {   // 弹层＝冶炼面板的左右镜像：同宽（LayoutWidth）、同高（画布全高）、右缘＝面板左缘零缝。
        // 画布宽＝面板左缘＋面板宽（主题层保证面板右缘＝画布右缘）——纯推送值，
        // 不再依赖缓存几何（首帧未测量时回落成全画布宽，就是"大小完全错误"的根因，2026-09-24）。
        const float W=FMath::Max(1.f,LayoutWidth)/Scale;
        const float L=FMath::Max(8.f/Scale,P-W);
        UpgradeFlySlot->SetOffsets(FMargin(L,0.f,W,0.f));   // 右留白＝W：rect 右缘＝P 钉在缝上
    }
}

void UColdSteelSmeltingWidget::LayoutUpgradeTab()
{
    if(!UpgradeTabSlot||PanelScreenPx<0.f||Scale<=0.f)return;
    const float P=PanelScreenPx/Scale;                      // 面板左缘（单位系）
    const float W=FMath::Max(1.f,LayoutWidth)/Scale;
    const float L=FMath::Max(8.f/Scale,P-W);                // 弹层全开左缘（与 ApplyScreenLayout 同式）
    const float TabW=64.f/Scale;
    // v12：方片已无自身描边（并入主体），右缘压线 1px 只为消掉抗锯齿发丝缝。
    // 展开态跟随：EaseSmooth(FlyMotion) 与弹层 RenderScale 同曲线同拍，方片右缘钉在弹层左缘上推到最左；
    // 屏幕边钳制：1280 宽下弹层左缘仅 8px，方片贴到 x=0 盖在弹层角上（ZOrder 1，可点收回）。
    const float X=FMath::Max(0.f,FMath::Lerp(P-TabW,L-TabW,ColdSteelUI::EaseSmooth(FlyMotion))+1.f/Scale);
    UpgradeTabSlot->SetPosition(FVector2D(X,0.f));
}

void UColdSteelSmeltingWidget::ApplyUpgradeTabVisual()
{
    if(!UpgradeTab)return;
    // v12（用户"取消边界、做成主体一部分，保留功能"）：无描边填充，颜色跟随所贴主体——
    // 收起＝冶炼栏 GlassTint，展开＝升级栏 Content（ZOrder 1 盖在弹层缘上，同色即无缝）。
    // v12b（用户"卡片还是圆边角处理"）：只圆左两角 8px、右两角直角——右侧是接缝，
    // 圆接缝侧会在面板/弹层边线上咬出两个背景缺口（凸舌 tab 的标准做法）。
    const FLinearColor Fill=bTabVisualOpen?ColdSteelUI::Content:ColdSteelUI::GlassTint;
    const float R=8.f/Scale;
    UpgradeTab->SetBrush(ColdSteelUI::RoundedBrushCorners(Fill,FVector4(R,0.f,0.f,R)));
    if(UpgradeTabBtn)
    {   FButtonStyle S;   // 钮面透明（卡片感来源就是它这层描边底），只留 hover/pressed 的轻反馈
        S.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0.f,FLinearColor::Transparent,0.f));
        S.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6.f/Scale,FLinearColor::Transparent,0.f));
        S.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,6.f/Scale,FLinearColor::Transparent,0.f));
        S.SetDisabled(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0.f,FLinearColor::Transparent,0.f));
        UpgradeTabBtn->SetStyle(S);   }
}
