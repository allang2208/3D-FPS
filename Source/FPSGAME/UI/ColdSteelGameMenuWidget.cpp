#include "ColdSteelGameMenuWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/VoxelBuildWorld.h"
#include "AudioDevice.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/ConfigCacheIni.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    constexpr const TCHAR* SettingsSection = TEXT("ColdSteel.GameMenu");
    FText Text(const FString& Value) { return FText::FromString(Value); }
    void ApplyFrameSettings(UGameUserSettings* Settings)
    {
        // These two controls must not reapply scalability and overwrite the live scene's quality settings.
        if (auto* VSync=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync")))
            VSync->Set(Settings->IsVSyncEnabled()?1:0,ECVF_SetByGameSetting);
        if (auto* Limit=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS")))
            Limit->Set(Settings->GetFrameRateLimit(),ECVF_SetByGameSetting);
        Settings->SaveSettings();
    }
    TSharedRef<STextBlock> Label(const FString& Value, float Pixels = 14.f,
        FLinearColor Color = ColdSteelUI::TextPrimary, bool Number = false)
    {
        return SNew(STextBlock).Text(Text(Value)).AutoWrapText(false)
            .Font(Number ? ColdSteelUI::NumberFont(Pixels * .75f) : ColdSteelUI::TextFont(Pixels * .75f))
            .ColorAndOpacity(Color);
    }
}

void UColdSteelGameMenuWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    SetNavigationRuleBase(EUINavigation::Next, EUINavigationRule::Wrap);
    SetNavigationRuleBase(EUINavigation::Previous, EUINavigationRule::Wrap);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    PanelBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, ColdSteelUI::PanelRadius);
    HeaderBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint, ColdSteelUI::CardRadius, FLinearColor::Transparent, 0);
    DimBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(0,110), 0, FLinearColor::Transparent, 0);
    ActionStyle = ColdSteelUI::ButtonStyle();
    SliderStyle = FCoreStyle::Get().GetWidgetStyle<FSliderStyle>("Slider");
    GConfig->GetFloat(SettingsSection, TEXT("MasterVolume"), MasterVolume, GGameUserSettingsIni);
    GConfig->GetFloat(SettingsSection, TEXT("HubMusicVolume"), MusicVolume, GGameUserSettingsIni);
    GConfig->GetFloat(SettingsSection, TEXT("MouseScale"), MouseScale, GGameUserSettingsIni);
    GConfig->GetBool(SettingsSection, TEXT("InvertY"), bInvertY, GGameUserSettingsIni);
    MasterVolume = FMath::Clamp(MasterVolume, 0.f, 1.f);
    MusicVolume = FMath::Clamp(MusicVolume, 0.f, 1.f);
    MouseScale = FMath::Clamp(MouseScale, .25f, 3.f);
    if (auto* PC = GetOwningPlayer(); PC && PC->PlayerInput)
    {
        bHasMouseX = PC->PlayerInput->GetAxisProperties(EKeys::MouseX, BaseMouseX);
        bHasMouseY = PC->PlayerInput->GetAxisProperties(EKeys::MouseY, BaseMouseY);
    }
    ApplyLocalSettings();
}

FVector2D UColdSteelGameMenuWidget::ViewportSize() const
{
    const FVector2D Size = UWidgetLayoutLibrary::GetViewportSize(this);
    return Size.X > 1 && Size.Y > 1 ? Size : FVector2D(1280,720);
}

float UColdSteelGameMenuWidget::PanelWidth() const
{
    return FMath::Min(Page == EPage::Main ? 320.f : 560.f, FMath::Max(120.f, float(ViewportSize().X) - 24.f));
}

