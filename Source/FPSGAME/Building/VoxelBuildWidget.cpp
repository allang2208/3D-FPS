#include "VoxelBuildWidget.h"
#include "VoxelBuildComponent.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../UI/GunsmithUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"

// Pixel sizes follow Docs/UI/ui-cold-steel-design-system.md (20/16/14/12 tiers).
namespace
{
    constexpr float HeaderHeight=36.f,CardHeight=44.f,CardGap=4.f;
    constexpr float DrawerViewportFraction=.48f,DrawerMinWidth=720.f,DrawerMaxWidth=1040.f,DrawerEdgeInset=12.f;
    // Number row while the drawer is focused: the Nth card of the visible category.
    int32 NumberKeyIndex(const FKey& Key)
    {
        static const FKey Keys[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five,EKeys::Six,EKeys::Seven,EKeys::Eight,EKeys::Nine};
        for(int32 Index=0;Index<UE_ARRAY_COUNT(Keys);++Index)if(Key==Keys[Index])return Index;
        return INDEX_NONE;
    }
}

void UVoxelBuildCardProxy::Clicked()
{
    if(auto* Owner=Panel.Get())Owner->Pick(CardId,bComponentCard);
}

void UVoxelBuildCardProxy::Hovered()
{
    if(auto* Owner=Panel.Get())Owner->ShowTooltip(CardIndex);
}

void UVoxelBuildCardProxy::Unhovered()
{
    if(auto* Owner=Panel.Get())Owner->HideTooltip();
}

UTextBlock* UVoxelBuildWidget::Text(const FString& Caption,float Pixels,bool Numeric,bool Medium,bool bTrack)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Caption));
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    // Tooltip rows are rebuilt on every hover, so they are not tracked for DPI re-scaling.
    if(bTrack)Labels.Add({Label,Pixels,Numeric,Medium});return Label;
}

UButton* UVoxelBuildWidget::Tab(const FString& Caption,bool bComponents)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Button=WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    Button->SetContent(Text(Caption,14,false,bComponents));
    if(bComponents)Button->OnClicked.AddDynamic(this,&ThisClass::ShowComponentCategory);
    else Button->OnClicked.AddDynamic(this,&ThisClass::ShowMaterialCategory);
    return Button;
}

void UVoxelBuildWidget::NativeOnInitialized()
{
    // The drawer takes keyboard focus while it owns the cursor, so Esc/B and 1-9 stay here.
    Super::NativeOnInitialized();SetIsFocusable(true);
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    Surface=WidgetTree->ConstructWidget<UBorder>();PanelSlot=Root->AddChildToCanvas(Surface);
    PanelSlot->SetAnchors(FAnchors(1,0,1,1));PanelSlot->SetAlignment(FVector2D(1,0));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    Surface->SetPadding(FMargin(1/Scale));
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetPadding(FMargin(0));
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetApplyAlphaToBlur(true);
    Blur->SetCornerRadius(FVector4(ColdSteelUI::PanelRadius));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    Surface->SetContent(Blur);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();
    Tint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));Tint->SetPadding(FMargin(0));
    Blur->SetContent(Tint);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);
    auto* Header=WidgetTree->ConstructWidget<UBorder>();
    Header->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Stack->AddChildToVerticalBox(Header);
    auto* HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSize->SetHeightOverride(HeaderHeight/Scale);Header->SetContent(HeaderSize);
    Header->SetPadding(FMargin(18/Scale,0));
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    Title=Text(TEXT("自由建造"),20,false,true);
    auto* TitleSlot=Heading->AddChildToHorizontalBox(Title);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    Selection=Text(TEXT(""),12,true);
    auto* CountSlot=Heading->AddChildToHorizontalBox(Selection);CountSlot->SetVerticalAlignment(VAlign_Center);
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Stack->AddChildToVerticalBox(Body)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Status=Text(TEXT(""),14);Status->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Status)->SetPadding(FMargin(18/Scale,10/Scale,12/Scale,2/Scale));
    Structure=Text(TEXT(""),12);Structure->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Structure->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Structure)->SetPadding(FMargin(18/Scale,0,12/Scale,10/Scale));
    auto* Tabs=WidgetTree->ConstructWidget<UHorizontalBox>();
    Body->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(12/Scale,0,12/Scale,8/Scale));
    MaterialTab=Tab(TEXT("材质"),false);ComponentTab=Tab(TEXT("构件"),true);
    for(UButton* Entry:{MaterialTab.Get(),ComponentTab.Get()})
    {
        auto* TabSlot=Tabs->AddChildToHorizontalBox(Entry);TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        TabSlot->SetPadding(FMargin(ColdSteelUI::ActionGap*.5f/Scale,0));
        Cast<UButtonSlot>(Entry->GetContent()->Slot)->SetPadding(FMargin(10/Scale,8/Scale));
    }
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetAllowOverscroll(false);
    auto* ScrollSlot=Body->AddChildToVerticalBox(Scroll);
    ScrollSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ScrollSlot->SetPadding(FMargin(18/Scale,0,12/Scale,0));
    CardList=WidgetTree->ConstructWidget<UVerticalBox>();Scroll->AddChild(CardList);
    Controls=Text(TEXT(""),12);Controls->SetColorAndOpacity(ColdSteelUI::TextTertiary);Controls->SetAutoWrapText(true);
    Stack->AddChildToVerticalBox(Controls)->SetPadding(FMargin(18/Scale,8/Scale,18/Scale,12/Scale));
    BuildTooltipCard();
    SetVisibility(ESlateVisibility::Collapsed);
}

