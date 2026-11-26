#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelDungeonLoot.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Async/Async.h"
#include "Engine/Texture2D.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SToolTip.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SGridPanel.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Text/STextBlock.h"

TSharedRef<SWidget> UColdSteelExpeditionWidget::Section(const FString& Title,const FString& Text)
{
    return SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(Title,16,ColdSteelUI::HUDGold)]
            +SVerticalBox::Slot().AutoHeight()[Label(Text,14,ColdSteelUI::TextPrimary)];
}

void UColdSteelExpeditionWidget::RefreshDetail()
{
    UpdateSelectionStyles();
    if(!DetailRows)return;
    if(bStackOverview)PreparationRows.Reset();
    ON_SCOPE_EXIT
    {
        if(bStackOverview)DetailRows->AddSlot().AutoHeight().Padding(0,18,0,0)[BuildPreparation()];
        RefreshPreparation();
    };
    DetailRows->ClearChildren();
    const auto* Entry=Selection();
    if(!Entry)
    {
        DetailRows->AddSlot().AutoHeight()[Section(TEXT("尚未选择目的地"),TEXT("选择目的地后可查看路线、奖励与出征规则。"))];
        return;
    }
    if(DetailTab==1){AddRewards();return;}
    if(DetailTab==2)
    {
        DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)[Label(TEXT("出征规则"),16,ColdSteelUI::HUDGold)];
        for(const auto& Rule:Entry->Rules)
            DetailRows->AddSlot().AutoHeight().Padding(0,0,0,10)[Section(Rule.Title,Rule.Text)];
        if(Entry->Rules.IsEmpty())DetailRows->AddSlot().AutoHeight()[Section(TEXT("暂无规则情报"),TEXT("此目的地尚未提供详细规则。"))];
        return;
    }
    auto Brief = SNew(SVerticalBox);
    if (!Entry->Completion.IsEmpty())
    {
        Brief->AddSlot().AutoHeight().Padding(0, 0, 0, 8)[Label(TEXT("通关目标"), 12, ColdSteelUI::HUDGold)];
        Brief->AddSlot().AutoHeight().Padding(0, 0, 0, 10)[Label(Entry->Completion, 20, ColdSteelUI::TextPrimary)];
    }
    if (!Entry->Description.IsEmpty())
        Brief->AddSlot().AutoHeight()[Label(Entry->Description, 14, ColdSteelUI::TextSecondary)];

    auto BriefCard = SNew(SBorder).BorderImage(&HeroBrush).Padding(16, 12)
        [SNew(SBox).MinDesiredHeight(68).VAlign(VAlign_Center)[Brief]];
    if(Brief->NumSlots()>0)DetailRows->AddSlot().AutoHeight().Padding(0,0,0,16)[BriefCard];
    TArray<FColdSteelExpeditionSection> Facts;
    if (!Entry->Scale.IsEmpty()) Facts.Add({TEXT("探索规模"), Entry->Scale});
    if (!Entry->Threat.IsEmpty()) Facts.Add({TEXT("威胁情报"), Entry->Threat});
    if (!Entry->RecommendedLevel.IsEmpty()) Facts.Add({TEXT("推荐等级"), Entry->RecommendedLevel});
    if (!Facts.IsEmpty())
    {
        auto FactGrid = SNew(SGridPanel);
        for (int32 Index = 0; Index < Facts.Num(); ++Index)
        {
            const int32 Column = bSingleColumnFacts ? 0 : 2 * Index;
            const int32 RowIndex = bSingleColumnFacts ? 2 * Index : 0;
            if (Index > 0)
            {
                if (bSingleColumnFacts) FactGrid->AddSlot(0, RowIndex - 1)[Divider()];
                else FactGrid->AddSlot(Column - 1, 0)[Divider(Orient_Vertical)];
            }
            FactGrid->SetColumnFill(Column, 1.f);
            FactGrid->AddSlot(Column, RowIndex).Padding(16, 8)
                [SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()[Label(Facts[Index].Title, 12, ColdSteelUI::HUDGold)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0, 3, 0, 0)[Label(Facts[Index].Text, 14, ColdSteelUI::TextPrimary)]];
        }
        DetailRows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)[Card(FactGrid, 1)];
    }
    if(!Entry->Routes.IsEmpty())
    {
        DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)[Label(TEXT("路线情报"),16,ColdSteelUI::HUDGold)];
        const int32 Columns=FMath::Min(CardColumns,Entry->Routes.Num());
        auto RouteGrid=SNew(SGridPanel);
        for(int32 Index=0;Index<Entry->Routes.Num();++Index)
        {
            const int32 Column=Index%Columns;
            const auto& Route=Entry->Routes[Index];
            RouteGrid->SetColumnFill(Column,1.f);
            auto Summary=SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[Label(Route.Title,16,ColdSteelUI::HUDGold)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[Divider()]
                +SVerticalBox::Slot().AutoHeight()[Label(Route.Text,14,ColdSteelUI::TextPrimary)];
            RouteGrid->AddSlot(Column,Index/Columns)
                .Padding(Column>0?4.f:0.f,0,Column+1<Columns?4.f:0.f,8.f)
                [Card(Summary,16)];
        }
        // Route cards follow their content height; the overview no longer stretches room steps.
        DetailRows->AddSlot().AutoHeight()[RouteGrid];
        DetailRows->AddSlot().AutoHeight().Padding(0,0,0,16)
            [Label(TEXT("所列为沿途可搜索的主要奖励类别，实际获得以探索结果为准。"),12,ColdSteelUI::TextTertiary)];
    }
    if(!Entry->MonsterIntel.IsEmpty())
    {
        auto IntelRows=SNew(SVerticalBox);
        for(int32 Index=0;Index<Entry->MonsterIntel.Num();++Index)
        {
            if(Index>0)IntelRows->AddSlot().AutoHeight()[Divider()];
            const auto& Intel=Entry->MonsterIntel[Index];
            TSharedRef<SWidget> Content=SNullWidget::NullWidget;
            if(bSingleColumnFacts)
                Content=Section(Intel.Title,Intel.Text);
            else
                Content=SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,20,0)
                        [SNew(SBox).WidthOverride(116)[Label(Intel.Title,16,ColdSteelUI::HUDGold,false,false)]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(Intel.Text,14,ColdSteelUI::TextPrimary)];
            IntelRows->AddSlot().FillHeight(1).VAlign(VAlign_Center)
                [SNew(SBox).MinDesiredHeight(54).VAlign(VAlign_Center).Padding(FMargin(0,10))[Content]];
        }
        auto IntelCard=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(TEXT("怪物情况"),16,ColdSteelUI::HUDGold)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
                [Label(TEXT("已知大类与活动迹象"),12,ColdSteelUI::TextTertiary)]
            +SVerticalBox::Slot().AutoHeight()[Divider()]
            +SVerticalBox::Slot().FillHeight(1)[IntelRows]
            +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)
                [Label(TEXT("各区域遭遇不同，具体种类与数量以本次探索为准。"),12,ColdSteelUI::TextTertiary)];
        if(bStackOverview)DetailRows->AddSlot().AutoHeight()[Card(IntelCard,16)];
        else DetailRows->AddSlot().FillHeight(1)[Card(IntelCard,16)];
    }
}

