#include "ColdSteelNpcDialogue.h"
#include "ColdSteelUIStyle.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

using namespace ColdSteelUI;
namespace
{
struct FProject
{
    FName Id, Group;
    FString Name, Glyph, Branch, Description, Result;
};
const TArray<FProject>& Projects()
{
    static const TArray<FProject> Data = {
        {TEXT("village"), NAME_None, TEXT("村庄复兴"), TEXT("村"), TEXT("共同起点"),
            TEXT("补齐围墙，重开铁匠铺和木工工坊，让村民再次在酒馆相聚。"),
            TEXT("各处建筑可分别修复。当前世界的所有玩家共享建设成果。")},
        {TEXT("wall"), TEXT("defense"), TEXT("修复围墙"), TEXT("墙"), TEXT("村庄防御"),
            TEXT("补齐村庄外围的残墙与墙柱，清理坍塌缺口的碎石，为留下的居民恢复完整的防护边界。"),
            TEXT("整圈残破围墙切换为修复后的围墙，恢复墙体碰撞，保留原有城门通道。")},
        {TEXT("blacksmith"), TEXT("production"), TEXT("重建铁匠铺"), TEXT("锻"), TEXT("村庄生产"),
            TEXT("修复铁匠铺的破损墙体，清走废木和落砖，整理铁料与工具，让熄灭的炉火再次燃起。"),
            TEXT("隐藏残破构件，启用修复后的房屋构件与碰撞，恢复铁匠铺铸造工作站。")},
        {TEXT("carpenter"), TEXT("production"), TEXT("修复木工工坊"), TEXT("木"), TEXT("村庄生产"),
            TEXT("修补铁匠铺对面的木工工坊，将院里的木料码齐，整理工作台和二楼住处。"),
            TEXT("修复后可在一楼使用木工工作台，沿楼梯进入木匠的起居室。")},
        {TEXT("tavern"), TEXT("community"), TEXT("重建酒馆"), TEXT("酒"), TEXT("村庄生活"),
            TEXT("把木工工坊旁的长屋修成酒馆，重新摆好吧台、桌椅和酒桶。"),
            TEXT("修复后的酒馆向所有玩家开放。")}
    };
    return Data;
}
const FProject& Project(FName Id)
{
    for(const auto& P : Projects()) if(P.Id == Id) return P;
    return Projects()[0];
}
int32 RepairedProjectCount(const UChapelDialogueComponent* Conversation)
{
    int32 Count=0;
    if(Conversation)for(const FProject& P:Projects())
        if(P.Id!=TEXT("village")&&Conversation->BuildingRepaired(P.Id))++Count;
    return Count;
}
}

void UColdSteelNpcDialogue::RelayoutVillage()
{
    if(!Tree)return;
    using namespace ColdSteelSkillTreeLayout;
    FRow Row;Row.Key=TEXT("village");Row.Name=TEXT("村庄复兴");Row.Note=TEXT("安全 · 生产 · 生活");
    FItem Root;Root.Id=TEXT("village");Row.Items.Add(Root);
    int32 Lane=0;
    for(const auto& P:Projects())
    {
        if(P.Id==TEXT("village")||(!Group.IsNone()&&P.Group!=Group))continue;
        FItem Node;Node.Id=P.Id;Node.Column=1;Node.Lane=Lane++;
        ColdSteelSkillTree::FRequirement Req;Req.Skills.Add(TEXT("village"));Node.Requires.Add(Req);Row.Items.Add(Node);
    }
    Row.Lanes=FMath::Max(1,Lane);
    FConfig Config;Config.Columns=2; // Keep the skill tree's card sizes, spacing and routing.
    Tree->SetLayout(Build({Row},Config));
    if(!Tree->GetLayout().Card(Selected))Selected=Row.Items.Last().Id;
    if(Detail)Refresh();else Tree->SetSource(VillageSource());
}

