#include "ColdSteelIncineratorWidget.h"
#include "ColdSteelIncineratorStorage.h"
#include "ColdSteelIncineration.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Text/STextBlock.h"

class SColdSteelIncineratorPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelIncineratorPanel){} SLATE_ARGUMENT(UColdSteelIncineratorWidget*,Owner) SLATE_END_ARGS()
    void Construct(const FArguments& Args){Owner=Args._Owner;Build();Reset();}
    static FText SingleLine(FString Text)
    {
        Text.ReplaceInline(TEXT("\r\n"),TEXT(" · "));
        Text.ReplaceInline(TEXT("\n"),TEXT(" · "));
        Text.ReplaceInline(TEXT("\r"),TEXT(" · "));
        return FText::FromString(Text);
    }
    TSharedRef<STextBlock> Label(const FString& Text,float Size,bool Bold=false)
    {return SNew(STextBlock).Text(SingleLine(Text)).Font(GunsmithUI::TextFont(Size/Scale,Bold)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false).WrapTextAt(0);}
    TSharedRef<SWidget> HorizontalText(const TSharedRef<SWidget>& Text)
    {return SNew(SScrollBox).Orientation(Orient_Horizontal).AllowOverscroll(EAllowOverscroll::No)
        .ScrollBarThickness(FVector2D(4/Scale)).Clipping(EWidgetClipping::ClipToBounds)+SScrollBox::Slot()[Text];}
    TSharedRef<SWidget> Action(const FString& Text,TFunction<FReply()> Function)
    {return SNew(SBox).HeightOverride(36/Scale).MinDesiredWidth(64/Scale)[SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center).VAlign(VAlign_Center).ContentPadding(FMargin(8/Scale,0)).OnClicked_Lambda(MoveTemp(Function))[Label(Text,14)]];}
    void Build()
    {
        Scale=FMath::Max(.01f,ColdSteelUI::PixelScale(Owner.Get()));Buttons=ColdSteelUI::ButtonStyle(Scale);
        Frame=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale);
        Fallback=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale);
        Header=ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,0);
        Card=ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale);
        InputStyle=FCoreStyle::Get().GetWidgetStyle<FEditableTextBoxStyle>(TEXT("NormalEditableTextBox"));
        InputStyle.SetBackgroundImageNormal(Card).SetBackgroundImageHovered(Card).SetBackgroundImageFocused(Card).SetForegroundColor(ColdSteelUI::TextPrimary);
        auto Heading=SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(TEXT("焚化炉"),20,true)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8/Scale,0)[SAssignNew(Capacity,STextBlock).Font(GunsmithUI::NumberFont(12/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(false).WrapTextAt(0)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(64/Scale)[Action(TEXT("关闭"),[this](){Owner->RequestClose();return FReply::Handled();})]];
        auto Actions=SNew(SUniformGridPanel).SlotPadding(FMargin(4/Scale,0));
        Actions->AddSlot(0,0)[Action(TEXT("全部取回"),[this](){Retrieve();return FReply::Handled();})];
        Actions->AddSlot(1,0)[SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .ContentPadding(FMargin(8/Scale,0)).IsEnabled_Lambda([this](){return Ready()&&Preview.bValid&&!bSubmitting;})
            .OnClicked_Lambda([this](){Review();return FReply::Handled();})[Label(TEXT("焚化"),14,true)]];
        auto ConfirmActions=SNew(SUniformGridPanel).SlotPadding(FMargin(4/Scale,0));
        ConfirmActions->AddSlot(0,0)[Action(TEXT("取消"),[this](){Cancel();return FReply::Handled();})];
        ConfirmActions->AddSlot(1,0)[Action(TEXT("确认焚化"),[this](){Confirm();return FReply::Handled();})];
        auto Contents=SNew(SVerticalBox);
        Contents->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(&Header).Padding(FMargin(16/Scale,10/Scale))[Heading]];
        Contents->AddSlot().AutoHeight().Padding(16/Scale,8/Scale)[HorizontalText(Label(TEXT("待焚化物品 · 放入后仍可取回"),14,true))];
        Contents->AddSlot().FillHeight(1).Padding(4/Scale,0)
            [SAssignNew(GridScroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No).ScrollBarThickness(FVector2D(6/Scale))
                +SScrollBox::Slot()[Owner->InputBoard()->TakeWidget()]];
        Contents->AddSlot().AutoHeight().Padding(16/Scale,4/Scale)[HorizontalText(Label(TEXT("拖动 / 右键取放 · Shift 单击拆分 · 拖动时 F 旋转"),12))];
        auto Yield=SNew(SVerticalBox);
        Yield->AddSlot().AutoHeight()[Label(TEXT("预计收获"),16,true)];
        Yield->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[SNew(SBox).HeightOverride(64/Scale)
            [HorizontalText(SAssignNew(YieldText,STextBlock).Font(GunsmithUI::TextFont(14/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(false).WrapTextAt(0))]];
        Contents->AddSlot().AutoHeight().Padding(12/Scale,6/Scale)[SAssignNew(YieldBox,SBorder).BorderImage(&Card).Padding(FMargin(12/Scale,8/Scale))[Yield]];
        auto Confirmation=SNew(SVerticalBox);
        Confirmation->AddSlot().AutoHeight()[HorizontalText(Label(TEXT("确认焚化投入区内全部物品？"),16,true))];
        Confirmation->AddSlot().AutoHeight().Padding(0,6/Scale)[SNew(SBox).HeightOverride(84/Scale)
            [HorizontalText(SAssignNew(ConfirmText,STextBlock).Font(GunsmithUI::TextFont(14/Scale)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false).WrapTextAt(0))]];
        Confirmation->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(36/Scale)[ConfirmActions]];
        Contents->AddSlot().AutoHeight().Padding(12/Scale,0)[SAssignNew(ConfirmBox,SBorder).BorderImage(&Card).Padding(FMargin(12/Scale,8/Scale)).Visibility(EVisibility::Collapsed)[Confirmation]];
        auto AmmoControls=SNew(SVerticalBox);
        AmmoControls->AddSlot().AutoHeight()[HorizontalText(SAssignNew(AmmoCaption,STextBlock).Font(GunsmithUI::TextFont(14/Scale)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false).WrapTextAt(0))];
        AmmoControls->AddSlot().AutoHeight().Padding(0,6/Scale)[SNew(SBox).HeightOverride(36/Scale)
            [SAssignNew(AmmoQuantity,SEditableTextBox).Style(&InputStyle).Font(GunsmithUI::NumberFont(14/Scale))
                .OnTextCommitted_Lambda([this](const FText&,ETextCommit::Type Type){if(Type==ETextCommit::OnEnter)AcceptAmmo();})]];
        AmmoControls->AddSlot().AutoHeight()[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Action(TEXT("取消"),[this](){Cancel();return FReply::Handled();})]
            +SHorizontalBox::Slot().FillWidth(1).Padding(8/Scale,0,0,0)[Action(TEXT("投入弹药"),[this](){AcceptAmmo();return FReply::Handled();})]];
        Contents->AddSlot().AutoHeight().Padding(12/Scale,0)[SAssignNew(AmmoBox,SBorder).BorderImage(&Card).Padding(FMargin(12/Scale,8/Scale)).Visibility(EVisibility::Collapsed)[AmmoControls]];
        Contents->AddSlot().AutoHeight().Padding(16/Scale,6/Scale)[SNew(SBox).HeightOverride(34/Scale)
            [HorizontalText(SAssignNew(Status,STextBlock).Font(GunsmithUI::TextFont(12/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(false).WrapTextAt(0))]];
        Contents->AddSlot().AutoHeight().Padding(8/Scale,4/Scale,8/Scale,12/Scale)[SAssignNew(ActionBox,SBox).HeightOverride(36/Scale)[Actions]];
        ChildSlot[SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength)
            .BlurRadius(ColdSteelUI::GlassBlurRadius).CornerRadius(FVector4(10/Scale,10/Scale,10/Scale,10/Scale)).LowQualityFallbackBrush(&Fallback)
            [SNew(SBorder).BorderImage(&Frame).Padding(FMargin(1/Scale))[Contents]]];
        Refresh();
    }
    bool Ready() const {return Owner.IsValid()&&Owner->IsInputReady()&&Owner->StationReady();}
    void Reset(){Session.Cancel();bReview=false;AmmoId.Reset();Notice.Reset();Rules=ColdSteelIncineratorStorage::LoadRules();Refresh();}
    void Refresh()
    {
        if(!Owner.IsValid()||!Owner->GetModel()||!YieldText)return;
        auto* M=Owner->GetModel();Preview=ColdSteelIncineratorStorage::Quote(M->Snapshot(),Owner->ContainerKey(),Rules);
        int32 Used=0,Objects=0;for(const auto& I:M->Items())if(I.Place==4&&I.Container==Owner->ContainerKey()){Used+=I.Width*I.Height;++Objects;}
        Capacity->SetText(FText::FromString(FString::Printf(TEXT("%d / 216 格"),Used)));
        const FString Description=Objects?ColdSteelIncineratorStorage::Describe(Preview,*M,false)
            :Rules.bValid?(Rules.Recipes.IsEmpty()?TEXT("产出未配置\n投入物品后，在这里查看预计收获"):TEXT("投入物品后自动计算预计收获")):Rules.Error;
        YieldText->SetText(SingleLine(Description));
        Status->SetText(SingleLine(Notice.IsEmpty()?TEXT("关闭面板不会焚化；暂存物品会随档案保存。可在仓库取回各炉暂存。"):Notice));
        ConfirmBox->SetVisibility(bReview?EVisibility::Visible:EVisibility::Collapsed);
        AmmoBox->SetVisibility(AmmoId.IsEmpty()?EVisibility::Collapsed:EVisibility::Visible);
        ActionBox->SetVisibility(bReview||!AmmoId.IsEmpty()?EVisibility::Collapsed:EVisibility::Visible);
        GridScroll->SetEnabled(!bReview&&!bSubmitting&&AmmoId.IsEmpty());
        if(bReview)ConfirmText->SetText(SingleLine(ColdSteelIncineratorStorage::Describe(Session.Draft,*M,true)));
    }
    void Changed(){if(bReview||!AmmoId.IsEmpty())Notice=TEXT("物品状态已变化，请重新操作");Session.Cancel();bReview=false;AmmoId.Reset();Refresh();}
    bool Cancel(){const bool Had=bReview||!AmmoId.IsEmpty();bReview=false;AmmoId.Reset();Session.Cancel();Refresh();return Had;}
    bool Review()
    {if(!Ready())return false;Rules=ColdSteelIncineratorStorage::LoadRules();bReview=Session.Review(*Owner->GetModel(),Owner->ContainerKey(),Rules);if(!bReview)Notice=Session.Draft.Reason;else Notice.Reset();Refresh();return bReview;}
    bool Confirm()
    {
        if(!Ready()||!bReview||bSubmitting)return false;
        bSubmitting=true;bReview=false;FString Reason;const bool OK=Session.Confirm(*Owner->GetModel(),ColdSteelIncineratorStorage::LoadRules(),Reason);
        bSubmitting=false;Notice=Reason;Rules=ColdSteelIncineratorStorage::LoadRules();Refresh();return OK;
    }
    bool Retrieve()
    {if(!Ready()||bSubmitting)return false;Cancel();FString Reason;const bool OK=ColdSteelIncineratorStorage::Retrieve(*Owner->GetModel(),Owner->ContainerKey(),Reason);Notice=Reason;Refresh();return OK;}
    void RequestAmmo(const FString& Id,int64 Available,int32 Cell)
    {
        if(!Ready()||Available<=0)return;Cancel();AmmoId=Id;AmmoCell=Cell;AmmoBefore=Available;AmmoGeneration=Owner->GetModel()->Snapshot().Generation;
        AmmoCaption->SetText(SingleLine(FString::Printf(TEXT("%s · 最多 %lld · 输入暂存数量"),*Owner->GetModel()->AmmoLabel(Id),Available)));
        AmmoQuantity->SetText(FText::FromString(LexToString(Available)));Refresh();FSlateApplication::Get().SetKeyboardFocus(AmmoQuantity,EFocusCause::SetDirectly);
    }
    bool Deposit(const FString& Id,int64 Count)
    {if(!Ready())return false;FString Reason;const bool OK=ColdSteelIncineratorStorage::DepositAmmo(*Owner->GetModel(),Id,Count,Reason,AmmoCell);Notice=Reason;AmmoId.Reset();Refresh();return OK;}
    void AcceptAmmo()
    {
        if(!Ready()||AmmoId.IsEmpty())return;int64 Count=0;
        if(!ColdSteelIncineration::ParseQuantity(AmmoQuantity->GetText().ToString(),Count)||Count>AmmoBefore){Notice=TEXT("请输入不超过弹药袋数量的正整数");Refresh();return;}
        if(Owner->GetModel()->Snapshot().Generation!=AmmoGeneration||Owner->GetModel()->PouchCount(AmmoId)!=AmmoBefore){Cancel();Notice=TEXT("弹药袋已变化，请重新选择");Refresh();return;}
        const FString Id=AmmoId;Deposit(Id,Count);
    }
    bool Geometry(FString& Reason) const
    {
        const auto Bounds=GetCachedGeometry().GetLayoutBoundingRect();
        for(const TSharedPtr<SWidget>& W:{StaticCastSharedPtr<SWidget>(GridScroll),StaticCastSharedPtr<SWidget>(YieldBox),StaticCastSharedPtr<SWidget>(ActionBox)})
        {const auto R=W->GetCachedGeometry().GetLayoutBoundingRect();if(R.Left<Bounds.Left-1||R.Right>Bounds.Right+1||R.Top<Bounds.Top-1||R.Bottom>Bounds.Bottom+1){Reason=TEXT("child outside panel");return false;}}
        if(GridScroll->GetCachedGeometry().GetLocalSize().Y<24/Scale){Reason=TEXT("grid viewport collapsed");return false;}return true;
    }
    FString PreviewText()const{return YieldText?YieldText->GetText().ToString():FString();}
private:
    TWeakObjectPtr<UColdSteelIncineratorWidget> Owner;
    ColdSteelIncineratorStorage::FRules Rules;ColdSteelIncineratorStorage::FQuote Preview;ColdSteelIncineratorStorage::FSession Session;
    float Scale=1;bool bReview=false,bSubmitting=false;FString Notice,AmmoId;int32 AmmoCell=-1;int64 AmmoBefore=0,AmmoGeneration=0;
    FButtonStyle Buttons;FEditableTextBoxStyle InputStyle;FSlateBrush Frame,Fallback,Header,Card;
    TSharedPtr<SScrollBox> GridScroll;TSharedPtr<SBorder> YieldBox,ConfirmBox,AmmoBox;TSharedPtr<SBox> ActionBox;
    TSharedPtr<STextBlock> Capacity,YieldText,Status,ConfirmText,AmmoCaption;TSharedPtr<SEditableTextBox> AmmoQuantity;
};

void UColdSteelIncineratorWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;if(Board)Board->ConfigureWarehouse(Owner);}
void UColdSteelIncineratorWidget::NativeOnInitialized()
{Super::NativeOnInitialized();SetIsFocusable(true);Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Board=CreateWidget<UColdSteelInventoryWidget>(GetOwningPlayer());Board->ConfigureWarehouse(HUD);}
TSharedRef<SWidget> UColdSteelIncineratorWidget::RebuildWidget(){return SAssignNew(Panel,SColdSteelIncineratorPanel).Owner(this);}
void UColdSteelIncineratorWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::OnInventoryChanged);}
void UColdSteelIncineratorWidget::NativeDestruct(){CloseStation();if(Model&&ChangedHandle.IsValid())Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
void UColdSteelIncineratorWidget::ReleaseSlateResources(bool Children){Super::ReleaseSlateResources(Children);Panel.Reset();}
void UColdSteelIncineratorWidget::OpenStation(AActor* InStation)
{
    CloseStation();auto* Piece=Cast<AVoxelBuildPrefabActor>(InStation);auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!World||!Model)return;Container=World->IncineratorContainerAt(Piece->AnchorCell());if(Container.IsEmpty())return;
    Station=InStation;bStationOpen=true;Model->bIncineratorOpen=true;Model->BeginStorageSession(Container,1,TEXT("焚化投入"));Board->ResetStoragePage();if(Panel){Panel->Build();Panel->Reset();}
}
void UColdSteelIncineratorWidget::CloseStation()
{
    if(bStationOpen){if(FSlateApplication::IsInitialized())FSlateApplication::Get().CancelDragDrop();if(Board)Board->CancelInteraction();if(Model){Model->bIncineratorOpen=false;if(Model->ActiveContainer==Container)Model->EndStorageSession();}}
    bStationOpen=false;bInputReady=false;Station.Reset();Container.Reset();if(Panel)Panel->Reset();
}
void UColdSteelIncineratorWidget::SetInputReady(bool Ready){bInputReady=Ready;if(Panel)Panel->SetEnabled(Ready);}
bool UColdSteelIncineratorWidget::StationReady() const
{
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Station.Get());const auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;const auto* Pawn=GetOwningPlayerPawn();
    return bStationOpen&&Model&&HUD&&HUD->IsWorkbenchOpen()&&Piece&&!Piece->IsFalling()&&Piece->PrefabId()==VoxelIncineratorId&&World
        &&World->IncineratorContainerAt(Piece->AnchorCell())==Container&&Model->bIncineratorOpen&&Model->ActiveContainer==Container
        &&Pawn&&FVector::Dist(Pawn->GetActorLocation(),Piece->GetActorLocation()+FVector(0,0,70))<=240.f;
}
void UColdSteelIncineratorWidget::NativeTick(const FGeometry& G,float Delta)
{Super::NativeTick(G,Delta);const float S=ColdSteelUI::PixelScale(this);if(Panel&&!FMath::IsNearlyEqual(LastScale,S,.001f)){LastScale=S;Panel->Build();}if(bStationOpen&&!StationReady())RequestClose();}
void UColdSteelIncineratorWidget::OnInventoryChanged(){if(bStationOpen&&Panel)Panel->Changed();}
bool UColdSteelIncineratorWidget::CancelConfirmation(){return Panel&&Panel->Cancel();}
void UColdSteelIncineratorWidget::RequestClose(){CloseStation();if(HUD)HUD->CloseWorkbench();}
void UColdSteelIncineratorWidget::RequestAmmo(const FString& Id,int64 Available,int32 Cell){if(Panel)Panel->RequestAmmo(Id,Available,Cell);}
FReply UColdSteelIncineratorWidget::NativeOnPreviewKeyDown(const FGeometry& G,const FKeyEvent& E)
{if(!E.IsRepeat()&&E.GetKey()==EKeys::Escape){if(!CancelConfirmation())RequestClose();return FReply::Handled();}if(!E.IsRepeat()&&E.GetKey()==EKeys::Tab){RequestClose();return FReply::Handled();}return Super::NativeOnPreviewKeyDown(G,E);}
bool UColdSteelIncineratorWidget::AuditReview(){return Model&&Model->IsAudit()&&Panel&&Panel->Review();}
bool UColdSteelIncineratorWidget::AuditConfirm(){return Model&&Model->IsAudit()&&Panel&&Panel->Confirm();}
bool UColdSteelIncineratorWidget::AuditRetrieve(){return Model&&Model->IsAudit()&&Panel&&Panel->Retrieve();}
bool UColdSteelIncineratorWidget::AuditDepositAmmo(const FString& Id,int64 Count){return Model&&Model->IsAudit()&&Panel&&Panel->Deposit(Id,Count);}
bool UColdSteelIncineratorWidget::AuditGeometry(FString& Reason)const{return Model&&Model->IsAudit()&&Panel&&Panel->Geometry(Reason);}
FString UColdSteelIncineratorWidget::AuditPreview()const{return Panel?Panel->PreviewText():FString();}