void UColdSteelExpeditionWidget::BuildRewardPreview()
{
    auto* Model=Profile();
    if(bRewardsLoaded||!Model)return;
    bRewardsLoaded=true;
    for(const auto& Candidate:FColdSteelDungeonLoot::PreviewItems())
    {
        FColdSteelExpeditionReward Row;
        const auto* Ammo=Model->AmmoType(Candidate.Definition);
        if(Ammo)
        {
            Row.Content.Name=Ammo->Name;Row.Content.Description=Ammo->Description;
            Row.Content.Type=TEXT("弹药");Row.Content.Icon=Ammo->Icon;Row.Content.Rarity=TEXT("common");
        }
        else
        {
            const auto Item=Model->CreateItem(Candidate.Definition);
            Row.Content=BuildColdSteelItemTooltip(Item,Model,nullptr);
        }
        if(Row.Content.Name.IsEmpty())continue;
        Row.Group=Candidate.Definition.StartsWith(TEXT("enchant_scroll_"))?2:
            (Ammo||Candidate.Definition.StartsWith(TEXT("hp_potion"))||Candidate.Definition.StartsWith(TEXT("mp_potion")))?0:1;
        Row.Availability=Candidate.MinimumDepth<=0?TEXT("起始区域可出现"):Candidate.MinimumDepth<8?TEXT("深入设施后可出现"):TEXT("深层区域可出现");
        if(Candidate.bInFinalTier)Row.Availability+=TEXT(" · 最终宝箱候选");
        if(!Row.Content.Icon.IsEmpty())Row.IconPath=FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Row.Content.Icon;
        Row.Brush=MakeShared<FSlateBrush>();
        Row.Brush->DrawAs=ESlateBrushDrawType::Image;
        RewardPreview.Add(MoveTemp(Row));
    }
}

