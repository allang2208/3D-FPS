#include "ColdSteelAmmoPouchWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Engine/GameInstance.h"
#include "Misc/Crc.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"

// 弹药袋页的视图模型：先从模型采集，再由同一份数据生成内容键与控件树。
// 采集与构建分离，保证“内容键覆盖的字段”和“画出来的字段”不会走散。
struct FColdSteelAmmoRowView
{
    FString Id,Title,Effect,Description,State;
    const FSlateBrush* Icon=nullptr;
    int64 Count=0;
    FLinearColor Color=ColdSteelUI::TextPrimary;
    FLinearColor TierColor=FLinearColor::Transparent;
    bool bActive=false,bChosen=false,bEnabled=false,bTier=false;
};
struct FColdSteelAmmoGroupView
{
    FString Key,Name;
    int64 Total=0;
    bool bOpen=false;
    TArray<FColdSteelAmmoRowView> Rows;
};
struct FColdSteelAmmoPouchView
{
    FString Caption,CurrentGroup;
    TArray<FColdSteelAmmoGroupView> Groups;
    bool bEmpty=false,bConfirm=false;
};

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

void UColdSteelAmmoPouchWidget::CollectPouchView(FString& Key,FColdSteelAmmoPouchView& View) const
{
    const auto* Gun=Model->Equipped();const FString Group=Gun?Model->AmmoGroupFor(*Gun):FString();
    const FString Loaded=Gun?Model->AmmoDefinitionFor(*Gun):FString();
    View.CurrentGroup=Group;
    View.Caption=Gun&&!Group.IsEmpty()?FString::Printf(TEXT("当前武器  %s\n已装填 %d 发 · %s"),*ColdSteelInventory::Text(*Gun,TEXT("name")),Gun->Magazine,*Model->AmmoLabel(Loaded)):TEXT("未装备枪械 · 弹药自动保留");
    const bool bBow=Gun&&ColdSteelInventory::IsBow(*Gun);
    if(bBow)View.Caption=FString::Printf(TEXT("当前弓  %s\n已选择 %s · 射出时扣箭"),*ColdSteelInventory::Text(*Gun,TEXT("name")),*Model->AmmoLabel(Loaded));
    View.bConfirm=!Selected.IsEmpty();
    // TSet 的遍历顺序不参与内容键，排序后再写入。
    TArray<FString> Open;for(const auto& Name:Expanded)Open.Add(Name);Open.Sort();
    Key+=View.Caption+TEXT("|")+FString::Join(Open,TEXT(","))+TEXT("|")+(Selected.IsEmpty()?TEXT("-"):Selected)+TEXT("|");
    TArray<FString> Groups;if(!Group.IsEmpty())Groups.Add(Group);
    for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled||Model->PouchCount(Type.Id)>0)Groups.AddUnique(Type.Group);
    View.bEmpty=Groups.IsEmpty();
    for(const auto& GroupKey:Groups)
    {
        FColdSteelAmmoGroupView& GroupView=View.Groups.AddDefaulted_GetRef();
        GroupView.Key=GroupKey;
        for(const auto& Type:Model->AmmoCatalog())if(Type.Group==GroupKey){GroupView.Name=Type.GroupName;GroupView.Total+=Model->PouchCount(Type.Id);}
        GroupView.bOpen=Expanded.Contains(GroupKey);
        Key+=FString::Printf(TEXT("%s:%s:%lld:%d|"),*GroupKey,*GroupView.Name,GroupView.Total,GroupView.bOpen?1:0);
        if(!GroupView.bOpen)continue;
        for(const auto& Type:Model->AmmoCatalog())if(Type.Group==GroupKey&&(Type.Enabled||Model->PouchCount(Type.Id)>0))
        {
            FColdSteelAmmoRowView& Row=GroupView.Rows.AddDefaulted_GetRef();
            const bool Compatible=Gun&&GroupKey==Group&&Type.Enabled;
            Row.Id=Type.Id;Row.Count=Model->PouchCount(Type.Id);
            Row.bActive=Loaded==Type.Id;Row.bChosen=Selected==Type.Id;Row.bEnabled=Compatible&&Row.Count>0&&!Row.bActive;
            Row.Title=Type.Name+(Type.TierName.IsEmpty()?FString():TEXT(" · ")+Type.TierName);
            Row.Effect=Model->AmmoEffectSummary(Type.Id);Row.Description=Type.Description;
            Row.Icon=Model->AmmoIcon(Type.Id);
            Row.Color=Row.Count>0?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary;
            Row.bTier=Type.TierColor.A>0;Row.TierColor=Type.TierColor;
            Row.State=Row.bActive?TEXT("当前装填"):!Type.Enabled?TEXT("暂不可用"):Row.bChosen?TEXT("待切换"):!Compatible?TEXT("未装备兼容枪械"):Row.Count==0?TEXT("已用尽"):TEXT("选择");
            if(Row.bActive&&bBow)Row.State=TEXT("当前箭种");
            else if(!Compatible&&Type.Group==TEXT("arrow"))Row.State=TEXT("未装备兼容弓");
            Key+=FString::Printf(TEXT("%s:%lld:%d%d%d:%s:%s:%s:"),*Row.Id,Row.Count,Row.bActive?1:0,Row.bChosen?1:0,Row.bEnabled?1:0,*Row.State,*Row.Title,*Row.Effect);
            Key+=Type.TierColor.ToString();
            Key+=(Row.Icon?TEXT(":icon:"):TEXT(":noicon:"))+Type.Description+TEXT("|");
        }
    }
}