void UVoxelBuildWidget::BuildTooltipCard()
{
    // Same card as the equipment tooltip (surface, outline, 16px radius, red close button).
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);
    if(!Root)return;
    TooltipCard=WidgetTree->ConstructWidget<UBorder>();
    TooltipCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::TooltipGlass,16/Scale,ColdSteelUI::TooltipOutline,1/Scale));
    TooltipCard->SetPadding(FMargin(20/Scale,16/Scale));
    TooltipCard->SetClipping(EWidgetClipping::ClipToBounds);
    TooltipCard->SetVisibility(ESlateVisibility::Collapsed);
    TooltipSlot=Root->AddChildToCanvas(TooltipCard);
    TooltipSlot->SetAnchors(FAnchors(0));TooltipSlot->SetAlignment(FVector2D(0,0));TooltipSlot->SetZOrder(60);
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();TooltipCard->SetContent(Column);
    auto* Header=WidgetTree->ConstructWidget<UHorizontalBox>();
    Column->AddChildToVerticalBox(Header)->SetPadding(FMargin(0,0,0,8/Scale));
    auto* Titles=WidgetTree->ConstructWidget<UVerticalBox>();
    Header->AddChildToHorizontalBox(Titles)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TooltipTitle=Text(TEXT(""),16,false,true);Titles->AddChildToVerticalBox(TooltipTitle);
    TooltipSubtitle=Text(TEXT(""),12);TooltipSubtitle->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Titles->AddChildToVerticalBox(TooltipSubtitle);
    auto* Close=WidgetTree->ConstructWidget<UButton>();
    Close->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::TooltipCloseNormal,12/Scale,FLinearColor::Transparent,0))
        .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TooltipCloseHover,12/Scale,FLinearColor::Transparent,0)));
    Close->SetContent(Text(TEXT("×"),14));Close->OnClicked.AddDynamic(this,&ThisClass::CloseTooltip);
    auto* CloseSize=WidgetTree->ConstructWidget<USizeBox>();
    CloseSize->SetWidthOverride(24/Scale);CloseSize->SetHeightOverride(24/Scale);CloseSize->SetContent(Close);
    Header->AddChildToHorizontalBox(CloseSize);
    TooltipBox=WidgetTree->ConstructWidget<UVerticalBox>();Column->AddChildToVerticalBox(TooltipBox);
}