void UColdSteelExpeditionWidget::LoadNextRewardIcon()
{
    if(bClosing||bRewardIconLoading||DetailTab!=1||!IsInViewport())return;
    while(RewardPreview.IsValidIndex(NextRewardIcon)&&RewardPreview[NextRewardIcon].IconPath.IsEmpty())++NextRewardIcon;
    if(!RewardPreview.IsValidIndex(NextRewardIcon))return;
    const int32 Index=NextRewardIcon++;
    const FString Filename=RewardPreview[Index].IconPath;
    bRewardIconLoading=true;
    const TWeakObjectPtr<UColdSteelExpeditionWidget> Weak(this);
    // One bounded decode at a time; full-resolution source PNGs never become UI textures.
    Async(EAsyncExecution::ThreadPool,[Weak,Index,Filename]()
    {
        auto Thumbnail=MakeShared<FImage,ESPMode::ThreadSafe>();FImage Source;
        bool Loaded=FImageUtils::LoadImage(*Filename,Source);
        if(Loaded)
        {
            const float Scale=FMath::Min(1.f,192.f/FMath::Max(Source.SizeX,Source.SizeY));
            FImageCore::ResizeImageAllocDest(Source,*Thumbnail,FMath::Max(1,FMath::RoundToInt(Source.SizeX*Scale)),
                FMath::Max(1,FMath::RoundToInt(Source.SizeY*Scale)),ERawImageFormat::BGRA8,EGammaSpace::sRGB);
        }
        AsyncTask(ENamedThreads::GameThread,[Weak,Index,Thumbnail,Loaded]()
        {
            auto* Self=Weak.Get();if(!Self||Self->bClosing)return;
            Self->bRewardIconLoading=false;
            if(Loaded)if(auto* Texture=FImageUtils::CreateTexture2DFromImage(*Thumbnail))
            {
                Self->RewardTextures.Add(Texture);
                auto& Row=Self->RewardPreview[Index];Row.Brush->SetResourceObject(Texture);
                Row.Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
                if(auto Image=Row.Image.Pin()){Image->SetImage(Row.Brush.Get());Image->Invalidate(EInvalidateWidgetReason::Layout);}
            }
            Self->LoadNextRewardIcon();
        });
    });
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::RewardCard(FColdSteelExpeditionReward& Reward)
{
    const auto Brush=Reward.Brush;
    const FString RarityLabel=ColdSteelUI::RarityLabel(Reward.Content.Rarity);
    auto Details=SNew(SVerticalBox);
    Details->AddSlot().AutoHeight().Padding(0,0,0,8)[Label(Reward.Content.Name,20,ColdSteelUI::ItemTooltipText)];
    Details->AddSlot().AutoHeight().Padding(0,0,0,8)
        [Label(RarityLabel.IsEmpty()?Reward.Content.Type:RarityLabel+TEXT(" · ")+Reward.Content.Type,12,ColdSteelUI::ItemTooltipGold)];
    if(!Reward.Content.Description.IsEmpty())Details->AddSlot().AutoHeight().Padding(0,0,0,10)
        [Label(Reward.Content.Description,14,ColdSteelUI::ItemTooltipText)];
    for(const auto& Stat:Reward.Content.Summary)
        Details->AddSlot().AutoHeight().Padding(0,0,0,5)[Label(Stat.Label+TEXT("  ")+Stat.Value,14,ColdSteelUI::ItemTooltipText)];
    Details->AddSlot().AutoHeight().Padding(0,8,0,0)[Label(Reward.Availability+TEXT("\n可能获得 · 不保证掉落"),12,ColdSteelUI::ItemTooltipSecondary)];
    auto Tip=SNew(SToolTip).BorderImage(&RewardTooltipBrush).TextMargin(16)
        [SNew(SBox).WidthOverride_Lambda([this]() { return BodyHost?FMath::Min(340.f,FMath::Max(120.f,BodyHost->GetCachedGeometry().GetLocalSize().X-48.f)):340.f; })[Details]];
    TSharedPtr<SImage> Image;
    auto CardContent=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12,0)
            [SNew(SBox).WidthOverride(48).HeightOverride(48)
                [SNew(SOverlay)
                    +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(Reward.Content.Name.Left(1)))
                            .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                            .Visibility_Lambda([Brush](){return Brush->GetResourceObject()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})]
                    +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                        [SAssignNew(Image,SImage).Image(Brush.Get()).Visibility_Lambda([Brush]() { return Brush->GetResourceObject()?EVisibility::HitTestInvisible:EVisibility::Collapsed; })]]]]
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(Reward.Content.Name,14,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[Label(RarityLabel.IsEmpty()?Reward.Content.Type:RarityLabel,12,ColdSteelUI::RarityColor(Reward.Content.Rarity))]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(TEXT("可能获得"),12,ColdSteelUI::TextTertiary)]];
    Reward.Image=Image;
    return SNew(SBorder).BorderImage(&HeroBrush).Padding(12).ToolTip(Tip)
        [SNew(SBox).MinDesiredHeight(80)[CardContent]];
}

