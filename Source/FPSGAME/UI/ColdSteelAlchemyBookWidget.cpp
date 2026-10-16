#include "ColdSteelAlchemyBookWidget.h"
#include "AlchemyManualLayout.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemTooltipData.h"
#include "../Building/AlchemyManualArtwork.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/ScaleBox.h"
#include "Components/Spacer.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Misc/Paths.h"

namespace {
const FLinearColor FolioInk=AlchemyManualLayout::Ink;
const FLinearColor FolioMuted=AlchemyManualLayout::Muted;
const FLinearColor FolioGold=AlchemyManualLayout::Gold;
FSlateFontInfo FolioFont(float Pixels,bool Semibold=false)
{
    return AlchemyManualLayout::Font(Pixels,Semibold);
}
UTextBlock* FolioLabel(UWidgetTree* Tree,const FString& Value,float Pixels,bool Strong=false,bool Wrap=false,FLinearColor Color=FolioInk)
{
    auto* T=Tree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Value));T->SetFont(FolioFont(Pixels,Strong));
    T->SetColorAndOpacity(Color);T->SetAutoWrapText(false);if(Wrap)T->SetWrapTextAt(AlchemyManualLayout::ContentWidth);T->SetLineHeightPercentage(1.24f);return T;
}
void FolioLine(UWidgetTree* Tree,UVerticalBox* Stack,const FString& Value,float Pixels,bool Strong=false,bool Wrap=false,FLinearColor Color=FolioInk,float After=12)
{Stack->AddChildToVerticalBox(FolioLabel(Tree,Value,Pixels,Strong,Wrap,Color))->SetPadding(FMargin(0,0,0,After));}
void FolioRule(UWidgetTree* Tree,UVerticalBox* Stack,float After=22)
{
    auto* Rule=Tree->ConstructWidget<UBorder>();Rule->SetBrushColor(FLinearColor::FromSRGBColor(FColor(176,155,117)));Rule->SetPadding(FMargin(0,.7f));
    Stack->AddChildToVerticalBox(Rule)->SetPadding(FMargin(0,0,0,After));
}
USizeBox* FolioArt(UWidgetTree* Tree,const FString& Definition,float Width,float Height)
{
    auto* Art=Tree->ConstructWidget<UImage>();Art->SetBrushFromTexture(Cast<UTexture2D>(AlchemyManualArtwork::Texture(TEXT("_")+Definition).ResolveObject()),true);
    auto* Fit=Tree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);Fit->SetContent(Art);
    auto* Box=Tree->ConstructWidget<USizeBox>();Box->SetWidthOverride(Width);Box->SetHeightOverride(Height);Box->SetContent(Fit);return Box;
}
void FolioHeading(UWidgetTree* Tree,UVerticalBox* Stack,const FString& Eyebrow,const FString& Title,float Height=AlchemyManualLayout::HeadingHeight)
{
    auto* Size=Tree->ConstructWidget<USizeBox>();Size->SetHeightOverride(Height);Stack->AddChildToVerticalBox(Size);
    auto* Header=Tree->ConstructWidget<UVerticalBox>();Size->SetContent(Header);
    FolioLine(Tree,Header,Eyebrow,22,false,false,FolioMuted,8);
    FolioLine(Tree,Header,Title,48,true,false,FolioInk,16);FolioRule(Tree,Header,20);
}
void FolioSection(UWidgetTree* Tree,UVerticalBox* Stack,const FString& Title)
{FolioLine(Tree,Stack,Title,28,true,false,FolioGold,14);}
void FolioPair(UWidgetTree* Tree,UVerticalBox* Stack,const FString& Label,const FString& Value)
{
    auto* Row=Tree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Row)->SetPadding(FMargin(0,0,0,10));
    Row->AddChildToHorizontalBox(FolioLabel(Tree,Label,30))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Row->AddChildToHorizontalBox(FolioLabel(Tree,Value,38,true,false,FolioGold));
}
void FolioFooter(UWidgetTree* Tree,UVerticalBox* Stack,int32 Page,int32 Total=0)
{
    auto* Space=Tree->ConstructWidget<USpacer>();Stack->AddChildToVerticalBox(Space)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    FolioRule(Tree,Stack,14);auto* Row=Tree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Row);
    Row->AddChildToHorizontalBox(FolioLabel(Tree,TEXT("炼金手记"),21,false,false,FolioMuted))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    const FString Number=Total>0?FString::Printf(TEXT("%02d / %02d"),Page,Total):FString::Printf(TEXT("%02d"),Page);
    Row->AddChildToHorizontalBox(FolioLabel(Tree,Number,27,true,false,FolioGold));
}
void FolioSteps(UWidgetTree* Tree,UVerticalBox* Stack,const FAlchemyRecipe& R,const FAlchemyManualLeaf& Leaf)
{
    for(const auto& Fragment:Leaf.Steps)
    {
        const auto& Step=R.Steps[Fragment.Step];auto* Row=Tree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Row)->SetPadding(FMargin(0,0,0,26));
        auto* Number=Tree->ConstructWidget<USizeBox>();Number->SetWidthOverride(72);Number->SetContent(FolioLabel(Tree,Fragment.bContinuation?TEXT("续"):FString::Printf(TEXT("%02d"),Fragment.Step+1),38,true,false,FolioGold));Row->AddChildToHorizontalBox(Number);
        auto* Body=Tree->ConstructWidget<UVerticalBox>();Row->AddChildToHorizontalBox(Body)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        FolioLine(Tree,Body,AlchemyManualLayout::Action(Step.Action),30,true,false,FolioInk,8);
        auto* Description=FolioLabel(Tree,Fragment.Text,34,false,true);Description->SetWrapTextAt(AlchemyManualLayout::StepWidth);
        Body->AddChildToVerticalBox(Description)->SetPadding(FMargin(0,0,0,12));
        if(Fragment.bParameters)for(const auto& Parameter:AlchemyManualLayout::Parameters(R,Step))
        {
            auto* Size=Tree->ConstructWidget<USizeBox>();Size->SetHeightOverride(52);Body->AddChildToVerticalBox(Size);
            auto* Values=Tree->ConstructWidget<UHorizontalBox>();Size->SetContent(Values);
            auto* Label=Values->AddChildToHorizontalBox(FolioLabel(Tree,Parameter.Label,28,false,false,Parameter.Color));Label->SetSize(FSlateChildSize(ESlateSizeRule::Fill));Label->SetVerticalAlignment(VAlign_Center);
            Values->AddChildToHorizontalBox(FolioLabel(Tree,Parameter.Value,38,true,false,Parameter.Color))->SetVerticalAlignment(VAlign_Center);
        }
    }
}
void FolioEndNotes(UWidgetTree* Tree,UVerticalBox* Stack,const FAlchemyRecipe& R)
{
    FolioSection(Tree,Stack,TEXT("装瓶与收存"));
    FolioLine(Tree,Stack,FString::Printf(TEXT("装瓶温度 ≤ %.0f °C"),R.BottleHeat),38,true,false,AlchemyManualLayout::Heat,12);
    FolioLine(Tree,Stack,TEXT("未充分融合便装瓶会失败；工艺影响额外产量。离台会封存本炉并关闭火力。"),30,false,true,FolioMuted,24);
}
void FolioFlow(UWidgetTree* Tree,UVerticalBox* Stack,const FAlchemyRecipe& R,const FAlchemyManualLeaf& Leaf)
{
    FolioHeading(Tree,Stack,R.Name,Leaf.bFinish?TEXT("收存与成品"):Leaf.Steps.IsEmpty()?TEXT("收存要点"):(R.FreeBrewing?TEXT("参考工序"):TEXT("炼制工序")));
    FolioSteps(Tree,Stack,R,Leaf);
    if(Leaf.bFinish)
    {
        auto* Art=Stack->AddChildToVerticalBox(FolioArt(Tree,R.Output,280,280));Art->SetHorizontalAlignment(HAlign_Center);Art->SetPadding(FMargin(0,16,0,34));
        FolioSection(Tree,Stack,TEXT("成品记录"));FolioPair(Tree,Stack,TEXT("基础产出"),FString::Printf(TEXT("%d 瓶"),R.BaseCount));FolioPair(Tree,Stack,TEXT("精制额外"),FString::Printf(TEXT("%d 瓶"),R.BonusCount));
        auto* Gap=Tree->ConstructWidget<USpacer>();Gap->SetSize(FVector2D(1,28));Stack->AddChildToVerticalBox(Gap);
    }
    if(Leaf.bNotes)FolioEndNotes(Tree,Stack,R);
}
}
void UColdSteelAlchemyBookWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Root=WidgetTree->ConstructWidget<UOverlay>();WidgetTree->RootWidget=Root;
    auto* Background=WidgetTree->ConstructWidget<UImage>();Background->SetBrushFromTexture(Cast<UTexture2D>(AlchemyManualArtwork::Texture(TEXT("Paper")).ResolveObject()),true);
    auto* PaperSlot=Root->AddChildToOverlay(Background);PaperSlot->SetHorizontalAlignment(HAlign_Fill);PaperSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Columns=WidgetTree->ConstructWidget<UHorizontalBox>();auto* ColumnsSlot=Root->AddChildToOverlay(Columns);
    ColumnsSlot->SetHorizontalAlignment(HAlign_Fill);ColumnsSlot->SetVerticalAlignment(VAlign_Fill);
    LeftPage=WidgetTree->ConstructWidget<UVerticalBox>();RightPage=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* L=Columns->AddChildToHorizontalBox(LeftPage);L->SetSize(FSlateChildSize(ESlateSizeRule::Fill));L->SetPadding(FMargin(82,82,112,68));
    auto* R=Columns->AddChildToHorizontalBox(RightPage);R->SetSize(FSlateChildSize(ESlateSizeRule::Fill));R->SetPadding(FMargin(112,82,82,68));
}
void UColdSteelAlchemyBookWidget::Configure(const FAlchemyRecipe& R,int32 Spread,int32 FirstFolio,int32 FolioCount)
{
    if(!LeftPage||!RightPage)return;const int32 P=FMath::Clamp(Spread,0,Pages(R)-1);
    const auto& Layout=AlchemyManualLayout::Leaves(R);
    LeftPage->ClearChildren();RightPage->ClearChildren();auto* Tree=WidgetTree.Get();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(P==0)
    {
        FolioHeading(Tree,LeftPage,TEXT("炼金手记  /  配方"),R.Name);
        auto* Hero=Tree->ConstructWidget<UHorizontalBox>();LeftPage->AddChildToVerticalBox(Hero)->SetPadding(FMargin(0,0,0,26));
        Hero->AddChildToHorizontalBox(FolioArt(Tree,R.Output,218,216))->SetPadding(FMargin(0,0,28,0));
        auto* Effects=Tree->ConstructWidget<UVerticalBox>();auto* EffectsSlot=Hero->AddChildToHorizontalBox(Effects);EffectsSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));EffectsSlot->SetVerticalAlignment(VAlign_Center);
        FolioSection(Tree,Effects,TEXT("成品效用"));const auto Info=BuildColdSteelItemTooltip(Model->CreateItem(R.Output),Model,nullptr);
        for(const auto& Card:Info.Cards)for(const auto& Row:Card.Rows)if(Row.Label.StartsWith(TEXT("恢复")))
        {
            auto* Effect=FolioLabel(Tree,Row.Label+TEXT("  ")+Row.Value,32,true,true,AlchemyManualLayout::Material);Effect->SetWrapTextAt(584);
            Effects->AddChildToVerticalBox(Effect)->SetPadding(FMargin(0,0,0,10));
        }
        FolioSection(Tree,LeftPage,TEXT("备料"));
        for(const auto& Input:R.Inputs)
        {
            auto* Row=Tree->ConstructWidget<UHorizontalBox>();LeftPage->AddChildToVerticalBox(Row)->SetPadding(FMargin(0,0,0,12));
            Row->AddChildToHorizontalBox(FolioArt(Tree,Input.Item,78,74))->SetPadding(FMargin(0,0,18,0));
            auto* Name=Row->AddChildToHorizontalBox(FolioLabel(Tree,ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("name")),33,false,false,AlchemyManualLayout::Material));Name->SetSize(FSlateChildSize(ESlateSizeRule::Fill));Name->SetVerticalAlignment(VAlign_Center);
            Row->AddChildToHorizontalBox(FolioLabel(Tree,FString::Printf(TEXT("× %d"),Input.Count),38,true,false,AlchemyManualLayout::Material))->SetVerticalAlignment(VAlign_Center);
        }
        if(R.AutoBase)FolioLine(Tree,LeftPage,TEXT("基液开炉时自动加入，已计入备料。"),26,false,true,FolioMuted,18);
        FolioSection(Tree,LeftPage,TEXT("产出"));FolioPair(Tree,LeftPage,TEXT("基础产出"),FString::Printf(TEXT("%d 瓶"),R.BaseCount));FolioPair(Tree,LeftPage,TEXT("精制额外"),FString::Printf(TEXT("%d 瓶"),R.BonusCount));
        FolioLine(Tree,LeftPage,R.FreeBrewing?TEXT("观察药色与火候，决定装瓶时机。沙漏每轮十秒，仅供估时。"):TEXT("旧批次熬煮时，手动翻转沙漏计时。"),27,false,true,FolioMuted,18);
    }
    else FolioFlow(Tree,LeftPage,R,Layout[P*2]);
    FolioFlow(Tree,RightPage,R,Layout[P*2+1]);
    const int32 First=FirstFolio>0?FirstFolio:P*2+1;
    FolioFooter(Tree,LeftPage,First,FolioCount);FolioFooter(Tree,RightPage,First+1,FolioCount);
}
int32 UColdSteelAlchemyBookWidget::Pages(const FAlchemyRecipe& Recipe)
{return AlchemyManualLayout::Leaves(Recipe).Num()/2;}
void UColdSteelAlchemyBookWidget::Configure(const FAlchemyManualView& View)
{
    if(!View.bContents){Configure(View.Recipe,View.Spread,View.FirstFolio,View.TotalFolios);return;}
    if(!LeftPage||!RightPage)return;
    LeftPage->ClearChildren();RightPage->ClearChildren();auto* Tree=WidgetTree.Get();
    for(int32 Side=0;Side<2;++Side)
    {
        auto* Stack=Side?RightPage.Get():LeftPage.Get();
        FolioHeading(Tree,Stack,TEXT("炼金手记 / 目录"),TEXT("配方索引"),AlchemyManualLayout::ContentsHeading);
        for(int32 Row=0;Row<AlchemyManualLayout::ContentsRows;++Row)
        {
            const int32 Index=View.Spread*8+Side*4+Row;
            auto* Size=Tree->ConstructWidget<USizeBox>();Size->SetHeightOverride(AlchemyManualLayout::ContentsRow);Stack->AddChildToVerticalBox(Size);
            if(!View.Chapters.IsValidIndex(Index))continue;
            const auto& Entry=View.Chapters[Index];auto* Body=Tree->ConstructWidget<UVerticalBox>();Size->SetContent(Body);
            FolioLine(Tree,Body,Entry.Title,38,true,false,AlchemyManualLayout::Time,12);
            FolioLine(Tree,Body,FString::Printf(TEXT("第 %02d 页  ·  点击阅读"),Entry.FirstFolio),27,false,false,FolioGold,14);
            FolioRule(Tree,Body,12);
        }
        if(Side)
        {
            FolioLine(Tree,Stack,TEXT("苔绿 · 材料与用量"),29,true,false,AlchemyManualLayout::Material,10);
            FolioLine(Tree,Stack,TEXT("赤赭 · 火候与温度"),29,true,false,AlchemyManualLayout::Heat,10);
            FolioLine(Tree,Stack,TEXT("靛蓝 · 时间"),29,true,false,AlchemyManualLayout::Time,10);
            FolioLine(Tree,Stack,TEXT("紫墨 · 调和方向与圈数"),29,true,false,AlchemyManualLayout::Stir,10);
        }
        else
        {
            FolioLine(Tree,Stack,TEXT("长按纸页，向左右拖动翻页。"),30,false,true,FolioMuted,16);
            FolioLine(Tree,Stack,TEXT("左上书签回目录，右上书签到末页。"),30,false,true,FolioMuted,16);
            FolioLine(Tree,Stack,TEXT("方向键翻页 · B / Esc 放下手册"),27,false,true,FolioMuted,16);
        }
        FolioFooter(Tree,Stack,View.FirstFolio+Side,View.TotalFolios);
    }
}
