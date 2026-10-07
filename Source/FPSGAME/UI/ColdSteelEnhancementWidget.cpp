#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelWeaponText.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelWeaponIcons.h"
#include "M4GunsmithWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/AzureDragonReach.h"
#include "../Weapons/Bow/BowStats.h"
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
    if(!PendingIcons.Contains(Definition))PendingIcons.Add(Definition);
    return FCoreStyle::Get().GetBrush("NoBrush");
}
void UColdSteelEnhancementWidget::ImportMaterialIcon(const FString& Definition)
{
    TSharedPtr<FSlateBrush> Brush;
    const auto Item=Profile()->CreateItem(Definition);const FString File=Text(Item,TEXT("ue_icon"));
    if(!File.IsEmpty())if(auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File))
    {
        Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(Texture);
        Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush->DrawAs=ESlateBrushDrawType::Image;
        MaterialTextures.Add(Definition,Texture);
    }
    if(!Brush)Brush=MakeShared<FSlateBrush>(); // 缺图/坏图缓存为空画刷，与图鉴口径一致不再重试
    MaterialBrushes.Add(Definition,Brush);
    const bool bReady=Brush->DrawAs==ESlateBrushDrawType::Image;
    if(auto* Entries=PendingIconImages.Find(Definition))
        for(auto& Entry:*Entries)if(auto Image=Entry.Pin()){Image->SetImage(Brush.Get());Image->SetVisibility(EVisibility::HitTestInvisible);}
    if(auto* Tiles=PendingIconTiles.Find(Definition))
        for(auto& Entry:*Tiles)if(auto Tile=Entry.Pin())Tile->SetVisibility(EVisibility::Collapsed);
    PendingIconImages.Remove(Definition);PendingIconTiles.Remove(Definition);
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
    if(FlashOverlay&&FlashUntil>=0)
    {
        const double Remain=FlashUntil-FPlatformTime::Seconds();
        if(Remain<=0){FlashUntil=-1;FlashOverlay->SetVisibility(EVisibility::Collapsed);}
        else{FlashOverlay->SetVisibility(EVisibility::HitTestInvisible);FlashOverlay->SetColorAndOpacity(FLinearColor(1,1,1,FMath::Clamp(Remain/.9,0.,1.)));}
    }
    // 限时图标泵：每帧最多花 4ms 补目录小图，避免打开面板时被成批 PNG 解码卡住首帧。
    if(!PendingIcons.IsEmpty())
    {
        const double Until=FPlatformTime::Seconds()+.004;bool Imported=false;
        while(!PendingIcons.IsEmpty()&&FPlatformTime::Seconds()<Until)
        {
            const FString Definition=PendingIcons[0];PendingIcons.RemoveAt(0);
            ImportMaterialIcon(Definition);Imported=true;
            if(const auto* I=Profile()->FindItem(ItemId);I&&I->Definition==Definition&&!WorkbenchPreview->HasWorkbenchCapture())
                if(auto* Brush=MaterialBrushes.Find(Definition))WeaponBrush=**Brush;
        }
        if(Imported)if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
    }
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
    bLastApplySucceeded=System()->Apply(Preview,Message);if(bLastApplySucceeded)FlashUntil=Now+.9;Refresh();return bLastApplySucceeded;
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
    auto Image=[&](const FString& Definition,float Size,const FString& Mark=FString())->TSharedRef<SWidget>{
        const FSlateBrush* Brush=MaterialIcon(Definition);
        const bool bPending=!MaterialBrushes.Contains(Definition); // 缓存未命中=已入泵队列；解析为缺图的空画刷不再登记
        auto ItemImage=SNew(SImage).Image(Brush);
        auto Tile=SNew(SBorder).BorderImage(&RowBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [Label(Mark,Size>=48?20:12,ColdSteelUI::TextSecondary)];
        // 未就绪时亮字牌（金/空），泵导入完成后按 Definition 回填这一份图标。
        ItemImage->SetVisibility(bPending?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        Tile->SetVisibility(bPending&&!Mark.IsEmpty()?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        if(bPending)
        {
            PendingIconImages.FindOrAdd(Definition).Add(ItemImage);
            if(!Mark.IsEmpty())PendingIconTiles.FindOrAdd(Definition).Add(Tile);
        }
        return SNew(SBox).WidthOverride(Size).HeightOverride(Size)
            [SNew(SOverlay)
                +SOverlay::Slot()[Tile]
                +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[ItemImage]]];
    };
    int32 ItemCount=0;
    for(const auto& Candidate:P->Items())if(E->Supports(Candidate))
    {
        ++ItemCount;const FString Id=Candidate.InstanceId,Name=Text(Candidate,TEXT("name"));
        const auto* Brush=MaterialIcon(Candidate.Definition);
        if(Icons->Supports(Candidate)){Icons->Request(Candidate);if(const auto* Live=Icons->Find(Candidate))Brush=Live;}
        auto ItemImage=SNew(SImage).Image(Brush);ItemImages.Add(Id,ItemImage);
        if(!MaterialBrushes.Contains(Candidate.Definition))PendingIconImages.FindOrAdd(Candidate.Definition).Add(ItemImage);
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
    const int64 DustHave=bEnchant?P->CountMaterial(TEXT("magic_dust")):0;
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
    ItemLevel->SetText(FText::FromString(I?FString::Printf(TEXT("%s · 保留现有配件"),I->Place==1?TEXT("已装备"):TEXT("背包")):TEXT("从左侧选择装备，预览加工结果")));
    LevelBadge->SetText(FText::FromString(I?FString::Printf(TEXT("+%d"),int32(Number(*I,TEXT("enhanceLevel")))):TEXT("")));
    LevelMax->SetText(FText::FromString(I?FString::Printf(TEXT("/ %d"),E->MaxLevel(*I)):TEXT("")));
    GoldChip->SetText(FText::FromString(FString::Printf(TEXT("%lld"),P->CountMaterial(TEXT("gold")))));
    StoneChip->SetText(FText::FromString(FString::Printf(TEXT("%lld"),P->CountMaterial(TEXT("enhancement_stone")))));
    DustChip->SetText(FText::FromString(FString::Printf(TEXT("%lld"),P->CountMaterial(TEXT("magic_dust")))));
    if(LevelTrack)
    {
        LevelTrack->ClearChildren();
        if(I)for(int32 N=0,Level=int32(Number(*I,TEXT("enhanceLevel"))),Max=E->MaxLevel(*I);N<Max;++N)
            LevelTrack->AddSlot().AutoWidth().Padding(0,0,3,0)[SNew(SBox).WidthOverride(16).HeightOverride(6)
                [SNew(SBorder).BorderImage(N<Level?&TrackDone:N==Level?&TrackNext:&TrackIdle)]];
    }
    if(AffixRow)
    {
        AffixRow->ClearChildren();
        if(I)
        {
            const TCHAR* Slots[]={TEXT("prefix"),TEXT("suffix")};const TCHAR* Names[]={TEXT("前缀"),TEXT("后缀")};
            for(int32 S=0;S<2;++S)
            {
                const FString Affix=E->Affix(*I,Slots[S]);
                if(S)AffixRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8,0,8,0)[Label(TEXT("·"),12,ColdSteelUI::TextTertiary)];
                AffixRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,4,0)[Label(Names[S],12,ColdSteelUI::TextTertiary)];
                AffixRow->AddSlot().AutoWidth().VAlign(VAlign_Center)[Label(Affix.IsEmpty()?TEXT("—"):Affix,12,Affix.IsEmpty()?ColdSteelUI::TextTertiary:ColdSteelUI::Enchanted)];
            }
        }
    }
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
                // 涡轮增压是时间轴效果：给出实战两档射速，避免只看到静态射击间隔。
                const double TurboStart=E->Effect(After,TEXT("turboRampStartMul")),TurboPeak=E->Effect(After,TEXT("turboRampPeakMul")),TurboSeconds=E->Effect(After,TEXT("turboRampSeconds"));
                if(TurboStart>0.&&TurboPeak>0.&&TurboSeconds>0.&&G->Weapon(I->Definition))
                {
                    const double BaseInterval=ColdSteelWeaponStats::Interval(I,P,G->CalculateItem(*I,G->Installed(*I)).Interval);
                    if(BaseInterval>0.)Summary(FString::Printf(TEXT("持续开火 %.1f 秒：射速 %.0f → %.0f 发/分"),TurboSeconds,60./(BaseInterval*TurboStart),60./(BaseInterval*TurboPeak)),12,ColdSteelUI::TextSecondary);
                }
                // 汇聚同样是模式改变：给出整匣合计与聚合后的实战单发伤害。
                const double ConvergenceScale=E->Effect(After,TEXT("convergenceDamageScale"));
                if(E->Effect(After,TEXT("convergenceShot"))>0.&&ConvergenceScale>0.&&G->Weapon(I->Definition))
                {
                    const auto Stats=G->CalculateItem(*I,G->Installed(*I));
                    const double PerShot=ColdSteelWeaponStats::DamageParts(*I,P,Stats.Damage).Total();
                    if(PerShot>0.&&Stats.Capacity>0)
                        Summary(FString::Printf(TEXT("打空 %d 发弹匣：合计 %.0f → 聚合 %.0f 伤害"),Stats.Capacity,PerShot*Stats.Capacity,PerShot*Stats.Capacity*ConvergenceScale),12,ColdSteelUI::TextSecondary);
                }
                // 碎裂/感电与涡轮、汇聚同为模式型词缀：给一行实战说明，呈现口径统一。
                if(ColdSteelInventory::IsBow(After)&&E->Effect(After,TEXT("bowDrawSpeedBonus"))>0.)
                    Summary(FString::Printf(TEXT("力量 +%.0f；拉弓速度 +%.0f%%，与改造件及装备的加成相加"),E->Effect(After,TEXT("str")),E->Effect(After,TEXT("bowDrawSpeedBonus"))*100.),12,ColdSteelUI::TextSecondary);
                else if(E->Effect(After,TEXT("heavyChargeSpeedBonus"))>0.)
                    Summary(FString::Printf(TEXT("力量 +%.0f；重击蓄力速度 +%.0f%%，与改造件的加成相加"),E->Effect(After,TEXT("str")),E->Effect(After,TEXT("heavyChargeSpeedBonus"))*100.),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("cowboyReload"))>0.)
                    Summary(TEXT("进入滑铲状态 0.25 秒后，从弹药袋瞬间补弹；每次滑铲一次，仅附魔枪生效，无换弹动画"),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("calmFirearm"))>0.)
                    Summary(FString::Printf(TEXT("精神 +%.0f；暴击加 1 层沉着冷静，每层稳定性 +%.0f%%、后坐力 −%.0f%%，最多 %.0f 层；暴击刷新 %.0f 秒，满层也刷新，到期全部清除"),
                        E->Effect(After,TEXT("wis")),E->Effect(After,TEXT("composureStabilityPerStack"))*100.,E->Effect(After,TEXT("composureRecoilReductionPerStack"))*100.,
                        E->Effect(After,TEXT("composureMaxStacks")),E->Effect(After,TEXT("composureSeconds"))),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("berserkMelee"))>0.)
                    Summary(FString::Printf(TEXT("当前武器命中加 1 层狂暴：每层攻速 +%.0f%%，最多 %.0f 层；每 %.0f 秒减 1 层，命中不刷新倒计时"),
                        E->Effect(After,TEXT("berserkSpeedPerStack"))*100.,E->Effect(After,TEXT("berserkMaxStacks")),E->Effect(After,TEXT("berserkDecaySeconds"))),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("bigBlind"))>0.)
                    Summary(FString::Printf(TEXT("命中获得赌注：暴击伤害倍率每层 +%.1f，最多 %.0f 层；命中刷新 %.0f 秒，仅附魔手枪暴击后清空；枪口金色脉冲"),
                        E->Effect(After,TEXT("wagerCriticalBonusPerStack")),E->Effect(After,TEXT("wagerMaxStacks")),E->Effect(After,TEXT("wagerSeconds"))),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("azureDragonClaw"))>0.)
                {
                    const double Required=FMath::Max(1.,E->Effect(After,TEXT("azureDragonHitsToSummon"),9.));
                    Summary(FString::Printf(TEXT("仅限剑类：每次攻击有效命中积蓄 %g%%，%.0f 次攻击积满后激活 %.0f 秒；同次攻击只充能一次"),100./Required,Required,E->Effect(After,TEXT("azureDragonActiveSeconds"),30.)),12,ColdSteelUI::TextSecondary);
                    Summary(TEXT("从下一次出手开始，持续期间每次攻击都生效"),12,ColdSteelUI::TextSecondary);
                    Summary(FString::Printf(TEXT("斩击、重击、上挑延伸到龙爪爪尖约 %.1f 米（其余攻击距离 +%g%%），物理伤害 ×%g；另行结算翻倍前角色物理攻击值的 %g%% 魔法伤害"),
                        AzureDragonReach::ClawReachCM/100.,(E->Effect(After,TEXT("azureDragonReachMultiplier"),1.5)-1.)*100.,E->Effect(After,TEXT("azureDragonPhysicalMultiplier"),2.),
                        E->Effect(After,TEXT("azureDragonMagicAttackScale"),1.)*100.),12,ColdSteelUI::TextSecondary);
                    Summary(TEXT("停止攻击保留未满能量；切换武器、移除附魔或死亡清空。龙爪随剑同步，激活期间能量随时间燃烧，不刷新"),12,ColdSteelUI::TextSecondary);
                }
                if(E->Effect(After,TEXT("shatterBullet"))>0.)
                    Summary(FString::Printf(TEXT("命中后向 %.0f 米内弹射一颗，继承 %.0f%% 伤害；击杀时全员弹射"),E->Effect(After,TEXT("shatterRadiusM")),E->Effect(After,TEXT("shatterDamageScale"))*100),12,ColdSteelUI::TextSecondary);
                if(E->Effect(After,TEXT("electrifiedMelee"))>0.)
                    Summary(FString::Printf(TEXT("近战命中向 %.0f 米内放电连锁，闪电等级取 %.0f 级与当前等级较高者"),E->Effect(After,TEXT("electrifiedRadiusM")),E->Effect(After,TEXT("electrifiedMinLevel"))),12,ColdSteelUI::TextSecondary);
                Summary(TEXT("同位置词缀替换，另一位置保留"),12,ColdSteelUI::TextTertiary);
            }
            else Summary(Preview.Reason);
        }
        else
        {
            Summary(FString::Printf(TEXT("强化等级 +%d → +%d"),int32(Number(*I,TEXT("enhanceLevel"))),int32(Number(After,TEXT("enhanceLevel")))),16,ColdSteelUI::TextPrimary);
            Summary(TEXT("确认后消耗材料并保存"),12,ColdSteelUI::TextTertiary);
        }
        auto Row=[&](const FString& Name,double Before,double Final,int32 Digits=1,bool LowerBetter=false)
        {
            const double Delta=Final-Before;const int32 Benefit=FMath::Abs(Delta)<.001?0:(Delta>0)!=LowerBetter?1:-1;
            Inspector->AddSlot().AutoHeight().Padding(0,0,0,1)[TableRow(Name,FString::Printf(TEXT("%.*f"),Digits,Before),
                FString::Printf(TEXT("%.*f"),Digits,Final),Benefit?FString::Printf(TEXT("%+.*f"),Digits,Delta):TEXT("—"),Benefit)];
        };
        if(G->Weapon(I->Definition)||ColdSteelInventory::IsTwoHandedSword(*I)||ColdSteelInventory::IsBow(*I))
        {
            const auto Stats=G->CalculateItem(*I,G->Installed(*I));
            const double Base=ColdSteelInventory::IsBow(*I)?Number(*I,TEXT("full_damage"),69):Stats.Damage;
            Row(TEXT("强化等级"),bCompareBase?0:Number(*I,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
            Row(TEXT("附魔伤害 %"),bCompareBase?0:E->Effect(*I,TEXT("damagePercent"))*100,E->Effect(After,TEXT("damagePercent"))*100);
            Row(TEXT("暴击率 %"),bCompareBase?0:E->Effect(*I,TEXT("critRate"))*100,E->Effect(After,TEXT("critRate"))*100);
            auto Comparison=*I;
            if(bCompareBase){TSharedPtr<FJsonObject> Data;if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Comparison.Data),Data)){Data->SetNumberField(TEXT("enhanceLevel"),0);Data->RemoveField(TEXT("_enchantEffects"));FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Comparison.Data));}}
            const bool Melee=ColdSteelInventory::IsTwoHandedSword(*I);
            const bool Bow=ColdSteelInventory::IsBow(*I);
            const float Charge=Bow?ColdSteelBow::DrawDamageMultiplier(1.f):1.f;
            const auto BeforeDamage=(Melee?ColdSteelMelee::Evaluate(Comparison,P).DamageParts:ColdSteelWeaponStats::DamageParts(Comparison,P,Base)).Scaled(Charge);
            const auto AfterDamage=(Melee?ColdSteelMelee::Evaluate(After,P).DamageParts:ColdSteelWeaponStats::DamageParts(After,P,Base)).Scaled(Charge);
            Row(ColdSteelWeaponText::TotalDamage,BeforeDamage.Total(),AfterDamage.Total(),2);
            Row(ColdSteelWeaponText::BasePhysical,BeforeDamage.BasePhysical,AfterDamage.BasePhysical,2);
            if(BeforeDamage.AddedPhysical>0||AfterDamage.AddedPhysical>0)Row(ColdSteelWeaponText::AddedPhysical,BeforeDamage.AddedPhysical,AfterDamage.AddedPhysical,2);
            if(BeforeDamage.AddedMagic>0||AfterDamage.AddedMagic>0)Row(ColdSteelWeaponText::AddedMagic,BeforeDamage.AddedMagic,AfterDamage.AddedMagic,2);
            if(Bow)Inspector->AddSlot().AutoHeight().Padding(0,6)[Label(ColdSteelWeaponText::BowScope,12,ColdSteelUI::TextSecondary)];
            // 附魔改攻击间隔（沉重 ×1.35）必须进比较表：越低越好，反向判色；近战取挥砍节奏，枪械/弓取射击间隔。
            const double BeforeInterval=Melee?ColdSteelMelee::Evaluate(Comparison,P).AttackSeconds:Bow?ColdSteelBow::Evaluate(Comparison,P).Draw:ColdSteelWeaponStats::Interval(&Comparison,P,Stats.Interval);
            const double AfterInterval=Melee?ColdSteelMelee::Evaluate(After,P).AttackSeconds:Bow?ColdSteelBow::Evaluate(After,P).Draw:ColdSteelWeaponStats::Interval(&After,P,Stats.Interval);
            Row(TEXT("攻击间隔 ms"),FMath::RoundToDouble(BeforeInterval*1000),FMath::RoundToDouble(AfterInterval*1000),0,true);
            Row(TEXT("附魔力量"),bCompareBase?0:E->Effect(*I,TEXT("str")),E->Effect(After,TEXT("str")),0);
            Row(TEXT("附魔精神"),bCompareBase?0:E->Effect(*I,TEXT("wis")),E->Effect(After,TEXT("wis")),0);
            if(Melee)
            {
                const auto BeforeMelee=ColdSteelMelee::Evaluate(Comparison,P);
                const auto AfterMelee=ColdSteelMelee::Evaluate(After,P);
                Row(TEXT("重击蓄力速度加成 %"),BeforeMelee.HeavyChargeSpeedBonus*100.,AfterMelee.HeavyChargeSpeedBonus*100.,0);
                Row(TEXT("重击蓄力时间 s"),BeforeMelee.HeavyChargeSeconds,AfterMelee.HeavyChargeSeconds,2,true);
            }
            else if(Bow)
            {
                const auto BeforeBow=ColdSteelBow::Evaluate(Comparison,P);
                const auto AfterBow=ColdSteelBow::Evaluate(After,P);
                Row(TEXT("拉弓速度加成 %"),BeforeBow.DrawSpeedBonus*100.,AfterBow.DrawSpeedBonus*100.,1);
                Row(TEXT("拉弓时间 s"),BeforeBow.Draw,AfterBow.Draw,2,true);
            }
            Row(TEXT("额外穿透目标"),bCompareBase?0:E->Effect(*I,TEXT("piercingBonus")),E->Effect(After,TEXT("piercingBonus")),0);
            Row(TEXT("命中叠毒层数"),bCompareBase?0:E->Effect(*I,TEXT("poisonStacks")),E->Effect(After,TEXT("poisonStacks")),0);
        }
        else
        {
            Row(TEXT("装备防御"),E->Defense(*I),E->Defense(After));
            Row(TEXT("强化等级"),bCompareBase?0:Number(*I,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
        }
    }
    else
    {
        Summary(TEXT("请选择一件可加工装备"));
        Inspector->AddSlot().AutoHeight().Padding(4,12)[Label(TEXT("选择后显示当前与加工后的属性"),14,ColdSteelUI::TextTertiary)];
    }

    for(const auto& Cost:Preview.Costs)
        Costs->AddSlot().AutoHeight().Padding(0,0,0,4)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)[Image(Cost.Definition,28,Cost.Definition==TEXT("gold")?TEXT("金"):TEXT(""))]
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
                            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Image(Option.Item,48)]
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Option.Name)).Font(GunsmithUI::TextFont(14,true))
                                    .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(Option.Slot==TEXT("prefix")?TEXT("前缀卷轴"):TEXT("后缀卷轴"),12,ColdSteelUI::TextTertiary)]]]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(SBox).HeightOverride(44).Clipping(EWidgetClipping::ClipToBounds)[Label(Option.Description,14,ColdSteelUI::TextSecondary)]]
                        +SVerticalBox::Slot().FillHeight(1).VAlign(VAlign_Bottom)[SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().FillWidth(1)[Label(State,12,Selected?ColdSteelUI::Accent:ColdSteelUI::TextTertiary)]
                            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[Label(TEXT("尘"),12,ColdSteelUI::TextTertiary)]
                            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Label(FString::Printf(TEXT("%lld"),Option.Dust),12,DustHave>=Option.Dust?ColdSteelUI::TextSecondary:ColdSteelUI::Warning,true)]
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
                    +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Image(Cost.Definition,48,Cost.Definition==TEXT("gold")?TEXT("金"):TEXT(""))]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(Cost.Name,16,ColdSteelUI::TextPrimary)]]
                +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Amount(TEXT("需要"),Cost.Need,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Amount(TEXT("持有"),Cost.Have,Cost.Have>=Cost.Need?ColdSteelUI::TextSecondary:ColdSteelUI::Warning)]]]];
    }
    if((!bEnchant&&Preview.Costs.IsEmpty())||(bEnchant&&HeldScrolls.IsEmpty()))
        Options->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(264).HeightOverride(142)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(16).VAlign(VAlign_Center)[Label(bEnchant?TEXT("背包中暂无附魔卷轴"):Preview.Reason,14,ColdSteelUI::TextSecondary)]]];

    const FString ConfirmLabel=bEnchant?TEXT("确认附魔"):(I&&Preview.Valid?FString::Printf(TEXT("强化至 +%d"),int32(Number(Preview.After,TEXT("enhanceLevel")))):TEXT("确认强化"));
    ConfirmText->SetText(FText::FromString(ConfirmLabel));ConfirmControl->SetToolTipText(FText::FromString(ConfirmLabel+TEXT(" · ")+Preview.Reason));ConfirmControl->SetEnabled(Preview.Valid);
    Footer->SetText(FText::FromString(Message.IsEmpty()?Preview.Reason:Message));
    Footer->SetColorAndOpacity(Message.IsEmpty()?(Preview.Valid?ColdSteelUI::TextSecondary:ColdSteelUI::Warning):(bLastApplySucceeded?ColdSteelUI::Success:ColdSteelUI::Warning));
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
