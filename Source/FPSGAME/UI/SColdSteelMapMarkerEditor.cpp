#include "SColdSteelMapMarkerEditor.h"
#include "TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"
#include "SColdSteelWorldMap.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SViewport.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

TSharedRef<SWidget> SColdSteelMapMarkerEditor::Action(const TCHAR* Caption,TFunction<void()> Click,bool bPrimary)
{
    return SNew(SBox).MinDesiredWidth(72).HeightOverride(ColdSteelUI::ActionHeight)
        [SNew(SButton).ButtonStyle(bPrimary?&PrimaryButton:&Button).IsFocusable(true).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .OnClicked_Lambda([Click](){Click();return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(Caption)).Font(ColdSteelUI::TextFont(14*.75f))
                .ColorAndOpacity(bPrimary?ColdSteelUI::Content:ColdSteelUI::TextPrimary)]];
}

void SColdSteelMapMarkerEditor::Construct(const FArguments& Args,APlayerController* InPlayer,TSharedRef<FColdSteelWorldMapSession> InSession)
{
    Player=InPlayer; Session=InSession; OnSelected=Args._OnSelected;
    SetCanTick(true);
    Button=ColdSteelUI::ButtonStyle();
    PrimaryButton=Button;
    PrimaryButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,ColdSteelUI::ButtonRadius));
    PrimaryButton.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary,ColdSteelUI::ButtonRadius));
    PrimaryButton.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::TextSecondary,ColdSteelUI::ButtonRadius));
    FormBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::CardRadius);
    SelectedBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius,ColdSteelUI::Accent);
    SwatchBrush=ColdSteelUI::RoundedBrush(FLinearColor::White,3,FLinearColor::Transparent,0);
    InputNormal=ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius);
    InputFocus=ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius,ColdSteelUI::Accent);
    Input=FCoreStyle::Get().GetWidgetStyle<FEditableTextBoxStyle>("NormalEditableTextBox");
    Input.SetBackgroundImageNormal(InputNormal).SetBackgroundImageHovered(InputFocus).SetBackgroundImageFocused(InputFocus)
        .SetForegroundColor(ColdSteelUI::TextPrimary).SetBackgroundColor(FLinearColor::White)
        .SetFont(ColdSteelUI::TextFont(14*.75f)).SetPadding(FMargin(8,6));
    auto Label=[](const TCHAR* Caption,float Pixels=14.f)
    {
        return SNew(STextBlock).Text(FText::FromString(Caption)).Font(ColdSteelUI::TextFont(Pixels*.75f))
            .AutoWrapText(false).ColorAndOpacity(ColdSteelUI::TextSecondary);
    };
    auto Colors=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(4,4));
    for (int32 I=0;I<FColdSteelMapMarkers::ColorCount;++I)
        Colors->AddSlot()
            [SNew(SBorder).BorderImage_Lambda([this,I](){return Draft.ColorIndex==I?&SelectedBrush:FCoreStyle::Get().GetBrush("NoBrush");}).Padding(1)
            [SNew(SBox).WidthOverride(36).HeightOverride(ColdSteelUI::ActionHeight)
                [SNew(SButton).ButtonStyle(&Button).IsFocusable(true).ContentPadding(0).HAlign(HAlign_Center).VAlign(VAlign_Center)
                    .ToolTipText(FColdSteelMapMarkers::ColorName(I))
                    .OnClicked_Lambda([this,I](){Draft.ColorIndex=I;Session->MarkerDraft=Draft;++Session->MarkerUIRevision;return FReply::Handled();})
                    [SNew(STextBlock).Text(FColdSteelMapMarkers::ColorName(I))
                        .Font(ColdSteelUI::TextFont(14*.75f,true)).ColorAndOpacity(FColdSteelMapMarkers::Color(I))]]]];
    auto Delete=Action(TEXT("删除此标记"),[this](){Session->Markers.Remove(Draft.Id); Session->SelectedMarker.Invalidate(); Cancel();});
    Delete->SetVisibility(TAttribute<EVisibility>::CreateLambda([this](){return Draft.Id.IsValid()?EVisibility::Visible:EVisibility::Collapsed;}));
    auto Form=SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)
            [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(Draft.Id.IsValid()?TEXT("编辑标记"):TEXT("新建标记"));})
                .Font(ColdSteelUI::TextFont(16*.75f,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,4)
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("标记名称"))]
                + SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Font(ColdSteelUI::NumberFont(12*.75f))
                    .ColorAndOpacity_Lambda([this](){return Name && Name->GetText().ToString().Len()>FColdSteelMapMarkers::LabelLimit?ColdSteelUI::Danger:ColdSteelUI::TextSecondary;})
                    .Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("%d / 32"),Name?Name->GetText().ToString().Len():0));})]]
        + SVerticalBox::Slot().AutoHeight()
            [SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)
                [SAssignNew(Name,SEditableTextBox).Style(&Input).HintText(FText::FromString(TEXT("输入名称，留空使用「标记」")))
                    .SelectAllTextWhenFocused(true).ClearKeyboardFocusOnCommit(false)
                    .OnTextChanged_Lambda([this](const FText& Value)
                    {
                        Draft.Label=Value.ToString(); Error.Reset();
                        if(Session->bEditingMarker){Session->MarkerDraft=Draft;++Session->MarkerUIRevision;}
                    })
                    .OnTextCommitted_Lambda([this](const FText&,ETextCommit::Type Type){if(Type==ETextCommit::OnEnter) Save();})]]
        + SVerticalBox::Slot().AutoHeight().Padding(0,10,0,4)[Label(TEXT("可见范围"))]
        + SVerticalBox::Slot().AutoHeight()
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)
                    [SNew(SBorder).Padding(1).BorderImage_Lambda([this](){return Draft.Visibility==EColdSteelMapMarkerVisibility::Personal?&SelectedBrush:FCoreStyle::Get().GetBrush("NoBrush");})
                        [Action(TEXT("仅本人"),[this](){Draft.Visibility=EColdSteelMapMarkerVisibility::Personal;Session->MarkerDraft=Draft;++Session->MarkerUIRevision;})]]
                + SHorizontalBox::Slot().FillWidth(1)
                    [SNew(SBorder).Padding(1).BorderImage_Lambda([this](){return Draft.Visibility==EColdSteelMapMarkerVisibility::Team?&SelectedBrush:FCoreStyle::Get().GetBrush("NoBrush");})
                        [Action(TEXT("全队可见"),[this](){Draft.Visibility=EColdSteelMapMarkerVisibility::Team;Session->MarkerDraft=Draft;++Session->MarkerUIRevision;})]]]
        + SVerticalBox::Slot().AutoHeight().Padding(0,10,0,4)
            [SNew(STextBlock).Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                .Text_Lambda([this](){return FText::FromString(TEXT("光柱颜色 · ")+FColdSteelMapMarkers::ColorName(Draft.ColorIndex).ToString());})]
        + SVerticalBox::Slot().AutoHeight()[Colors]
        + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)
            [SNew(STextBlock).Font(ColdSteelUI::TextFont(12*.75f)).ColorAndOpacity(ColdSteelUI::Danger).AutoWrapText(true)
                .Text_Lambda([this](){return FText::FromString(Error);})
                .Visibility_Lambda([this](){return Error.IsEmpty()?EVisibility::Collapsed:EVisibility::Visible;})]
        + SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)[Action(TEXT("保存标记"),[this](){Save();},true)]
                + SHorizontalBox::Slot().FillWidth(1)[Action(TEXT("取消"),[this](){Cancel();})]]
        + SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[Delete]
        + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("编辑时暂停移动 · Enter 保存 · Esc 取消"),12)];
    ChildSlot[SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1)
            [SNew(SOverlay)
                + SOverlay::Slot()[SAssignNew(MapHost,SBox)]
                + SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(12)
                    [SNew(SBox)
                        .Visibility_Lambda([this](){return Session->bEditingMarker?EVisibility::Visible:EVisibility::Collapsed;})
                        .WidthOverride_Lambda([this](){return FMath::Clamp(GetCachedGeometry().GetLocalSize().X-24.,120.,360.);})
                        .MaxDesiredHeight_Lambda([this](){return FMath::Max(80.,MapHost->GetCachedGeometry().GetLocalSize().Y-24.);})
                        [SNew(SBorder).BorderImage(&FormBrush).Padding(12)
                            [SNew(SScrollBox).ConsumeMouseWheel(EConsumeMouseWheel::Always)
                                + SScrollBox::Slot()[Form]]]]]
        + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,4)
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,8,0)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("地图标记"))).Font(ColdSteelUI::TextFont(14*.75f,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12,0)
                    [SNew(STextBlock).Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)
                        .Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("我的 %d / %d · 队友 %d"),Session->Markers.OwnedCount(),FColdSteelMapMarkers::Limit,Session->Markers.TeammateCount()));})]
                + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [SNew(STextBlock).Font(ColdSteelUI::TextFont(12*.75f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                        .ColorAndOpacity_Lambda([this](){return !Session->bEditingMarker && (!Error.IsEmpty()||!Session->Markers.ShareError().IsEmpty())?ColdSteelUI::Danger:ColdSteelUI::TextSecondary;})
                        .Text_Lambda([this](){const FString& Message=Error.IsEmpty()?Session->Markers.ShareError():Error;return FText::FromString(!Session->bEditingMarker && !Message.IsEmpty()?Message:TEXT("点击标签定位 · 队友标记只读"));})]]
        + SVerticalBox::Slot().AutoHeight()
            [SNew(SBox).HeightOverride(58)
                [SNew(SOverlay)
                    + SOverlay::Slot().VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("点击地图上的地面，创建你的第一个标记")))
                            .Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                            .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                            .Visibility_Lambda([this](){return Session->Markers.All().IsEmpty()?EVisibility::Visible:EVisibility::Collapsed;})]
                    + SOverlay::Slot()
                        [SNew(SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(6,6))
                            .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                            .Visibility_Lambda([this](){return Session->Markers.All().IsEmpty()?EVisibility::Collapsed:EVisibility::Visible;})
                            + SScrollBox::Slot()[SAssignNew(List,SHorizontalBox)]]]]];
    RebuildList();
}

