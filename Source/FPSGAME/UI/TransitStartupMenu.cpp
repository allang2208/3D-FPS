#include "TransitLoadingSubsystem.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelUIStyle.h"
#include "GameResourcePreparation.h"
#include "../Skills/PlayerSkillPreparation.h"
#include "Brushes/SlateDynamicImageBrush.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "RHI.h"
#include "RHIStats.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "MoviePlayer.h"
#include "ShaderPipelineCache.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Styling/CoreStyle.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "CommonActivatableWidget.h"
#include "Dom/JsonObject.h"
#include "Engine/LocalPlayer.h"
#include "Framework/Application/SlateUser.h"
#include "Input/CommonUIActionRouterBase.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"
#include "Widgets/SViewport.h"

#include "TransitLoadingViewPrivate.h"

namespace TransitLoading
{
class SStartupMenuRoot : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SStartupMenuRoot) {}
        SLATE_ARGUMENT(TSharedPtr<FStartupLoadingView>, View)
        SLATE_DEFAULT_SLOT(FArguments, Content)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args) { State=Args._View;ChildSlot[Args._Content.Widget]; }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent& Event) override
    {
        if(Event.GetKey()==EKeys::Escape)
        {
            if(State&&State->Page!=0)State->Page=0;
            return FReply::Handled();
        }
        return FReply::Unhandled();
    }
private:
    TSharedPtr<FStartupLoadingView> State;
};
}

