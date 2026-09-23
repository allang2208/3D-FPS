#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelWeaponIcons.h"
#include "M4GunsmithWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"
#include "HAL/PlatformTime.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
using namespace ColdSteelInventory;

const FSlateBrush* UColdSteelEnhancementWidget::MaterialIcon(const FString& Definition)
{
    if(auto* Brush=MaterialBrushes.Find(Definition))return Brush->Get();
    const auto Item=Profile()->CreateItem(Definition);const FString File=Text(Item,TEXT("ue_icon"));
    if(File.IsEmpty())return FCoreStyle::Get().GetBrush("NoBrush");
    auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);
    if(!Texture)return FCoreStyle::Get().GetBrush("NoBrush");
    MaterialTextures.Add(Definition,Texture);
    auto Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(Texture);
    Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush->DrawAs=ESlateBrushDrawType::Image;
    MaterialBrushes.Add(Definition,Brush);return &Brush.Get();
}
UColdSteelEnhancementSystem* UColdSteelEnhancementWidget::System()const{return GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();}
UColdSteelStatusModel* UColdSteelEnhancementWidget::Profile()const{return GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();}

void UColdSteelEnhancementWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(!ProfileHandle.IsValid())ProfileHandle=Profile()->OnChanged.AddUObject(this,&ThisClass::Refresh);
    if(!IconHandle.IsValid())IconHandle=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->OnReady.AddUObject(this,&ThisClass::OnWeaponIconReady);
    Refresh();
}
void UColdSteelEnhancementWidget::NativeDestruct()
{
    Profile()->OnChanged.Remove(ProfileHandle);ProfileHandle.Reset();
    GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->OnReady.Remove(IconHandle);IconHandle.Reset();
    if(WorkbenchPreview)WorkbenchPreview->CloseStandalonePreview();PreviewSurface.Reset();
    Super::NativeDestruct();
}
void UColdSteelEnhancementWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);UpdateResponsiveLayout();
    if(WorkbenchPreview)WorkbenchPreview->TickStandalonePreview(Delta,PreviewSurface);
}
void UColdSteelEnhancementWidget::OnWeaponIconReady(const FString& Recipe)
{
    if (!IsVisible()) return;
    auto* Icons = GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    for (const auto& Pair : ItemImages)
        if (const auto* Item = Profile()->FindItem(Pair.Key); Item && Icons->Supports(*Item) && Icons->Key(*Item) == Recipe)
        {
            const auto* Brush = Icons->Find(*Item);
            Pair.Value->SetImage(Brush ? Brush : MaterialIcon(Item->Definition));
        }
}
void UColdSteelEnhancementWidget::RefreshIcons()
{
    auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    for(const auto& Pair:ItemImages)if(const auto* Item=Profile()->FindItem(Pair.Key))
    {
        const auto* Brush=Icons->Supports(*Item)?Icons->Find(*Item):nullptr;Pair.Value->SetImage(Brush?Brush:MaterialIcon(Item->Definition));
    }
}
void UColdSteelEnhancementWidget::SelectItem(const FString& Id)
{
    ItemId=Id;Message.Empty();if(OverviewScroll)OverviewScroll->ScrollToStart();Refresh();
}
void UColdSteelEnhancementWidget::SelectTab(bool Enchant)
{
    bEnchant=Enchant;Message.Empty();if(OptionScroll)OptionScroll->ScrollToStart();if(OverviewScroll)OverviewScroll->ScrollToStart();Refresh();
}
void UColdSteelEnhancementWidget::SelectScroll(const FString& Id){ScrollId=Id;Message.Empty();Refresh();}
bool UColdSteelEnhancementWidget::Confirm()
{
    const double Now=FPlatformTime::Seconds();if(Now-LastConfirm<.4)return false;LastConfirm=Now;
    bLastApplySucceeded=System()->Apply(Preview,Message);Refresh();return bLastApplySucceeded;
}
FReply UColdSteelEnhancementWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape||E.GetKey()==EKeys::Tab||E.GetKey()==EKeys::K){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();return FReply::Handled();}
    return Super::NativeOnKeyDown(G,E);
}