void UColdSteelAmmoPouchWidget::Refresh()
{
    if(!Surface||!Model)return;
    const float Scale=ColdSteelUI::PixelScale(this);const float U=1.f/Scale;
    Buttons=ColdSteelUI::ButtonStyle(Scale);
    const auto* Gun=Model->Equipped();const FString Group=Gun?Model->AmmoGroupFor(*Gun):FString();
    if((Gun?Gun->InstanceId:FString())!=LastWeapon){Selected.Reset();WeaponInstance.Reset();if(!Group.IsEmpty())Expanded.Add(Group);LastWeapon=Gun?Gun->InstanceId:FString();}
    if(!Selected.IsEmpty()&&!Model->CanSwitchAmmo(WeaponInstance,Selected)){Selected.Reset();WeaponInstance.Reset();}
    // Refresh 挂在 OnChanged 上，而 OnChanged 每次成功存档都会广播：自动存档无条件每 5 秒
    // 一次，训练待写盘时最快每 1 秒一次，广播时弹药袋的显示内容往往完全没变。旧实现每次都
    // ClearChildren 重建整页（含 SScrollBox、全部 SButton 与图标），行的悬停／按下态随之丢失，
    // 观感就是无操作闪动。现在先采集视图模型与内容键，内容没变直接返回，不碰控件树。
    FColdSteelAmmoPouchView View;FString Key=FString::Printf(TEXT("%.4f|"),Scale);
    CollectPouchView(Key,View);
    const uint32 Hash=FCrc::StrCrc32(*Key);
    if(FMath::IsNearlyEqual(LastScale,Scale)&&Hash==ContentKey&&Surface->GetChildren()->Num()>0)return;
    LastScale=Scale;ContentKey=Hash;
    BuildPage(View,U);
}