void SColdSteelMapMarkerEditor::SetMapContent(TSharedRef<SWidget> Content) { MapHost->SetContent(Content); }

void SColdSteelMapMarkerEditor::Begin(const FColdSteelMapMarker& Marker)
{
    if(Session->bEditingMarker)
    { Error=TEXT("请先保存或取消当前编辑，再选择其他标记"); return; }
    if(Marker.bReadOnly)
    {
        Error.Reset();Session->SelectedMarker=Marker.Id;++Session->MarkerUIRevision;
        OnSelected.ExecuteIfBound(Marker);return;
    }
    if (!Marker.Id.IsValid() && Session->Markers.OwnedCount()>=FColdSteelMapMarkers::Limit)
    { Error=TEXT("已达 10 个标记，请先删除一个"); return; }
    Draft=Marker; Session->SelectedMarker=Marker.Id; Error.Reset();
    Session->MarkerDraft=Draft; ++Session->MarkerUIRevision;
    Session->bEditingMarker=true;
    Name->SetText(FText::FromString(Draft.Label));
    auto* PC=Player.Get();
    if (PC)
    {
        if (!bOwnsMoveBlock) { PC->SetIgnoreMoveInput(true); bOwnsMoveBlock=true; }
        if (PC->PlayerInput) PC->PlayerInput->FlushPressedKeys();
        FInputModeUIOnly Mode;
        Mode.SetWidgetToFocus(Name);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        PC->SetInputMode(Mode);
    }
}