void UColdSteelEnhancementWidget::Refresh()
{
    if(!Rail||!Inspector||!Options||!ProjectSummary||!Costs)return;
    auto* P=Profile();auto* E=System();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    ItemImages.Reset();Rail->ClearChildren();Inspector->ClearChildren();Options->ClearChildren();ProjectSummary->ClearChildren();Costs->ClearChildren();
    const auto* I=P->FindItem(ItemId);
    if(ItemId.IsEmpty())for(const auto& Candidate:P->Items())if(E->Supports(Candidate)){ItemId=Candidate.InstanceId;I=P->FindItem(ItemId);break;}
    auto Image=[&](const FSlateBrush* Brush,float Size,const FString& Mark=FString())->TSharedRef<SWidget>{
        if(Brush->DrawAs==ESlateBrushDrawType::NoDrawType&&!Mark.IsEmpty())
            return SNew(SBox).WidthOverride(Size).HeightOverride(Size)[SNew(SBorder).BorderImage(&RowBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)
                [Label(Mark,Size>=48?20:12,ColdSteelUI::TextSecondary)]];
        return SNew(SBox).WidthOverride(Size).HeightOverride(Size)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(Brush)]];
    };
    int32 ItemCount=0;
    for(const auto& Candidate:P->Items())if(E->Supports(Candidate))
    {
        ++ItemCount;const FString Id=Candidate.InstanceId,Name=Text(Candidate,TEXT("name"));
        const auto* Brush=MaterialIcon(Candidate.Definition);
        if(Icons->Supports(Candidate)){Icons->Request(Candidate);if(const auto* Live=Icons->Find(Candidate))Brush=Live;}
        auto ItemImage=SNew(SImage).Image(Brush);ItemImages.Add(Id,ItemImage);
        const FString Location=Candidate.Place==1?TEXT("已装备"):TEXT("背包");
        Rail->AddSlot().AutoHeight().Padding(0,0,0,6)
            [SNew(SBox).MinDesiredHeight(76)[SNew(SButton).ButtonStyle(Id==ItemId?&SelectedStyle:&Normal).ContentPadding(8)
                .ToolTipText(FText::FromString(Name+TEXT(" · ")+Location)).OnClicked_Lambda([this,Id](){SelectItem(Id);return FReply::Handled();})
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(48).HeightOverride(48)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[ItemImage]]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0,0,0)
                        [SNew(SVerticalBox)
                            +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Name)).Font(GunsmithUI::TextFont(14,true))
                                .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(Location,12,ColdSteelUI::TextSecondary)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[SNew(STextBlock)
                                .Text(FText::FromString(FString::Printf(TEXT("+%d"),int32(Number(Candidate,TEXT("enhanceLevel"))))))
                                .Font(GunsmithUI::NumberFont(12)).ColorAndOpacity(ColdSteelUI::Enhanced)]]]]];
    }
    if(!ItemCount)Rail->AddSlot().AutoHeight()[Label(TEXT("暂无可加工装备"),14,ColdSteelUI::TextTertiary)];
    EnhanceControl->SetButtonStyle(bEnchant?&Normal:&SelectedStyle);EnchantControl->SetButtonStyle(bEnchant?&SelectedStyle:&Normal);
    CurrentCompare->SetButtonStyle(bCompareBase?&Normal:&SelectedStyle);BaseCompare->SetButtonStyle(bCompareBase?&SelectedStyle:&Normal);
    TArray<const FColdSteelEnchantOption*> HeldScrolls;
    if(bEnchant)for(const auto& Option:E->Scrolls())if(E->BackpackScrollCount(Option.Item)>0)HeldScrolls.Add(&Option);
    if(bEnchant)
    {
        const auto* Selected=E->Scroll(ScrollId);
        if(!I||!Selected||E->BackpackScrollCount(Selected->Item)<=0||!E->CanEnchant(*I,*Selected))
        {
            ScrollId.Empty();
            if(I)for(const auto* Option:HeldScrolls)if(E->CanEnchant(*I,*Option)){ScrollId=Option->Id;break;}
        }
    }
    Preview=E->Quote(ItemId,bEnchant?(ScrollId.IsEmpty()?TEXT("__none"):ScrollId):TEXT(""));
    if(bEnchant&&I&&ScrollId.IsEmpty())Preview.Reason=HeldScrolls.IsEmpty()?TEXT("背包中暂无附魔卷轴"):TEXT("背包中的卷轴与该装备不兼容");
    if(I&&Icons->Supports(*I))WorkbenchPreview->SetStandaloneItem(*I);else WorkbenchPreview->CloseStandalonePreview();
    WeaponBrush=I?*MaterialIcon(I->Definition):*FCoreStyle::Get().GetBrush("NoBrush");
    ResetViewControl->SetEnabled(WorkbenchPreview->HasWorkbenchCapture());AimViewControl->SetEnabled(WorkbenchPreview->CanAimPreview());
    AimViewControl->SetVisibility(WorkbenchPreview->CanAimPreview()?EVisibility::Visible:EVisibility::Collapsed);
    const FString Title=I?Text(*I,TEXT("name")):TEXT("请选择装备");
    ItemTitle->SetText(FText::FromString(Title));ItemTitle->SetToolTipText(FText::FromString(Title));
    ItemLevel->SetText(FText::FromString(I?FString::Printf(TEXT("强化 +%d / +%d · %s · 保留现有配件"),
        int32(Number(*I,TEXT("enhanceLevel"))),E->MaxLevel(*I),I->Place==1?TEXT("已装备"):TEXT("背包")):TEXT("从左侧选择装备，预览加工结果")));
    auto Summary=[&](const FString& Text,int32 Size=14,FLinearColor Tone=ColdSteelUI::TextSecondary){
        ProjectSummary->AddSlot().AutoHeight().Padding(0,0,0,5)[Label(Text,Size,Tone)];
    };
    if(I)
    {
        const auto& After=Preview.After.InstanceId.IsEmpty()?*I:Preview.After;
        if(bEnchant)
        {
            if(const auto* Option=E->Scroll(ScrollId))
            {
                const FString SlotLabel=Option->Slot==TEXT("prefix")?TEXT("前缀"):TEXT("后缀"),Old=E->Affix(*I,*Option->Slot);
                Summary(TEXT("当前")+SlotLabel+TEXT("：")+(Old.IsEmpty()?TEXT("无"):Old));
                Summary(TEXT("附魔后：")+Option->Name,14,ColdSteelUI::TextPrimary);
                Summary(Option->Description,12,ColdSteelUI::TextSecondary);
                Summary(TEXT("同位置词缀替换，另一位置保留"),12,ColdSteelUI::TextTertiary);
            }
            else Summary(Preview.Reason);
        }
        else
        {
            Summary(FString::Printf(TEXT("主属性强化  +%d → +%d"),int32(Number(*I,TEXT("enhanceLevel"))),int32(Number(After,TEXT("enhanceLevel")))),16,ColdSteelUI::TextPrimary);
            Summary(TEXT("确认后消耗材料并保存"),12,ColdSteelUI::TextTertiary);
        }
        auto Row=[&](const FString& Name,double Before,double Final,int32 Digits=1)
        {
            const double Delta=Final-Before;const int32 Benefit=FMath::Abs(Delta)<.001?0:Delta>0?1:-1;
            Inspector->AddSlot().AutoHeight().Padding(0,0,0,1)[TableRow(Name,FString::Printf(TEXT("%.*f"),Digits,Before),
                FString::Printf(TEXT("%.*f"),Digits,Final),Benefit?FString::Printf(TEXT("%+.*f"),Digits,Delta):TEXT("—"),Benefit)];
        };
        if(G->Weapon(I->Definition))
        {
            const auto Stats=G->Calculate(I->Definition,G->Installed(*I));const double Base=Stats.Damage,Attack=P->Derived(TEXT("atk"));
            Row(TEXT("强化等级"),bCompareBase?0:Number(*I,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
            Row(TEXT("附魔伤害加成 %"),bCompareBase?0:E->Effect(*I,TEXT("damagePercent"))*100,E->Effect(After,TEXT("damagePercent"))*100);
            auto Comparison=*I;
            if(bCompareBase){TSharedPtr<FJsonObject> Data;if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Comparison.Data),Data)){Data->SetNumberField(TEXT("enhanceLevel"),0);Data->RemoveField(TEXT("_enchantEffects"));FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Comparison.Data));}}
            Row(TEXT("基础命中伤害"),E->ProcessedDamage(Comparison,Base,Attack),E->ProcessedDamage(After,Base,Attack));
            Row(TEXT("额外穿透目标"),bCompareBase?0:E->Effect(*I,TEXT("piercingBonus")),E->Effect(After,TEXT("piercingBonus")),0);
            Row(TEXT("命中叠毒层数"),bCompareBase?0:E->Effect(*I,TEXT("poisonStacks")),E->Effect(After,TEXT("poisonStacks")),0);
        }
        else Row(TEXT("装备防御"),E->Defense(*I),E->Defense(After));
        Row(TEXT("强化等级"),bCompareBase?0:Number(*I,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
    }
    else
    {
        Summary(TEXT("请选择一件可加工装备"));
        Inspector->AddSlot().AutoHeight().Padding(4,12)[Label(TEXT("选择后显示当前与加工后的属性"),14,ColdSteelUI::TextTertiary)];
    }

    for(const auto& Cost:Preview.Costs)
        Costs->AddSlot().AutoHeight().Padding(0,0,0,4)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)[Image(MaterialIcon(Cost.Definition),28,Cost.Definition==TEXT("gold")?TEXT("金"):TEXT(""))]
            +SHorizontalBox::Slot().FillWidth(1.2f).VAlign(VAlign_Center).Padding(0,0,4,0)[Label(Cost.Name,14,ColdSteelUI::TextSecondary)]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(FString::Printf(TEXT("%lld / %lld"),Cost.Need,Cost.Have),14,
                Cost.Have>=Cost.Need?ColdSteelUI::TextSecondary:ColdSteelUI::Warning,true)]];
    if(Preview.Costs.IsEmpty())Costs->AddSlot().AutoHeight()[Label(I?Preview.Reason:TEXT("尚未选择加工项目"),12,ColdSteelUI::TextTertiary)];

    if(bEnchant)
    {
        for(const auto* Held:HeldScrolls)
        {
            const auto& Option=*Held;
            const FString Id=Option.Id;const bool Compatible=I&&E->CanEnchant(*I,Option);
            const bool Applied=I&&E->Affix(*I,*Option.Slot)==Option.Name,Selected=Id==ScrollId;
            const int64 Have=E->BackpackScrollCount(Option.Item);
            const FString State=!Compatible?TEXT("不兼容"):Applied?TEXT("当前词缀"):Selected?TEXT("已选 · 待附魔"):TEXT("可选择");
            const FString Hint=Option.Name+TEXT("\n")+Option.Description+FString::Printf(TEXT("\n卷轴需要 1 / 背包持有 %lld\n魔法粉尘需要 %lld\n%s"),Have,Option.Dust,*State);
            Options->AddSlot().AutoWidth().Padding(0,0,10,0)[SNew(SBox).WidthOverride(264).HeightOverride(142)
                [SNew(SButton).ButtonStyle(Selected?&SelectedStyle:&Normal).ContentPadding(12).IsEnabled(Compatible)
                    .ToolTipText(FText::FromString(Hint)).OnClicked_Lambda([this,Id](){SelectScroll(Id);return FReply::Handled();})
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Image(MaterialIcon(Option.Item),48)]
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Option.Name)).Font(GunsmithUI::TextFont(14,true))
                                    .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(Option.Slot==TEXT("prefix")?TEXT("前缀卷轴"):TEXT("后缀卷轴"),12,ColdSteelUI::TextTertiary)]]]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(SBox).HeightOverride(42).Clipping(EWidgetClipping::ClipToBounds)[Label(Option.Description,14,ColdSteelUI::TextSecondary)]]
                        +SVerticalBox::Slot().FillHeight(1).VAlign(VAlign_Bottom)[SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().FillWidth(1)[Label(State,12,Selected?ColdSteelUI::Accent:ColdSteelUI::TextTertiary)]
                            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[Label(TEXT("背包"),12,ColdSteelUI::TextTertiary)]
                            +SHorizontalBox::Slot().AutoWidth()[Label(FString::Printf(TEXT("%lld"),Have),12,Have?ColdSteelUI::TextSecondary:ColdSteelUI::Warning,true)]]]]];
        }
    }
    else for(const auto& Cost:Preview.Costs)
    {
        auto Amount=[&](const FString& Name,int64 Value,FLinearColor Color)->TSharedRef<SWidget>{
            return SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[Label(Name,14,ColdSteelUI::TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth()[Label(FString::Printf(TEXT("%lld"),Value),14,Color,true)];
        };
        Options->AddSlot().AutoWidth().Padding(0,0,10,0)[SNew(SBox).WidthOverride(264).HeightOverride(142)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(12)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Image(MaterialIcon(Cost.Definition),48,Cost.Definition==TEXT("gold")?TEXT("金"):TEXT(""))]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(Cost.Name,16,ColdSteelUI::TextPrimary)]]
                +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Amount(TEXT("需要"),Cost.Need,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Amount(TEXT("持有"),Cost.Have,Cost.Have>=Cost.Need?ColdSteelUI::TextSecondary:ColdSteelUI::Warning)]]]];
    }
    if((!bEnchant&&Preview.Costs.IsEmpty())||(bEnchant&&HeldScrolls.IsEmpty()))
        Options->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(264).HeightOverride(142)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(16).VAlign(VAlign_Center)[Label(bEnchant?TEXT("背包中暂无附魔卷轴"):Preview.Reason,14,ColdSteelUI::TextSecondary)]]];

    const FString ConfirmLabel=bEnchant?TEXT("确认附魔"):TEXT("确认强化");
    ConfirmText->SetText(FText::FromString(ConfirmLabel));ConfirmControl->SetToolTipText(FText::FromString(ConfirmLabel+TEXT(" · ")+Preview.Reason));ConfirmControl->SetEnabled(Preview.Valid);
    Footer->SetText(FText::FromString(Message.IsEmpty()?Preview.Reason:Message));
    Footer->SetColorAndOpacity(Message.IsEmpty()?(Preview.Valid?ColdSteelUI::TextSecondary:ColdSteelUI::Warning):(bLastApplySucceeded?ColdSteelUI::Success:ColdSteelUI::Warning));
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
