#include "ColdSteelSmeltingWidget.h"
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
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

namespace
{
    /**
     * 复刻原项目 game-dev `game-ui-manager.js:51-68` 的 `timelineProgressColor`：
     * 四个色标之间按进度线性插值。**方向按冶炼语义正向化**（规划文档第 2.2 节）：
     * 0%=红 → 1/3=黄 → 2/3=蓝 → 100%=绿；原项目为倒计时威胁语义（0 绿 1 红），常量在此不混用。
     */
    FLinearColor SmeltingProgressColor(float T)
    {
        static const FLinearColor Stops[4]=
        {
            FLinearColor::FromSRGBColor(FColor(0xE5,0x41,0x3E)),   // #E5413E 红
            FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F)),   // #F1C13F 黄
            FLinearColor::FromSRGBColor(FColor(0x41,0x8B,0xE7)),   // #418BE7 蓝
            FLinearColor::FromSRGBColor(FColor(0x3D,0xC4,0x5B))    // #3DC45B 绿
        };
        const float X=FMath::Clamp(T,0.f,1.f)*3.f;
        const int32 Step=FMath::Clamp(FMath::FloorToInt(X),0,2);
        const float A=X-Step;
        return Stops[Step]*(1.f-A)+Stops[Step+1]*A;   // 线性插值（sRGB 空间，与原项目 CSS 侧一致）
    }

    FString DefinitionName(UColdSteelStatusModel* Model,const FString& Definition)
    {
        if(!Model||Definition.IsEmpty())return Definition;
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("name"));
        return Name.IsEmpty()?Definition:Name;
    }

    /** 燃料条底色：按存料占比从暖橙 #F0BE71（Warning 档）渐变到亮黄 #F1C13F——
     *  越满越"有货"，与左侧进度条的四段色语义分开（燃料=存量、进度=时间）。 */
    FLinearColor FuelFillColor(float Ratio)
    {
        const FLinearColor Low=FLinearColor::FromSRGBColor(FColor(0xF0,0xBE,0x71));
        const FLinearColor High=FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F));
        const float X=FMath::Clamp(Ratio,0.f,1.f);
        return Low*(1.f-X)+High*X;
    }

    /** 秒数 → 人类可读：≥60 秒折算"X 分 Y 秒"（整分省秒），否则原样。燃料每件 1 分钟，界面按分读。 */
    FString ReadableSeconds(double Seconds)
    {
        const int64 Total=FMath::RoundToInt64(Seconds);
        if(Total<60)return FString::Printf(TEXT("%lld 秒"),Total);
        const int64 M=Total/60,R=Total%60;
        return R>0?FString::Printf(TEXT("%lld 分 %lld 秒"),M,R):FString::Printf(TEXT("%lld 分钟"),M);
    }
}

void UColdSteelSmeltingRowProxy::Clicked()
{
    if(auto* Owner=Panel.Get())Owner->SelectRecipe(Recipe);
}

void UColdSteelSmeltingRowProxy::AxisClicked()
{
    if(auto* Owner=Panel.Get())Owner->SelectUpgradeAxis(Axis);
}

namespace { const TCHAR* const AxisNames[3]={TEXT("冶炼速度"),TEXT("燃料仓容量"),TEXT("每次投料上限")}; }

UTextBlock* UColdSteelSmeltingWidget::Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium,bool bWrap)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetColorAndOpacity(Color);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    if(bWrap)Label->SetAutoWrapText(true);   // Slate 不裁剪不换行=文字画出玻璃框（正式规则 §3）。
    Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    Labels.Add({Label,Pixels,Numeric,Medium});return Label;
}

UButton* UColdSteelSmeltingWidget::Action(const FString& Caption)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();
    B->SetContent(Text(Caption,14,ColdSteelUI::TextPrimary));
    StyledButtons.Add(B);return B;
}

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
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);

    HeaderSurface=WidgetTree->ConstructWidget<UBorder>();
    HeaderSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Stack->AddChildToVerticalBox(HeaderSurface);
    HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSurface->SetContent(HeaderSize);
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    // 顶栏＝标题（20px Medium 档）＋ × 关闭：面板独立于背包后需要自带出口（Esc 同效）。
    auto* TitleSlot=Heading->AddChildToHorizontalBox(Text(TEXT("冶炼"),20,ColdSteelUI::TextPrimary,false,true));
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
    JobDetail=Text(TEXT("从下方选择矿石投料"),12,ColdSteelUI::TextTertiary,false,false,true);
    JobStack->AddChildToVerticalBox(JobDetail)->SetPadding(FMargin(0,0,0,8/Scale));
    // —— 上段·冶炼进度条（通栏）：燃烧时脉冲提亮＋前沿亮头。5px 版用户反馈"太细不明显"，加粗到 12px。
    // 2026-09-23 拆分：燃料不再与它同排双列，移到面板底部的独立燃料卡（FuelCard）。
    SmeltSection=WidgetTree->ConstructWidget<UVerticalBox>();
    JobStack->AddChildToVerticalBox(SmeltSection)->SetPadding(FMargin(0,0,0,6/Scale));
    SmeltSection->AddChildToVerticalBox(Text(TEXT("冶炼进度"),12,ColdSteelUI::TextTertiary));
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

    // —— 可冶炼矿石列表 ——
    SectionTitle=Text(TEXT("可冶炼矿石"),16,ColdSteelUI::TextPrimary,false,true);
    Body->AddChildToVerticalBox(SectionTitle)->SetPadding(FMargin(0,0,0,8/Scale));
    RowsScroll=WidgetTree->ConstructWidget<UScrollBox>();RowsScroll->SetAllowOverscroll(false);
    Body->AddChildToVerticalBox(RowsScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    RowsBox=WidgetTree->ConstructWidget<UVerticalBox>();RowsScroll->AddChild(RowsBox);
    RowsEmpty=Text(TEXT("背包与仓库中没有可冶炼的矿石"),12,ColdSteelUI::TextTertiary,false,false,true);
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
    BatchRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    Stack->AddChildToVerticalBox(BatchRow)->SetPadding(FMargin(16/Scale,4/Scale,16/Scale,6/Scale));
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
    BatchTextSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
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
    FooterSlot=Stack->AddChildToVerticalBox(Text(TEXT("Esc 或 × 关闭 · 存料持续燃烧（没矿也烧）· 有燃料才推进冶炼（关闭游戏也计入）"),12,ColdSteelUI::TextTertiary,false,false,true));

    // —— 升级页签（2026-09-24 用户"在冶炼栏的左边添加一个类似事件进度栏的扩大箭头小方块，
    // 小箭头替换成升级二字，点击后左方弹出针对这个冶炼炉的升级界面"）：
    // 挂在面板左缘外（根 Canvas 允许负坐标外溢），弹出面板再往左开，只对这座炉生效。——
    UpgradeTab=WidgetTree->ConstructWidget<UBorder>();
    UpgradeTab->SetPadding(FMargin(0));   // v12：无描边并入主体，不再需要卡片内衬
    UpgradeTabBtn=WidgetTree->ConstructWidget<UButton>();
    // v11c（2026-09-24 用户"升级、收回两字从上到下排列，居中"）：竖排两字＋逐行居中——
    // 此前看着不居中的根因是块内每行默认左对齐，SetJustification(Center) 修正；展开态文案由 RefreshJob 换"收\n回"。
    UpgradeTabText=Text(TEXT("升\n级"),14,ColdSteelUI::TextPrimary,false,true);
    UpgradeTabText->SetJustification(ETextJustify::Center);
    UpgradeTabText->SetLineHeightPercentage(.88f);   // 收紧两字行距，墨迹块更接近方片几何中心
    UpgradeTabBtn->SetContent(UpgradeTabText);
    // v12：不进 StyledButtons（共享样式带描边），外观由 ApplyUpgradeTabVisual 统一给无描边样式。
    UpgradeTabBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeToggled);   // 收回态点击＝与关闭升级栏同一功能（互斥翻转）
    UpgradeTab->SetContent(UpgradeTabBtn);
    ApplyUpgradeTabVisual();
    UpgradeTabSlot=RootCanvas->AddChildToCanvas(UpgradeTab);
    // 页签＝36×60 竖排方块（字由上至下），大小随字收，右缘紧贴面板左缘零缝、垂直居中
    //（2026-09-24 用户"字体由上至下顺序排列，调整器大小匹配，并且跟冶炼栏无缝衔接，不要留有缝隙"）。
    UpgradeTabSlot->SetAnchors(FAnchors(0,.5f));UpgradeTabSlot->SetAlignment(FVector2D(0,.5f));
    UpgradeTabSlot->SetSize(FVector2D(36/Scale,60/Scale));
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
    if(auto* BS=Cast<UVerticalBoxSlot>(BatchRow->Slot))BS->SetPadding(FMargin(16/Scale,4/Scale,16/Scale,6/Scale));
    for(auto* B:{BatchMinus.Get(),BatchPlus.Get()})if(B)if(auto* SZ=Cast<USizeBox>(B->GetParent()))
        {SZ->SetWidthOverride(30/Scale);SZ->SetHeightOverride(30/Scale);}
    if(UpgradeTabSlot)UpgradeTabSlot->SetSize(FVector2D(36/Scale,60/Scale));
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

void UColdSteelSmeltingWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;}

void UColdSteelSmeltingWidget::SetFurnace(AVoxelBuildWorld* InWorld,FIntVector InCell)
{
    World=InWorld;Cell=InCell;SelectedRecipe=NAME_None;
    bUpgradeOpen=false;   // 换炉上下文时收起升级弹层（等级是逐炉数据，别把上一座的弹层带过来）
    UpgSel=VoxelFurnaceAxisSpeed;   // 页签选择同样归零：新炉从默认轴看起
    CdLastBranch=-1;CdLastFuelSec=CdLastNeedSec=-1;   // 换炉后燃料行强制重绘一次
    FlyMotion=0.f;   // 换炉上下文时弹层瞬关（不播收回动画，防残影随面板滑入）
    if(UpgradeFlyout){UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);UpgradeFlyout->SetRenderScale(FVector2D(1.f,1.f));}
    SetStatus(FString());RefreshRows();RefreshJob();
}

void UColdSteelSmeltingWidget::SetLayoutWidth(float PixelsX)
{
    if(FMath::IsNearlyEqual(LayoutWidth,PixelsX,.5f))return;
    LayoutWidth=PixelsX;ApplyScreenLayout();RefreshJob();   // 弹层与面板同宽，宽度推送要同步重排（2026-09-24）
}

void UColdSteelSmeltingWidget::SetPanelScreenX(float Px)
{
    if(FMath::IsNearlyEqual(PanelScreenPx,Px,.5f))return;
    PanelScreenPx=Px;ApplyScreenLayout();
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
    const float TabW=36.f/Scale;
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

void UColdSteelSmeltingWidget::SelectRecipe(FName Recipe)
{
    if(SelectedRecipe==Recipe)return;
    SelectedRecipe=Recipe;SetStatus(FString());RefreshSelection();RefreshJob();
}

void UColdSteelSmeltingWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshJob);
    RefreshRows();RefreshJob();
}

void UColdSteelSmeltingWidget::NativeDestruct()
{
    if(Model)Model->OnChanged.Remove(ChangedHandle);
    ChangedHandle.Reset();Super::NativeDestruct();
}

void UColdSteelSmeltingWidget::NativeTick(const FGeometry& MyGeometry,float InDeltaTime)
{
    Super::NativeTick(MyGeometry,InDeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f)){UpdateScale();return;}
    if(GetVisibility()==ESlateVisibility::Collapsed)return;
    AnimateBars(InDeltaTime);   // 每帧：脉冲与火星读缓存值，不触发数据刷新
    PaintFuelLine();            // 每帧：燃料行挂钟外推；整数秒没变即返回（零分配零写入）
    // 升级弹层动画（2026-09-24 用户"作为一个独立的页面，以冶炼栏左边线条边界为基准，弹出和收回"）：
    // 右缘钉死在面板左缘那条缝上（枢轴右中），横向缩放 0→1 向左展开、1→0 向右收回，同款 4.0/s。
    // 不再从面板背后滑出——磨砂玻璃半透明，"藏"会漏成穿帮（上一版动画问题的根因）。
    FlyMotion=FMath::FInterpConstantTo(FlyMotion,bUpgradeOpen?1.f:0.f,InDeltaTime,4.0f);
    if(UpgradeFlyout)
    {
        UpgradeFlyout->SetVisibility(FlyMotion>KINDA_SMALL_NUMBER?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        UpgradeFlyout->SetRenderScale(FVector2D(FMath::Max(ColdSteelUI::EaseSmooth(FlyMotion),.02f),1.f));
    }
    LayoutUpgradeTab();   // v11：方片逐帧跟弹层左缘（与 RenderScale 同曲线）；静止时仅一次属性写，开销可忽略。
    RefreshAccum+=InDeltaTime;
    if(RefreshAccum<.1f)return;   // 进度与剩余时间按 0.1s 节流刷新（面板开着才计）。
    RefreshAccum=0.f;
    if(auto* W=World.Get())if(System)System->SettleFurnace(W,Cell);   // 面板开着的挂钟落账（写档脏标由 Settle 判定）
    RefreshJob();
}