SColdSteelSkillTreeCanvas::FSource UColdSteelNpcDialogue::VillageSource() const
{
    using EStatus=SColdSteelSkillTreeCanvas::EStatus;using EEdge=SColdSteelSkillTreeCanvas::EEdge;
    SColdSteelSkillTreeCanvas::FSource Source;
    Source.Columns={TEXT("复兴起点"),TEXT("村庄建设")};Source.Selected=Selected;
    Source.Path.Add(TEXT("village"));Source.Path.Add(Selected);
    Source.Card=[this](FName Id)
    {
        const auto& P=Project(Id);const bool Root=Id==TEXT("village");
        const bool Done=Root||(Conversation.IsValid()&&Conversation->BuildingRepaired(Id));
        SColdSteelSkillTreeCanvas::FCardView V;
        V.Name=P.Name;V.Icon=VillageIcons.Find(Id);V.Glyph=P.Glyph;V.GlyphColor=Done?HUDGoldLight:TextPrimary;
        V.Status=Done?EStatus::Learned:EStatus::Available;
        V.State=Root?TEXT("共同起点"):Done?TEXT("已修复"):TEXT("可解锁并修复");
        V.Side=Done?TEXT("1"):FString();V.SideSmall=Done?TEXT("/1"):FString();
        V.Progress=1.f;V.bStateHighlight=!Root;V.bStateGold=Done;
        if(!Query.IsEmpty()){V.bMatch=P.Name.Contains(Query)||P.Branch.Contains(Query)||P.Description.Contains(Query);V.bDim=!V.bMatch;}
        return V;
    };
    Source.Edge=[this](int32 I)
    {
        if(!Tree||!Tree->GetLayout().Entries.IsValidIndex(I))return EEdge::Unmet;
        const FName Target=Tree->GetLayout().Entries[I].To;
        return Conversation.IsValid()&&Conversation->BuildingRepaired(Target)?EEdge::Lit:EEdge::Met;
    };
    Source.EdgeLabel=[](int32){return FString();};Source.Gate=[](int32){return EEdge::Met;};Source.GateLabel=[](int32){return FString();};
    Source.BandNote=[this](const ColdSteelSkillTreeLayout::FBand&)
    {
        return FString::Printf(TEXT("已修复 %d / %d"),RepairedProjectCount(Conversation.Get()),Projects().Num()-1);
    };
    return Source;
}

TSharedRef<SWidget> UColdSteelNpcDialogue::VillageHeader()
{
    const TArray<ColdSteelTreePanel::FTab> Tabs={{NAME_None,TEXT("全部")},{TEXT("defense"),TEXT("防御")},{TEXT("production"),TEXT("生产")},{TEXT("community"),TEXT("生活")}};
    auto TabRow=ColdSteelTreePanel::Tabs(TreeStyle,Tabs,TAttribute<FName>::CreateLambda([this]{return Group;}),true,
        [this](FName Id){Group=Id;RelayoutVillage();});
    ColdSteelTreePanel::FHeader Header;
    Header.Title=TEXT("村庄");Header.Breadcrumb=FText::FromString(TEXT("建设树"));Header.SearchHint=TEXT("搜索建设项目");Header.CloseKey=TEXT("Esc");
    Header.Summary=TAttribute<FText>::CreateLambda([this]
    {
        const int32 Done=RepairedProjectCount(Conversation.Get()),Total=Projects().Num()-1;
        return FText::FromString(FString::Printf(TEXT("已修复 %d / %d　·　可建设 %d　·　村庄共享"),Done,Total,Total-Done));
    });
    Header.OnSearch=[this](const FText& Value){Query=Value.ToString().TrimStartAndEnd();if(Tree)Tree->SetSource(VillageSource());};
    Header.OnClose=[this]{ShowPage(0);};
    auto Back=SNew(SButton).ButtonStyle(&TreeStyle.Muted).ContentPadding(FMargin(12,0)).OnClicked_Lambda([this]{ShowPage(0);return FReply::Handled();})
        [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[ColdSteelTreePanel::Label(TEXT("返回交谈"),14,TextPrimary)]];
    return ColdSteelTreePanel::Header(TreeStyle,Header,TabRow,Back);
}