void SColdSteelMapMarkerEditor::FinishEditing(bool bRestoreInput)
{
    Session->bEditingMarker=false;
    Session->MarkerDraft.Reset(); ++Session->MarkerUIRevision;
    if (auto* PC=Player.Get())
    {
        if (bOwnsMoveBlock) { PC->SetIgnoreMoveInput(false); bOwnsMoveBlock=false; }
        const auto* Loading=PC->GetGameInstance()?PC->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
        if (bRestoreInput && (!Loading || !Loading->OwnsPlayerCursor()))
        {
            FInputModeGameAndUI Mode;
            if (auto* Viewport=PC->GetWorld()->GetGameViewport()) Mode.SetWidgetToFocus(Viewport->GetGameViewportWidget());
            Mode.SetHideCursorDuringCapture(false);
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            PC->SetInputMode(Mode);
            UWidgetBlueprintLibrary::SetFocusToGameViewport();
        }
    }
}

SColdSteelMapMarkerEditor::~SColdSteelMapMarkerEditor() { FinishEditing(false); }

void SColdSteelMapMarkerEditor::Cancel()
{
    FinishEditing(true); Error.Reset();
}

void SColdSteelMapMarkerEditor::Save()
{
    if (!Session->bEditingMarker) return;
    Draft.Label=Name->GetText().ToString();
    if (FColdSteelMapMarkers::CleanLabel(Draft.Label)!=Draft.Label.TrimStartAndEnd() || Draft.Label.Len()>FColdSteelMapMarkers::LabelLimit)
    { Error=TEXT("名称最多 32 字，请勿使用换行或控制字符"); return; }
    if (!Draft.Id.IsValid() && !Session->Markers.IsActive(Draft))
    { Error=TEXT("地图已切换，请取消后重新选点"); return; }
    if (!Session->Markers.Save(Draft)) { Error=Session->Markers.ShareError().IsEmpty()?TEXT("无法保存，请重新选点或删除一个标记"):Session->Markers.ShareError(); return; }
    Session->SelectedMarker=Draft.Id;
    FinishEditing(true); Error.Reset(); RebuildList();
}