TSharedRef<SWidget> UColdSteelGameMenuWidget::RebuildWidget()
{
    Body = SNew(SVerticalBox);
    const auto ModalVisibility = [this]() { return bOpen ? EVisibility::Visible : EVisibility::Collapsed; };
    auto Root = SNew(SOverlay)
        + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(12)
        [
            SNew(SBox).WidthOverride(124).HeightOverride(ColdSteelUI::ActionHeight)
            .Visibility_Lambda([this]()
            {
                const auto* PC = GetOwningPlayer<AFPSGAMEPlayerController>();
                return !bOpen && PC && PC->CanOpenGameMenu() ? EVisibility::Visible : EVisibility::Collapsed;
            })
            [
                SNew(SButton).ButtonStyle(&ActionStyle).IsFocusable(false).ContentPadding(FMargin(12,0))
                .OnClicked_Lambda([this]() { if (auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>()) PC->OpenGameMenu(); return FReply::Handled(); })
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(TEXT("菜单"),14,ColdSteelUI::HUDGoldLight)]
                    + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(TEXT("Esc"),14,ColdSteelUI::TextSecondary,true)]
                ]
            ]
        ]
        + SOverlay::Slot()
        [
            SNew(SBorder).Visibility_Lambda(ModalVisibility).BorderImage(&DimBrush).Padding(0)
            .OnMouseButtonDown_Lambda([](const FGeometry&, const FPointerEvent&) { return FReply::Handled(); })
        ]
        + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(FMargin(12,56,12,12))
        [
            SNew(SBox).Visibility_Lambda(ModalVisibility)
            .WidthOverride_Lambda([this]() { return PanelWidth(); })
            .MaxDesiredHeight_Lambda([this]() { return FMath::Max(100.f,float(ViewportSize().Y)-68.f); })
            [
                SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius)
                .CornerRadius(FVector4(ColdSteelUI::PanelRadius)).Padding(0)
                [
                    SNew(SBorder).BorderImage(&PanelBrush).Padding(12).Clipping(EWidgetClipping::ClipToBounds)
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
                        [
                            SNew(SBorder).BorderImage(&HeaderBrush).Padding(FMargin(8,4))
                            [
                                SNew(SHorizontalBox)
                                + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                                [
                                    SNew(STextBlock).AutoWrapText(false).Font(ColdSteelUI::TextFont(18*.75f,true))
                                    .ColorAndOpacity(ColdSteelUI::TextPrimary).Text_Lambda([this]()
                                    {
                                        return Text(Page==EPage::Settings?TEXT("设置"):Page==EPage::Controls?TEXT("操作说明"):Page==EPage::Quit?TEXT("退出游戏"):TEXT("游戏菜单"));
                                    })
                                ]
                                + SHorizontalBox::Slot().AutoWidth().Padding(12,0,0,0)
                                [Action(TEXT("返回"),[this]() { GoBack(); },TEXT("Esc"))]
                            ]
                        ]
                        + SVerticalBox::Slot().FillHeight(1)
                        [
                            SAssignNew(VerticalScroll,SScrollBox).Orientation(Orient_Vertical).ScrollBarThickness(FVector2D(4,4))
                            + SScrollBox::Slot()
                            [
                                SAssignNew(HorizontalScroll,SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(4,4))
                                + SScrollBox::Slot()
                                [
                                    SNew(SBox).WidthOverride_Lambda([this]() { return Page==EPage::Main?288.f:528.f; })[Body.ToSharedRef()]
                                ]
                            ]
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(4,12,4,0)
                        [
                            SNew(STextBlock).AutoWrapText(false).Font(ColdSteelUI::TextFont(12*.75f)).ColorAndOpacity(ColdSteelUI::TextTertiary)
                            .Text_Lambda([this]() { return Text(GetWorld() && GetWorld()->GetNetMode()!=NM_Standalone?TEXT("联机游戏继续运行"):TEXT("Esc 返回 · Tab 切换选项")); })
                        ]
                    ]
                ]
            ]
        ];
    BuildPage();
    // Match the buff HUD's physical-pixel placement rather than applying DPI twice.
    return SNew(SDPIScaler).DPIScale_Lambda([this]() { return 1.f/FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this)); })[Root];
}

TSharedRef<SWidget> UColdSteelGameMenuWidget::Action(const FString& Caption, TFunction<void()> Callback, const FString& Key, bool bDanger)
{
    auto Button = SNew(SButton).ButtonStyle(&ActionStyle).ContentPadding(FMargin(12,0)).HAlign(HAlign_Fill)
        .OnClicked_Lambda([Callback=MoveTemp(Callback)]() { Callback(); return FReply::Handled(); })
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(Caption,14,bDanger?ColdSteelUI::Danger:ColdSteelUI::TextPrimary)]
            + SHorizontalBox::Slot().AutoWidth().Padding(Key.IsEmpty()?0:12,0,0,0).VAlign(VAlign_Center)[Label(Key,14,ColdSteelUI::TextTertiary,true)]
        ];
    if (!DefaultFocus.IsValid()) DefaultFocus = Button;
    return SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)[Button];
}

void UColdSteelGameMenuWidget::AddSection(const FString& Caption)
{
    Body->AddSlot().AutoHeight().Padding(4,12,4,8)[Label(Caption,14,ColdSteelUI::HUDGoldLight)];
}