TSharedRef<SWidget> UColdSteelNpcDialogue::Village()
{
    if (VillageIcons.IsEmpty())
    {
        const FString Directory = FPaths::ProjectContentDir() / TEXT("UI/VillageConstruction");
        for (const FProject& P : Projects())
        {
            const FString File = Directory / (P.Id.ToString().ToLower() + TEXT(".png"));
            if (!FPaths::FileExists(File)) continue;
            if (UTexture2D* Texture = FImageUtils::ImportFileAsTexture2D(File))
            {
                FSlateBrush& Brush = VillageIcons.Add(P.Id);
                Brush.SetResourceObject(Texture);
                Brush.DrawAs = ESlateBrushDrawType::Image;
                Brush.ImageSize = FVector2D(92);
            }
        }
    }
    SAssignNew(Tree,SColdSteelSkillTreeCanvas).OnCardClicked_Lambda([this](FName Id)
    {Selected=Id;Tree->Reveal(Id);Refresh();});
    // Build the layout before installing the frame. Refresh only updates existing controls.
    RelayoutVillage();
    SAssignNew(Detail,SBox)[VillageDetail()];
    auto Main=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[ColdSteelTreePanel::Legend(TreeStyle,Tree,TEXT("项目"))]
        +SVerticalBox::Slot().FillHeight(1)[Tree.ToSharedRef()];
    return ColdSteelTreePanel::Frame(this,TreeStyle,VillageHeader(),Main,Detail.ToSharedRef());
}

