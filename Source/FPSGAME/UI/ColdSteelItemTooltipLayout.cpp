#include "ColdSteelItemTooltip.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelDisclosureIndicator.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/ExpandableArea.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/NativeWidgetHost.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SLeafWidget.h"

namespace
{
class SItemTooltipCloseIcon final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SItemTooltipCloseIcon){} SLATE_ARGUMENT(float,PixelScale) SLATE_END_ARGS()
    void Construct(const FArguments& Args){IconScale=Args._PixelScale;}
    virtual FVector2D ComputeDesiredSize(float)const override{return FVector2D(24/IconScale,24/IconScale);}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool)const override
    {
        const FVector2f Center=FVector2f(Geometry.GetLocalSize())*.5f;
        const float Half=4.5f/IconScale;
        const FLinearColor Color=ColdSteelUI::ItemTooltipSecondary*Style.GetColorAndOpacityTint();
        FSlateDrawElement::MakeLines(Out,Layer,Geometry.ToPaintGeometry(),TArray<FVector2f>{Center+FVector2f(-Half,-Half),Center+FVector2f(Half,Half)},ESlateDrawEffect::None,Color,true,1.5f/IconScale);
        FSlateDrawElement::MakeLines(Out,Layer,Geometry.ToPaintGeometry(),TArray<FVector2f>{Center+FVector2f(-Half,Half),Center+FVector2f(Half,-Half)},ESlateDrawEffect::None,Color,true,1.5f/IconScale);
        return Layer;
    }
private:
    float IconScale=1;
};
class SItemTooltipDashedRule final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SItemTooltipDashedRule){} SLATE_ARGUMENT(float,PixelScale) SLATE_END_ARGS()
    void Construct(const FArguments& Args){RuleScale=Args._PixelScale;}
    virtual FVector2D ComputeDesiredSize(float)const override{return FVector2D(1,1/RuleScale);}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool)const override
    {
        const float Width=Geometry.GetLocalSize().X,Dash=5/RuleScale,Pitch=9/RuleScale;
        const auto Color=ColdSteelUI::ItemTooltipRule*Style.GetColorAndOpacityTint();
        for(float X=0;X<Width;X+=Pitch)
            FSlateDrawElement::MakeBox(Out,Layer,Geometry.ToPaintGeometry(FVector2D(FMath::Min(Dash,Width-X),1/RuleScale),FSlateLayoutTransform(FVector2D(X,0))),FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")),ESlateDrawEffect::None,Color);
        return Layer;
    }
private:
    float RuleScale=1;
};
bool TooltipNumeric(const FString& Value)
{
    FString Remainder=Value;
    for(const TCHAR* Unit:{TEXT("m/s"),TEXT("ms"),TEXT("cm"),TEXT("mm"),TEXT("s"),TEXT("m"),TEXT("发"),TEXT("秒"),TEXT("分"),TEXT("米"),TEXT("次"),TEXT("个"),TEXT("点"),TEXT("级")})Remainder.ReplaceInline(Unit,TEXT(""),ESearchCase::CaseSensitive);
    bool HasNumber=false;
    for(const TCHAR Character:Remainder)
    {
        if(FChar::IsDigit(Character)){HasNumber=true;continue;}
        if(Character==TEXT('∞')){HasNumber=true;continue;}
        if(!FCString::Strchr(TEXT(" +-−×/.,%()（）→:°"),Character))return false;
    }
    return HasNumber;
}
FSlateChildSize TooltipFill(float Weight=1.f)
{FSlateChildSize Result(ESlateSizeRule::Fill);Result.Value=Weight;return Result;}
FString TooltipLabel(const FString& Label)
{return Label==TEXT("当前伤害")?TEXT("伤害"):Label;}
/**
 * 「特殊性质」段按类别上色。Icon 是目录里的语义标签，未知标签落到中性色，
 * 这样将来新增武器类型不需要改这里。
 */
const FLinearColor& TraitColor(const FString& Icon)
{
    if(Icon==TEXT("special")) return ColdSteelUI::ItemTraitSpecial;
    if(Icon==TEXT("magic")) return ColdSteelUI::ItemTraitMagic;
    if(Icon==TEXT("mechanic")) return ColdSteelUI::ItemTraitMechanic;
    if(Icon==TEXT("drawback")) return ColdSteelUI::ItemTraitDrawback;
    return ColdSteelUI::ItemTraitNeutral;
}
}