void UColdSteelSmeltingWidget::RefreshRows()
{
    if(!RowsBox||!Model||!System)return;
    FString Signature;
    for(const FColdSteelSmeltingRecipe& R:System->Catalog())
        Signature+=FString::Printf(TEXT("%s:%lld;"),*R.Id.ToString(),Model->CountMaterial(R.Input));
    if(Signature==RowsSignature)
    {
        // 持有量没变就不重建行（保住选择与滚动位置），但换炉子后的选中高亮仍要刷一次。
        if(Rows.IsEmpty())RowsEmpty->SetVisibility(ESlateVisibility::Visible);
        else RefreshSelection();
        return;
    }
    RowsSignature=Signature;
    RowsBox->ClearChildren();Rows.Reset();RowProxies.Reset();
    for(const FColdSteelSmeltingRecipe& R:System->Catalog())
    {
        const int64 Have=Model->CountMaterial(R.Input);
        if(Have<=0)continue;   // 未持有不生成卡片（与附魔卷轴同一口径），列表只报价可负担的配方。
        auto* Card=WidgetTree->ConstructWidget<UBorder>();
        Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
        Card->SetPadding(FMargin(12/Scale,10/Scale));   // 与炉内状态卡的 12px 内沿同一列
        RowsBox->AddChildToVerticalBox(Card)->SetPadding(FMargin(0,0,0,6/Scale));
        auto* Row=WidgetTree->ConstructWidget<UButton>();
        // 行按钮透明常态 + 语义色悬停：卡片底色与选中描边由外层 Border 负责（建造抽屉行卡先例）。
        Row->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));
        Card->SetContent(Row);
        auto* Content=WidgetTree->ConstructWidget<UHorizontalBox>();Row->SetContent(Content);
        // UButtonSlot 默认 HAlign_Center：行内容按 desired 收缩并居中，Fill 列撑不开、"持有"贴不到右缘，
        // 名称/产出被挤到换行（2026-09-23 截图审计实锤）。改为铺满按钮，行内左中右三段才成立。
        if(auto* RowSlot=Cast<UButtonSlot>(Content->Slot)){RowSlot->SetPadding(FMargin(0));
            RowSlot->SetHorizontalAlignment(HAlign_Fill);RowSlot->SetVerticalAlignment(VAlign_Center);}
        const FString InputName=DefinitionName(Model,R.Input);
        const FString OutputName=DefinitionName(Model,R.Output);
        if(const FSlateBrush* Brush=IconFor(R.Input))
        {
            auto* IconSize=WidgetTree->ConstructWidget<USizeBox>();
            IconSize->SetWidthOverride(28/Scale);IconSize->SetHeightOverride(28/Scale);
            Content->AddChildToHorizontalBox(IconSize)->SetVerticalAlignment(VAlign_Center);
            auto* Icon=WidgetTree->ConstructWidget<UImage>();Icon->SetBrush(*Brush);IconSize->SetContent(Icon);
        }
        // 行结构＝图标｜名称＋产出（Fill 撑开）｜持有数（右对齐卡边）。
        // 之前没有 Fill 列，整簇内容居中、"持有 N"悬在半空——不对称的主因。
        auto* Names=WidgetTree->ConstructWidget<UVerticalBox>();
        auto* NamesSlot=Content->AddChildToHorizontalBox(Names);
        NamesSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        NamesSlot->SetPadding(FMargin(10/Scale,0,0,0));
        Names->AddChildToVerticalBox(Text(FString::Printf(TEXT("%s ×%lld"),*InputName,R.InputCount),14,ColdSteelUI::TextPrimary,false,false,true));
        Names->AddChildToVerticalBox(Text(FString::Printf(TEXT("→ %s ×%lld · %g 秒"),*OutputName,R.OutputCount,R.Seconds),12,ColdSteelUI::TextSecondary,false,false,true));
        auto* Held=Text(FString::Printf(TEXT("持有 %lld"),Have),12,ColdSteelUI::TextTertiary,true);
        auto* HeldSlot=Content->AddChildToHorizontalBox(Held);
        HeldSlot->SetVerticalAlignment(VAlign_Center);
        HeldSlot->SetPadding(FMargin(8/Scale,0,0,0));
        // UButton::OnClicked 是动态无参委托：按工程先例（UVoxelBuildCardProxy）用代理携带配方 id。
        auto* Proxy=NewObject<UColdSteelSmeltingRowProxy>(this);
        Proxy->Panel=this;Proxy->Recipe=R.Id;
        Row->OnClicked.AddDynamic(Proxy,&UColdSteelSmeltingRowProxy::Clicked);
        RowProxies.Add(Proxy);
        Rows.Add({Row,Card,R.Id});
    }
    // 空态行随重建挂回（ClearChildren 只摘不毁，但它需要重新入面板）。
    if(Rows.IsEmpty())RowsBox->AddChild(RowsEmpty);
    RefreshSelection();
}

void UColdSteelSmeltingWidget::RefreshSelection()
{
    for(const FRow& Row:Rows)
    {
        auto* Card=Row.Card.Get();if(!Card)continue;
        const bool bSelected=Row.Recipe==SelectedRecipe;
        Card->SetBrush(ColdSteelUI::RoundedBrush(bSelected?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,
            ColdSteelUI::CardRadius/Scale,bSelected?ColdSteelUI::Accent:ColdSteelUI::Border,bSelected?2.f/Scale:1.f/Scale));
    }
}

