#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelAlchemyBookWidget.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/AlchemySystem.h"
#include "../Building/AlchemyWorldView.h"
#include "../Building/PotionWorkbenchVisualComponent.h"
#include "../Building/AlchemyWorkbenchLayout.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Weapons/GunsmithSystem.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/Image.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Input/Reply.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/PlatformTime.h"

namespace {
void Caption(UButton* Button,const FString& Text){if(Button)if(auto* Label=Cast<UTextBlock>(Button->GetContent());Label&&Label->GetText().ToString()!=Text)Label->SetText(FText::FromString(Text));}
void Value(UTextBlock* Label,const FString& Text){if(Label&&Label->GetText().ToString()!=Text)Label->SetText(FText::FromString(Text));}
}
void UColdSteelAlchemyAction::Click(){if(!Hold&&Widget.IsValid())Widget->Act(Action);}
void UColdSteelAlchemyAction::Press(){if(Hold&&Widget.IsValid())Widget->Act(Action);}
void UColdSteelAlchemyAction::Release(){if(Hold&&Widget.IsValid())Widget->Act(Action,true);}
UTextBlock* UColdSteelAlchemyWidget::Text(const FString& V,float Pixels,bool Wrap,bool Numeric,bool Medium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(V));T->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    T->SetAutoWrapText(Wrap);T->SetColorAndOpacity(ColdSteelUI::TextPrimary);Labels.Add({T,Pixels,Numeric,Medium});return T;
}
UButton* UColdSteelAlchemyWidget::Button(const FString& V,int32 Id,bool Hold)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();auto* L=Text(V,14,false,false,true);L->SetJustification(ETextJustify::Center);B->SetContent(L);
    auto* LabelSlot=Cast<UButtonSlot>(L->Slot);LabelSlot->SetPadding(FMargin(12/Scale,4/Scale));LabelSlot->SetHorizontalAlignment(HAlign_Fill);LabelSlot->SetVerticalAlignment(VAlign_Center);B->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    auto* Bind=NewObject<UColdSteelAlchemyAction>(this);Bind->Widget=this;Bind->Action=Id;Bind->Hold=Hold;Bindings.Add(Bind);Actions.Add(Id,B);
    B->OnClicked.AddDynamic(Bind,&UColdSteelAlchemyAction::Click);B->OnPressed.AddDynamic(Bind,&UColdSteelAlchemyAction::Press);B->OnReleased.AddDynamic(Bind,&UColdSteelAlchemyAction::Release);return B;
}
void UColdSteelAlchemyWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Scale=ColdSteelUI::PixelScale(this);
    System=GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>();Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model)ModelChanged=Model->OnChanged.AddWeakLambda(this,[this](){bMaterialsDirty=true;if(!System||!System->HasJob())bShowEntryReadiness=true;});
    Build();if(System&&!System->Recipes().IsEmpty())Selection=System->Recipes()[0].Id;
    for(const auto& R:System->Recipes())
    {
        const auto Item=Model->CreateItem(R.Output);const FString Path=ColdSteelInventory::Text(Item,TEXT("ue_icon"));
        if(!Path.IsEmpty()&&!Images.Contains(Path))Images.Add(Path,FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path));
        Choice->AddOption(R.Name);
    }
    Choice->SetSelectedIndex(0);Refresh();
}
bool UColdSteelAlchemyWidget::Configure(AActor* Station)
{
    WorkingPawn=GetOwningPlayerPawn();if(!System||!System->Open(Station,WorkingPawn.Get()))return false;
    TableVisual=System->Workbench()->FindComponentByClass<UPotionWorkbenchVisualComponent>();
    if(System->HasJob())Selection=System->Job().Recipe;PrepareView();Refresh();return true;
}
void UColdSteelAlchemyWidget::Build()
{
    Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();Canvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);WidgetTree->RootWidget=Canvas;
    BuildEntry();
    auto Panel=[this](TObjectPtr<UBorder>& Border,TWeakObjectPtr<UCanvasPanelSlot>& PanelSlot)
    {
        Border=WidgetTree->ConstructWidget<UBorder>();Border->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10));Border->SetPadding(14/Scale);
        PanelSlot=Canvas->AddChildToCanvas(Border);auto* Scroller=WidgetTree->ConstructWidget<UScrollBox>();Border->SetContent(Scroller);
        auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Scroller->AddChild(Body);return Body;
    };
    auto Label=[this](UVerticalBox* Parent,const FString& V,float Size,bool Wrap=false)
    {auto* T=Text(V,Size,Wrap);Parent->AddChildToVerticalBox(T)->SetPadding(FMargin(0,4/Scale,0,8/Scale));return T;};
    auto* Ingredients=Panel(IngredientPanel,IngredientSlot);Label(Ingredients,TEXT("备料余量"),15);
    for(int32 I=0;I<3;++I)
    {
        auto* Item=WidgetTree->ConstructWidget<UVerticalBox>();Ingredients->AddChildToVerticalBox(Item);IngredientRows.Add(Item);
        IngredientLabels.Add(Label(Item,TEXT(""),13));
    }
    PrepStatus=Label(Ingredients,TEXT(""),12,true);PrepStatus->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    auto* Work=Panel(Controls,ControlSlot);Label(Work,TEXT("坩埚"),15);
    LiveStatus=Label(Work,TEXT(""),18);Instruction=Label(Work,TEXT(""),13,true);
    FinishPanel=WidgetTree->ConstructWidget<UBorder>();FinishPanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10));FinishPanel->SetPadding(8/Scale);FinishSlot=Canvas->AddChildToCanvas(FinishPanel);
    HoverHint=Text(TEXT("金边器具可操作 · B 查阅手册 · Esc 收火暂存"),13,true);HoverHint->SetJustification(ETextJustify::Center);FinishPanel->SetContent(HoverHint);
    HoverPopup=WidgetTree->ConstructWidget<UBorder>();HoverPopup->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,7,ColdSteelUI::HUDGoldLight,1));HoverPopup->SetPadding(12/Scale);
    HoverPopupSlot=Canvas->AddChildToCanvas(HoverPopup);HoverPopupSlot->SetAutoSize(true);HoverPopupSlot->SetZOrder(9);
    HoverSize=WidgetTree->ConstructWidget<USizeBox>();HoverSize->SetWidthOverride(356/Scale);HoverPopup->SetContent(HoverSize);
    auto* HoverStack=WidgetTree->ConstructWidget<UVerticalBox>();HoverSize->SetContent(HoverStack);
    HoverTitle=Text(TEXT(""),15);HoverTitle->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);HoverStack->AddChildToVerticalBox(HoverTitle)->SetPadding(FMargin(0,0,0,6/Scale));
    HoverText=Text(TEXT(""),13,true);HoverStack->AddChildToVerticalBox(HoverText);HoverPopup->SetVisibility(ESlateVisibility::Collapsed);
    SetWorkVisibility(ESlateVisibility::Collapsed);
    Reader=WidgetTree->ConstructWidget<UBorder>();FSlateBrush ClearBookBrush;ClearBookBrush.DrawAs=ESlateBrushDrawType::NoDrawType;Reader->SetBrush(ClearBookBrush);Reader->SetPadding(0);ReaderSlot=Canvas->AddChildToCanvas(Reader);ReaderSlot->SetZOrder(10);
    auto* BookScale=WidgetTree->ConstructWidget<UScaleBox>();BookScale->SetStretch(EStretch::ScaleToFit);Reader->SetContent(BookScale);
    auto* BookSize=WidgetTree->ConstructWidget<USizeBox>();BookSize->SetWidthOverride(1400);BookSize->SetHeightOverride(1100);BookScale->SetContent(BookSize);
    BookPage=WidgetTree->ConstructWidget<UColdSteelAlchemyBookPreviewWidget>();BookSize->SetContent(BookPage);
    BookPage->OnPageChanged.BindUObject(this,&ThisClass::BookChanged);
    Reader->SetVisibility(ESlateVisibility::Collapsed);
}
const FAlchemyRecipe* UColdSteelAlchemyWidget::Recipe() const
{return System->HasJob()?System->Recipe():System->Find(Selection);}
void UColdSteelAlchemyWidget::Select(FString Name,ESelectInfo::Type How)
{
    if(How==ESelectInfo::Direct||!System||System->HasJob()||bPreparing||System->Pending()||System->Saving())return;
    for(const auto& R:System->Recipes())if(R.Name==Name){Selection=R.Id;Spread=0;break;}
    LocalNotice.Reset();bShowEntryReadiness=true;bMaterialsDirty=true;bConfirmDiscard=false;Refresh();
}
UWidget* UColdSteelAlchemyWidget::Option(FString Label)
{
    auto* Row=CreateWidget<UColdSteelGunRecipeOptionWidget>(this);if(!Row)return nullptr;Row->Configure(Label,Scale);
    EntryOptions.RemoveAll([](const auto& Entry){return !Entry.IsValid();});EntryOptions.Add(Row);return Row;
}
void UColdSteelAlchemyWidget::PrepareView()
{
    if(View||!System->Workbench())return;FActorSpawnParameters P;P.ObjectFlags|=RF_Transient;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    View=GetWorld()->SpawnActor<AAlchemyWorldView>(P);if(View)View->Configure(System->Workbench(),GetOwningPlayer());
}
void UColdSteelAlchemyWidget::Refresh()
{
    if(!System||!Model)return;const auto* R=Recipe();const auto& J=System->Job();
    if(CachedJob!=J.Id)
    {
        bConfirmDiscard=false;
        if(!CachedJob.IsEmpty()&&J.Id.IsEmpty())
        {
            // A successful claim/discard changes the same physical button into
            // Start. Do not let the second click of a double-click pay a new batch.
            EntryActionReadyAt=FPlatformTime::Seconds()+.5;bShowEntryReadiness=false;
        }
        if(!J.Id.IsEmpty()&&System->Find(J.Recipe))Selection=J.Recipe;
    }
    if(bConfirmDiscard&&(DiscardConfirmJob!=J.Id||DiscardConfirmRevision!=J.Revision))bConfirmDiscard=false;
    const bool Rebuild=bMaterialsDirty||CachedRecipe!=(R?R->Id:NAME_None)||CachedJob!=J.Id||CachedJobRevision!=J.Revision;
    if(Rebuild)IngredientNames.Reset();
    if(R)
    {
        Choice->SetSelectedOption(R->Name);
        for(int32 I=0;I<R->Inputs.Num();++I)
        {
            const auto& In=R->Inputs[I];
            if(Rebuild)
            {
                const FString Name=ColdSteelInventory::Text(Model->CreateItem(In.Item),TEXT("name"));IngredientNames.Add(Name);
            }
            const FString& Name=IngredientNames[I];
            const bool AutoBase=R->AutoBase&&In.Item==TEXT("alchemy_pure_base_fluid");
            if(IngredientLabels.IsValidIndex(I))Value(IngredientLabels[I],AutoBase?Name+TEXT(" · 已入锅"):FString::Printf(TEXT("%s × %lld"),*Name,FMath::Max<int64>(0,In.Count-J.Poured.FindRef(In.Item))));
            if(IngredientRows.IsValidIndex(I))IngredientRows[I]->SetVisibility(ESlateVisibility::HitTestInvisible);
        }
        for(int32 I=R->Inputs.Num();I<3;++I)IngredientRows[I]->SetVisibility(ESlateVisibility::Collapsed);
        if(CachedJob!=J.Id)
        {
            SelectedGrind=INDEX_NONE;for(int32 I=0;I<R->Inputs.Num();++I)if(System->CanGrind(I)){SelectedGrind=I;break;}
        }
        Value(PrepStatus,SelectedGrind!=INDEX_NONE&&IngredientNames.IsValidIndex(SelectedGrind)?TEXT("研钵选料：")+IngredientNames[SelectedGrind]:TEXT(""));
        if(Held>=200&&!System->CanGrind(Held-200))Stop();
    }
    const bool InventoryPending=Model->IsCampfireInventoryPending();
    Choice->SetIsEnabled(!System->HasJob()&&!System->Pending()&&!System->Saving()&&!bPreparing&&System->Recipes().Num()>1);
    if(Rebuild)RefundSummary=TEXT("开炉时一次备料；离台收火暂存，再次进入可继续。");
    if(Rebuild&&System->HasJob())
    {
        const auto Items=System->DiscardRefund();TMap<FString,int64> Counts;
        for(const auto& Item:Items)Counts.FindOrAdd(Item.Definition)+=Item.Count;
        FString List;
        for(const auto& Item:Items)
        {
            const int64 Count=Counts.FindRef(Item.Definition);if(Count<=0)continue;
            const FString Name=ColdSteelInventory::Text(Item,TEXT("name"));
            List+=FString::Printf(TEXT("%s × %lld  "),Name.IsEmpty()?*Item.Definition:*Name,Count);Counts.Remove(Item.Definition);
        }
        RefundSummary=(J.bFinished?TEXT("作废退回一半材料："):TEXT("废弃仅退回未开封材料："))+FString(List.IsEmpty()?TEXT("无"):*List);
        if(J.bFinished)RefundSummary+=TEXT("\n按每种实际投入材料分别向下取整，不足 1 份不返还；作废后不能领取本炉药水。");
    }
    const FString RefundText=RefundSummary+(bConfirmDiscard?TEXT("\n再次点击确认作废并退料。"):TEXT(""));
    bMaterialsDirty=false;CachedRecipe=R?R->Id:NAME_None;CachedJob=J.Id;CachedJobRevision=J.Revision;
    Value(Refund,RefundText);
    FString Reason;
    const bool ActionReady=FPlatformTime::Seconds()>=EntryActionReadyAt;
    const bool Can=!bClose&&!bReturn&&!System->Pending()&&!System->Saving()&&!InventoryPending&&!bPreparing&&ActionReady&&
        (J.bFinished?J.bPassed:System->HasJob()?System->CanResume(Reason):System->CanStart(Selection,Reason));
    FString State=System->Message();
    if(!System->HasJob()&&bShowEntryReadiness)State=Can?TEXT("配方与材料已就绪，可备料开炉。"):Reason;
    if(State.IsEmpty())State=TEXT("按手册控制顺序、研磨、火候与搅拌。");
    if(J.bFinished&&!J.Faults.IsEmpty())State+=TEXT("\n工艺偏差：")+FString::Join(J.Faults,TEXT("；"));
    if(bPreparing)State=PreparingJob.IsEmpty()?TEXT("正在准备台面和手部资源，完成后开炉。"):TEXT("正在准备台面，随后继续原批次，不重复扣料。");
    if(!LocalNotice.IsEmpty())State=LocalNotice;
    if(InventoryPending||System->Pending())State=TEXT("本炉或背包正在同步，请稍候。");
    else if(System->Saving())State=TEXT("本炉保存尚未确认，请稍候。");
    Value(Status,State);
    Caption(Actions[10],System->Pending()||InventoryPending?TEXT("同步中…"):System->Saving()?TEXT("保存中…"):bPreparing?TEXT("准备中…"):J.bFinished?(J.bPassed?TEXT("领取药水"):TEXT("本炉失败")):System->HasJob()?TEXT("继续本炉"):TEXT("备料开炉"));
    Actions[10]->SetIsEnabled(Can);Actions[10]->SetToolTipText(FText::FromString(Reason));Actions[12]->SetIsEnabled(System->HasJob()&&!System->Pending()&&!System->Saving()&&!InventoryPending&&!bPreparing&&!bReturn&&!bClose&&ActionReady);
    if(!Can&&!Reason.IsEmpty()&&LocalNotice.IsEmpty())Value(Status,Reason);
    Caption(Actions[12],bConfirmDiscard?TEXT("确认作废退料"):J.bFinished?TEXT("作废退回一半"):TEXT("废弃本炉"));Actions[12]->SetToolTipText(FText::FromString(RefundText));
    const int32 Current=System->StepIndex();
    if(R&&!R->FreeBrewing&&Current!=ObservedStep&&(Held==31||Held==32||bDragging))Stop();ObservedStep=Current;
    Value(Instruction,System->Saving()?System->Message():System->Bottling()?TEXT("正在舀取、装瓶并放回器具"):System->Observation());
    static const TCHAR* Fires[]={TEXT("已收火"),TEXT("低火"),TEXT("中火"),TEXT("高火")};
    Value(LiveStatus,FString::Printf(TEXT("%.0f °C  ·  %s"),J.Temperature,Fires[FMath::Clamp(System->Heat(),0,3)]));
    RefreshEntry(Rebuild);
    UpdateHover();
}
void UColdSteelAlchemyWidget::Layout(const FGeometry& G)
{
    const float NewScale=ColdSteelUI::PixelScale(this);if(!FMath::IsNearlyEqual(Scale,NewScale))
    {
        Scale=FMath::Max(.1f,NewScale);for(auto& L:Labels)if(L.Widget.IsValid())L.Widget->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    }
    if(HoverSize)HoverSize->SetWidthOverride(356/Scale);
    const FVector2D Size=G.GetLocalSize();LayoutEntry(Size);
    const float SideWidth=244.f/Scale;
    if(IngredientSlot.IsValid()){IngredientSlot->SetPosition(FVector2D(16/Scale,24/Scale));IngredientSlot->SetSize(FVector2D(SideWidth,206/Scale));}
    if(ControlSlot.IsValid()){ControlSlot->SetPosition(FVector2D(Size.X-SideWidth-16/Scale,24/Scale));ControlSlot->SetSize(FVector2D(SideWidth,166/Scale));}
    const float W=FMath::Min(float(Size.X)-24/Scale,780.f/Scale);
    if(FinishSlot.IsValid()){FinishSlot->SetPosition(FVector2D((Size.X-W)*.5f,Size.Y-68/Scale));FinishSlot->SetSize(FVector2D(W,52/Scale));}
    // Let the physical reader use the available height, including on 1440p/4K displays.
    const FVector2D BookSize(FMath::Max(1.,Size.X-8/Scale),FMath::Max(1.,Size.Y-8/Scale));
    if(ReaderSlot.IsValid()){ReaderSlot->SetPosition((Size-BookSize)*.5f);ReaderSlot->SetSize(BookSize);}
}
void UColdSteelAlchemyWidget::SetWorkVisibility(ESlateVisibility Mode)
{for(auto* Panel:{Controls.Get(),IngredientPanel.Get(),FinishPanel.Get()})if(Panel)Panel->SetVisibility(Mode==ESlateVisibility::Visible?ESlateVisibility::HitTestInvisible:Mode);}
void UColdSteelAlchemyWidget::World(bool On)
{
    if(bWorld==On)return;Stop();bWorld=On;Book(false);
    Management->SetVisibility(On?ESlateVisibility::Collapsed:ESlateVisibility::Visible);SetWorkVisibility(On?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Canvas->SetVisibility(On?ESlateVisibility::Visible:ESlateVisibility::SelfHitTestInvisible);
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())HUD->SetAlchemyManagement(!On);
    if(View){if(On)View->Enter();else View->Leave();}SetKeyboardFocus();
}
void UColdSteelAlchemyWidget::Book(bool On)
{
    if(On&&!Recipe()){LocalNotice=TEXT("当前配方未就绪，请先处理本炉。");Refresh();return;}
    Stop();bBook=On;Reader->SetVisibility(On?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Management->SetVisibility(!On&&!bWorld?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    SetWorkVisibility(!On&&bWorld?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Canvas->SetVisibility(On||bWorld?ESlateVisibility::Visible:ESlateVisibility::SelfHitTestInvisible);
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())HUD->SetAlchemyManagement(!On&&!bWorld);
    if(On)if(const auto* R=Recipe()){BookPage->Configure(System->Recipes(),*R,Spread,bWorld&&System->Active());if(bWorld)System->Input(EAlchemyOp::Book,Spread);}
    if(!On&&BookPage)BookPage->ReleasePreview(false);
    SetKeyboardFocus();
}
void UColdSteelAlchemyWidget::BookChanged(int32)
{
    const auto* R=Recipe();if(!BookPage||!R||BookPage->CurrentRecipeId()!=R->Id)return;
    // Browsing another chapter is private reading, not a recipe-selection command.
    Spread=BookPage->CurrentSpread();if(bWorld&&System&&System->Active())System->Input(EAlchemyOp::Book,Spread);
}
void UColdSteelAlchemyWidget::Stop()
{
    if(bStoppingInput)return;TGuardValue<bool> Guard(bStoppingInput,true);
    if(TableVisual.IsValid())TableVisual->SetHoverTarget({},false);if(HoverPopup)HoverPopup->SetVisibility(ESlateVisibility::Collapsed);
    if(BookPage)BookPage->CancelInteraction();if(Held>=0&&System&&System->Active())System->Input(EAlchemyOp::Stop);
    Held=-1;DragRadians=0;bDragging=bWorldHold=bHasStirAngle=false;SetCursor(EMouseCursor::Default);
    if(HasMouseCapture()&&FSlateApplication::IsInitialized())FSlateApplication::Get().ReleaseAllPointerCapture();
}
void UColdSteelAlchemyWidget::Return()
{Stop();Book(false);bReturn=true;if(!System->Pending())System->Suspend();}
void UColdSteelAlchemyWidget::RequestClose()
{
    if(bBook){Book(false);return;}if(bWorld){Return();return;}bClose=true;bPreparing=false;if(System->Active()&&!System->Pending())System->Suspend();
}
void UColdSteelAlchemyWidget::Act(int32 Id,bool Released)
{
    if(bEnded||!System)return;if(Released){if(Held==Id)Stop();return;}
    if(Id==1){RequestClose();return;}if(Id==11){Book(!bBook);return;}
    if(Id==62){Book(false);return;}if(Id==60||Id==61)
    {if(bBook&&BookPage)BookPage->Flip(Id==60?-1:1);return;}
    if(System->Pending())return;
    if(Id==10||Id==12)
    {
        if(bWorld||bBook||bPreparing||bReturn||bClose||System->Saving()||!Model||Model->IsCampfireInventoryPending()||FPlatformTime::Seconds()<EntryActionReadyAt)return;
        const auto& CurrentJob=System->Job();
        // An inventory receipt may arrive between the last paint and this click.
        // Refresh first instead of applying the old label's click to a new job.
        if(CachedJob!=CurrentJob.Id||CachedJobRevision!=CurrentJob.Revision){Refresh();return;}
    }
    if(auto* Button=Actions.FindRef(Id).Get();Button&&!Button->GetIsEnabled())return;
    if(Id==10)
    {
        LocalNotice.Reset();bShowEntryReadiness=false;
        bConfirmDiscard=false;if(System->HasJob()&&System->Job().bFinished){System->Claim();Refresh();return;}
        FString Reason;if(!(System->HasJob()?System->CanResume(Reason):System->CanStart(Selection,Reason))){bShowEntryReadiness=true;Refresh();return;}
        PreparingJob=System->Job().Id;PreparingRecipe=System->HasJob()?System->Job().Recipe:Selection;
        PrepareView();if(!View){LocalNotice=TEXT("无法准备炼药台面，本次未扣料，原批次保留。");Refresh();return;}
        bPreparing=true;Refresh();return;
    }
    if(Id==12)
    {
        if(!System->HasJob())return;LocalNotice.Reset();bShowEntryReadiness=false;const auto& CurrentJob=System->Job();
        if(bConfirmDiscard&&DiscardConfirmJob==CurrentJob.Id&&DiscardConfirmRevision==CurrentJob.Revision)
        {System->Discard();bConfirmDiscard=false;DiscardConfirmJob.Reset();DiscardConfirmRevision=-1;}
        else {bConfirmDiscard=true;DiscardConfirmJob=CurrentJob.Id;DiscardConfirmRevision=CurrentJob.Revision;}
        Refresh();return;
    }
    if(!bWorld||!System->Active()||bBook)return;
    if(Id==51){Return();return;}
    if(!CanTableAct(Id))return;
    if(Id>=100&&Id<103){Stop();System->Input(EAlchemyOp::Pour,Id-100);}
    else if(Id>=200&&Id<=202){SelectedGrind=Id-200;Held=Id;System->Input(EAlchemyOp::Grind,Id-200);}
    else if(Id==31||Id==32){Held=Id;System->Input(EAlchemyOp::Stir,0,Id==31?-1:1);}
    else if(Id>=40&&Id<=45)System->Input(EAlchemyOp::Heat,Id-40);
    else if(Id==50){Stop();System->Bottle();}
    else if(Id==70){Stop();System->Input(EAlchemyOp::Timer);}
    else if(Id==51)Return();Refresh();SetKeyboardFocus();
}
void UColdSteelAlchemyWidget::NativeTick(const FGeometry& G,float Dt)
{
    Super::NativeTick(G,Dt);if(bEnded||!System)return;Layout(G);
    if(FSlateApplication::IsInitialized()&&!HasMouseCapture())PointerScreen=FSlateApplication::Get().GetCursorPos();
    if(FSlateApplication::IsInitialized()&&!FSlateApplication::Get().IsActive())Stop();
    if(bPreparing&&View&&View->Failed()){bPreparing=false;LocalNotice=TEXT("台面或手部资源尚未安装完成，本次未扣料。请重新进入工作台。");Refresh();}
    if(WorkingPawn.Get()!=GetOwningPlayerPawn()||!System->Reachable()){bClose=true;bPreparing=false;Stop();if(System->Active()&&!System->Pending())System->Suspend();}
    if(bPreparing&&!bBook&&View&&View->Ready()&&!System->Pending()&&!Model->IsCampfireInventoryPending())
    {
        bPreparing=false;bShowEntryReadiness=false;
        if(PreparingJob.IsEmpty())
        {
            if(!System->HasJob()&&Selection==PreparingRecipe)System->Start(PreparingRecipe);
            else LocalNotice=TEXT("配方或本炉状态已变化，请重新选择操作；本次未扣料。");
        }
        else if(System->HasJob()&&System->Job().Id==PreparingJob&&System->Job().Recipe==PreparingRecipe&&!System->Job().bFinished)System->Resume();
        else LocalNotice=TEXT("原批次状态已变化，请重新选择继续、领取或作废；未另开新炉。");
        PreparingJob.Reset();PreparingRecipe=NAME_None;Refresh();
    }
    if(bReturn&&!System->Pending()){if(System->Active())System->Suspend();else {bReturn=false;World(false);}}
    if(bClose&&!System->Pending())
    {
        if(System->Active()){System->Suspend();return;}
        if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseAlchemy();return;
    }
    if(!bReturn&&!bClose)World(System->Active()&&View&&View->Ready());
    InputClock+=Dt;if(InputClock>=.1f)
    {
        const float Interval=InputClock;InputClock=0;
        if(!bBook&&System->Active()&&!System->Pending())
        {
            if(bDragging)
            {
                const float Speed=FMath::Clamp(DragRadians/(Interval*.75f*2*PI),-1.f,1.f);
                // Zero angular velocity is a held spoon, not a release/re-pickup.
                System->Input(EAlchemyOp::Stir,0,Speed);
            }
            else if(Held>=0)System->Input(Held>=200?EAlchemyOp::Grind:EAlchemyOp::Stir,Held>=200?Held-200:0,Held==31?-1:1);
        }
        DragRadians=0;
    }
    Clock+=Dt;if(Clock>=.1f){Clock=0;Refresh();}
}
FReply UColdSteelAlchemyWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    const auto K=E.GetKey();if(E.IsRepeat())return FReply::Handled();
    if(K==EKeys::Escape||K==EKeys::Tab)RequestClose();else if(K==EKeys::B)Book(!bBook);
    else if(bBook&&(K==EKeys::Left||K==EKeys::Right))Act(K==EKeys::Left?60:61);
    else if(bWorld&&!bBook)
    {
        if(K==EKeys::R)Act(201);else if(K==EKeys::T)Act(202);else if(K==EKeys::A)Act(31);else if(K==EKeys::D)Act(32);
        else if(K==EKeys::One)Act(40);else if(K==EKeys::Two)Act(41);else if(K==EKeys::Three)Act(42);else if(K==EKeys::Four)Act(43);
        else if(K==EKeys::F)Act(70);
    }
    return FReply::Handled();
}
FReply UColdSteelAlchemyWidget::NativeOnKeyUp(const FGeometry& G,const FKeyEvent& E)
{if((Held==201&&E.GetKey()==EKeys::R)||(Held==202&&E.GetKey()==EKeys::T)||(Held==31&&E.GetKey()==EKeys::A)||(Held==32&&E.GetKey()==EKeys::D))Stop();return FReply::Handled();}
void UColdSteelAlchemyWidget::EndSession()
{
    if(bEnded)return;bEnded=true;Stop();if(System&&System->Active())System->Suspend();
    if(Model)Model->OnChanged.Remove(ModelChanged);ModelChanged.Reset();
    if(BookPage)BookPage->ReleasePreview();
    if(View){View->Leave();View->Destroy();View=nullptr;}
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())HUD->SetAlchemyManagement(false);
}
void UColdSteelAlchemyWidget::NativeDestruct(){EndSession();Super::NativeDestruct();}