void UColdSteelAmmoPouchWidget::BuildPage(const FColdSteelAmmoPouchView& View,float U)
{
    const float Offset=List?List->GetScrollOffset():0;
    Surface->ClearChildren();
    auto Label=[&](const FString& Text,float Pixels,FLinearColor Color=ColdSteelUI::TextPrimary,bool Numeric=false,bool Wrap=true)->TSharedRef<SWidget>
    {return SNew(STextBlock).Text(FText::FromString(Text)).Font(Numeric?ColdSteelUI::NumberFont(Pixels*.75f*U):ColdSteelUI::TextFont(Pixels*.75f*U)).ColorAndOpacity(Color).AutoWrapText(Wrap);};
    // 右侧数字列与状态列按本页最长内容定宽。定宽之后每张卡的左栏可用宽度完全相同，
    // 数量多的那一行不会把左栏挤窄去换行，卡片高度也就不会因内容长度而参差。
    const FSlateFontInfo CountFont=ColdSteelUI::NumberFont(16*.75f*U);
    const FSlateFontInfo StateFont=ColdSteelUI::TextFont(12*.75f*U);
    const auto Measure=[&](const FString& Text,const FSlateFontInfo& Font)->float
    {
        // 无 Slate 的自动化上下文不量文字，列宽退回下面的下限值。
        if(!FSlateApplication::IsInitialized())return 0.f;
        const FVector2D Size=FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text,Font);return float(Size.X);
    };
    float CountColumn=48*U,StateColumn=36*U,TotalColumn=48*U;
    for(const auto& Group:View.Groups)
    {
        TotalColumn=FMath::Max(TotalColumn,Measure(FString::Printf(TEXT("%lld %s"),Group.Total,Group.Key==TEXT("arrow")?TEXT("支"):TEXT("发")),CountFont));
        for(const auto& Row:Group.Rows)
        {
            CountColumn=FMath::Max(CountColumn,Measure(FString::Printf(TEXT("%lld"),Row.Count),CountFont));
            StateColumn=FMath::Max(StateColumn,Measure(Row.State,StateFont));
        }
    }
    Surface->AddSlot().AutoHeight().Padding(16*U,14*U)[Label(TEXT("弹药袋"),20)];
    Surface->AddSlot().AutoHeight().Padding(16*U,0,16*U,12*U)[Label(TEXT("自动收纳 · 不占背包空间"),12,ColdSteelUI::TextSecondary)];
    Surface->AddSlot().AutoHeight().Padding(16*U,0,16*U,14*U)[Label(View.Caption,14)];
    Surface->AddSlot().FillHeight(1).Padding(16*U,0)[SAssignNew(List,SScrollBox).AllowOverscroll(EAllowOverscroll::No)];
    for(const auto& Group:View.Groups)
    {
        const FString Key=Group.Key;
        List->AddSlot().Padding(0,4*U)
        [SNew(SButton).ButtonStyle(&Buttons).ContentPadding(FMargin(12*U,12*U))
            .OnClicked_Lambda([this,Key](){if(Expanded.Contains(Key))Expanded.Remove(Key);else Expanded.Add(Key);Refresh();return FReply::Handled();})
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[Label((Group.bOpen?TEXT("−  "):TEXT("+  "))+Group.Name+(Key==View.CurrentGroup?TEXT("   当前武器"):TEXT("")),16)]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).MinDesiredWidth(TotalColumn).HAlign(HAlign_Right)
                    [Label(FString::Printf(TEXT("%lld %s"),Group.Total,Key==TEXT("arrow")?TEXT("支"):TEXT("发")),16,ColdSteelUI::TextPrimary,true,false)]]]];
        for(const auto& Row:Group.Rows)
        {
            auto& RowStyle=AmmoButtons.FindOrAdd(Row.Id);if(!RowStyle)RowStyle=MakeShared<FButtonStyle>();
            *RowStyle=Buttons;
            if(Row.bTier)
            {
                const auto Base=FMath::Lerp(ColdSteelUI::GlassTint,Row.TierColor,.14f);
                const auto HoverColor=FMath::Lerp(ColdSteelUI::GlassTint,Row.TierColor,.25f);
                RowStyle->Normal=ColdSteelUI::RoundedBrush(Row.bChosen?HoverColor:Base,6*U,Row.TierColor,1*U);
                RowStyle->Hovered=ColdSteelUI::RoundedBrush(HoverColor,6*U,Row.TierColor,1*U);
                RowStyle->Pressed=ColdSteelUI::RoundedBrush(Base,6*U,Row.TierColor,1*U);
                RowStyle->Disabled=RowStyle->Normal;
            }
            auto Contents=SNew(SHorizontalBox);
            if(Row.Icon)Contents->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,14*U,0)
                [SNew(SBox).WidthOverride(80*U).HeightOverride(80*U)
                    [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(Row.Icon)]]];
            auto Details=SNew(SVerticalBox);
            Details->AddSlot().AutoHeight()[Label(Row.Title,16,Row.Color)];
            Details->AddSlot().AutoHeight().Padding(0,5*U,0,0)[Label(Row.Effect,12,ColdSteelUI::TextSecondary)];
            if(!Row.Description.IsEmpty())Details->AddSlot().AutoHeight().Padding(0,4*U,0,0)[Label(Row.Description,12,ColdSteelUI::TextTertiary)];
            Contents->AddSlot().FillWidth(1).VAlign(VAlign_Center)[Details];
            // 数字右对齐、不换行：位数变多时向左边延展，卡片高度与右侧起点都不动。
            Contents->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8*U,0)
            [SNew(SBox).MinDesiredWidth(CountColumn).HAlign(HAlign_Right)
                [Label(FString::Printf(TEXT("%lld"),Row.Count),16,Row.Color,true,false)]];
            Contents->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(12*U,0)
            [SNew(SBox).MinDesiredWidth(StateColumn).HAlign(HAlign_Left)
                [Label(Row.State,12,ColdSteelUI::TextSecondary,false,false)]];
            const FString Id=Row.Id;
            List->AddSlot().Padding(8*U,2*U,0,2*U)
            [SNew(SButton).ButtonStyle(RowStyle.Get()).ContentPadding(FMargin(14*U,12*U)).IsEnabled(Row.bEnabled)
                .OnClicked_Lambda([this,Id](){if(const auto* Equipped=Model->Equipped()){Selected=Id;WeaponInstance=Equipped->InstanceId;}Refresh();return FReply::Handled();})
                [Contents]];
        }
    }
    if(View.bEmpty)List->AddSlot()[Label(TEXT("尚未获得弹药，获得后会自动收纳"),14,ColdSteelUI::TextSecondary)];
    List->SetScrollOffset(Offset);
    const auto* Equipped=Model->Equipped();
    const bool bBow=Equipped&&ColdSteelInventory::IsBow(*Equipped);
    Surface->AddSlot().AutoHeight().Padding(16*U,14*U,16*U,6*U)[Label(bBow?TEXT("搭箭不扣数量，射出时扣除\n短按 R 搭箭 · 长按 R 选箭 · 松开 R 换箭"):TEXT("数量仅含备弹，枪内子弹单独计算\n长按 R 打开轮盘 · 移动鼠标选择 · 松开 R 换弹"),12,ColdSteelUI::TextSecondary)];
    Surface->AddSlot().AutoHeight().Padding(16*U,6*U,16*U,14*U)
    [SNew(SButton).ButtonStyle(&Buttons).ContentPadding(FMargin(12*U,10*U)).IsEnabled(View.bConfirm)
        .OnClicked_Lambda([this](){if(HUD&&!Selected.IsEmpty()){const FString Id=WeaponInstance,Target=Selected;Selected.Reset();HUD->RequestAmmoChange(Id,Target);}return FReply::Handled();})
        [Label(bBow?TEXT("返回并更换箭种"):TEXT("返回并切换弹种"),14)]];
}