void UColdSteelGameMenuWidget::AddSlider(const FString& Caption, float Min, float Max, TAttribute<float> Value,
    TFunction<void(float)> Changed, TAttribute<FText> Formatted)
{
    auto Slider = SNew(SSlider).Style(&SliderStyle).MinValue(Min).MaxValue(Max).StepSize(Caption==TEXT("鼠标灵敏度")?.05f:.01f)
        .Value(Value).SliderBarColor(ColdSteelUI::Border).SliderHandleColor(ColdSteelUI::Accent)
        .OnValueChanged_Lambda([this,Changed=MoveTemp(Changed)](float NewValue)
        { Changed(NewValue); bSettingsDirty=true; ApplyLocalSettings(); })
        .OnMouseCaptureEnd_Lambda([this]() { SaveSettings(); })
        .OnControllerCaptureEnd_Lambda([this]() { SaveSettings(); });
    if (!DefaultFocus.IsValid()) DefaultFocus=Slider;
    Body->AddSlot().AutoHeight().Padding(4,0,4,8)
    [
        SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(138)[Label(Caption)]]
            + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0)
            [
                Slider
            ]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(SBox).WidthOverride(74)
                [SNew(STextBlock).Text(Formatted).AutoWrapText(false).Justification(ETextJustify::Right)
                    .Font(ColdSteelUI::NumberFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
            ]
        ]
    ];
}