void UVoxelBuildWidget::ShowTooltip(int32 CardIndex)
{
    if(!TooltipCard||!TooltipBox||!Cards.IsValidIndex(CardIndex))return;
    const FCard& Card=Cards[CardIndex];
    const TArray<FVoxelBuildPanelCard>& Source=Card.bComponent?ComponentCards:MaterialCards;
    const FVoxelBuildPanelCard* Entry=Source.FindByPredicate([&Card](const FVoxelBuildPanelCard& Candidate){return Candidate.Id==Card.Id;});
    if(!Entry)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    TooltipTitle->SetText(FText::FromString(Entry->Caption));
    TooltipSubtitle->SetText(FText::FromString(Entry->Subtitle));
    TooltipBox->ClearChildren();
    for(const TPair<FString,FString>& Row:Entry->Rows)
    {
        if(Row.Value.IsEmpty())
        {
            auto* Section=Text(Row.Key,16,false,true,false);
            TooltipBox->AddChildToVerticalBox(Section)->SetPadding(FMargin(0,10/Scale,0,4/Scale));
            auto* Divider=WidgetTree->ConstructWidget<UBorder>();
            Divider->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::TooltipRule,0));
            auto* Height=WidgetTree->ConstructWidget<USizeBox>();Height->SetHeightOverride(1/Scale);Divider->SetContent(Height);
            TooltipBox->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0,0,0,4/Scale));
            continue;
        }
        auto* Line=WidgetTree->ConstructWidget<UHorizontalBox>();
        TooltipBox->AddChildToVerticalBox(Line)->SetPadding(FMargin(0,2/Scale));
        auto* Label=Text(Row.Key,14,false,false,false);Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        FSlateChildSize LabelSize(ESlateSizeRule::Fill);LabelSize.Value=.45f;
        Line->AddChildToHorizontalBox(Label)->SetSize(LabelSize);
        auto* Value=Text(Row.Value,14,true,false,false);Value->SetJustification(ETextJustify::Right);
        FSlateChildSize ValueSize(ESlateSizeRule::Fill);ValueSize.Value=.55f;
        Line->AddChildToHorizontalBox(Value)->SetSize(ValueSize);
    }
    if(!Entry->Note.IsEmpty())
    {
        auto* Note=Text(Entry->Note,12,false,false,false);Note->SetColorAndOpacity(ColdSteelUI::TextTertiary);Note->SetAutoWrapText(true);
        TooltipBox->AddChildToVerticalBox(Note)->SetPadding(FMargin(0,8/Scale,0,0));
    }
    TooltipIndex=CardIndex;
    TooltipCard->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    UpdateTooltipPlacement();
}

void UVoxelBuildWidget::HideTooltip(bool bForce)
{
    // Keep the card open while the pointer sits on the tooltip itself, so its close button is reachable.
    if(!bForce&&TooltipIndex!=INDEX_NONE&&TooltipCard&&TooltipCard->IsVisible())
    {
        float MouseX=0,MouseY=0;
        if(auto* PC=GetOwningPlayer();PC&&UWidgetLayoutLibrary::GetMousePositionScaledByDPI(PC,MouseX,MouseY))
        {
            const FGeometry& Geometry=TooltipCard->GetCachedGeometry();
            const FVector2D Local=Geometry.AbsoluteToLocal(FVector2D(MouseX,MouseY));
            const FVector2D Size=Geometry.GetLocalSize();
            if(Local.X>=0&&Local.Y>=0&&Local.X<=Size.X&&Local.Y<=Size.Y)return;
        }
    }
    TooltipIndex=INDEX_NONE;
    if(TooltipCard)TooltipCard->SetVisibility(ESlateVisibility::Collapsed);
}

void UVoxelBuildWidget::CloseTooltip(){HideTooltip(true);}