void UTransitLoadingSubsystem::ShowStartupMenu(APlayerController* Controller)
{
    if(!Controller||!Controller->IsLocalController()||!FSlateApplication::IsInitialized()||StartupOverlay)return;
    if(GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(bStartupChosen)
    {
        ApplyLoadingBudget();
        if(bCompletePreload&&!View){BeginTransition(UGameplayStatics::GetCurrentLevelName(this,true));bDestinationLoaded=true;}
        return;
    }
    auto* VP=GetGameInstance()->GetGameViewportClient();
    if(!VP)return;
    if(!View){BeginTransition(UGameplayStatics::GetCurrentLevelName(this,true));bDestinationLoaded=true;}
    StartupController=Controller;StartupViewport=VP;
    bStartupPreviousIgnore=VP->IgnoreInput();bStartupPreviousCursor=Controller->bShowMouseCursor;
    bStartupPausedWorld=!UGameplayStatics::IsGamePaused(this)&&Controller->SetPause(true);
    VP->SetIgnoreInput(true);Controller->bShowMouseCursor=true;
    StartupView=MakeShared<FStartupLoadingView>();StartupView->PreviousMode=bCompletePreload?1:0;
    const auto State=StartupView;
    TWeakObjectPtr<UGameViewportClient> WeakVP=VP;
    GConfig->GetString(TEXT("FPSGAME.Menu"),TEXT("Nick"),State->Nick,GGameUserSettingsIni);
    GConfig->GetString(TEXT("FPSGAME.Menu"),TEXT("RoomPassword"),State->Password,GGameUserSettingsIni);
    // A persistent per-player default room code. The host can share the value
    // shown in the field; joiners replace it with the host's code.
    if(State->Password.IsEmpty())
        State->Password=FGuid::NewGuid().ToString(EGuidFormats::Digits).Left(6).ToUpper();
    {
        FString Joined;
        if(GConfig->GetString(TEXT("FPSGAME.Menu"),TEXT("RecentHosts"),Joined,GGameUserSettingsIni))
            Joined.ParseIntoArray(State->RecentHosts,TEXT(","),true);
    }
    {
        const FString BgFile=FPaths::ProjectContentDir()/TEXT("UI/MainMenu/start-screen-background.png");
        if(FPaths::FileExists(BgFile))State->Background=MakeShared<FSlateDynamicImageBrush>(FName(*BgFile),FVector2D(2048,1536));
    }
    if(!PendingMenuStatus.IsEmpty())
    {State->StatusLine=PendingMenuStatus;State->bStatusError=bPendingMenuError;PendingMenuStatus.Empty();bPendingMenuError=false;}
    // 子页统一套玻璃面板；主页按原版菜单样式直接压在背景图上（无面板窄列）。
    auto PanelPage=[State,WeakVP](TSharedRef<SWidget> Content) -> TSharedRef<SWidget>
    {
        return SNew(SBox)
            .WidthOverride_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(200.f,FMath::Min(560.f,float(Size.X)-48)));})
            .MaxDesiredHeight_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(120.f,float(Size.Y)-48));})
            [SNew(SBorder).BorderImage(&State->Panel).Padding(24)
                [ColdSteelUI::ApplyGoldScroll(SNew(SScrollBox)+SScrollBox::Slot()[Content],FVector2D(5.5f,5.5f),FMargin(4,0,0,0),true)]];
    };
    auto Eyebrow=[](const TCHAR* Text) -> TSharedRef<SWidget>
    {
        return SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::NumberFont(9))
            .Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextTertiary);
    };
    auto MenuBtn=[State](const TCHAR* Label,TFunction<void()> Fn,bool bPrimary=false,bool bDanger=false) -> TSharedRef<SWidget>
    {
        return SNew(SButton).ButtonStyle(bPrimary?&State->Primary:&State->Button)
            .ContentPadding(FMargin(0,13)).HAlign(HAlign_Center)
            .OnClicked_Lambda([Fn](){Fn();return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(Label))
                .Font(ColdSteelUI::TextFont(bPrimary?13.f:11.f,bPrimary))
                .ColorAndOpacity(bPrimary?FSlateColor(ColdSteelUI::Gray(18)):
                    (bDanger?FSlateColor(ColdSteelUI::Danger):FSlateColor(ColdSteelUI::TextPrimary)))];
    };
    auto StatusLine=[State]() -> TSharedRef<SWidget>
    {
        return SNew(STextBlock).Text_Lambda([State](){return FText::FromString(State->StatusLine);})
            .Font(ColdSteelUI::NumberFont(9)).Justification(ETextJustify::Center)
            .ColorAndOpacity_Lambda([State](){return FSlateColor(State->bStatusError?ColdSteelUI::Danger:ColdSteelUI::TextSecondary);});
    };
    TSharedPtr<SButton> FocusButton;
    // ----- 主页 -----
    auto MainPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 接入终端"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("无 尽 轮 回")))
            .Font(ColdSteelUI::TextFont(26,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("第一人称动作 RPG")))
            .Font(ColdSteelUI::TextFont(10.5f)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("V 0.1.0")))
            .Font(ColdSteelUI::NumberFont(8)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,24,0,0)
        [SAssignNew(FocusButton,SButton).ButtonStyle(&State->Primary).ContentPadding(FMargin(0,14)).HAlign(HAlign_Center)
            .OnClicked_Lambda([State](){State->Page=1;return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(TEXT("开 始 游 戏"))).Font(ColdSteelUI::TextFont(13,true)).ColorAndOpacity(ColdSteelUI::Gray(18))]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("多 人 游 戏"),[State](){State->Page=2;})]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("设    置"),[State](){State->Page=4;})]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[MenuBtn(TEXT("操作说明"),[State](){State->Page=3;})]
            +SHorizontalBox::Slot().FillWidth(1).Padding(10,0,0,0)[MenuBtn(TEXT("退出游戏"),[this](){MenuQuitGame();},false,true)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,16,0,0)[StatusLine()]
        +SVerticalBox::Slot().AutoHeight().Padding(0,14,0,0)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,11))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("快 捷 操 作")))
                    .Font(ColdSteelUI::NumberFont(8)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock)
                    .Text(FText::FromString(TEXT("基础操作会在实际游玩中逐步提示。完整键位可随时从「操作说明」查看。")))
                    .Font(ColdSteelUI::TextFont(10)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]]];
    // ----- 进入方式 -----
    auto ModeOption=[State](const TCHAR* Title,const TCHAR* Desc,int32 Mode) -> TSharedRef<SWidget>
    {
        return SNew(SButton).ButtonStyle(&State->Button).ContentPadding(16).HAlign(HAlign_Fill)
            .OnClicked_Lambda([State,Mode](){State->RequestedMode=Mode;return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(FString(Title)+(State->PreviousMode==Mode?TEXT("  ·  上次选择"):TEXT(""))))
                    .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Text(FText::FromString(Desc))
                    .Font(ColdSteelUI::TextFont(10)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
    };
    auto StartPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 接入终端"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("选 择 进 入 方 式")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[ModeOption(TEXT("快速测试"),TEXT("优先进入游戏，高清纹理在游玩时逐步加载。适合快速调试。"),0)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[ModeOption(TEXT("完整预加载"),TEXT("场景、装备与高清纹理准备完成后再进入。等待更久，占用更多显存；资源未就绪会显示原因并保留在加载界面。"),1)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 联机终端 -----
    FString LocalIps;
    if(auto* Sub=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM))
    {
        TArray<TSharedPtr<FInternetAddr>> Addrs;
        if(Sub->GetLocalAdapterAddresses(Addrs))
            for(const auto& A:Addrs)
            {
                if(!A.IsValid())continue;
                const FString S=A->ToString(false);
                if(!S.IsEmpty()&&S!=TEXT("127.0.0.1")&&!S.StartsWith(TEXT("169.254."))&&!S.Contains(TEXT(":")))
                    LocalIps+=LocalIps.IsEmpty()?S:TEXT(" / ")+S;
            }
    }
    auto MpPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 联机协议"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("联 机 终 端")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("建立房间等待好友接入，或按地址加入他人房间。")))
            .Font(ColdSteelUI::TextFont(10)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock).Text(FText::FromString(TEXT("昵称")))
            .Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,14)
        [SAssignNew(State->NickBox,SEditableTextBox).Style(&State->InputStyle).Padding(FMargin(10,9))
            .Text(FText::FromString(State->Nick)).HintText(FText::FromString(TEXT("显示给其他玩家的名字")))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock).Text(FText::FromString(TEXT("房间口令")))
            .Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)
        [SAssignNew(State->PasswordBox,SEditableTextBox).Style(&State->InputStyle).Padding(FMargin(10,9))
            .Text(FText::FromString(State->Password))
            .HintText(FText::FromString(TEXT("加入时填写房主显示的口令")))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[SNew(STextBlock).Text(FText::FromString(TEXT("创建房间时若留空会自动生成口令，并显示在此栏。")))
            .Font(ColdSteelUI::TextFont(9)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[MenuBtn(TEXT("创 建 房 间（主机）"),[this](){MenuHostRoom();},true)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,4)[SNew(STextBlock).Text(FText::FromString(TEXT("以当前场景开启监听房间，好友通过你的 IP 加入。")))
            .Font(ColdSteelUI::TextFont(9)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).Text(FText::FromString(
            LocalIps.IsEmpty()?TEXT("本机地址：未检测到局域网 IP"):FString::Printf(TEXT("本机地址：%s:7777"),*LocalIps)))
            .Font(ColdSteelUI::NumberFont(9)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,14)[SNew(SSeparator).Orientation(Orient_Horizontal)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock).Text(FText::FromString(TEXT("加入房间")))
            .Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(State->AddressBox,SEditableTextBox).Style(&State->InputStyle).Padding(FMargin(10,8))
                .HintText(FText::FromString(TEXT("IP[:端口]，例如 192.168.1.10:7777")))]
            +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0).VAlign(VAlign_Center)
            [SNew(SButton).ButtonStyle(&State->Button).ContentPadding(FMargin(18,8))
                .OnClicked_Lambda([this](){MenuJoinByAddress(TEXT(""));return FReply::Handled();})
                [SNew(STextBlock).Text(FText::FromString(TEXT("连 接"))).Font(ColdSteelUI::TextFont(11,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]];
    if(State->RecentHosts.Num()>0)
    {
        MpPage->AddSlot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("最 近 连 接")))
            .Font(ColdSteelUI::NumberFont(8)).ColorAndOpacity(ColdSteelUI::TextTertiary)];
        for(const FString& Host:State->RecentHosts)
        {
            const FString HostCopy=Host;
            MpPage->AddSlot().AutoHeight().Padding(0,6,0,0)
            [SNew(SButton).ButtonStyle(&State->Button).ContentPadding(FMargin(12,7)).HAlign(HAlign_Left)
                .OnClicked_Lambda([this,HostCopy](){MenuJoinByAddress(HostCopy);return FReply::Handled();})
                [SNew(STextBlock).Text(FText::FromString(HostCopy)).Font(ColdSteelUI::NumberFont(10)).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
        }
    }
    MpPage->AddSlot().AutoHeight().Padding(0,14,0,0)[StatusLine()];
    MpPage->AddSlot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 操作说明 -----
    auto HelpPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 键位"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("操 作 说 明")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,12))
            [SNew(STextBlock)
                .Text(FText::FromString(TEXT("W A S D　移动\n空格　跳跃\nShift　冲刺\nCtrl / C　滑铲\n鼠标左键　攻击 / 开火\n鼠标右键　瞄准\nR　换弹\nF　快速近战\nG　符文刃\nL　检视武器\nTab / B　背包\nEsc　系统菜单")))
                .Font(ColdSteelUI::TextFont(10.5f)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 设置 -----
    auto SettingsPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 终端设置"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("设    置")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,12))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([State](){
                    return FText::FromString(FString::Printf(TEXT("进入方式：%s"),State->PreviousMode==1?TEXT("完整预加载"):TEXT("快速测试")));})
                    .Font(ColdSteelUI::TextFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextSecondary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock)
                    .Text(FText::FromString(TEXT("载入档位可在「开始游戏」里切换。画面、音频与键位设置将在后续版本开放。")))
                    .Font(ColdSteelUI::TextFont(9.5f)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    StartupOverlay=SNew(TransitLoading::SStartupMenuRoot).View(State)
        [SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.031f,0.051f,0.070f,1))]
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill).HAlign(HAlign_Center).VAlign(VAlign_Bottom)
            [SNew(SImage).Image(State->Background.Get())]]
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.016f,0.031f,0.070f,0.30f))]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(24)
        [SNew(SWidgetSwitcher).WidgetIndex_Lambda([State](){return State->Page;})
            +SWidgetSwitcher::Slot()[SNew(SBox).WidthOverride(300)[MainPage]]
            +SWidgetSwitcher::Slot()[PanelPage(StartPage)]
            +SWidgetSwitcher::Slot()[PanelPage(MpPage)]
            +SWidgetSwitcher::Slot()[PanelPage(HelpPage)]
            +SWidgetSwitcher::Slot()[PanelPage(SettingsPage)]]];
    VP->AddViewportWidgetContent(StartupOverlay.ToSharedRef(),100010);
    Controller->SetInputMode(FInputModeUIOnly().SetWidgetToFocus(FocusButton).SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock));
    FSlateApplication::Get().SetAllUserFocus(FocusButton,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::RemoveStartupMenu()
{
    if(auto* PC=StartupController.Get())
    {
        if(bStartupPausedWorld)PC->SetPause(false);
        PC->bShowMouseCursor=bStartupPreviousCursor;PC->SetInputMode(FInputModeGameOnly());
    }
    if(auto* VP=StartupViewport.Get())
    {
        if(StartupOverlay)VP->RemoveViewportWidgetContent(StartupOverlay.ToSharedRef());
        VP->SetIgnoreInput(bStartupPreviousIgnore);
    }
    StartupOverlay.Reset();StartupView.Reset();StartupViewport.Reset();StartupController.Reset();bStartupPausedWorld=false;
    if(Overlay&&FSlateApplication::IsInitialized())FSlateApplication::Get().SetAllUserFocus(Overlay,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::ChooseLoadingMode(bool Complete)
{
    bStartupChosen=true;bCompletePreload=Complete;
    GConfig->SetInt(TEXT("FPSGAME.Loading"),TEXT("Mode"),Complete?1:0,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    ResourcePreparation.Reset();ReleasePreparedPlayer();bPreparationFailed=false;
    if(SkillPreparation)SkillPreparation->Cancel();
    bSkillPreparationStarted=false;
    ApplyLoadingBudget();RemoveStartupMenu();
    if(View){View->ReturnToMenu=Complete&&bScenePrepared;View->RetryAvailable=false;View->Opacity=1;View->Progress=0;StartedAt=FPlatformTime::Seconds();View->Start=StartedAt;}
    if(bScenePrepared)CompletePreparation();
}

void UTransitLoadingSubsystem::MenuApplyNick()
{
    if(!StartupView)return;
    FString Nick=StartupView->NickBox.IsValid()?StartupView->NickBox->GetText().ToString():StartupView->Nick;
    Nick=Nick.TrimStartAndEnd();
    Nick.ReplaceInline(TEXT("?"),TEXT(""));Nick.ReplaceInline(TEXT("&"),TEXT(""));
    Nick.ReplaceInline(TEXT("/"),TEXT(""));Nick.ReplaceInline(TEXT("="),TEXT(""));
    Nick.ReplaceInline(TEXT(" "),TEXT(""));Nick.ReplaceInline(TEXT("\t"),TEXT(""));
    if(Nick.Len()>20)Nick=Nick.Left(20);
    StartupView->Nick=Nick;
    GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("Nick"),*Nick,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
}

void UTransitLoadingSubsystem::MenuApplyPassword()
{
    if(!StartupView)return;
    FString Password=StartupView->PasswordBox.IsValid()
        ?StartupView->PasswordBox->GetText().ToString():StartupView->Password;
    Password.TrimStartAndEndInline();
    FString Clean;
    for(const TCHAR Ch:Password)
        if(FChar::IsAlnum(Ch)&&Clean.Len()<24)Clean.AppendChar(Ch);
    StartupView->Password=Clean;
    if(StartupView->PasswordBox.IsValid())StartupView->PasswordBox->SetText(FText::FromString(Clean));
    GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("RoomPassword"),*Clean,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
}

void UTransitLoadingSubsystem::MenuHostRoom()
{
    MenuApplyNick();MenuApplyPassword();
    if(!StartupView||!GetWorld())return;
    if(StartupView->Password.IsEmpty())
    {
        StartupView->Password=FGuid::NewGuid().ToString(EGuidFormats::Digits).Left(6).ToUpper();
        if(StartupView->PasswordBox.IsValid())
            StartupView->PasswordBox->SetText(FText::FromString(StartupView->Password));
        GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("RoomPassword"),*StartupView->Password,GGameUserSettingsIni);
        GConfig->Flush(false,GGameUserSettingsIni);
    }
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    const FString Nick=StartupView->Nick;
    const int32 Mode=StartupView->PreviousMode;
    FString Options=TEXT("listen");
    bool bHasOption=false;
    const auto AppendOption=[&Options,&bHasOption](const FString& Option)
    {
        Options+=bHasOption?TEXT("&"):TEXT("?");
        Options+=Option;
        bHasOption=true;
    };
    if(!Nick.IsEmpty())AppendOption(FString::Printf(TEXT("Name=%s"),*Nick));
    if(!StartupView->Password.IsEmpty())AppendOption(FString::Printf(TEXT("Password=%s"),*StartupView->Password));
    ChooseLoadingMode(Mode==1);
    UGameplayStatics::OpenLevel(this,FName(*Map),true,Options);
}

void UTransitLoadingSubsystem::MenuJoinByAddress(FString Address)
{
    MenuApplyNick();MenuApplyPassword();
    if(!StartupView)return;
    Address=Address.TrimStartAndEnd();
    if(Address.IsEmpty()&&StartupView->AddressBox.IsValid())
        Address=StartupView->AddressBox->GetText().ToString().TrimStartAndEnd();
    if(Address.IsEmpty()||Address.Contains(TEXT("?"))||Address.Contains(TEXT("&"))||Address.Contains(TEXT(" ")))
    {
        StartupView->StatusLine=TEXT("地址无效：请输入 IP 或 IP:端口，例如 192.168.1.10:7777");
        StartupView->bStatusError=true;
        return;
    }
    StartupView->StatusLine=FString::Printf(TEXT("正在连接 %s …"),*Address);
    StartupView->bStatusError=false;
    StartupView->RecentHosts.Remove(Address);
    StartupView->RecentHosts.Insert(Address,0);
    if(StartupView->RecentHosts.Num()>4)StartupView->RecentHosts.SetNum(4);
    GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("RecentHosts"),*FString::Join(StartupView->RecentHosts,TEXT(",")),GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    const FString Nick=StartupView->Nick;
    const int32 Mode=StartupView->PreviousMode;
    ChooseLoadingMode(Mode==1);
    TArray<FString> Args;
    if(!Nick.IsEmpty())Args.Add(FString::Printf(TEXT("Name=%s"),*Nick));
    if(!StartupView->Password.IsEmpty())Args.Add(FString::Printf(TEXT("Password=%s"),*StartupView->Password));
    UGameplayStatics::OpenLevel(this,FName(*Address),true,FString::Join(Args,TEXT("&")));
}

void UTransitLoadingSubsystem::MenuQuitGame()
{
    if(!UWildlifeSubsystem::FlushPendingLoot(GetWorld()))
    {
        if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Model->PostNotice(TEXT("暂时无法退出"),TEXT("掉落保存失败，请稍后重试。"));
        return;
    }
    UKismetSystemLibrary::QuitGame(this,StartupController.Get(),EQuitPreference::Quit,false);
}