void UColdSteelGameMenuWidget::BuildPage()
{
    if (!Body) return;
    Body->ClearChildren(); DefaultFocus.Reset();
    auto Add = [this](TSharedRef<SWidget> Widget) { Body->AddSlot().AutoHeight().Padding(0,0,0,8)[Widget]; };
    if (Page==EPage::Main)
    {
        Add(Action(TEXT("回到游戏"),[this]() { if(auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>()) PC->CloseGameMenu(); },TEXT("Esc")));
        Add(Action(TEXT("设置"),[this]() { SetPage(EPage::Settings); }));
        Add(Action(TEXT("操作说明"),[this]() { SetPage(EPage::Controls); }));
        Add(Action(TEXT("退出游戏"),[this]() { QuitError.Reset(); SetPage(EPage::Quit); },FString(),true));
    }
    else if (Page==EPage::Settings)
    {
        AddSection(TEXT("声音"));
        AddSlider(TEXT("总音量"),0,1,TAttribute<float>::CreateLambda([this]() { return MasterVolume; }),
            [this](float V) { MasterVolume=V; },TAttribute<FText>::CreateLambda([this]() { return Text(FString::Printf(TEXT("%d%%"),FMath::RoundToInt(MasterVolume*100))); }));
        AddSlider(TEXT("主神空间音乐"),0,1,TAttribute<float>::CreateLambda([this]() { return MusicVolume; }),
            [this](float V) { MusicVolume=V; },TAttribute<FText>::CreateLambda([this]() { return Text(FString::Printf(TEXT("%d%%"),FMath::RoundToInt(MusicVolume*100))); }));
        AddSection(TEXT("操作"));
        AddSlider(TEXT("鼠标灵敏度"),.25f,3.f,TAttribute<float>::CreateLambda([this]() { return MouseScale; }),
            [this](float V) { MouseScale=V; },TAttribute<FText>::CreateLambda([this]() { return Text(FString::Printf(TEXT("%.2f x"),MouseScale)); }));
        auto ToggleRow = [this,&Add](const FString& Caption, TAttribute<FText> State, TFunction<void()> Toggle, bool Enabled=true)
        {
            Add(SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(4,0)[Label(Caption)]
                + SHorizontalBox::Slot().AutoWidth()
                [SNew(SBox).WidthOverride(172)
                    [SNew(SButton).ButtonStyle(&ActionStyle).IsEnabled(Enabled).HAlign(HAlign_Center)
                        .OnClicked_Lambda([Toggle=MoveTemp(Toggle)]() { Toggle(); return FReply::Handled(); })
                        [SNew(STextBlock).Text(State).AutoWrapText(false).Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]]]);
        };
        ToggleRow(TEXT("反转纵向视角"),TAttribute<FText>::CreateLambda([this]() { return Text(bInvertY?TEXT("开启"):TEXT("关闭")); }),
            [this]() { bInvertY=!bInvertY; bSettingsDirty=true; ApplyLocalSettings(); SaveSettings(); });
        AddSection(TEXT("显示"));
        ToggleRow(TEXT("垂直同步"),TAttribute<FText>::CreateLambda([]() { return Text(UGameUserSettings::GetGameUserSettings()->IsVSyncEnabled()?TEXT("开启"):TEXT("关闭")); }),
            []() { auto* S=UGameUserSettings::GetGameUserSettings(); S->SetVSyncEnabled(!S->IsVSyncEnabled()); ApplyFrameSettings(S); });
        ToggleRow(TEXT("帧率上限"),TAttribute<FText>::CreateLambda([]()
            { const float V=UGameUserSettings::GetGameUserSettings()->GetFrameRateLimit(); return Text(V<=0?TEXT("不限"):FString::Printf(TEXT("%d FPS"),FMath::RoundToInt(V))); }),
            []() { auto* S=UGameUserSettings::GetGameUserSettings(); const TArray<float> Values={60,90,120,144,165,240,0};
                const int32 Index=Values.IndexOfByPredicate([S](float V) { return FMath::IsNearlyEqual(V,S->GetFrameRateLimit()); });
                S->SetFrameRateLimit(Values[(Index+1)%Values.Num()]); ApplyFrameSettings(S); });
        const bool CanChangeWindow=GetWorld() && GetWorld()->WorldType!=EWorldType::PIE;
        ToggleRow(TEXT("显示模式"),TAttribute<FText>::CreateLambda([CanChangeWindow]()
            { return Text(!CanChangeWindow?TEXT("由编辑器控制"):UGameUserSettings::GetGameUserSettings()->GetFullscreenMode()==EWindowMode::Windowed?TEXT("窗口"):TEXT("无边框")); }),
            []() { auto* S=UGameUserSettings::GetGameUserSettings(); S->SetFullscreenMode(S->GetFullscreenMode()==EWindowMode::Windowed?EWindowMode::WindowedFullscreen:EWindowMode::Windowed);
                S->ApplyResolutionSettings(false); S->ConfirmVideoMode(); S->SaveSettings(); },CanChangeWindow);
        Add(Label(TEXT("更改即时生效，自动保存设置。"),12,ColdSteelUI::TextTertiary));
        Add(Action(TEXT("返回菜单"),[this]() { GoBack(); },TEXT("Esc")));
    }
    else if (Page==EPage::Controls)
    {
        const auto KeyRow = [&Add](const TCHAR* Key,const TCHAR* Meaning)
        {
            Add(SNew(SBox).HeightOverride(28)[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(180)[Label(Key,14,ColdSteelUI::HUDGoldLight,true)]]
                + SHorizontalBox::Slot().FillWidth(1)[Label(Meaning)]]);
        };
        AddSection(TEXT("移动与战斗"));
        KeyRow(TEXT("W A S D"),TEXT("移动")); KeyRow(TEXT("鼠标"),TEXT("转动视角"));
        KeyRow(TEXT("Space / Shift"),TEXT("跳跃 / 奔跑")); KeyRow(TEXT("Ctrl / C"),TEXT("滑铲"));
        KeyRow(TEXT("鼠标左键 / 右键"),TEXT("攻击 / 瞄准（随装备变化）"));
        KeyRow(TEXT("R / 长按 R"),TEXT("换弹 / 选择弹药")); KeyRow(TEXT("滚轮"),TEXT("切换武器 / 调节可变倍镜"));
        KeyRow(TEXT("F / L"),TEXT("快速近战 / 检视武器"));
        KeyRow(TEXT("Q E X / 1～0"),TEXT("技能与消耗品快捷槽"));
        KeyRow(TEXT("G"),TEXT("长剑特殊攻击 / 法杖特殊功能"));
        KeyRow(TEXT("Shift+F7 / F7"),TEXT("取出铁铲 / 收起工具"));
        AddSection(TEXT("交互与界面"));
        KeyRow(TEXT("E / Z"),TEXT("交互 / 拾取附近掉落")); KeyRow(TEXT("Tab"),TEXT("背包"));
        KeyRow(TEXT("Caps / P / N"),TEXT("人物状态 / 技能 / 图鉴")); KeyRow(TEXT("J / K"),TEXT("改造台 / 强化台"));
        KeyRow(TEXT("Left Alt"),TEXT("显示或收起交互光标")); KeyRow(TEXT("Esc"),TEXT("关闭当前界面 / 打开菜单"));
        Add(Label(TEXT("技能与快捷物品以底部栏显示的绑定为准。"),12,ColdSteelUI::TextTertiary));
        Add(Action(TEXT("返回菜单"),[this]() { GoBack(); },TEXT("Esc")));
    }
    else
    {
        Add(Label(TEXT("确定退出游戏？"),18));
        Add(Label(GetWorld()->GetNetMode()==NM_Standalone?TEXT("退出前保存角色与建筑进度。 "):TEXT("将离开当前联机会话。"),14,ColdSteelUI::TextSecondary));
        if (!QuitError.IsEmpty()) Add(Label(QuitError,14,ColdSteelUI::Danger));
        Add(Action(TEXT("取消，返回菜单"),[this]() { SetPage(EPage::Main); },TEXT("Esc")));
        Add(Action(TEXT("确认退出"),[this]() { ConfirmQuit(); },FString(),true));
    }
}

