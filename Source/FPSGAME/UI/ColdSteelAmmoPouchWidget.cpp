#include "ColdSteelAmmoPouchWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Engine/GameInstance.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SScaleBox.h"

void UColdSteelAmmoPouchWidget::SetHUD(UColdSteelHUDWidget* Owner){HUD=Owner;}
TSharedRef<SWidget> UColdSteelAmmoPouchWidget::RebuildWidget()
{return SAssignNew(Surface,SVerticalBox);}
void UColdSteelAmmoPouchWidget::ReleaseSlateResources(bool ReleaseChildren)
{Super::ReleaseSlateResources(ReleaseChildren);Surface.Reset();List.Reset();}
void UColdSteelAmmoPouchWidget::NativeConstruct()
{
    Super::NativeConstruct();Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::Refresh);
    Refresh();
}
void UColdSteelAmmoPouchWidget::NativeDestruct()
{if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
void UColdSteelAmmoPouchWidget::NativeTick(const FGeometry& G,float Delta)
{Super::NativeTick(G,Delta);if(!FMath::IsNearlyEqual(LastScale,ColdSteelUI::PixelScale(this)))Refresh();}
void UColdSteelAmmoPouchWidget::Refresh()
{
    if(!Surface||!Model)return;
    const float Offset=List?List->GetScrollOffset():0;
    LastScale=ColdSteelUI::PixelScale(this);const float U=1.f/LastScale;
    Buttons=ColdSteelUI::ButtonStyle(LastScale);
    const auto* Gun=Model->Equipped();const FString Group=Gun?Model->AmmoGroupFor(*Gun):FString();
    const FString Loaded=Gun?Model->AmmoDefinitionFor(*Gun):FString();
    if((Gun?Gun->InstanceId:FString())!=LastWeapon){Selected.Reset();WeaponInstance.Reset();if(!Group.IsEmpty())Expanded.Add(Group);LastWeapon=Gun?Gun->InstanceId:FString();}
    if(!Selected.IsEmpty()&&!Model->CanSwitchAmmo(WeaponInstance,Selected)){Selected.Reset();WeaponInstance.Reset();}
    Surface->ClearChildren();
    auto Label=[&](const FString& Text,float Pixels,FLinearColor Color=ColdSteelUI::TextPrimary,bool Numeric=false)->TSharedRef<SWidget>
    {return SNew(STextBlock).Text(FText::FromString(Text)).Font(Numeric?ColdSteelUI::NumberFont(Pixels*.75f*U):ColdSteelUI::TextFont(Pixels*.75f*U)).ColorAndOpacity(Color).AutoWrapText(true);};
    Surface->AddSlot().AutoHeight().Padding(16*U,14*U)[Label(TEXT("弹药袋"),20)];
    Surface->AddSlot().AutoHeight().Padding(16*U,0,16*U,12*U)[Label(TEXT("自动收纳 · 不占背包空间"),12,ColdSteelUI::TextSecondary)];
    const FString Current=Gun&&!Group.IsEmpty()?FString::Printf(TEXT("当前武器  %s\n已装填 %d 发 · %s"),*ColdSteelInventory::Text(*Gun,TEXT("name")),Gun->Magazine,*Model->AmmoLabel(Loaded)):TEXT("未装备枪械 · 弹药自动保留");
    Surface->AddSlot().AutoHeight().Padding(16*U,0,16*U,14*U)[Label(Current,14)];
    Surface->AddSlot().FillHeight(1).Padding(16*U,0)[SAssignNew(List,SScrollBox).AllowOverscroll(EAllowOverscroll::No)];
    TArray<FString> Groups;if(!Group.IsEmpty())Groups.Add(Group);
    for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled||Model->PouchCount(Type.Id)>0)Groups.AddUnique(Type.Group);
    for(const auto& Key:Groups)
    {
        FString Name=Key;int64 Total=0;
        for(const auto& Type:Model->AmmoCatalog())if(Type.Group==Key){Name=Type.GroupName;Total+=Model->PouchCount(Type.Id);}
        const bool Open=Expanded.Contains(Key);
        List->AddSlot().Padding(0,4*U)
        [SNew(SButton).ButtonStyle(&Buttons).ContentPadding(FMargin(12*U,12*U))
            .OnClicked_Lambda([this,Key](){if(Expanded.Contains(Key))Expanded.Remove(Key);else Expanded.Add(Key);Refresh();return FReply::Handled();})
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[Label((Open?TEXT("−  "):TEXT("+  "))+Name+(Key==Group?TEXT("   当前武器"):TEXT("")),16)]
                +SHorizontalBox::Slot().AutoWidth()[Label(FString::Printf(TEXT("%lld 发"),Total),16,ColdSteelUI::TextPrimary,true)]]];
        if(!Open)continue;
        for(const auto& Type:Model->AmmoCatalog())if(Type.Group==Key&&(Type.Enabled||Model->PouchCount(Type.Id)>0))
        {
            const int64 Count=Model->PouchCount(Type.Id);const FString Id=Type.Id;
            const bool Active=Loaded==Id,Chosen=Selected==Id,Compatible=Gun&&Key==Group&&Type.Enabled;
            const FString State=Active?TEXT("当前装填"):!Type.Enabled?TEXT("暂不可用"):Chosen?TEXT("待切换"):!Compatible?TEXT("未装备兼容枪械"):Count==0?TEXT("已用尽"):TEXT("选择");
            const auto Color=Count>0?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary;
            auto& RowStyle=AmmoButtons.FindOrAdd(Id);if(!RowStyle)RowStyle=MakeShared<FButtonStyle>();
            *RowStyle=Buttons;
            if(Type.TierColor.A>0)
            {
                const auto Base=FMath::Lerp(ColdSteelUI::GlassTint,Type.TierColor,.14f);
                const auto HoverColor=FMath::Lerp(ColdSteelUI::GlassTint,Type.TierColor,.25f);
                RowStyle->Normal=ColdSteelUI::RoundedBrush(Chosen?HoverColor:Base,6*U,Type.TierColor,1*U);
                RowStyle->Hovered=ColdSteelUI::RoundedBrush(HoverColor,6*U,Type.TierColor,1*U);
                RowStyle->Pressed=ColdSteelUI::RoundedBrush(Base,6*U,Type.TierColor,1*U);
                RowStyle->Disabled=RowStyle->Normal;
            }
            auto Row=SNew(SHorizontalBox);
            if(const auto* Icon=Model->AmmoIcon(Id))Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,14*U,0)
                [SNew(SBox).WidthOverride(80*U).HeightOverride(80*U)
                    [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(Icon)]]];
            auto Details=SNew(SVerticalBox);
            Details->AddSlot().AutoHeight()[Label(Type.Name+(Type.TierName.IsEmpty()?FString():TEXT(" · ")+Type.TierName),16,Color)];
            Details->AddSlot().AutoHeight().Padding(0,5*U,0,0)[Label(Model->AmmoEffectSummary(Id),12,ColdSteelUI::TextSecondary)];
            if(!Type.Description.IsEmpty())Details->AddSlot().AutoHeight().Padding(0,4*U,0,0)[Label(Type.Description,12,ColdSteelUI::TextTertiary)];
            Row->AddSlot().FillWidth(1).VAlign(VAlign_Center)[Details];
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8*U,0)[Label(FString::Printf(TEXT("%lld"),Count),16,Color,true)];
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(12*U,0)[Label(State,12,ColdSteelUI::TextSecondary)];
            List->AddSlot().Padding(8*U,2*U,0,2*U)
            [SNew(SButton).ButtonStyle(RowStyle.Get()).ContentPadding(FMargin(14*U,12*U)).IsEnabled(Compatible&&Count>0&&!Active)
                .OnClicked_Lambda([this,Id](){if(const auto* Equipped=Model->Equipped()){Selected=Id;WeaponInstance=Equipped->InstanceId;}Refresh();return FReply::Handled();})
                [Row]];
        }
    }
    if(Groups.IsEmpty())List->AddSlot()[Label(TEXT("尚未获得弹药，获得后会自动收纳"),14,ColdSteelUI::TextSecondary)];
    List->SetScrollOffset(Offset);
    Surface->AddSlot().AutoHeight().Padding(16*U,14*U,16*U,6*U)[Label(TEXT("数量仅含备弹，枪内子弹单独计算\n长按 R 打开轮盘 · 移动鼠标选择 · 松开 R 换弹"),12,ColdSteelUI::TextSecondary)];
    Surface->AddSlot().AutoHeight().Padding(16*U,6*U,16*U,14*U)
    [SNew(SButton).ButtonStyle(&Buttons).ContentPadding(FMargin(12*U,10*U)).IsEnabled(!Selected.IsEmpty())
        .OnClicked_Lambda([this](){if(HUD&&!Selected.IsEmpty()){const FString Id=WeaponInstance,Target=Selected;Selected.Reset();HUD->RequestAmmoChange(Id,Target);}return FReply::Handled();})
        [Label(TEXT("返回并切换弹种"),14)]];
}