float UColdSteelItemTooltip::InnerWidth()const{return FMath::Max(1.f,(WidthPixels-42)/Scale);}
UTextBlock* UColdSteelItemTooltip::Text(const FString& Value,float Pixels,const FLinearColor& Color,bool Numeric)
{
    auto* Result=WidgetTree->ConstructWidget<UTextBlock>();Result->SetText(FText::FromString(Value));
    Result->SetFont(Numeric?ColdSteelUI::NumberFont(Pixels*.75f/Scale,Pixels>=20):ColdSteelUI::TextFont(Pixels*.75f/Scale,Pixels>=16));
    Result->SetColorAndOpacity(Color);Result->SetWrapTextAt(InnerWidth());
    Result->SetVisibility(ESlateVisibility::HitTestInvisible);return Result;
}
const FColdSteelTooltipRow& UColdSteelItemTooltip::RowData(const FRowView& View)const
{
    if(View.Card==-1)return Presentation.Summary[View.Row];
    if(View.Card==-2)return Presentation.Comparison[View.Row];
    return Presentation.Cards[View.Card].Rows[View.Row];
}
void UColdSteelItemTooltip::AddRule(UVerticalBox* Column,float Top,float Bottom,bool Dashed)
{
    auto* Height=WidgetTree->ConstructWidget<USizeBox>();Height->SetHeightOverride(1/Scale);
    if(Dashed)
    {
        auto* Host=WidgetTree->ConstructWidget<UNativeWidgetHost>();Host->SetVisibility(ESlateVisibility::HitTestInvisible);
        Host->SetContent(SNew(SItemTooltipDashedRule).PixelScale(Scale));Height->SetContent(Host);
    }
    else
    {
        auto* Rule=WidgetTree->ConstructWidget<UBorder>();Rule->SetPadding(FMargin(0));Rule->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ItemTooltipRule,0,FLinearColor::Transparent,0));Height->SetContent(Rule);
    }
    Column->AddChildToVerticalBox(Height)->SetPadding(FMargin(0,Top/Scale,0,Bottom/Scale));
}
void UColdSteelItemTooltip::AddRow(UVerticalBox* Column,const FColdSteelTooltipRow& Row,int32 CardIndex,int32 RowIndex,bool Compact)
{
    if(Row.bSection)
    {
        auto* Heading=Text(Row.Label,14,ColdSteelUI::ItemTooltipText);Heading->SetFont(ColdSteelUI::TextFont(14*.75f/Scale,true));
        Column->AddChildToVerticalBox(Heading)->SetPadding(FMargin(0,12/Scale,0,4/Scale));
        if(Row.bDashedAfter)AddRule(Column,9,5,true);return;
    }
    if(Row.bStacked)
    {
        auto* Group=WidgetTree->ConstructWidget<UVerticalBox>();Column->AddChildToVerticalBox(Group)->SetPadding(FMargin(0,6/Scale,0,4/Scale));
        auto* Label=Text(Row.Label,12,ColdSteelUI::ItemTooltipSecondary);Group->AddChildToVerticalBox(Label);
        auto* Value=Text(Row.Value,14,ColdSteelUI::ItemTooltipText);Value->SetLineHeightPercentage(1.15f);Value->SetJustification(ETextJustify::Left);
        Group->AddChildToVerticalBox(Value)->SetPadding(FMargin(0,3/Scale,0,0));RowViews.Add({CardIndex,RowIndex,Row.Tone,Label,Value});
        if(Row.bDashedAfter)AddRule(Column,9,5,true);return;
    }
    auto* Line=WidgetTree->ConstructWidget<UHorizontalBox>();
    Column->AddChildToVerticalBox(Line)->SetPadding(FMargin(0,5/Scale));
    const bool Paired=!Row.Label.IsEmpty()||Row.bContinuation;
    UTextBlock* Label=nullptr;
    if(Paired)
    {
        Label=Text(TooltipLabel(Row.Label),14,ColdSteelUI::ItemTooltipSecondary);Label->SetWrapTextAt(FMath::Max(1.f,InnerWidth()*.4f-12/Scale));
        auto* LabelSlot=Line->AddChildToHorizontalBox(Label);LabelSlot->SetSize(TooltipFill(.4f));LabelSlot->SetPadding(FMargin(0,0,12/Scale,0));
    }
    const FString& Display=Compact&&!Row.CompactValue.IsEmpty()?Row.CompactValue:Row.Value;
    auto* Value=Text(Display,14,Row.Tone>0?ColdSteelUI::ItemTooltipPositive:Row.Tone<0?ColdSteelUI::ItemTooltipNegative:ColdSteelUI::ItemTooltipText,TooltipNumeric(Display));
    Value->SetWrapTextAt(InnerWidth()*(Paired?.6f:1.f));Value->SetJustification(Paired?ETextJustify::Right:ETextJustify::Left);
    Line->AddChildToHorizontalBox(Value)->SetSize(TooltipFill(Paired?.6f:1.f));
    RowViews.Add({CardIndex,RowIndex,Row.Tone,Label,Value,14.f,Compact,false});
    if(Row.bDashedAfter)AddRule(Column,9,5,true);
}
void UColdSteelItemTooltip::AddCoreGrid(UVerticalBox* Body)
{
    Body->AddChildToVerticalBox(Text(TEXT("核心属性"),16,ColdSteelUI::ItemTooltipText))->SetPadding(FMargin(0,0,0,6/Scale));
    const int32 Columns=WidthPixels>=340?2:1;
    const float CellWidth=(InnerWidth()-(Columns-1)*16/Scale)/Columns;
    auto* Grid=WidgetTree->ConstructWidget<UUniformGridPanel>();Body->AddChildToVerticalBox(Grid);
    for(int32 Index=0;Index<Presentation.Summary.Num();++Index)
    {
        const auto& Row=Presentation.Summary[Index];const int32 X=Index%Columns,Y=Index/Columns;
        auto* Width=WidgetTree->ConstructWidget<USizeBox>();Width->SetWidthOverride(CellWidth);
        auto* Cell=WidgetTree->ConstructWidget<UVerticalBox>();Width->SetContent(Cell);
        auto* Label=Text(TooltipLabel(Row.Label),14,ColdSteelUI::ItemTooltipSecondary);Label->SetWrapTextAt(CellWidth);Cell->AddChildToVerticalBox(Label);
        const float Pixels=TooltipNumeric(Row.Value)?24.f:16.f;
        auto* Value=Text(Row.Value,Pixels,Row.Tone>0?ColdSteelUI::ItemTooltipPositive:Row.Tone<0?ColdSteelUI::ItemTooltipNegative:ColdSteelUI::ItemTooltipText,TooltipNumeric(Row.Value));
        Value->SetWrapTextAt(CellWidth);Cell->AddChildToVerticalBox(Value)->SetPadding(FMargin(0,3/Scale,0,0));
        AddRule(Cell,7,0);
        auto* Spaced=WidgetTree->ConstructWidget<UBorder>();Spaced->SetPadding(FMargin(Columns>1&&X>0?8/Scale:0,5/Scale,Columns>1&&X==0?8/Scale:0,5/Scale));Spaced->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0));
        Spaced->SetContent(Width);auto* GridSlot=Grid->AddChildToUniformGrid(Spaced,Y,X);GridSlot->SetHorizontalAlignment(HAlign_Fill);GridSlot->SetVerticalAlignment(VAlign_Top);
        RowViews.Add({-1,Index,Row.Tone,Label,Value,Pixels,false,true});
    }
}
UExpandableArea* UColdSteelItemTooltip::AddSection(UVerticalBox* Column,const FString& Key,const FString& Title,bool Open)
{
    auto* Area=WidgetTree->ConstructWidget<UExpandableArea>();
    auto SectionStyle=Area->GetStyle();SectionStyle.CollapsedImage.DrawAs=ESlateBrushDrawType::NoDrawType;SectionStyle.CollapsedImage.ImageSize=FVector2D::ZeroVector;SectionStyle.ExpandedImage=SectionStyle.CollapsedImage;Area->SetStyle(SectionStyle);
    Area->SetBorderBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0));
    Area->SetHeaderPadding(FMargin(0,7/Scale));Area->SetAreaPadding(FMargin(0,0,0,6/Scale));
    const bool IsOpen=Expanded.Contains(Key)?Expanded[Key]:Open;
    const bool Intro=bStartDisclosureIntro&&!IsOpen;if(Intro)bStartDisclosureIntro=false;
    auto* HeadingRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    auto* Arrow=WidgetTree->ConstructWidget<UColdSteelDisclosureIndicator>();Arrow->Configure(Scale,IsOpen,Area,Intro);Disclosures.Add(Key,Arrow);
    auto* ArrowSlot=HeadingRow->AddChildToHorizontalBox(Arrow);ArrowSlot->SetPadding(FMargin(0,0,6/Scale,0));ArrowSlot->SetVerticalAlignment(VAlign_Center);
    auto* Heading=Text(Title,14,ColdSteelUI::ItemTooltipText);Heading->SetWrapTextAt(FMath::Max(1.f,InnerWidth()-40/Scale));
    auto* HeadingSlot=HeadingRow->AddChildToHorizontalBox(Heading);HeadingSlot->SetSize(TooltipFill());HeadingSlot->SetVerticalAlignment(VAlign_Center);
    Area->SetContentForSlot(TEXT("Header"),HeadingRow);
    Area->SetContentForSlot(TEXT("Body"),WidgetTree->ConstructWidget<UVerticalBox>());
    Area->SetIsExpanded(IsOpen);
    Area->OnExpansionChanged.AddDynamic(this,&ThisClass::ExpansionChanged);Sections.Add(Key,Area);
    Column->AddChildToVerticalBox(Area);AddRule(Column,0,0);return Area;
}
void UColdSteelItemTooltip::AddDetails(UVerticalBox* Body)
{
    if(!Presentation.ComparisonTitle.IsEmpty())
    {
        AddRule(Body,12,12);Body->AddChildToVerticalBox(Text(TEXT("装备对比"),16,ColdSteelUI::ItemTooltipText));
        ComparisonText=Text(Presentation.ComparisonTitle,12,ColdSteelUI::ItemTooltipSecondary);Body->AddChildToVerticalBox(ComparisonText)->SetPadding(FMargin(0,4/Scale,0,6/Scale));
        for(int32 Index=0;Index<FMath::Min(3,Presentation.Comparison.Num());++Index)
        {AddRow(Body,Presentation.Comparison[Index],-2,Index,true);AddRule(Body,2,2);}
    }
    AddRule(Body,12,10);Body->AddChildToVerticalBox(Text(TEXT("进阶详情"),16,ColdSteelUI::ItemTooltipText))->SetPadding(FMargin(0,0,0,6/Scale));
    if(Presentation.Cards.Num()>1)
    {
        auto* Area=AddSection(Body,TEXT("extra:processing"),TEXT("改造与附魔"),false);auto* Rows=Cast<UVerticalBox>(Area->GetContentForSlot(TEXT("Body")));
        for(int32 Index=0;Index+1<Presentation.Cards.Num();++Index)
        {
            const auto& Card=Presentation.Cards[Index];
            if(Index>0)AddRule(Rows,12,10);
            Rows->AddChildToVerticalBox(Text(Card.Title,16,ColdSteelUI::ItemTooltipText))->SetPadding(FMargin(0,10/Scale,0,4/Scale));
            for(int32 Row=0;Row<Card.Rows.Num();++Row)AddRow(Rows,Card.Rows[Row],Index,Row);
        }
    }
    if(!Presentation.Cards.IsEmpty()||!Presentation.Comparison.IsEmpty())
    {
        auto* Area=AddSection(Body,TEXT("main:details"),TEXT("详细参数"),false);auto* Rows=Cast<UVerticalBox>(Area->GetContentForSlot(TEXT("Body")));
        if(!Presentation.Summary.IsEmpty())
        {
            AddRow(Rows,{TEXT("核心参数"),TEXT(""),0,true},-1,0);
            for(int32 Index=0;Index<Presentation.Summary.Num();++Index)AddRow(Rows,Presentation.Summary[Index],-1,Index);
            AddRule(Rows,8,2);
        }
        if(!Presentation.Cards.IsEmpty())
        {
            const int32 CardIndex=Presentation.Cards.Num()-1;const auto& Main=Presentation.Cards[CardIndex];
            FString PendingHeading;
            for(int32 Index=0;Index<Main.Rows.Num();++Index)
            {
                const auto& Row=Main.Rows[Index];if(Row.bSection){PendingHeading=Row.Label;continue;}
                if(Presentation.Summary.ContainsByPredicate([&](const auto& Core){return Core.Label==Row.Label&&Core.Value==Row.Value;}))continue;
                if(!PendingHeading.IsEmpty()){AddRow(Rows,{PendingHeading,TEXT(""),0,true},CardIndex,Index);PendingHeading.Empty();}
                AddRow(Rows,Row,CardIndex,Index);
            }
        }
        if(!Presentation.Comparison.IsEmpty())
        {
            AddRule(Rows,12,8);Rows->AddChildToVerticalBox(Text(TEXT("完整装备对比"),14,ColdSteelUI::ItemTooltipText));
            Rows->AddChildToVerticalBox(Text(TEXT("差值（已装备 → 当前查看）"),12,ColdSteelUI::ItemTooltipSecondary));
            for(int32 Index=0;Index<Presentation.Comparison.Num();++Index)AddRow(Rows,Presentation.Comparison[Index],-2,Index);
        }
    }
    if(!Presentation.Description.IsEmpty())
    {
        auto* Area=AddSection(Body,TEXT("description"),TEXT("物品说明"),true);
        auto* Description=Text(Presentation.Description,14,ColdSteelUI::ItemTooltipSecondary);Description->SetWrapTextAt(FMath::Max(1.f,InnerWidth()-30/Scale));
        Cast<UVerticalBox>(Area->GetContentForSlot(TEXT("Body")))->AddChildToVerticalBox(Description)->SetPadding(FMargin(30/Scale,0,0,0));
    }
    if(!Presentation.Traits.IsEmpty())
    {
        // Placed directly under 物品说明 so the mechanical character of a weapon is
        // read straight after its background text. Only weapons carry traits, so
        // other categories simply never render this section.
        auto* Area=AddSection(Body,TEXT("traits"),TEXT("特殊性质"),true);
        auto* Rows=Cast<UVerticalBox>(Area->GetContentForSlot(TEXT("Body")));
        for(int32 Index=0;Index<Presentation.Traits.Num();++Index)
        {
            const auto& Trait=Presentation.Traits[Index];
            auto* Line=Text(Trait.Text,14,TraitColor(Trait.Icon));
            Line->SetWrapTextAt(FMath::Max(1.f,InnerWidth()-30/Scale));
            Rows->AddChildToVerticalBox(Line)->SetPadding(FMargin(30/Scale,Index>0?6/Scale:0,0,0));
        }
    }
}
void UColdSteelItemTooltip::BuildCards()
{
    const float OldScroll=Vertical?Vertical->GetScrollOffset():0;const bool HadFocus=HasFocusedDescendants();
    RootColumn->ClearChildren();RowViews.Reset();Sections.Reset();Disclosures.Reset();ComparisonText=nullptr;
    Shadow->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(0,35),10/Scale,FLinearColor::Transparent,0));Shadow->SetRenderTranslation(FVector2D(2/Scale,4/Scale));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ItemTooltipSurface,8/Scale,ColdSteelUI::ItemTooltipBorder,1/Scale));Surface->SetPadding(FMargin(0));
    Header=WidgetTree->ConstructWidget<UVerticalBox>();RootColumn->AddChildToVerticalBox(Header);
    auto* HeaderPanel=WidgetTree->ConstructWidget<UBorder>();HeaderPanel->SetPadding(FMargin(16/Scale));HeaderPanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ItemTooltipHeader,8/Scale,FLinearColor::Transparent,0));Header->AddChildToVerticalBox(HeaderPanel);
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderPanel->SetContent(Heading);
    const float IconWidth=Presentation.bWideIcon?FMath::Min(bPinned?200.f:128.f,WidthPixels*.4f):64.f;
    const float IconHeight=Presentation.bWideIcon?(bPinned?88.f:64.f):64.f;
    auto* IconFrame=WidgetTree->ConstructWidget<USizeBox>();IconFrame->SetWidthOverride(IconWidth/Scale);IconFrame->SetHeightOverride(IconHeight/Scale);
    auto* PictureSlot=Heading->AddChildToHorizontalBox(IconFrame);PictureSlot->SetPadding(FMargin(0,0,16/Scale,0));PictureSlot->SetVerticalAlignment(VAlign_Center);
    auto* IconLayers=WidgetTree->ConstructWidget<UOverlay>();IconFrame->SetContent(IconLayers);
    auto* FitIcon=WidgetTree->ConstructWidget<UScaleBox>();FitIcon->SetStretch(EStretch::ScaleToFit);
    auto* FitSlot=IconLayers->AddChildToOverlay(FitIcon);FitSlot->SetHorizontalAlignment(HAlign_Fill);FitSlot->SetVerticalAlignment(VAlign_Fill);
    Icon=WidgetTree->ConstructWidget<UImage>();FitIcon->SetContent(Icon);
    MissingIcon=Text(TEXT("?"),24,ColdSteelUI::ItemTooltipSecondary);auto* MissingSlot=IconLayers->AddChildToOverlay(MissingIcon);MissingSlot->SetHorizontalAlignment(HAlign_Center);MissingSlot->SetVerticalAlignment(VAlign_Center);
    auto* Identity=WidgetTree->ConstructWidget<UVerticalBox>();auto* IdentitySlot=Heading->AddChildToHorizontalBox(Identity);IdentitySlot->SetSize(TooltipFill());IdentitySlot->SetVerticalAlignment(VAlign_Center);
    const float IdentityWidth=FMath::Max(1.f,(WidthPixels-32-IconWidth-16-(bPinned?32:0))/Scale);
    TitleText=Text(TEXT(""),20,ColdSteelUI::ItemTooltipText);TitleText->SetWrapTextAt(IdentityWidth);Identity->AddChildToVerticalBox(TitleText);
    MetaText=Text(TEXT(""),12,ColdSteelUI::ItemTooltipSecondary);MetaText->SetWrapTextAt(IdentityWidth);Identity->AddChildToVerticalBox(MetaText)->SetPadding(FMargin(0,5/Scale,0,0));
    LocationText=Text(TEXT(""),12,ColdSteelUI::ItemTooltipSecondary);LocationText->SetWrapTextAt(IdentityWidth);Identity->AddChildToVerticalBox(LocationText)->SetPadding(FMargin(0,5/Scale,0,0));
    Close=WidgetTree->ConstructWidget<UButton>();FButtonStyle CloseStyle=ColdSteelUI::ButtonStyle(Scale);
    CloseStyle.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,4/Scale,FLinearColor::Transparent,0));
    CloseStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ItemTooltipRule,4/Scale,FLinearColor::Transparent,0));
    CloseStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(204),4/Scale,FLinearColor::Transparent,0));
    CloseStyle.SetNormalPadding(FMargin(0));CloseStyle.SetPressedPadding(FMargin(0));Close->SetStyle(CloseStyle);
    auto* CloseIcon=WidgetTree->ConstructWidget<UNativeWidgetHost>();CloseIcon->SetVisibility(ESlateVisibility::HitTestInvisible);CloseIcon->SetContent(SNew(SItemTooltipCloseIcon).PixelScale(Scale));Close->SetContent(CloseIcon);
    auto* CloseContent=CastChecked<UButtonSlot>(CloseIcon->Slot);CloseContent->SetPadding(FMargin(0));CloseContent->SetHorizontalAlignment(HAlign_Fill);CloseContent->SetVerticalAlignment(VAlign_Fill);
    Close->OnClicked.AddDynamic(this,&ThisClass::CloseClicked);Close->SetToolTipText(FText::FromString(TEXT("关闭详情（Esc）")));
    auto* CloseFrame=WidgetTree->ConstructWidget<USizeBox>();CloseFrame->SetWidthOverride(24/Scale);CloseFrame->SetHeightOverride(24/Scale);CloseFrame->SetContent(Close);CloseFrame->SetVisibility(bPinned?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    auto* CloseSlot=Heading->AddChildToHorizontalBox(CloseFrame);CloseSlot->SetPadding(FMargin(8/Scale,0,0,0));CloseSlot->SetVerticalAlignment(VAlign_Top);
    BodyHeight=WidgetTree->ConstructWidget<USizeBox>();RootColumn->AddChildToVerticalBox(BodyHeight)->SetPadding(FMargin(16/Scale,12/Scale,16/Scale,0));
    Vertical=WidgetTree->ConstructWidget<UScrollBox>();Vertical->SetAllowOverscroll(false);Vertical->SetScrollbarThickness(FVector2D(6/Scale,6/Scale));Vertical->SetConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible);BodyHeight->SetContent(Vertical);
    Cards=WidgetTree->ConstructWidget<UHorizontalBox>();Vertical->AddChild(Cards);auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Cards->AddChildToHorizontalBox(Body)->SetSize(TooltipFill());
    AddCoreGrid(Body);
    ScopeText=Text(TEXT(""),12,ColdSteelUI::ItemTooltipSecondary);Body->AddChildToVerticalBox(ScopeText)->SetPadding(FMargin(0,7/Scale,0,0));
    if(bPinned)AddDetails(Body);
    FooterFrame=WidgetTree->ConstructWidget<UBorder>();FooterFrame->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0));FooterFrame->SetPadding(FMargin(16/Scale,10/Scale,16/Scale,12/Scale));RootColumn->AddChildToVerticalBox(FooterFrame);
    auto* Footer=WidgetTree->ConstructWidget<UVerticalBox>();FooterFrame->SetContent(Footer);AddRule(Footer,0,9);
    FooterText=Text(bPinned?TEXT("已固定 · 滚轮浏览 · Esc 关闭"):TEXT("点击物品或按 F1 查看完整详情"),12,ColdSteelUI::ItemTooltipSecondary);FooterText->SetJustification(ETextJustify::Center);Footer->AddChildToVerticalBox(FooterText);
    Vertical->SetScrollOffset(OldScroll);if(HadFocus)SetKeyboardFocus();
}
void UColdSteelItemTooltip::UpdateRows()
{
    auto Set=[](UTextBlock* Block,const FString& Value){if(Block&&Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));};
    Set(TitleText,Presentation.Name);
    FString Meta=Presentation.Type+TEXT(" · ")+ColdSteelUI::RarityLabel(Presentation.Rarity);
    if(Presentation.Level>0)Meta+=FString::Printf(TEXT(" · Lv.%d"),Presentation.Level);
    if(!Presentation.Enhancement.IsEmpty())Meta+=TEXT(" · ")+Presentation.Enhancement;
    Set(MetaText,Meta);Set(LocationText,Presentation.Location);Set(ScopeText,Presentation.ValueScope);Set(ComparisonText,Presentation.ComparisonTitle);
    ScopeText->SetVisibility(Presentation.ValueScope.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    for(auto& View:RowViews)
    {
        const auto& Row=RowData(View);Set(View.Label.Get(),TooltipLabel(Row.Label));
        if(auto* Value=View.Value.Get())
        {
            const FString& Display=View.bCompact&&!Row.CompactValue.IsEmpty()?Row.CompactValue:Row.Value;
            if(Value->GetText().ToString()!=Display)
            {
                Value->SetText(FText::FromString(Display));const bool Numeric=TooltipNumeric(Display);
                if(View.bMetric)View.Pixels=Numeric?24.f:16.f;
                Value->SetFont(Numeric?ColdSteelUI::NumberFont(View.Pixels*.75f/Scale,View.Pixels>=20):ColdSteelUI::TextFont(View.Pixels*.75f/Scale,View.Pixels>=16));
            }
            if(View.Tone!=Row.Tone){View.Tone=Row.Tone;Value->SetColorAndOpacity(Row.Tone>0?ColdSteelUI::ItemTooltipPositive:Row.Tone<0?ColdSteelUI::ItemTooltipNegative:ColdSteelUI::ItemTooltipText);}
        }
    }
}