void UColdSteelGameMenuWidget::ApplyLocalSettings()
{
    if (GetWorld()) if (auto Audio=GetWorld()->GetAudioDevice()) Audio->SetTransientPrimaryVolume(MasterVolume);
    if (auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>())
    {
        PC->SetHubMusicUserVolume(MusicVolume);
        if (PC->PlayerInput)
        {
            auto X=BaseMouseX, Y=BaseMouseY;
            X.Sensitivity*=MouseScale; Y.Sensitivity*=MouseScale;
            Y.bInvert=BaseMouseY.bInvert!=bInvertY;
            if (bHasMouseX) PC->PlayerInput->SetAxisProperties(EKeys::MouseX,X);
            if (bHasMouseY) PC->PlayerInput->SetAxisProperties(EKeys::MouseY,Y);
        }
    }
}

void UColdSteelGameMenuWidget::SaveSettings()
{
    if (!bSettingsDirty) return;
    GConfig->SetFloat(SettingsSection,TEXT("MasterVolume"),MasterVolume,GGameUserSettingsIni);
    GConfig->SetFloat(SettingsSection,TEXT("HubMusicVolume"),MusicVolume,GGameUserSettingsIni);
    GConfig->SetFloat(SettingsSection,TEXT("MouseScale"),MouseScale,GGameUserSettingsIni);
    GConfig->SetBool(SettingsSection,TEXT("InvertY"),bInvertY,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    bSettingsDirty=false;
}

void UColdSteelGameMenuWidget::SetPage(EPage NewPage)
{
    SaveSettings(); Page=NewPage; BuildPage();
    if (VerticalScroll) VerticalScroll->ScrollToStart();
    if (HorizontalScroll) HorizontalScroll->ScrollToStart();
    if (bOpen)
    {
        if (Page==EPage::Controls) SetUserFocus(GetOwningPlayer());
        else if (DefaultFocus.IsValid()) FSlateApplication::Get().SetKeyboardFocus(DefaultFocus,EFocusCause::SetDirectly);
    }
}

void UColdSteelGameMenuWidget::ShowMenu()
{
    bOpen=true; SetPage(EPage::Main);
}

void UColdSteelGameMenuWidget::HideMenu()
{
    SaveSettings(); bOpen=false;
}

void UColdSteelGameMenuWidget::GoBack()
{
    if (!bOpen) return;
    if (Page!=EPage::Main) SetPage(EPage::Main);
    else if (auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>()) PC->CloseGameMenu();
}

void UColdSteelGameMenuWidget::ConfirmQuit()
{
    SaveSettings();
    bool Saved=true;
    // The local profile owns its disk copy in both standalone and network play.
    if (auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Saved=Profile->SaveNow();
    if (GetWorld()->GetNetMode()==NM_Standalone)
    {
        for (TActorIterator<AVoxelBuildWorld> It(GetWorld()); It; ++It)
            if (It->IsReady() && !It->FlushPersistenceNow()) Saved=false;
    }
    if (!Saved) { QuitError=TEXT("保存失败，请重试或返回游戏。"); BuildPage(); return; }
    UKismetSystemLibrary::QuitGame(this,GetOwningPlayer(),EQuitPreference::Quit,false);
}

FReply UColdSteelGameMenuWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    if (bOpen && Event.GetKey()==EKeys::Escape) { if (!Event.IsRepeat()) GoBack(); return FReply::Handled(); }
    return Super::NativeOnPreviewKeyDown(Geometry,Event);
}

void UColdSteelGameMenuWidget::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren); Body.Reset(); DefaultFocus.Reset(); VerticalScroll.Reset(); HorizontalScroll.Reset();
}