void UColdSteelExpeditionWidget::AddRewards()
{
    if(!Selection()||!Selection()->bDungeonLoot)
    {DetailRows->AddSlot().AutoHeight()[Section(TEXT("暂无奖励情报"),TEXT("此目的地尚未提供奖励列表。"))];return;}
    BuildRewardPreview();
    DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)
        [Section(TEXT("可能获得"),TEXT("奖励随探索推进变化。下列物品来自实际宝箱掉落池，每次只随机获得其中部分；悬停查看说明。"))];
    const TCHAR* Groups[]={TEXT("基础与进阶补给"),TEXT("材料与重铸"),TEXT("附魔卷轴")};
    for(int32 Group=0;Group<3;++Group)
    {
        auto Grid=SNew(SGridPanel);int32 Count=0;
        for(auto& Reward:RewardPreview)if(Reward.Group==Group)
        {
            const int32 Column=Count%CardColumns;
            Grid->SetColumnFill(Column,1.f);
            Grid->AddSlot(Column,Count/CardColumns).Padding(0,0,Column+1<CardColumns?8:0,8)[RewardCard(Reward)];++Count;
        }
        if(!Count)continue;
        DetailRows->AddSlot().AutoHeight().Padding(0,8,0,10)[Label(Groups[Group],16,ColdSteelUI::HUDGold)];
        DetailRows->AddSlot().AutoHeight()[Grid];
    }
    if(RewardPreview.IsEmpty())DetailRows->AddSlot().AutoHeight()[Section(TEXT("奖励情报暂不可用"),TEXT("未能读取奖励目录。出征不会因此扣除额外物品。"))];
    else DetailRows->AddSlot().AutoHeight().Padding(0,12,0,0)
        [Section(TEXT("首领后的最终宝箱"),FString::Printf(TEXT("击败首领后开放奖励区。最终宝箱使用最高档掉落池，普通补给的基础数量按 %g 倍发放。额外必得强化石 2–4 个、魔法粉尘 100–160；材料不叠加数量倍率。"),FColdSteelDungeonLoot::FinalQuantityMultiplier()))];
    LoadNextRewardIcon();
}