TSharedRef<SWidget> UColdSteelNpcDialogue::VillageDetail()
{
    const auto& P=Project(Selected);const bool Root=Selected==TEXT("village");
    const bool Done=!Root&&Conversation.IsValid()&&Conversation->BuildingRepaired(Selected);
    const bool Pending=Conversation.IsValid()&&Conversation->IsPending();
    const bool LegacyPlan=!Done&&Conversation.IsValid()&&Conversation->PlanUnlocked(Selected);
    const int32 Completed=RepairedProjectCount(Conversation.Get()),Total=Projects().Num()-1;
    const FSlateBrush* Artwork = VillageIcons.Find(P.Id);
    TSharedRef<SWidget> Icon = Artwork
        ? StaticCastSharedRef<SWidget>(SNew(SImage).Image(Artwork))
        : StaticCastSharedRef<SWidget>(SNew(SBorder).BorderImage(&TreeStyle.GlyphBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [ColdSteelTreePanel::Label(P.Glyph,36,Done||Root?HUDGoldLight:TextPrimary,true)]);
    auto Body=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[ColdSteelTreePanel::DetailHead(TreeStyle,Icon,P.Branch+TEXT(" · ")+(Root?TEXT("根基"):TEXT("初级 I")),P.Name,TEXT("永久建设"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,18,0,0)[ColdSteelTreePanel::Label(P.Description,14,TextSecondary,false,true)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,22,0,0)[ColdSteelTreePanel::Progress(TreeStyle,
            Root?TEXT("村庄复兴进度"):Done?TEXT("已修复"):TEXT("可解锁并修复"),Root?FString::Printf(TEXT("%d / %d 项"),Completed,Total):Done?TEXT("1 / 1 项"):TEXT("1 / 1 项条件"),
            Root?TEXT("选择要修复的村庄建筑。") : Done?TEXT("建筑已恢复；再次进入这个世界时会保留建设成果。"):
                TEXT("解锁后立即替换场景中的建筑，不消耗资源。"),Root?float(Completed)/Total:1.f,Done?HUDGoldLight:TextPrimary,Done||Root?HUDGold:Accent)];
    auto Conditions=SNew(SBorder).BorderImage(&TreeStyle.RowMetBrush).Padding(FMargin(12,9))
        [ColdSteelTreePanel::Label(Root?TEXT("村庄共同起点，所有建设路线共用"):TEXT("村庄复兴 · 已开启；无额外等级或资源要求"),14,TextSecondary,false,true)];
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("解锁条件"),Root?TEXT("起点"):TEXT("1 / 1"),Conditions)];
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("建设效果"),TEXT("永久"),ColdSteelTreePanel::Label(P.Result,14,TextSecondary,false,true))];
    if(Root)
    {
        auto Children=SNew(SVerticalBox);
        for(const auto& Child:Projects())
        {
            if(Child.Id==TEXT("village"))continue;
            const FName Id=Child.Id;const bool Repaired=Conversation.IsValid()&&Conversation->BuildingRepaired(Id);
            const FSlateBrush* ChildArtwork=VillageIcons.Find(Id);
            const TSharedRef<SWidget> ChildIcon=ChildArtwork
                ? StaticCastSharedRef<SWidget>(SNew(SImage).Image(ChildArtwork))
                : StaticCastSharedRef<SWidget>(ColdSteelTreePanel::Label(Child.Glyph,18,HUDGoldLight,true));
            Children->AddSlot().AutoHeight().Padding(0,0,0,6)
                [SNew(SButton).ButtonStyle(&TreeStyle.Quiet).ContentPadding(0).OnClicked_Lambda([this,Id]
                    {Selected=Id;Group=NAME_None;RelayoutVillage();Tree->Reveal(Id);return FReply::Handled();})
                    [SNew(SBorder).BorderImage(&TreeStyle.RowBrush).Padding(FMargin(10,7,12,7))[SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,9,0)
                            [SNew(SBox).WidthOverride(32).HeightOverride(32).VAlign(VAlign_Center).HAlign(HAlign_Center)[ChildIcon]]
                        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[ColdSteelTreePanel::Label(Child.Name,14,TextPrimary)]
                        +SHorizontalBox::Slot().AutoWidth()[SNew(SBorder).BorderImage(&TreeStyle.ChipBrush).Padding(FMargin(8,2))
                            [ColdSteelTreePanel::Label(Repaired?TEXT("已修复"):TEXT("可建设"),12,Repaired?HUDGoldLight:TextPrimary)]]]]];
        }
        Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("后续建设"),FString::Printf(TEXT("%d 项"),Total),Children)];
    }
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("村庄进度"),TEXT("联机共享"),
        ColdSteelTreePanel::Label(TEXT("保存于当前世界，所有玩家共享修复后的建筑。断线重连和重新进入村庄后继续保留。"),14,TextSecondary,false,true))];
    const FName Id=Selected;
    auto Actions=ColdSteelTreePanel::Action(Root?TEXT("请选择建设节点"):Done?TEXT("已完成修复"):Pending?TEXT("正在修复…"):LegacyPlan?TEXT("立即修复"):TEXT("解锁并修复"),
        &TreeStyle.Primary,!Root&&!Done&&!Pending&&Conversation.IsValid(),[this,Id]{if(Conversation.IsValid())Conversation->RequestAction(Id);},Gray(20),true);
    auto Note=SNew(STextBlock).Font(TextFont(12*.75f)).AutoWrapText(true).LineHeightPercentage(1.3f)
        .ColorAndOpacity_Lambda([this,Id]{return FSlateColor(Conversation.IsValid()&&!Conversation->NunActionMessage(Id).IsEmpty()?HUDGoldLight:TextTertiary);})
        .Text_Lambda([this,Id,Root,Done]
        {
            if(Conversation.IsValid()&&!Conversation->NunActionMessage(Id).IsEmpty())return FText::FromString(Conversation->NunActionMessage(Id));
            return FText::FromString(Root?TEXT("选择需要修复的建筑"):Done?TEXT("建设已完成，无需重复解锁"):TEXT("请让人员和动物离开施工区域，再确认修复"));
        });
    return ColdSteelTreePanel::DetailPage(Body,Actions,Note);
}