void UVoxelBuildWidget::UpdateTooltipPlacement()
{
    if(!TooltipCard||!TooltipSlot||TooltipIndex==INDEX_NONE)return;
    auto* PC=GetOwningPlayer();if(!PC)return;
    float MouseX=0,MouseY=0;
    if(!UWidgetLayoutLibrary::GetMousePositionScaledByDPI(PC,MouseX,MouseY))return;
    const float Scale=ColdSteelUI::PixelScale(this);
    const FVector2D Units=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;
    const FVector2D Extent(FMath::Min(430.f/Scale,FMath::Max(240.f/Scale,Units.X-40/Scale)),
        FMath::Min(430.f/Scale,FMath::Max(200.f/Scale,Units.Y-40/Scale)));
    const float Gap=10/Scale;
    // Open to the left of the cursor: the drawer itself sits on the right edge.
    FVector2D Position(MouseX-Extent.X-Gap,MouseY+Gap);
    if(Position.X<Gap)Position.X=MouseX+Gap;
    Position.X=FMath::Clamp(Position.X,Gap,FMath::Max(Gap,Units.X-Extent.X-Gap));
    Position.Y=FMath::Clamp(Position.Y,Gap,FMath::Max(Gap,Units.Y-Extent.Y-Gap));
    TooltipSlot->SetPosition(Position);
    TooltipSlot->SetSize(Extent);
}

void UVoxelBuildWidget::SetDrawerOpen(bool Open)
{
    bDrawerOpen=Open;
    // A collapsed widget is not ticked, so the drawer has to be visible before it can slide in.
    if(Open){SetVisibility(ESlateVisibility::SelfHitTestInvisible);RefreshLayout();}
    else HideTooltip(true);
}

void UVoxelBuildWidget::SetContent(const TArray<FVoxelBuildPanelCard>& Materials,const TArray<FVoxelBuildPanelCard>& Components)
{
    bool bChanged=MaterialCards.Num()!=Materials.Num()||ComponentCards.Num()!=Components.Num();
    for(int32 Index=0;!bChanged&&Index<Materials.Num();++Index)
        bChanged=MaterialCards[Index].Id!=Materials[Index].Id||MaterialCards[Index].Caption!=Materials[Index].Caption||MaterialCards[Index].Detail!=Materials[Index].Detail;
    for(int32 Index=0;!bChanged&&Index<Components.Num();++Index)
        bChanged=ComponentCards[Index].Id!=Components[Index].Id||ComponentCards[Index].Caption!=Components[Index].Caption||ComponentCards[Index].Detail!=Components[Index].Detail;
    if(!bChanged)return;
    MaterialCards=Materials;ComponentCards=Components;bCardsDirty=true;
}

void UVoxelBuildWidget::SetSelection(FName Material,FName Component)
{
    if(SelectedMaterial==Material&&SelectedComponent==Component)return;
    SelectedMaterial=Material;SelectedComponent=Component;bSelectionDirty=true;
}

void UVoxelBuildWidget::Pick(FName Id,bool bComponent)
{
    auto* Owner=Builder();
    if(!Owner)return;
    // Picking an entry ends the mouse phase; the component restores game input and aiming.
    if(bComponent)Owner->SelectComponent(Id);else Owner->SelectMaterial(Id);
}

UVoxelBuildComponent* UVoxelBuildWidget::Builder() const
{
    auto* PC=GetOwningPlayer();
    return PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
}

FReply UVoxelBuildWidget::NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    auto* Owner=Builder();
    if(!Owner)return Super::NativeOnKeyDown(Geometry,Event);
    const FKey Key=Event.GetKey();
    if(Key!=EKeys::Zero)
    {
        const int32 Number=NumberKeyIndex(Key);
        if(Number!=INDEX_NONE&&Cards.IsValidIndex(Number))
        {
            // Picking a card always returns to building (SelectMaterial/SelectComponent close the drawer).
            const FCard& Card=Cards[Number];
            if(Card.bComponent)Owner->SelectComponent(Card.Id);else Owner->SelectMaterial(Card.Id);
            return FReply::Handled();
        }
    }
    if(Owner->HandleDrawerKey(Key))return FReply::Handled();
    return Super::NativeOnKeyDown(Geometry,Event);
}

