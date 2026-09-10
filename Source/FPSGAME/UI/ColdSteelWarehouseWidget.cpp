#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseSortOption.h"
#include "ColdSteelItemTooltip.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ComboBoxString.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Components/SizeBox.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/BackgroundBlur.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "InputCoreTypes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "../Weapons/GunsmithSystem.h"
using namespace ColdSteelInventory;
void UColdSteelWarehouseDrag::Drop_Implementation(const FPointerEvent& E){if(SourceWidget.IsValid())SourceWidget->SetRenderOpacity(1);Super::Drop_Implementation(E);}
void UColdSteelWarehouseDrag::DragCancelled_Implementation(const FPointerEvent& E){if(SourceWidget.IsValid())SourceWidget->SetRenderOpacity(1);Super::DragCancelled_Implementation(E);}
namespace {
UTextBlock* Label(UWidgetTree* Tree,const FString& S,float Pixels,float Scale,bool Numbers=false)
{
    auto* T=Tree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(S));
    T->SetFont(Numbers?ColdSteelUI::NumberFont(Pixels*.75f/Scale):ColdSteelUI::TextFont(Pixels*.75f/Scale));T->SetColorAndOpacity(ColdSteelUI::TextPrimary);return T;
}
UButton* Button(UWidgetTree* Tree,const FString& S,float Scale)
{
    auto* B=Tree->ConstructWidget<UButton>();FButtonStyle Style;
    Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal,6/Scale));
    Style.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6/Scale,ColdSteelUI::Accent));
    Style.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,6/Scale));
    Style.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6/Scale));B->SetStyle(Style);B->SetContent(Label(Tree,S,13,Scale));return B;
}
}
void UColdSteelWarehouseCell::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);const float S=ColdSteelUI::PixelScale(this);
    auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetHeightOverride(56/S);Size->SetMinDesiredWidth(80/S);WidgetTree->RootWidget=Size;
    Surface=WidgetTree->ConstructWidget<UBorder>();Surface->SetPadding(FMargin(4/S));Size->SetContent(Surface);
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();Surface->SetContent(Overlay);
    auto* Center=WidgetTree->ConstructWidget<UHorizontalBox>();auto* CenterSlot=Overlay->AddChildToOverlay(Center);CenterSlot->SetHorizontalAlignment(HAlign_Center);CenterSlot->SetVerticalAlignment(VAlign_Center);CenterSlot->SetPadding(FMargin(30/S,0,30/S,0));
    Icon=WidgetTree->ConstructWidget<UImage>();auto* ImageSize=WidgetTree->ConstructWidget<USizeBox>();ImageSize->SetWidthOverride(32/S);ImageSize->SetHeightOverride(32/S);ImageSize->SetContent(Icon);Center->AddChildToHorizontalBox(ImageSize);
    Caption=Label(WidgetTree,TEXT(""),12,S);Caption->SetClipping(EWidgetClipping::ClipToBounds);Caption->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);
    auto* CS=Center->AddChildToHorizontalBox(Caption);CS->SetVerticalAlignment(VAlign_Center);CS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Quantity=Label(WidgetTree,TEXT(""),12,S,true);auto* QS=Overlay->AddChildToOverlay(Quantity);QS->SetHorizontalAlignment(HAlign_Right);QS->SetVerticalAlignment(VAlign_Bottom);
    Badges=Label(WidgetTree,TEXT(""),10,S);auto* BS=Overlay->AddChildToOverlay(Badges);BS->SetHorizontalAlignment(HAlign_Left);BS->SetVerticalAlignment(VAlign_Bottom);
    Badges->SetVisibility(ESlateVisibility::Collapsed);
    for(int32 N=0;N<4;++N){auto* Strip=WidgetTree->ConstructWidget<UBorder>();Strip->SetPadding(FMargin(0));auto* SS=Overlay->AddChildToOverlay(Strip);SS->SetHorizontalAlignment(N<2?HAlign_Left:HAlign_Right);SS->SetVerticalAlignment(VAlign_Fill);SS->SetPadding(FMargin(N==1?16/S:0,0,N==3?14/S:0,0));auto* Width=WidgetTree->ConstructWidget<USizeBox>();Width->SetWidthOverride((N==0?12:10)/S);Strip->SetContent(Width);auto* TextBlock=Label(WidgetTree,TEXT(""),10,S);TextBlock->SetJustification(ETextJustify::Center);Width->SetContent(TextBlock);BadgeSurfaces.Add(Strip);BadgeLabels.Add(TextBlock);Strip->SetVisibility(ESlateVisibility::Collapsed);}
}
void UColdSteelWarehouseCell::Configure(UColdSteelStatusModel* Source,int32 Index){Model=Source;Cell=Index;Refresh();}
void UColdSteelWarehouseCell::Refresh()
{
    if(!Surface||!Model)return;const float S=ColdSteelUI::PixelScale(this);
    const int32 ItemIndex=Owner(Model->Items(),4,Cell);const FColdSteelItem* I=ItemIndex>=0?&Model->Items()[ItemIndex]:nullptr;
    ItemId=I?I->InstanceId:TEXT("");Caption->SetText(FText::FromString(I?Text(*I,TEXT("name")):TEXT("")));Quantity->SetText(FText::FromString(I&&I->Count>1?FString::Printf(TEXT("%lld"),I->Count):TEXT("")));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,2/S,ColdSteelUI::Border));
    TSharedPtr<FJsonObject> Data;if(I)FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I->Data),Data);
    bool Crafted=I&&Flag(*I,TEXT("_isCrafted")),Enchanted=I&&Flag(*I,TEXT("_isEnchanted"));const TSharedPtr<FJsonObject>* Parts=nullptr;
    if(Data&&Data->TryGetObjectField(TEXT("_craftData"),Parts))Crafted|=!(*Parts)->Values.IsEmpty();
    if(Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))for(const auto& P:(*Parts)->Values)Crafted|=(P.Value->Type==EJson::Boolean&&P.Value->AsBool())||(P.Value->Type==EJson::String&&!P.Value->AsString().IsEmpty()&&P.Value->AsString()!=TEXT("false"));
    if(Data&&Data->TryGetObjectField(TEXT("_enchantData"),Parts))Enchanted|=(*Parts)->HasField(TEXT("prefix"))||(*Parts)->HasField(TEXT("suffix"));
    const bool Visible[]={I!=nullptr,I&&Number(*I,TEXT("enhanceLevel"))>0,Crafted,Enchanted};
    const FString Rarity=I?Text(*I,TEXT("rarity")):TEXT("");
    const TArray<FString> Rarities={TEXT("common"),TEXT("uncommon"),TEXT("rare"),TEXT("epic"),TEXT("mythic"),TEXT("legendary")};
    const TCHAR* RarityNames[]={TEXT("普\n通"),TEXT("优\n秀"),TEXT("稀\n有"),TEXT("史\n诗"),TEXT("神\n话"),TEXT("传\n说")};
    const FString Titles[]={RarityNames[FMath::Max(0,Rarities.Find(Rarity))],TEXT("强\n化"),TEXT("改\n造"),TEXT("附\n魔")};
    const TCHAR* RarityColors[]={TEXT("B4B4B4D9"),TEXT("7AC87AB2"),TEXT("7A9EC8B2"),TEXT("B47AC8B2"),TEXT("E6963CC7"),TEXT("D73C37CC")};
    const FLinearColor Colors[]={FLinearColor::FromSRGBColor(FColor::FromHex(RarityColors[FMath::Max(0,Rarities.Find(Rarity))])),FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E9BF63"))),FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("9B72C6"))),FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6FA7DE")))};
    for(int32 N=0;N<4;++N){BadgeSurfaces[N]->SetVisibility(Visible[N]?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);BadgeSurfaces[N]->SetBrush(ColdSteelUI::RoundedBrush(Colors[N],4/S,FLinearColor::Transparent,0));BadgeLabels[N]->SetText(FText::FromString(Titles[N]));BadgeLabels[N]->SetColorAndOpacity(N<2?ColdSteelUI::Tooltip:ColdSteelUI::TextPrimary);}
    if(I&&LoadedDefinition!=I->Definition){LoadedDefinition=I->Definition;Texture=nullptr;const FString File=Text(*I,TEXT("ue_icon"));if(!File.IsEmpty())Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);Icon->SetBrushFromTexture(Texture);}
    Icon->SetVisibility(I&&Texture?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    // The shared HUD tooltip owns hover, pinning and screen clamping.
    SetToolTip(nullptr);
}
UWidget* UColdSteelWarehouseCell::MakeDetails()
{
    if(!Model||!Model->FindItem(ItemId))return nullptr;
    auto* Tip=CreateWidget<UColdSteelItemTooltip>(GetOwningPlayer());Tip->ShowItem(ItemId,FVector2D::ZeroVector,true,this);return Tip;
}
FReply UColdSteelWarehouseCell::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& E)
{
    bPointerFocus=true;SetKeyboardFocus();bPointerFocus=false;if(E.GetEffectingButton()==EKeys::RightMouseButton){if(!ItemId.IsEmpty())Model->TransferWarehouse(ItemId,0);if(HUD){HUD->HideWarehouseDetails();HUD->HideItemTooltip(true);}return FReply::Handled();}
    return ItemId.IsEmpty()?FReply::Handled():FReply::Handled().DetectDrag(TakeWidget(),EKeys::LeftMouseButton);
}
FReply UColdSteelWarehouseCell::NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent& E){if(E.GetEffectingButton()==EKeys::LeftMouseButton&&HUD&&!ItemId.IsEmpty())HUD->ShowItemTooltip(ItemId,E.GetScreenSpacePosition(),true,this);return FReply::Handled();}
FReply UColdSteelWarehouseCell::NativeOnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent&){if(!ItemId.IsEmpty())Model->TransferWarehouse(ItemId,0);if(HUD){HUD->HideWarehouseDetails();HUD->HideItemTooltip(true);}return FReply::Handled();}
FReply UColdSteelWarehouseCell::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E){if(E.GetKey()==EKeys::F1){if(HUD){HUD->ShowItemTooltip(ItemId,G.LocalToAbsolute(G.GetLocalSize()),true,this);HUD->FocusItemTooltip();}return FReply::Handled();}if(E.GetKey()==EKeys::Enter){if(!ItemId.IsEmpty())Model->TransferWarehouse(ItemId,0);return FReply::Handled();}return Super::NativeOnKeyDown(G,E);}
void UColdSteelWarehouseCell::NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*& Out)
{
    if(HUD){HUD->HideWarehouseDetails();HUD->HideItemTooltip(true);}
    if(ItemId.IsEmpty())return;auto* D=NewObject<UColdSteelWarehouseDrag>(this);D->ItemId=ItemId;D->SourcePlace=4;D->SourceCell=Cell;D->SourceWidget=this;SetRenderOpacity(.3f);
    auto* Visual=NewObject<UImage>(this);Visual->SetBrushFromTexture(Texture);Visual->SetDesiredSizeOverride(FVector2D(56));Visual->SetRenderOpacity(.65f);D->DefaultDragVisual=Visual;D->Pivot=EDragPivot::CenterCenter;Out=D;
}
bool UColdSteelWarehouseCell::NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation* O)
{
    auto* D=Cast<UColdSteelItemDrag>(O);if(!D||D->HotbarIndex>=0)return false;
    const auto* I=Model->FindItem(D->ItemId);const bool Valid=I&&I->Place==D->SourcePlace&&I->Cell==D->SourceCell&&Model->ProposeWarehouse(D->ItemId,4,Cell).bValid;
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,2,Valid?ColdSteelUI::Success:ColdSteelUI::Danger));return true;
}
bool UColdSteelWarehouseCell::NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation* O)
{
    auto* D=Cast<UColdSteelItemDrag>(O);if(!D||D->HotbarIndex>=0)return false;
    const auto* I=Model->FindItem(D->ItemId);const bool OK=I&&I->Place==D->SourcePlace&&I->Cell==D->SourceCell&&Model->TransferWarehouse(D->ItemId,4,Cell);Refresh();return OK;
}
void UColdSteelWarehouseCell::NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*){Refresh();}
FReply UColdSteelWarehouseCell::NativeOnFocusReceived(const FGeometry& G,const FFocusEvent& E){if(HUD&&!ItemId.IsEmpty())HUD->ShowItemTooltip(ItemId,G.LocalToAbsolute(G.GetLocalSize()),false,this);return Super::NativeOnFocusReceived(G,E);}
void UColdSteelWarehouseCell::NativeOnFocusLost(const FFocusEvent& E){Super::NativeOnFocusLost(E);if(HUD&&!IsHovered())HUD->HideItemTooltip();}
void UColdSteelWarehouseCell::NativeOnMouseEnter(const FGeometry& G,const FPointerEvent& E){Super::NativeOnMouseEnter(G,E);if(HUD&&!ItemId.IsEmpty())HUD->ShowItemTooltip(ItemId,E.GetScreenSpacePosition(),false,this);Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,2,ColdSteelUI::Accent));}
void UColdSteelWarehouseCell::NativeOnMouseLeave(const FPointerEvent& E){Super::NativeOnMouseLeave(E);if(HUD&&!HasKeyboardFocus())HUD->HideItemTooltip();Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,2,ColdSteelUI::Border));}
void UColdSteelWarehouseWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const float S=ColdSteelUI::PixelScale(this);
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();WidgetTree->RootWidget=Overlay;
    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetBlurStrength(3.5f);auto* BlurSlot=Overlay->AddChildToOverlay(Blur);BlurSlot->SetHorizontalAlignment(HAlign_Fill);BlurSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Shell=WidgetTree->ConstructWidget<UBorder>();Shell->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,12/S));Shell->SetPadding(FMargin(4/S));auto* ShellSlot=Overlay->AddChildToOverlay(Shell);ShellSlot->SetHorizontalAlignment(HAlign_Fill);ShellSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Shell->SetContent(Stack);
    auto* Header=WidgetTree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Header)->SetPadding(FMargin(12/S,8/S));Header->AddChildToHorizontalBox(Label(WidgetTree,TEXT("仓库"),20,S))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Capacity=Label(WidgetTree,TEXT(""),12,S,true);Header->AddChildToHorizontalBox(Capacity)->SetVerticalAlignment(VAlign_Center);
    auto* X=Button(WidgetTree,TEXT("×"),S);Header->AddChildToHorizontalBox(X)->SetPadding(FMargin(8/S,0,0,0));X->OnClicked.AddDynamic(this,&ThisClass::Close);
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));auto* Grid=WidgetTree->ConstructWidget<UVerticalBox>();Scroll->AddChild(Grid);
    for(int32 Row=0;Row<10;++Row){auto* Pair=WidgetTree->ConstructWidget<UHorizontalBox>();Grid->AddChildToVerticalBox(Pair)->SetPadding(FMargin(0,0,0,2/S));for(int32 Col=0;Col<2;++Col){auto* C=CreateWidget<UColdSteelWarehouseCell>(GetOwningPlayer());Cells.Add(C);C->Configure(Model,Row*2+Col);auto* CellSlot=Pair->AddChildToHorizontalBox(C);CellSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CellSlot->SetPadding(FMargin(Col?2/S:0,0,0,0));}}
    Message=Label(WidgetTree,TEXT(""),12,S);Message->SetAutoWrapText(true);Stack->AddChildToVerticalBox(Message)->SetPadding(FMargin(8/S,4/S));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Actions)->SetPadding(FMargin(8/S,8/S));
    auto* Store=Button(WidgetTree,TEXT("↓ 全部存入"),S);Actions->AddChildToHorizontalBox(Store)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));Store->OnClicked.AddDynamic(this,&ThisClass::StoreAll);
    auto* Match=Button(WidgetTree,TEXT("↑ 取出同类"),S);auto* MatchSlot=Actions->AddChildToHorizontalBox(Match);MatchSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));MatchSlot->SetPadding(FMargin(4/S,0));Match->OnClicked.AddDynamic(this,&ThisClass::Matching);
    SortMenu=WidgetTree->ConstructWidget<UComboBoxString>();
    SortMenu->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::SortOption);
    auto ComboStyle=SortMenu->GetWidgetStyle();auto ComboButton=ComboStyle.ComboButtonStyle;auto ButtonStyle=ComboButton.ButtonStyle;
    ButtonStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal,6/S));ButtonStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6/S));ButtonStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,6/S));
    ComboButton.SetButtonStyle(ButtonStyle);ComboButton.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,6/S));ComboStyle.SetComboButtonStyle(ComboButton);SortMenu->SetWidgetStyle(ComboStyle);
    for(const FString Option:{TEXT("整理仓库"),TEXT("按稀有度"),TEXT("按价值"),TEXT("近战武器"),TEXT("远程武器"),TEXT("盾牌"),TEXT("防具与饰品"),TEXT("消耗品"),TEXT("强化材料"),TEXT("材料"),TEXT("贡品"),TEXT("金币"),TEXT("其他")})SortMenu->AddOption(Option);
    SortMenu->SetSelectedIndex(0);Actions->AddChildToHorizontalBox(SortMenu)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));SortMenu->OnSelectionChanged.AddDynamic(this,&ThisClass::SortChanged);
    auto* Footer=WidgetTree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Footer)->SetPadding(FMargin(12/S,10/S));
    Previous=Button(WidgetTree,TEXT("< 上一页"),S);Footer->AddChildToHorizontalBox(Previous);Previous->OnClicked.AddDynamic(this,&ThisClass::PreviousPage);
    Page=Label(WidgetTree,TEXT(""),12,S,true);Page->SetJustification(ETextJustify::Center);auto* PS=Footer->AddChildToHorizontalBox(Page);PS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));PS->SetVerticalAlignment(VAlign_Center);
    Next=Button(WidgetTree,TEXT("下一页 >"),S);Footer->AddChildToHorizontalBox(Next);Next->OnClicked.AddDynamic(this,&ThisClass::NextPage);Refresh();
}
void UColdSteelWarehouseWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;for(const auto& C:Cells)C->SetHUD(HUD);}
void UColdSteelWarehouseWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::Refresh);Refresh();}
void UColdSteelWarehouseWidget::NativeDestruct(){if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
void UColdSteelWarehouseWidget::ResetPage(){Model->WarehousePage=0;Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::Refresh(){if(!Model||!Capacity)return;int32 Used=0;for(const auto& I:Model->Items())if(I.Place==4)++Used;Capacity->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"),Used,Model->WarehouseCapacity())));Page->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"),Model->WarehousePage+1,Model->WarehouseCapacity()/20)));Message->SetText(FText::FromString(Model->ResultMessage()));Previous->SetIsEnabled(Model->WarehousePage>0);Next->SetIsEnabled(Model->WarehousePage<Model->WarehouseCapacity()/20-1);for(int32 N=0;N<Cells.Num();++N)Cells[N]->Configure(Model,Model->WarehousePage*20+N);}
void UColdSteelWarehouseWidget::Close(){if(HUD)HUD->CloseWarehouse();}
void UColdSteelWarehouseSortOption::SetCaption(const FString& Caption){WidgetTree->RootWidget=Label(WidgetTree,Caption,13,ColdSteelUI::PixelScale(this));}
UWidget* UColdSteelWarehouseWidget::SortOption(FString Item){auto* Option=CreateWidget<UColdSteelWarehouseSortOption>(GetOwningPlayer());Option->SetCaption(Item);return Option;}
void UColdSteelWarehouseWidget::StoreAll(){Model->WarehouseBatch(false);Refresh();}
void UColdSteelWarehouseWidget::Matching(){Model->WarehouseBatch(true);Refresh();}
void UColdSteelWarehouseWidget::PreviousPage(){Model->WarehousePage=FMath::Max(0,Model->WarehousePage-1);Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::NextPage(){Model->WarehousePage=FMath::Min(Model->WarehouseCapacity()/20-1,Model->WarehousePage+1);Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::SortChanged(FString Selection,ESelectInfo::Type Type){int32 N=SortMenu->FindOptionIndex(Selection);if(N<1)return;Model->SortWarehouse(N==1?TEXT("rarity"):N==2?TEXT("price"):TEXT("category"),N-3);SortMenu->SetSelectedIndex(0);Scroll->ScrollToStart();Refresh();}

FReply UColdSteelWarehouseCell::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E){if(HUD&&!ItemId.IsEmpty()&&!E.GetCursorDelta().IsNearlyZero())HUD->ShowItemTooltip(ItemId,E.GetScreenSpacePosition(),false,this);return Super::NativeOnMouseMove(G,E);}
