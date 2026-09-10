#include "ColdSteelItemTooltip.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
using namespace ColdSteelUI;

void UColdSteelItemTooltip::NativeOnInitialized()
{
    Super::NativeOnInitialized();Scale=PixelScale(this);SetIsFocusable(true);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    Frame=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=Frame;
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();Frame->SetContent(Overlay);
    Vertical=WidgetTree->ConstructWidget<UScrollBox>();Vertical->SetScrollbarThickness(FVector2D(12/Scale));Vertical->SetScrollbarPadding(FMargin(0));Vertical->SetAllowOverscroll(false);Vertical->SetAnimateWheelScrolling(false);Overlay->AddChildToOverlay(Vertical);
    HorizontalHeight=WidgetTree->ConstructWidget<USizeBox>();Vertical->AddChild(HorizontalHeight);
    Horizontal=WidgetTree->ConstructWidget<UScrollBox>();Horizontal->SetOrientation(Orient_Horizontal);Horizontal->SetScrollbarThickness(FVector2D(12/Scale));Horizontal->SetScrollbarPadding(FMargin(0));Horizontal->SetAllowOverscroll(false);Horizontal->SetAnimateWheelScrolling(false);HorizontalHeight->SetContent(Horizontal);
    Cards=WidgetTree->ConstructWidget<UHorizontalBox>();Horizontal->AddChild(Cards);
    Close=WidgetTree->ConstructWidget<UButton>();FButtonStyle B;
    B.SetNormal(RoundedBrush(ItemTooltipNegative,12/Scale,FLinearColor::Transparent,0)).SetHovered(RoundedBrush(FLinearColor(.72f,.035f,.035f,1),12/Scale,FLinearColor::Transparent,0)).SetPressed(B.Normal);
    Close->SetStyle(B);Close->SetContent(Text(TEXT("×"),18,FLinearColor::White));Close->OnClicked.AddDynamic(this,&ThisClass::CloseClicked);
    auto* ButtonSize=WidgetTree->ConstructWidget<USizeBox>();ButtonSize->SetWidthOverride(24/Scale);ButtonSize->SetHeightOverride(24/Scale);ButtonSize->SetContent(Close);
    auto* CloseSlot=Overlay->AddChildToOverlay(ButtonSize);CloseSlot->SetHorizontalAlignment(HAlign_Right);CloseSlot->SetVerticalAlignment(VAlign_Top);CloseSlot->SetPadding(FMargin(0,6/Scale,18/Scale,0));
    SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelItemTooltip::NativeConstruct(){Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::Refresh);}