void UVoxelBuildWidget::ShowMaterialCategory(){if(bComponentCategory){bComponentCategory=false;bCardsDirty=true;}}
void UVoxelBuildWidget::ShowComponentCategory(){if(!bComponentCategory){bComponentCategory=true;bCardsDirty=true;}}

void UVoxelBuildWidget::RebuildCards()
{
    if(!CardList)return;
    HideTooltip(true);
    const float Scale=ColdSteelUI::PixelScale(this);
    CardList->ClearChildren();Cards.Reset();CardProxies.Reset();
    const TArray<FVoxelBuildPanelCard>& Source=bComponentCategory?ComponentCards:MaterialCards;
    if(Source.IsEmpty())
    {
        auto* Empty=Text(bComponentCategory?TEXT("暂无构件 · 请在调色板 Components 中添加"):TEXT("暂无可用材质"),12);
        Empty->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        CardList->AddChildToVerticalBox(Empty)->SetPadding(FMargin(2/Scale,6/Scale));
        return;
    }
    for(const auto& Entry:Source)
    {
        auto* Proxy=NewObject<UVoxelBuildCardProxy>(this);Proxy->CardId=Entry.Id;Proxy->bComponentCard=Entry.bComponent;Proxy->Panel=this;
        Proxy->CardIndex=Cards.Num();
        CardProxies.Add(Proxy);
        auto* Button=WidgetTree->ConstructWidget<UButton>();
        Button->SetStyle(ColdSteelUI::ButtonStyle(Scale));
        Button->OnClicked.AddDynamic(Proxy,&UVoxelBuildCardProxy::Clicked);
        Button->OnHovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Hovered);
        Button->OnUnhovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Unhovered);
        auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetHeightOverride(CardHeight/Scale);Button->SetContent(Size);
        auto* SurfaceCard=WidgetTree->ConstructWidget<UBorder>();
        SurfaceCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale));
        SurfaceCard->SetPadding(FMargin(10/Scale,6/Scale));Size->SetContent(SurfaceCard);
        auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();SurfaceCard->SetContent(Row);
        auto* Caption=Text(Entry.Caption,14,false,false);
        auto* CaptionSlot=Row->AddChildToHorizontalBox(Caption);
        CaptionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CaptionSlot->SetVerticalAlignment(VAlign_Center);
        auto* Detail=Text(Entry.Detail,12,true);Detail->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        Row->AddChildToHorizontalBox(Detail)->SetVerticalAlignment(VAlign_Center);
        Cards.Add({Entry.Id,Entry.bComponent,Button,SurfaceCard});
        CardList->AddChildToVerticalBox(Button)->SetPadding(FMargin(0,0,0,CardGap/Scale));
    }
}

void UVoxelBuildWidget::RefreshSelection()
{
    const float Scale=ColdSteelUI::PixelScale(this);
    for(const FCard& Card:Cards)
    {
        auto* Widget=Card.Surface.Get();if(!Widget)continue;
        const bool bSelected=Card.bComponent?(!SelectedComponent.IsNone()&&SelectedComponent==Card.Id):(SelectedComponent.IsNone()&&SelectedMaterial==Card.Id);
        Widget->SetBrush(ColdSteelUI::RoundedBrush(bSelected?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,
            ColdSteelUI::CardRadius/Scale,bSelected?ColdSteelUI::Accent:ColdSteelUI::Border,bSelected?2/Scale:1/Scale));
    }
}