void SColdSteelMapMarkerEditor::RebuildList()
{
    SeenRevision=Session->Markers.Revision();
    List->ClearChildren();
    for (const auto& M:Session->Markers.All())
    {
        const FGuid Id=M.Id;
        const FString Scope=M.bReadOnly?TEXT("队友 ")+M.OwnerName:FColdSteelMapMarkers::VisibilityName(M.Visibility).ToString();
        const FString Where=Scope+TEXT(" · ")+M.Area+(M.bDungeon?TEXT(" · ")+FColdSteelDungeonMap::FloorName(M.Floor):FString());
        List->AddSlot().AutoWidth().Padding(0,0,6,0)
            [SNew(SBorder).Padding(1)
                .BorderImage_Lambda([this,Id](){return Session->SelectedMarker==Id?&SelectedBrush:FCoreStyle::Get().GetBrush("NoBrush");})
            [SNew(SBox).WidthOverride(188).HeightOverride(48)
                [SNew(SButton).ButtonStyle(&Button).IsFocusable(false).ContentPadding(FMargin(10,4))
                    .ToolTipText(FText::FromString(M.Label+TEXT(" · ")+Where))
                    .OnClicked_Lambda([this,Id]()
                    {
                        if(const auto* Mark=Session->Markers.Find(Id))
                        {
                            const bool bWasEditing=Session->bEditingMarker;
                            Begin(*Mark);
                            if(!bWasEditing && Session->bEditingMarker) OnSelected.ExecuteIfBound(*Mark);
                        }
                        return FReply::Handled();
                    })
                    [SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)
                            [SNew(SBox).WidthOverride(10).HeightOverride(10)
                                [SNew(SImage).Image(&SwatchBrush).ColorAndOpacity(FColdSteelMapMarkers::Color(M.ColorIndex))]]
                        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [SNew(SVerticalBox)
                                + SVerticalBox::Slot().AutoHeight()
                                    [SNew(STextBlock).Text(FText::FromString(M.Label)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                                        .Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                                + SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)
                                    [SNew(STextBlock).Text(FText::FromString(Where)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                                        .Font(ColdSteelUI::TextFont(12*.75f)).ColorAndOpacity(ColdSteelUI::TextSecondary)]]]]]];
    }
}

void SColdSteelMapMarkerEditor::Tick(const FGeometry&,double,float)
{
    if (SeenRevision==Session->Markers.Revision()) return;
    if (Session->bEditingMarker && Draft.bDungeon && Draft.LayoutSerial!=Session->DungeonMap.LayoutSerial) Cancel();
    if (Session->bEditingMarker && Draft.Id.IsValid() && !Session->Markers.Find(Draft.Id)) Cancel();
    if (Session->SelectedMarker.IsValid() && !Session->Markers.Find(Session->SelectedMarker)) Session->SelectedMarker.Invalidate();
    RebuildList();
}

FReply SColdSteelMapMarkerEditor::OnPreviewKeyDown(const FGeometry&,const FKeyEvent& Event)
{
    if (Session->bEditingMarker && Event.GetKey()==EKeys::Escape)
    { if(!Event.IsRepeat()) Cancel(); return FReply::Handled(); }
    return FReply::Unhandled();
}