void UColdSteelItemTooltip::NativeDestruct(){if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
UTextBlock* UColdSteelItemTooltip::Text(const FString& V,float Pixels,const FLinearColor& Color,bool Numeric)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(V));T->SetFont(Numeric?NumberFont(Pixels*.75f/Scale):TextFont(Pixels*.75f/Scale));T->SetColorAndOpacity(Color);T->SetAutoWrapText(false);T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
}
void UColdSteelItemTooltip::AddRow(UVerticalBox* Column,const FColdSteelTooltipRow& R)
{
    if(R.bSection){auto* Line=WidgetTree->ConstructWidget<UBorder>();Line->SetBrushColor(ItemTooltipBorder);Line->SetPadding(FMargin(0,.5f/Scale));Column->AddChildToVerticalBox(Line)->SetPadding(FMargin(0,8/Scale,0,6/Scale));Column->AddChildToVerticalBox(Text(R.Label,16,ItemTooltipText))->SetPadding(FMargin(0,0,0,6/Scale));return;}
    auto* H=WidgetTree->ConstructWidget<UHorizontalBox>();Column->AddChildToVerticalBox(H)->SetPadding(FMargin(0,0,0,6/Scale));
    if(!R.Label.IsEmpty()||R.bContinuation){auto* L=H->AddChildToHorizontalBox(Text(R.Label,16,ItemTooltipSecondary));FSlateChildSize S(ESlateSizeRule::Fill);S.Value=.4f;L->SetSize(S);L->SetPadding(FMargin(0,0,18/Scale,0));}
    bool Numeric=!R.Value.IsEmpty();const FString NumericChars=TEXT("0123456789 .,/+:−=×x%°±()[]msLvp发秒个层米-→");for(TCHAR Ch:R.Value)if(!NumericChars.Contains(FString::Chr(Ch))){Numeric=false;break;}
    auto* V=Text(R.Value,16,R.Tone>0?ItemTooltipPositive:R.Tone<0?ItemTooltipNegative:ItemTooltipText,Numeric);V->SetJustification(R.Label.IsEmpty()&&!R.bContinuation?ETextJustify::Left:ETextJustify::Right);
    auto* ValueSlot=H->AddChildToHorizontalBox(V);FSlateChildSize ValueSize(ESlateSizeRule::Fill);ValueSize.Value=R.Label.IsEmpty()&&!R.bContinuation?1.f:.6f;ValueSlot->SetSize(ValueSize);
}
void UColdSteelItemTooltip::BuildCards()
{
    Cards->ClearChildren();Textures.Reset();
    for(int32 Index=0;Index<Presentation.Cards.Num();++Index){const auto& Data=Presentation.Cards[Index];const bool Main=Index==Presentation.Cards.Num()-1;
        auto* Minimum=WidgetTree->ConstructWidget<USizeBox>();Minimum->SetMinDesiredWidth(Data.MinimumWidth/Scale);
        auto* CardSlot=Cards->AddChildToHorizontalBox(Minimum);CardSlot->SetVerticalAlignment(VAlign_Top);CardSlot->SetPadding(FMargin(Index?18/Scale:0,0,0,4/Scale));
        auto* Surface=WidgetTree->ConstructWidget<UBorder>();Surface->SetBrush(RoundedBrush(ItemTooltipSurface,8/Scale,ItemTooltipBorder,1/Scale));Surface->SetPadding(FMargin((Main?22:20)/Scale,(Main?18:16)/Scale));Minimum->SetContent(Surface);
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(Column);
        if(Main){auto* Header=WidgetTree->ConstructWidget<UHorizontalBox>();Column->AddChildToVerticalBox(Header)->SetPadding(FMargin(0,0,0,12/Scale));
            auto* IconSize=WidgetTree->ConstructWidget<USizeBox>();IconSize->SetWidthOverride(44/Scale);IconSize->SetHeightOverride(44/Scale);Header->AddChildToHorizontalBox(IconSize)->SetPadding(FMargin(0,0,10/Scale,0));
            auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);IconSize->SetContent(Fit);
            auto* Icon=WidgetTree->ConstructWidget<UImage>();Fit->SetContent(Icon);
            if(!Presentation.Icon.IsEmpty())if(auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Presentation.Icon)){Textures.Add(Texture);Icon->SetBrushFromTexture(Texture,true);}
            auto* TitleBox=WidgetTree->ConstructWidget<UVerticalBox>();auto* TitleSlot=Header->AddChildToHorizontalBox(TitleBox);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetPadding(FMargin(0,0,26/Scale,0));
            auto* NameRow=WidgetTree->ConstructWidget<UHorizontalBox>();TitleBox->AddChildToVerticalBox(NameRow);NameRow->AddChildToHorizontalBox(Text(Presentation.Name,20,ItemTooltipText))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
            if(!Presentation.Enhancement.IsEmpty()){auto* Badge=WidgetTree->ConstructWidget<UBorder>();Badge->SetBrush(RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E9BF63"))),4/Scale,FLinearColor::Transparent,0));Badge->SetPadding(FMargin(5/Scale,2/Scale));Badge->SetContent(Text(Presentation.Enhancement,12,ItemTooltipText));NameRow->AddChildToHorizontalBox(Badge)->SetPadding(FMargin(18/Scale,0,0,0));}
            static const TMap<FString,FString> Names={{TEXT("common"),TEXT("普通")},{TEXT("uncommon"),TEXT("优秀")},{TEXT("rare"),TEXT("稀有")},{TEXT("epic"),TEXT("史诗")},{TEXT("mythic"),TEXT("神话")},{TEXT("legendary"),TEXT("传说")}};
            const FString* Rarity=Names.Find(Presentation.Rarity);FString Type=Presentation.Type+TEXT(" | ")+(Rarity?*Rarity:Presentation.Rarity);if(Presentation.Level>0)Type+=FString::Printf(TEXT(" | Lv.%d"),Presentation.Level);
            TitleBox->AddChildToVerticalBox(Text(Type,12,ItemTooltipSecondary))->SetPadding(FMargin(0,4/Scale,0,0));
        }else Column->AddChildToVerticalBox(Text(Data.Title,20,ItemTooltipText))->SetPadding(FMargin(0,0,0,10/Scale));
        for(const auto& R:Data.Rows)AddRow(Column,R);
        if(Main&&!Presentation.Description.IsEmpty())Column->AddChildToVerticalBox(Text(Presentation.Description,16,ItemTooltipSecondary))->SetPadding(FMargin(0,8/Scale,0,0));
    }
    Vertical->SetScrollOffset(0);Settle=2;
}
void UColdSteelItemTooltip::ShowItem(const FString& Id,FVector2D Anchor,bool Pin,UWidget* Source)
{
    if(IsPinned()&&!Pin)return;
    const bool Changed=InstanceId!=Id;InstanceId=Id;At=Anchor;ReturnFocus=Source;bPinned=Pin;
    SetVisibility(Pin?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::HitTestInvisible);
    if(Changed)Signature.Empty();Refresh();FitAndPlace(Changed);
}
void UColdSteelItemTooltip::Refresh()
{
    if(!IsVisible()||!Model)return;const auto* I=Model->FindItem(InstanceId);if(!I||I->Place==2){Hide(true);return;}
    const FString New=I->Data+FString::Printf(TEXT("|%lld|%d|%d|%g|%g"),I->Count,I->Magazine,I->Place,Model->Derived(TEXT("atk")),Model->Derived(TEXT("aspd")));
    if(New==Signature)return;Signature=New;Presentation=BuildColdSteelItemTooltip(*I,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());BuildCards();FitAndPlace(true);
}
void UColdSteelItemTooltip::FitAndPlace(bool RevealMain)
{
    if(!Frame||!Cards)return;Cards->ForceLayoutPrepass();const FVector2D Natural=Cards->GetDesiredSize();const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;LastViewport=View;
    const FVector2D Available=View-FVector2D(24/Scale);bHorizontalOverflow=Natural.X>Available.X;
    const float Bar=bHorizontalOverflow?14/Scale:0;const float H=Natural.Y+Bar;bVerticalOverflow=H>Available.Y;
    Size=FVector2D(FMath::Min(Available.X,Natural.X+(bVerticalOverflow?14/Scale:0)),FMath::Min(Available.Y,H));
    Frame->SetWidthOverride(Size.X);Frame->SetHeightOverride(Size.Y);HorizontalHeight->SetHeightOverride(H);
    Horizontal->SetAlwaysShowScrollbar(bHorizontalOverflow);Vertical->SetAlwaysShowScrollbar(bVerticalOverflow);
    Horizontal->SetScrollBarVisibility(bHorizontalOverflow?ESlateVisibility::Visible:ESlateVisibility::Collapsed);Vertical->SetScrollBarVisibility(bVerticalOverflow?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!bHorizontalOverflow)Horizontal->SetScrollOffset(0);else if(RevealMain)Horizontal->ScrollToEnd();
    FVector2D Point(At.X-Size.X-10/Scale,At.Y+10/Scale);if(Point.X<10/Scale)Point.X=At.X+10/Scale;if(Point.Y+Size.Y>View.Y-10/Scale)Point.Y=At.Y-Size.Y-10/Scale;
    Point.X=FMath::Clamp(Point.X,10/Scale,FMath::Max(10.f/Scale,float(View.X-Size.X-10/Scale)));Point.Y=FMath::Clamp(Point.Y,10/Scale,FMath::Max(10.f/Scale,float(View.Y-Size.Y-10/Scale)));
    if(auto* CanvasSlot=Cast<UCanvasPanelSlot>(Slot)){CanvasSlot->SetPosition(Point);CanvasSlot->SetSize(Size);}
}
void UColdSteelItemTooltip::NativeTick(const FGeometry& G,float D)
{
    Super::NativeTick(G,D);if(!IsVisible())return;
    if(Settle>0){--Settle;FitAndPlace(true);}else if(!LastViewport.Equals(UWidgetLayoutLibrary::GetViewportSize(this)/Scale))FitAndPlace(false);
}
void UColdSteelItemTooltip::Hide(bool Force){if(IsPinned()&&!Force)return;const bool RestoreFocus=HasKeyboardFocus()||HasFocusedDescendants();bPinned=false;SetVisibility(ESlateVisibility::Collapsed);Signature.Empty();if(RestoreFocus&&ReturnFocus.IsValid())ReturnFocus->SetKeyboardFocus();}
void UColdSteelItemTooltip::CloseClicked(){Hide(true);if(ReturnFocus.IsValid())ReturnFocus->SetKeyboardFocus();}
void UColdSteelItemTooltip::ScrollToSideCards(){Horizontal->ScrollToStart();}
FReply UColdSteelItemTooltip::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape){CloseClicked();return FReply::Handled();}
    if(E.GetKey()==EKeys::Left||E.GetKey()==EKeys::Right){Horizontal->SetScrollOffset(FMath::Max(0.f,Horizontal->GetScrollOffset()+(E.GetKey()==EKeys::Left?-160:160)/Scale));return FReply::Handled();}
    if(E.GetKey()==EKeys::Up||E.GetKey()==EKeys::Down){Vertical->SetScrollOffset(FMath::Max(0.f,Vertical->GetScrollOffset()+(E.GetKey()==EKeys::Up?-80:80)/Scale));return FReply::Handled();}
    return Super::NativeOnKeyDown(G,E);
}