void UVoxelBuildWidget::RefreshCategory()
{
    const float Scale=ColdSteelUI::PixelScale(this);
    const FButtonStyle Normal=ColdSteelUI::ButtonStyle(Scale);
    const FButtonStyle Selected=ColdSteelUI::ButtonStyle(Scale).SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    if(MaterialTab)MaterialTab->SetStyle(bComponentCategory?Normal:Selected);
    if(ComponentTab)ComponentTab->SetStyle(bComponentCategory?Selected:Normal);
}

void UVoxelBuildWidget::RefreshLayout()
{
    if(!PanelSlot||!Surface)return;
    const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this);const float Scale=ColdSteelUI::PixelScale(this);
    if(View.Equals(LastViewport,.5)&&FMath::IsNearlyEqual(Scale,LastScale,.001f))return;
    LastViewport=View;LastScale=Scale;
    const float Pixels=FMath::Max(320.f,View.X);
    const float Width=FMath::Min(FMath::Clamp(Pixels*DrawerViewportFraction,DrawerMinWidth,DrawerMaxWidth),FMath::Max(240.f,Pixels-DrawerEdgeInset));
    DrawerWidth=Width/Scale;
    PanelSlot->SetOffsets(FMargin(0,DrawerEdgeInset/Scale,Width/Scale,DrawerEdgeInset/Scale));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    if(Blur)Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale));
    if(Scroll)Scroll->SetScrollbarThickness(FVector2D(6/Scale));
    for(const FLabel& Label:Labels)if(auto* TextBlock=Label.Widget.Get())
        TextBlock->SetFont(Label.Numeric?GunsmithUI::NumberFont(Label.Pixels/Scale,Label.Medium):GunsmithUI::TextFont(Label.Pixels/Scale,Label.Medium));
    Controls->SetText(FText::FromString(View.Y<650?
        TEXT("B 建造 ⇄ 面板 · 面板中再按 B 退出建造\n")
        TEXT("选中即回到建造：滚轮形状 · R 旋转 · F 吸附\n")
        TEXT("左键放 / 右键拆 · Esc 退一层 · Ctrl+Z 撤销"):
        TEXT("B 进入建造（面板选择）· 建造中 B 回面板 · 面板中再按 B 退出建造\n")
        TEXT("面板中 1-9 选择当前分类第 N 项 · 0 取消构件\n")
        TEXT("建造中 1 木材 2 石头 3 大理石 · 4-9 构件 · 滚轮切换形状\n")
        TEXT("R 旋转 · F 吸附 · 左键放置 / 右键拆除 · 中键取样 · Esc 退一层 · Ctrl+Z 撤销")));
    RefreshCategory();
}

void UVoxelBuildWidget::ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled)
{
    const FString SelectionText=FString::Printf(TEXT("%s\n%s\n%s"),*Headline,*Brush,bSnapEnabled?TEXT("体素吸附已开启 · F 自由放置"):TEXT("自由位置 · F 开启体素吸附"));
    const FString Signature=SelectionText+Message+(bValid?TEXT("1"):TEXT("0"));
    if(Signature!=LastState){LastState=Signature;Selection->SetText(FText::FromString(SelectionText));}
    if(Structure)Structure->SetText(FText::FromString(Message));
    if(Status)Status->SetColorAndOpacity(bValid?ColdSteelUI::Success:ColdSteelUI::Warning);
}

void UVoxelBuildWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    RefreshLayout();
    if(bCardsDirty){bCardsDirty=false;RebuildCards();bSelectionDirty=true;RefreshCategory();}
    if(bSelectionDirty){bSelectionDirty=false;RefreshSelection();}
    if(TooltipIndex!=INDEX_NONE)UpdateTooltipPlacement();
    DrawerProgress=FMath::FInterpConstantTo(DrawerProgress,bDrawerOpen?1.f:0.f,Delta,4.f);
    if(Surface)Surface->SetRenderTranslation(FVector2D((1.f-DrawerProgress)*DrawerWidth,0.f));
    if(!bDrawerOpen&&DrawerProgress<=KINDA_SMALL_NUMBER)SetVisibility(ESlateVisibility::Collapsed);
}