void UColdSteelSmeltingWidget::RefreshJob()
{
    if(!JobTitle||!System)return;
    AVoxelBuildWorld* W=World.Get();
    const FVoxelSmeltingJob* Job=W?W->FindSmelting(Cell):nullptr;
    const FColdSteelSmeltingRecipe* Recipe=Job?System->Find(Job->Recipe):nullptr;
    const bool bFurnace=W&&W->IsFurnaceAt(Cell);
    // 列表区只在炉内空闲时开放（规划文档第 6 节：空闲=选料，冶炼中=进度，完成=取出）；
    // 任务中同一区域交给炉况视觉区（A），分区标题随列表一起收起，不留空标题。
    const bool bShowRows=!Job&&bFurnace&&GetVisibility()!=ESlateVisibility::Collapsed;
    RowsScroll->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    SectionTitle->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Showcase->SetVisibility(Job&&bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!Job||!bFurnace)bWasDone=false;   // 出炉/拆炉复位完成沿，下次转完成仍会闪光

    // —— 批量步进行（2026-09-24 批量冶炼；v9 起上限受"每次投料"升级轴约束）：
    // 只在空闲选料态显示，上限＝min(持有÷单份投料, 批量轴×5)，兜底封顶 99。——
    BatchRow->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    int64 MaxBatch=1;
    if(bShowRows&&!SelectedRecipe.IsNone())
        if(const auto* R=System->Find(SelectedRecipe);R&&Model&&W)
            MaxBatch=FMath::Clamp<int64>(FMath::Min<int64>(Model->CountMaterial(R->Input)/R->InputCount,
                UColdSteelSmeltingSystem::BatchCapFor(W->FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisBatch))),1,99);   // 上限＝min(持有, 批量轴×5)，v9 起受升级约束
    Batch=FMath::Clamp<int64>(Batch,1,FMath::Max<int64>(1,MaxBatch));
    BatchText->SetText(FText::FromString(FString::Printf(TEXT("批量 ×%lld（最多 %lld）"),Batch,MaxBatch)));
    BatchMinus->SetIsEnabled(Batch>1);BatchPlus->SetIsEnabled(Batch<MaxBatch);
    if(auto* Cap=Cast<UTextBlock>(StartButton->GetContent()))
        Cap->SetText(FText::FromString(Batch>1?FString::Printf(TEXT("开始冶炼 ×%lld"),Batch):TEXT("开始冶炼")));

    // —— 升级页签/弹层：有炉子上下文才存在；弹层打开时数字跟着数据走（复用 10Hz 节拍，不加定时器）。——
    UpgradeTab->SetVisibility(bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!bFurnace)bUpgradeOpen=false;
    if(UpgradeTabText)   // v11（用户"打开升级栏后替换为收回二字，点击收回＝关闭"）：收回态点页签走的就是 HandleUpgradeToggled 的关闭分支。
    {   const FText Want=FText::FromString(bUpgradeOpen?TEXT("收\n回"):TEXT("升\n级"));   // v11c 竖排两字
        if(!UpgradeTabText->GetText().EqualTo(Want))UpgradeTabText->SetText(Want);
        if(bTabVisualOpen!=bUpgradeOpen){bTabVisualOpen=bUpgradeOpen;ApplyUpgradeTabVisual();}   // v12：换色跟随所贴主体
    }
    // 弹层可见性/滑位由 NativeTick 的 FlyMotion 统一驱动（复制冶炼面板的开合动画，2026-09-24）。
    if(bUpgradeOpen&&bFurnace&&W)
    {   // v10：页签只刷"名称字重＋Lv"，选中样式走配方行同款（ButtonHover 底＋Accent 2px 细边）；
        // 效果与材料集中在下方详情带，字号按 §4 分档，纯数值走 JetBrains Mono。
        const int64 Held=Model?Model->CountMaterial(TEXT("ironIngot")):0;
        UpgSel=FMath::Clamp(UpgSel,0,2);
        for(int32 A=0;A<3;++A)
        {
            const bool bSel=A==UpgSel;
            if(UpgTabSurfs.IsValidIndex(A)&&UpgTabSurfs[A])UpgTabSurfs[A]->SetBrush(ColdSteelUI::RoundedBrush(
                bSel?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,
                bSel?ColdSteelUI::Accent:ColdSteelUI::Border,bSel?2.f/Scale:1.f/Scale));
            if(UpgTabNames.IsValidIndex(A)&&UpgTabNames[A])
                UpgTabNames[A]->SetFont(GunsmithUI::TextFont(14/Scale,bSel));   // §4：Medium＝选中项
            if(UpgTabLv.IsValidIndex(A)&&UpgTabLv[A])UpgTabLv[A]->SetText(FText::FromString(
                FString::Printf(TEXT("Lv.%d / %d"),W->FurnaceUpgradeLevel(Cell,A),VoxelFurnaceAxisMax(A))));
        }
        const int32 Lvl=W->FurnaceUpgradeLevel(Cell,UpgSel);
        const int32 AxisMax=VoxelFurnaceAxisMax(UpgSel);
        const bool bMax=Lvl>=AxisMax;
        FString Cur,Next;
        AxisValueText(UpgSel,Lvl,Cur);AxisValueText(UpgSel,Lvl+1,Next);
        if(FlyDetailName)FlyDetailName->SetText(FText::FromString(AxisNames[UpgSel]));
        if(FlyDetailLv)FlyDetailLv->SetText(FText::FromString(FString::Printf(TEXT("Lv.%d / %d"),Lvl,AxisMax)));
        if(FlyFx)
        {   FlyFx->SetText(FText::FromString(bMax?FString::Printf(TEXT("已满级 · 当前 %s"),*Cur)
                :FString::Printf(TEXT("%s → %s"),*Cur,*Next)));
            FlyFx->SetColorAndOpacity(bMax?ColdSteelUI::TextSecondary:ColdSteelUI::Success);   }
        const int64 Cost=UColdSteelSmeltingSystem::UpgradeCostFor(Lvl);
        if(FlyMatRow)FlyMatRow->SetVisibility(bMax?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
        if(FlyNoMat)FlyNoMat->SetVisibility(bMax?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        if(!bMax)
        {
            if(FlyMatValue)
            {   FlyMatValue->SetText(FText::FromString(FString::Printf(TEXT("×%lld"),Cost)));
                FlyMatValue->SetColorAndOpacity(Held>=Cost?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);   }
            if(FlyMatOwned)
            {   FlyMatOwned->SetText(FText::FromString(Held>=Cost?FString::Printf(TEXT("持有 %lld"),Held)
                    :FString::Printf(TEXT("持有 %lld · 还差 %lld"),Held,Cost-Held)));
                FlyMatOwned->SetColorAndOpacity(Held>=Cost?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);   }
            if(FlyMatIcon)
            {   if(const FSlateBrush* B=IconFor(TEXT("ironIngot"))){FlyMatIcon->SetBrush(*B);FlyMatIcon->SetVisibility(ESlateVisibility::HitTestInvisible);}
                else FlyMatIcon->SetVisibility(ESlateVisibility::Collapsed);   }
        }
        if(FlyBtn)FlyBtn->SetIsEnabled(!bMax&&Held>=Cost);
        if(FlyBtnText)FlyBtnText->SetText(FText::FromString(
            bMax?TEXT("已满级"):Held>=Cost?TEXT("升级"):TEXT("铁锭不足")));
    }
    // 上段进度条＋下段燃料卡：有炉子上下文就常显（燃料独立于任务——空炉也能先添燃料）。
    SmeltSection->SetVisibility(bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    FuelCard->SetVisibility(bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    // —— 燃料卡（面板下段）：剩余燃料 + 添加燃料（每炉存料口径，取出产物不清燃料）——
    const FColdSteelSmeltingFuel& FC=System->FuelConfig();
    if(!FuelIcon->GetBrush().GetResourceObject())   // 燃料图标一次挂上（定义表启动即定，不再变）
    {
        if(const FSlateBrush* B=IconFor(FC.Item)){FuelIcon->SetBrush(*B);FuelIcon->SetVisibility(ESlateVisibility::HitTestInvisible);}
        else FuelIcon->SetVisibility(ESlateVisibility::Collapsed);
    }
    const double Fuel=bFurnace?W->FuelAt(Cell):0.0;
    const double Cap=bFurnace?System->FurnaceCapacity(W,Cell):FC.Capacity;   // v9：容量随燃料仓轴升级
    AnimFuelRatio=Cap>0?FMath::Clamp(static_cast<float>(Fuel/Cap),0.f,1.f):0.f;
    bFuelAlive=bFurnace&&Fuel>0;
    FuelBar->SetFillColorAndOpacity(FuelFillColor(AnimFuelRatio));
    // 用户 2026-09-24：燃料区也要看到剩余时间——任务中显示"存料 vs 还需烧"直接对比，
    // 存料不够烧完就转 Warning 橙（要不要添柴一眼可判）；空闲/完成态维持"存料 · 上限"。
    // 2026-09-24 实时化整改：这里只校准锚点，文案由 PaintFuelLine 每帧外推＋变化门控写一次。
    const bool bJobRunning=Job&&bFurnace&&!System->IsDone(W,Cell);
    bCdRunning=bJobRunning;
    // v8 语义（2026-09-24 用户定稿）：炉内有存料就在烧——外推门按"有料"开，
    // 空闲态"存料 X"同样逐秒走；任务中"还需烧"仍只在有任务时参与。
    bCdBurning=bFurnace&&Fuel>0;
    CdFuel=Fuel;
    CdNeed=bJobRunning?System->RemainingSeconds(W,Cell):0.0;
    CdStamp=FPlatformTime::Seconds();
    PaintFuelLine();
    AddFuelButton->SetIsEnabled(System->CanAddFuel(W,Cell));
    if(auto* Caption=Cast<UTextBlock>(AddFuelButton->GetContent()))
        Caption->SetText(FText::FromString(FString::Printf(TEXT("添加燃料 +%s"),*ReadableSeconds(FC.SecondsPerUnit))));
    if(!Job)
    {
        JobTitle->SetText(FText::FromString(TEXT("炉内空闲")));
        JobTitle->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        if(const auto* R=SelectedRecipe.IsNone()?nullptr:System->Find(SelectedRecipe))
        {   // 预览＝批量投料/产出与预计秒数（含这座炉的等级提速）。
            const double Mul=W&&bFurnace?UColdSteelSmeltingSystem::SpeedMultiplier(W->FurnaceLevel(Cell)):1.0;
            JobDetail->SetText(FText::FromString(FString::Printf(TEXT("%s ×%lld → %s ×%lld · %g 秒"),
                *DefinitionName(Model,R->Input),R->InputCount*Batch,*DefinitionName(Model,R->Output),R->OutputCount*Batch,
                R->Seconds*Batch/Mul)));
        }
        else JobDetail->SetText(FText::FromString(TEXT("从下方选择矿石投料")));
        JobDetail->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        AnimSmeltT=0;bBurning=false;
        JobTime->SetText(FText::FromString(Fuel>0?TEXT("待投料起火"):TEXT("未起火")));
        JobTime->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        CollectButton->SetVisibility(ESlateVisibility::Collapsed);
        CollectGlow->SetVisibility(ESlateVisibility::Collapsed);
        StartButton->SetVisibility(ESlateVisibility::Visible);
        StartButton->SetIsEnabled(!SelectedRecipe.IsNone());
        // 炉况卡图标＝选中配方的输入矿（C 锚点）；没选中就收起。
        if(const auto* R=SelectedRecipe.IsNone()?nullptr:System->Find(SelectedRecipe);
            R&&IconFor(R->Input)){JobIcon->SetBrush(*IconFor(R->Input));JobIcon->SetVisibility(ESlateVisibility::Visible);}
        else JobIcon->SetVisibility(ESlateVisibility::Collapsed);
    }
    else
    {
        const bool bDone=System->IsDone(W,Cell);
        const bool bBurn=System->IsBurning(W,Cell);
        const float T=System->Progress(W,Cell);
        AnimSmeltT=T;bBurning=bBurn&&!bDone;
        // 三态：完成（Success）｜燃烧（TextPrimary＋脉冲）｜停炉（Warning，等添燃料）。
        JobTitle->SetText(FText::FromString(bDone?TEXT("冶炼完成"):bBurn?TEXT("冶炼中"):TEXT("燃料耗尽")));
        JobTitle->SetColorAndOpacity(bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);
        JobDetail->SetText(FText::FromString(Recipe
            ?FString::Printf(TEXT("%s ×%lld → %s ×%lld · %g 秒"),
                *DefinitionName(Model,Recipe->Input),Recipe->InputCount*FMath::Max<int64>(1,Job->BatchCount),
                *DefinitionName(Model,Recipe->Output),Recipe->OutputCount*FMath::Max<int64>(1,Job->BatchCount),
                System->JobTotalSeconds(W,*Job,*Recipe))
            :FString(TEXT("配方已下架，炉内矿料无法结算"))));
        JobDetail->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        JobTime->SetVisibility(ESlateVisibility::Visible);
        JobTime->SetText(FText::FromString(bDone?TEXT("等待取出")
            :bBurn?FString::Printf(TEXT("剩余 %.1f 秒"),System->RemainingSeconds(W,Cell))
            :FString::Printf(TEXT("已停炉 · 剩余 %.1f 秒"),System->RemainingSeconds(W,Cell))));
        JobTime->SetColorAndOpacity(bBurn?ColdSteelUI::TextSecondary:ColdSteelUI::TextTertiary);
        CollectButton->SetVisibility(bDone?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        CollectGlow->SetVisibility(bDone?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        StartButton->SetVisibility(ESlateVisibility::Collapsed);
        // 炉况卡图标＝在炼的矿石（C 锚点）。
        if(Recipe&&IconFor(Recipe->Input)){JobIcon->SetBrush(*IconFor(Recipe->Input));JobIcon->SetVisibility(ESlateVisibility::Visible);}
        else JobIcon->SetVisibility(ESlateVisibility::Collapsed);
        // A 视觉区：投料图标→产物图标＋状态光环＋小字（缺图只隐不塌，布局稳定）。
        if(Recipe)
        {
            if(const FSlateBrush* B=IconFor(Recipe->Input)){ShowInIcon->SetBrush(*B);ShowInIcon->SetVisibility(ESlateVisibility::Visible);}
            else ShowInIcon->SetVisibility(ESlateVisibility::Hidden);
            if(const FSlateBrush* B=IconFor(Recipe->Output)){ShowOutIcon->SetBrush(*B);ShowOutIcon->SetVisibility(ESlateVisibility::Visible);}
            else ShowOutIcon->SetVisibility(ESlateVisibility::Hidden);
            ShowCaption->SetText(FText::FromString(FString::Printf(TEXT("%s ×%lld · %s"),
                *DefinitionName(Model,Recipe->Output),Recipe->OutputCount*FMath::Max<int64>(1,Job->BatchCount),
                bDone?TEXT("出炉待取"):bBurn?TEXT("冶炼中"):TEXT("停炉待燃"))));
            ShowCaption->SetColorAndOpacity(bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);
            ShowRing->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,12.f/Scale,
                bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::Warning:ColdSteelUI::Border,1.5f/Scale));
        }
        // B2：只在"转完成"那一拍起一次扫条闪光。
        if(bDone&&!bWasDone)FlashT=0.f;
        bWasDone=bDone;
    }
    // 两条都是通栏 UProgressBar：percent 驱动，轨道与填充同几何（无黑边、不溢出）。
    SmeltBar->SetPercent(FMath::Clamp(AnimSmeltT,0.f,1.f));
    FuelBar->SetPercent(FMath::Clamp(bFuelAlive?AnimFuelRatio:0.f,0.f,1.f));
    if(!bBurning)SmeltBar->SetFillColorAndOpacity(SmeltingProgressColor(AnimSmeltT));   // 燃烧时让 AnimateBars 每帧控色
}

FString UColdSteelSmeltingWidget::DebugFuelLineText() const {return FuelTime?FuelTime->GetText().ToString():FString();}

void UColdSteelSmeltingWidget::PaintFuelLine()
{
    if(!FuelTime||!System)return;
    // 帧间纯挂钟外推：燃烧中存料与还需烧同步递减（1:1），停炉待燃/空闲就冻结在锚点。
    const double Now=FPlatformTime::Seconds();
    const double Elapsed=FMath::Max(0.0,Now-CdStamp);
    const double Fuel=bCdBurning?FMath::Max(0.0,CdFuel-Elapsed):CdFuel;
    const double Need=bCdBurning?FMath::Max(0.0,CdNeed-Elapsed):CdNeed;
    const int32 Branch=bCdRunning?1:0;
    const int32 FuelSec=FMath::CeilToInt32(Fuel),NeedSec=FMath::CeilToInt32(Need);
    if(Branch==CdLastBranch&&FuelSec==CdLastFuelSec&&(Branch==0||NeedSec==CdLastNeedSec))return;   // 显示没变：零写入
    CdLastBranch=Branch;CdLastFuelSec=FuelSec;CdLastNeedSec=NeedSec;
    if(bCdRunning)
    {
        FuelTime->SetText(FText::FromString(FString::Printf(TEXT("存料 %s · 还需烧 %s"),
            *ReadableSeconds(Fuel),*ReadableSeconds(Need))));
        FuelTime->SetColorAndOpacity(Fuel<Need?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    }
    else
    {
        FuelTime->SetText(FText::FromString(FString::Printf(TEXT("%s · 上限 %s"),
            *ReadableSeconds(Fuel),*ReadableSeconds(System->FurnaceCapacity(World.Get(),Cell)))));   // v9：上限随燃料仓轴升级
        FuelTime->SetColorAndOpacity(Fuel>0?ColdSteelUI::TextSecondary:ColdSteelUI::TextTertiary);
    }
}

void UColdSteelSmeltingWidget::SetStatus(const FString& Line,bool bError)
{
    if(!StatusLine)return;
    StatusLine->SetText(FText::FromString(Line));
    StatusLine->SetColorAndOpacity(Line.IsEmpty()?ColdSteelUI::TextTertiary:bError?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

const FSlateBrush* UColdSteelSmeltingWidget::IconFor(const FString& Definition)
{
    if(!Model||Definition.IsEmpty())return nullptr;
    if(const auto* Found=IconBrushes.Find(Definition))return Found;
    if(FailedIcons.Contains(Definition))return nullptr;
    const FString File=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("ue_icon"));
    if(File.IsEmpty()){FailedIcons.Add(Definition);return nullptr;}
    auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);
    if(!Texture){FailedIcons.Add(Definition);return nullptr;}   // 失败要记住：源文件缺失，别每次刷新都重试。
    IconTextures.Add(Texture);
    FSlateBrush Brush;Brush.SetResourceObject(Texture);
    Brush.ImageSize=FVector2D(256,256);Brush.DrawAs=ESlateBrushDrawType::Image;
    return &IconBrushes.Add(Definition,Brush);
}

void UColdSteelSmeltingWidget::HandleStart()
{
    if(SelectedRecipe.IsNone()||!World.IsValid()||!System)return;
    const FColdSteelSmeltingRecipe* R=System->Find(SelectedRecipe);
    if(!R){SetStatus(TEXT("该配方不存在"),true);return;}
    const FString InputName=DefinitionName(Model,R->Input);
    const double Mul=UColdSteelSmeltingSystem::SpeedMultiplier(World->FurnaceLevel(Cell));
    const double Seconds=R->Seconds*Batch/Mul;   // 与结算同一口径：批量÷等级速度
    FString Reason;
    if(System->BeginSmelting(World.Get(),Cell,SelectedRecipe,Reason,Batch))
    {
        SelectedRecipe=NAME_None;
        RefreshRows();RefreshJob();
        SetStatus(FString::Printf(TEXT("已投料 %s ×%lld · 约 %g 秒后出炉"),*InputName,R->InputCount*Batch,Seconds));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleBatchMinus()
{
    if(Batch>1){--Batch;RefreshJob();}
}

void UColdSteelSmeltingWidget::HandleBatchPlus()
{
    if(Batch<99){++Batch;RefreshJob();}   // RefreshJob 再按持有量夹一次，超了自动回弹
}

void UColdSteelSmeltingWidget::HandleUpgradeToggled()
{
    bUpgradeOpen=!bUpgradeOpen;RefreshJob();
}

void UColdSteelSmeltingWidget::HandleUpgradeClose()
{
    bUpgradeOpen=false;RefreshJob();
}

void UColdSteelSmeltingWidget::HandleUpgradeClicked()        {UpgradeAxis(UpgSel);}   // 详情带升级钮：升当前选中轴
void UColdSteelSmeltingWidget::HandleUpgradeFuelClicked()    {SelectUpgradeAxis(VoxelFurnaceAxisFuelCapacity);UpgradeAxis(VoxelFurnaceAxisFuelCapacity);}
void UColdSteelSmeltingWidget::HandleUpgradeBatchClicked()   {SelectUpgradeAxis(VoxelFurnaceAxisBatch);UpgradeAxis(VoxelFurnaceAxisBatch);}

void UColdSteelSmeltingWidget::SelectUpgradeAxis(int32 Axis)
{
    // 点击立即换详情，不等下一拍刷新。
    UpgSel=FMath::Clamp(Axis,0,2);RefreshJob();
}

void UColdSteelSmeltingWidget::DebugClickUpgradeTab(int32 Axis)
{
    if(UpgTabs.IsValidIndex(Axis)&&UpgTabs[Axis])UpgTabs[Axis]->OnClicked.Broadcast();
}

void UColdSteelSmeltingWidget::AxisValueText(int32 Axis,int32 Level,FString& Out) const
{
    if(!System){Out.Reset();return;}
    switch(Axis)
    {   case VoxelFurnaceAxisFuelCapacity:
            Out=FString::Printf(TEXT("%d 分钟"),FMath::RoundToInt32(System->FuelConfig().Capacity*FMath::Clamp(Level,1,VoxelFurnaceAxisMax(Axis))/60.0));break;
        case VoxelFurnaceAxisBatch:
            Out=FString::Printf(TEXT("×%lld"),UColdSteelSmeltingSystem::BatchCapFor(Level));break;
        default:
            Out=FString::Printf(TEXT("+%d%%"),FMath::RoundToInt32((UColdSteelSmeltingSystem::SpeedMultiplier(Level)-1)*100));break;   }
}

void UColdSteelSmeltingWidget::UpgradeAxis(int32 Axis)
{
    if(!World.IsValid()||!System)return;
    FString Reason;
    if(System->UpgradeFurnace(World.Get(),Cell,Reason,Axis))
    {   static const TCHAR* const AxisDone[3]={TEXT("冶炼提速了"),TEXT("燃料仓扩容了"),TEXT("每次投料上限提高了")};
        SetStatus(FString::Printf(TEXT("升级成功 · %s"),Axis>=0&&Axis<3?AxisDone[Axis]:AxisDone[0]),false);RefreshJob();   }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleCollect()
{
    if(!World.IsValid()||!System)return;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    const FColdSteelSmeltingRecipe* R=Job?System->Find(Job->Recipe):nullptr;
    const FString OutputName=R?DefinitionName(Model,R->Output):FString();
    const int64 OutputCount=R?R->OutputCount:0;
    FString Reason;
    if(System->CollectSmelting(World.Get(),Cell,Reason))
    {
        RefreshRows();RefreshJob();
        SetStatus(FString::Printf(TEXT("已取出 %s ×%lld"),*OutputName,OutputCount));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleAddFuel()
{
    if(!World.IsValid()||!System)return;
    FString Reason;
    if(System->AddFuel(World.Get(),Cell,Reason))
    {
        RefreshJob();
        SetStatus(FString::Printf(TEXT("已添加燃料 +%s"),*ReadableSeconds(System->FuelConfig().SecondsPerUnit)));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleClose()
{
    // 面板独立于背包：× 与 Esc 走同一个出口（HUD 的 CloseSmelting 幂等，重复调用安全）。
    if(HUD)HUD->CloseSmelting();
}

void UColdSteelSmeltingWidget::AnimateBars(float DeltaSeconds)
{
    if(!SmeltBar||!FuelBar)return;
    AnimTime+=FMath::Clamp(DeltaSeconds,0.f,.25f);   // 挂起/切窗口回来不跳相位
    const float Pulse=.5f+.5f*FMath::Sin(AnimTime*2.f*PI/1.1f);   // 脉冲周期 1.1s
    // 亮头/火星参照宽＝条控件缓存几何（单位系），与 percent 同源 → 永远贴在条内。
    const float SmeltBarW=FMath::Max(1.f,BarSize->GetCachedGeometry().GetLocalSize().X);
    SmeltFillPx=SmeltBarW*FMath::Clamp(AnimSmeltT,0.f,1.f);
    FuelFillPx=FMath::Max(1.f,FuelBarSize->GetCachedGeometry().GetLocalSize().X)*FMath::Clamp(bFuelAlive?AnimFuelRatio:0.f,0.f,1.f);
    // 冶炼条脉冲：燃烧时填充亮度在 0.90~1.24 间起伏（提亮封顶靠 sRGB 钳位），前沿亮头同步呼吸。
    if(bBurning)
    {
        const FLinearColor Base=SmeltingProgressColor(AnimSmeltT);
        const float Bright=.90f+.34f*Pulse;
        SmeltBar->SetFillColorAndOpacity(FLinearColor(Base.R*Bright,Base.G*Bright,Base.B*Bright));
        SmeltBar->SetPercent(FMath::Clamp(AnimSmeltT,0.f,1.f));   // 燃烧中每帧跟手（占比小步长肉眼无跳变）
    }
    if(Head)
    {
        const bool bShowHead=bBurning&&SmeltFillPx>1.f;
        Head->SetVisibility(bShowHead?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(bShowHead)
        {
            Head->SetColorAndOpacity(FLinearColor(1.f,1.f,1.f,.22f+.5f*Pulse));
            const float HeadX=FMath::Max(0.f,SmeltFillPx-4.f/Scale);
            if(auto* HeadSlot=Cast<UCanvasPanelSlot>(Head->Slot))
            {
                HeadSlot->SetSize(FVector2D(7.f/Scale,12.f/Scale));
                HeadSlot->SetPosition(FVector2D(HeadX,0.f));
            }
            // B3 辉光：16px 软带垫在亮头后（左偏 4.5px），α 随同一脉冲。
            if(HeadGlow)
            {
                HeadGlow->SetVisibility(ESlateVisibility::HitTestInvisible);
                HeadGlow->SetColorAndOpacity(FLinearColor(1.f,1.f,1.f,.08f+.14f*Pulse));
                if(auto* GS=Cast<UCanvasPanelSlot>(HeadGlow->Slot))
                {GS->SetSize(FVector2D(16.f/Scale,12.f/Scale));GS->SetPosition(FVector2D(FMath::Max(0.f,HeadX-4.5f/Scale),0.f));}
            }
        }
        else if(HeadGlow)HeadGlow->SetVisibility(ESlateVisibility::Collapsed);
        // B4 刻度：每帧按条宽重摆（面板宽度会随抽屉变化，刻线必须跟着 25/50/75% 走）。
        for(int32 i=0;i<BarTicks.Num();++i)if(auto* T=BarTicks[i].Get())
            if(auto* S=Cast<UCanvasPanelSlot>(T->Slot))
            {S->SetSize(FVector2D(1.f/Scale,12.f/Scale));S->SetPosition(FVector2D((i+1)*.25f*SmeltBarW-.5f/Scale,0.f));}
    }
    // 燃料条火星：沿填充区从左向右漂的小暖粒，上下轻摆＋闪烁，流向头部逐渐冷却；
    // 只在有存料时激活——停燃不画粒子，与"没油不推进"的语义一致。
    const bool bSparks=bFuelAlive&&FuelFillPx>2.f&&EmberImages.Num()==Embers.Num();
    const FLinearColor Amber=FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F));
    for(int32 i=0;i<EmberImages.Num();++i)
    {
        UImage* Spark=EmberImages[i];if(!Spark)continue;
        if(!bSparks){Spark->SetColorAndOpacity(FLinearColor(1,1,1,0));continue;}
        FEmber& E=Embers[i];
        E.Phase+=E.Speed*DeltaSeconds;
        if(E.Phase>1.f){E.Phase-=1.f;E.Seed=FMath::FRand();}   // 回到尾部时换一颗新"火星"
        const float Sz=E.Size/Scale;
        const float Jitter=(2.4f/Scale)*FMath::Sin(2.f*PI*(E.Phase*1.7f+E.Seed));
        const float Flicker=.5f+.5f*FMath::Sin(3.f*(AnimTime*(2.2f+E.Speed*5.f)+E.Seed*9.f));
        const float Fade=1.f-.55f*E.Phase;
        const float Hot=.5f+.5f*FMath::Sin(E.Seed*17.f);       // 每颗固定的琥珀↔白偏色
        const FLinearColor Base=Amber*(1.f-.5f*Hot)+FLinearColor::White*(.5f*Hot);
        Spark->SetColorAndOpacity(FLinearColor(Base.R,Base.G,Base.B,(.18f+.62f*Flicker)*Fade));
        if(auto* SparkSlot=Cast<UCanvasPanelSlot>(Spark->Slot))
        {
            SparkSlot->SetSize(FVector2D(Sz,Sz));
            SparkSlot->SetPosition(FVector2D(E.Phase*FuelFillPx,(12.f/Scale-Sz)*.5f+Jitter));
        }
    }
    // B1 流动高光：燃烧时 8/20/8 三段亮带在填充区内往返（2.2s 一往返），位置数学钳制不越条。
    const float BandW=8.f/Scale,MainW=20.f/Scale,TotalW=2.f*BandW+MainW;
    const bool bSweep=bBurning&&SmeltFillPx>TotalW+2.f;
    float SweepX=0.f;
    if(bSweep)
    {   const float Ph=FMath::Frac(AnimTime/2.2f);
        const float Tri=Ph<.5f?Ph*2.f:(1.f-Ph)*2.f;
        SweepX=FMath::Lerp(0.f,SmeltFillPx-TotalW,Tri);}
    auto PlaceBand=[&](UImage* B,float OffX,float W)
    {
        if(!B)return;
        if(!bSweep){B->SetVisibility(ESlateVisibility::Collapsed);return;}
        B->SetVisibility(ESlateVisibility::HitTestInvisible);
        if(auto* S=Cast<UCanvasPanelSlot>(B->Slot)){S->SetSize(FVector2D(W,12.f/Scale));S->SetPosition(FVector2D(SweepX+OffX,0.f));}
    };
    PlaceBand(SweepA,0.f,BandW);PlaceBand(SweepB,BandW,MainW);PlaceBand(SweepC,BandW+MainW,BandW);
    // B2 完成闪光：一条宽带 0.55s 扫满条并淡出（一次性，扫完自动收起）。
    if(FlashT>=0.f)
    {
        FlashT+=FMath::Clamp(DeltaSeconds,0.f,.25f)/0.55f;
        const float W=26.f/Scale;
        if(FlashT<1.f&&SmeltFillPx>W)
        {
            FlashBand->SetVisibility(ESlateVisibility::HitTestInvisible);
            FlashBand->SetColorAndOpacity(FLinearColor(1,1,1,(1.f-FlashT)*.5f));
            const float X=FMath::Clamp(FlashT*(SmeltFillPx+W)-W,0.f,SmeltFillPx-W);
            if(auto* S=Cast<UCanvasPanelSlot>(FlashBand->Slot)){S->SetSize(FVector2D(W,12.f/Scale));S->SetPosition(FVector2D(X,0.f));}
        }
        else FlashBand->SetVisibility(ESlateVisibility::Collapsed);
        if(FlashT>=1.f)FlashT=-1.f;
    }
    // A/C 呼吸：光环完成态 1.8s 慢呼吸（栏目脉冲先例）、燃烧与条脉冲同步 1.1s、停炉静止低亮；
    // 取出按钮描边随完成态绿色呼吸。都只改 tint，不重绘数据。
    if(ShowRing&&ShowRing->GetVisibility()!=ESlateVisibility::Collapsed)
    {
        const float Breath=.5f+.5f*FMath::Sin(AnimTime*2.f*PI/(bWasDone?1.8f:1.1f));
        ShowRing->SetBrushColor(FLinearColor(1,1,1,bWasDone?.45f+.55f*Breath:bBurning?.3f+.6f*Breath:.35f));
    }
    if(CollectGlow&&CollectGlow->GetVisibility()!=ESlateVisibility::Collapsed)
        CollectGlow->SetBrushColor(FLinearColor(1,1,1,.4f+.6f*(.5f+.5f*FMath::Sin(AnimTime*2.f*PI/1.8f))));
}
