#include "ColdSteelNpcDialogue.h"
#include "ColdSteelUIStyle.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../Building/VillageBuildDefense.h"
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
struct FProject;
const FProject& Project(FName Id);

struct FProject
{
    FName Id, Group;
    FString Name, Glyph, Branch, Description, Result;
    bool bResearchOnly = false;
    FName Prerequisite = NAME_None;

    FName ArtworkId() const { return Id; }
    FName Parent() const { return Prerequisite.IsNone() ? FName(TEXT("village")) : Prerequisite; }
    bool IsAvailable(const UChapelDialogueComponent* Conversation) const
    {
        return Prerequisite.IsNone() || Project(Prerequisite).IsComplete(Conversation);
    }
    bool IsComplete(const UChapelDialogueComponent* Conversation) const
    {
        return Conversation && (bResearchOnly ? Conversation->PlanUnlocked(Id) : Conversation->BuildingRepaired(Id));
    }
    const TCHAR* StateLabel(bool bComplete,bool bAvailable=true) const
    {
        if(Id==TEXT("high_wall"))return bComplete ? TEXT("已升级") : bAvailable ? TEXT("可升级") : TEXT("需先修复城墙");
        if(!bComplete&&!bAvailable&&Prerequisite==TEXT("windmill"))return TEXT("需先修复风车");
        if(!bComplete&&!bAvailable&&Prerequisite==TEXT("blacksmith"))return TEXT("需先重建铁匠铺");
        if(!bComplete&&!bAvailable&&Prerequisite==TEXT("village_construction"))return TEXT("需先研究防御工事");
        if(bResearchOnly)return bComplete ? TEXT("已解锁") : bAvailable ? TEXT("可解锁") : TEXT("需先升级高墙");
        return bComplete ? TEXT("已修复") : TEXT("可解锁并修复");
    }
};
const TArray<FProject>& Projects()
{
    using VillageBuildDefense::ETier;
    using VillageBuildDefense::ProjectName;
    static const TArray<FProject> Data = {
        {TEXT("village"), NAME_None, TEXT("村庄复兴"), TEXT("村"), TEXT("共同起点"),
            TEXT("补齐围墙，修复村里的风车、工坊和店铺，让村民再次在酒馆相聚。"),
            TEXT("重建铁匠铺后可开设枪店，风车磨坊恢复后可重开面包屋，修复城墙后可升级高墙，继而研究防御工事与守备机械。当前世界的所有玩家共享建设成果。")},
        {TEXT("wall"), TEXT("defense"), ProjectName(ETier::RepairedWall), TEXT("墙"), TEXT("村庄防御"),
            TEXT("补齐村庄外围的残墙与墙柱，清理坍塌缺口的碎石，为留下的居民恢复完整的防护边界。"),
            TEXT("解锁矮墙和木质大门建造。修复后的城墙恢复东西门通道，沿街路灯在黄昏亮起。")},
        {TEXT("high_wall"), TEXT("defense"), ProjectName(ETier::HighCurtain), TEXT("垛"), TEXT("村庄防御"),
            TEXT("沿原有墙线加筑高墙与城垛。东西门楼下设升降铁闸，二层守望平台与墙顶步道相通。"),
            TEXT("解锁石砌高墙、石城门和登墙石阶建造。村庄围墙加筑步道，东西门改为升降铁闸。"),false,TEXT("wall")},
        {TEXT("village_construction"), TEXT("defense"), ProjectName(ETier::Fortifications), TEXT("塔"), TEXT("村庄防御"),
            TEXT("塔楼侧门连通墙顶步道，向上可抵达开阔的守望平台。"),
            TEXT("获赠东门工坊旁的一座高塔，解锁高塔建造与「守备机械」研究。"),true,TEXT("high_wall")},
        {VillageBuildDefense::MechanicsPlan, TEXT("defense"), ProjectName(ETier::Mechanics), TEXT("械"), TEXT("村庄防御"),
            TEXT("在东门马厩对面的路边建起机械工坊，木匠与铁匠在同一座装配台上整备守城器械。"),
            TEXT("解锁固定式弩炮、配重投石机和热油锅建造。机械工坊向全村开放。"),true,TEXT("village_construction")},
        {TEXT("blacksmith"), TEXT("production"), TEXT("重建铁匠铺"), TEXT("锻"), TEXT("村庄生产"),
            TEXT("修复铁匠铺的破损墙体，清走废木和落砖，整理铁料与工具，让熄灭的炉火再次燃起。"),
            TEXT("隐藏残破构件，启用修复后的房屋构件与碰撞，恢复铁匠铺铸造工作站。")},
        {TEXT("gunshop"), TEXT("production"), TEXT("修复枪店"), TEXT("枪"), TEXT("村庄生产"),
            TEXT("修好南侧长屋，把一楼改为枪铺，将二楼留作店主的住处。"),
            TEXT("一楼开放枪械工作台，柜台后的枪架和洞洞板陈列枪械与配件。"),false,TEXT("blacksmith")},
        {TEXT("carpenter"), TEXT("production"), TEXT("修复木工工坊"), TEXT("木"), TEXT("村庄生产"),
            TEXT("修补铁匠铺对面的木工工坊，将院里的木料码齐，整理工作台和二楼住处。"),
            TEXT("修复后可在一楼使用木工工作台，沿楼梯进入木匠的起居室。")},
        {TEXT("herbalist"), TEXT("production"), TEXT("修复草药铺"), TEXT("药"), TEXT("村庄生产"),
            TEXT("修补广场北屋的屋顶和窗墙，重新挂起药铺招牌，在柜台陈列草药。"),
            TEXT("修复后可使用店内的炼药工作台，按配方研磨、调制和装瓶。")},
        {TEXT("windmill"), TEXT("production"), TEXT("修复风车"), TEXT("风"), TEXT("村庄生产"),
            TEXT("补上磨坊破损的外墙，修整风车的轮轴和风帆。"),
            TEXT("风车重新随风转动，并解锁面包屋的修复。")},
        {TEXT("bakery"), TEXT("production"), TEXT("修复面包屋"), TEXT("麦"), TEXT("村庄生产"),
            TEXT("将风车旁的东侧长屋修成面包屋，修好石窑、烟囱和通往二楼的木梯。"),
            TEXT("一楼陈列面包、备料和烘烤，二楼恢复为面包师的住处。"),false,TEXT("windmill")},
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
int32 CompletedProjectCount(const UChapelDialogueComponent* Conversation)
{
    int32 Count=0;
    if(Conversation)for(const FProject& P:Projects())
        if(P.IsComplete(Conversation))++Count;
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
    FConfig Config;Config.Columns=2;
    for(const auto& P:Projects())
    {
        if(P.Id==TEXT("village")||(!Group.IsNone()&&P.Group!=Group))continue;
        const FName Parent=P.Parent();
        const auto* ParentNode=Row.Items.FindByPredicate([Parent](const FItem& Item){return Item.Id==Parent;});
        if(!ParentNode)continue;
        FItem Node;Node.Id=P.Id;Node.Column=ParentNode->Column+1;
        Node.Lane=P.Prerequisite.IsNone()?Lane++:ParentNode->Lane;
        Config.Columns=FMath::Max(Config.Columns,Node.Column+1);
        ColdSteelSkillTree::FRequirement Req;Req.Skills.Add(Parent);Node.Requires.Add(Req);Row.Items.Add(Node);
    }
    Row.Lanes=FMath::Max(1,Lane);
    Tree->SetLayout(Build({Row},Config));
    if(!Tree->GetLayout().Card(Selected))
    {
        Selected=Row.Items.Last().Id;
        if(Group==TEXT("defense"))
            for(const auto& P:Projects())
                if(P.Group==Group && P.IsAvailable(Conversation.Get()) && !P.IsComplete(Conversation.Get()))
                {Selected=P.Id;break;}
    }
    if(Detail)Refresh();else Tree->SetSource(VillageSource());
}

SColdSteelSkillTreeCanvas::FSource UColdSteelNpcDialogue::VillageSource() const
{
    using EStatus=SColdSteelSkillTreeCanvas::EStatus;using EEdge=SColdSteelSkillTreeCanvas::EEdge;
    SColdSteelSkillTreeCanvas::FSource Source;
    Source.Columns={TEXT("复兴起点"),TEXT("一级建设"),TEXT("二级建设"),TEXT("三级建设"),TEXT("四级建设")};
    if(Tree)Source.Columns.SetNum(FMath::Min(Source.Columns.Num(),Tree->GetLayout().Config.Columns));
    Source.Selected=Selected;
    Source.Path.Add(TEXT("village"));
    for(FName Ancestor=Selected;!Ancestor.IsNone();Ancestor=Project(Ancestor).Prerequisite)
        Source.Path.Add(Ancestor);
    Source.Card=[this](FName Id)
    {
        const auto& P=Project(Id);const bool Root=Id==TEXT("village");
        const bool Done=Root||P.IsComplete(Conversation.Get());
        const bool Available=P.IsAvailable(Conversation.Get());
        SColdSteelSkillTreeCanvas::FCardView V;
        V.Name=P.Name;V.Icon=VillageIcons.Find(P.ArtworkId());V.Glyph=P.Glyph;V.GlyphColor=Done?HUDGoldLight:TextPrimary;
        V.Status=Done?EStatus::Learned:Available?EStatus::Available:EStatus::Locked;
        V.State=Root?TEXT("共同起点"):P.StateLabel(Done,Available);
        V.Side=Done?TEXT("1"):FString();V.SideSmall=Done?TEXT("/1"):FString();
        V.Progress=Done||Available?1.f:0.f;V.bStateHighlight=!Root&&Available;V.bStateGold=Done;
        if(!Query.IsEmpty()){V.bMatch=P.Name.Contains(Query)||P.Branch.Contains(Query)||P.Description.Contains(Query)||P.Result.Contains(Query);V.bDim=!V.bMatch;}
        return V;
    };
    Source.Edge=[this](int32 I)
    {
        if(!Tree||!Tree->GetLayout().Entries.IsValidIndex(I))return EEdge::Unmet;
        const FName Target=Tree->GetLayout().Entries[I].To;
        const FProject& P=Project(Target);
        return P.IsComplete(Conversation.Get())?EEdge::Lit:P.IsAvailable(Conversation.Get())?EEdge::Met:EEdge::Unmet;
    };
    Source.EdgeLabel=[](int32){return FString();};Source.Gate=[](int32){return EEdge::Met;};Source.GateLabel=[](int32){return FString();};
    Source.BandNote=[this](const ColdSteelSkillTreeLayout::FBand&)
    {
        return FString::Printf(TEXT("建设进度 %d / %d"),CompletedProjectCount(Conversation.Get()),Projects().Num()-1);
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
        const int32 Done=CompletedProjectCount(Conversation.Get()),Total=Projects().Num()-1;
        int32 Available=0;
        for(const FProject& P:Projects())
            if(P.Id!=TEXT("village")&&P.IsAvailable(Conversation.Get())&&!P.IsComplete(Conversation.Get()))++Available;
        return FText::FromString(FString::Printf(TEXT("已完成 %d / %d　·　可建设 %d　·　村庄共享"),Done,Total,Available));
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
            const FName ArtworkId=P.ArtworkId();
            if(VillageIcons.Contains(ArtworkId))continue;
            const FString File = Directory / (ArtworkId.ToString().ToLower() + TEXT(".png"));
            UTexture2D* Texture = nullptr;
            if (ArtworkId == TEXT("bakery"))
                Texture = LoadObject<UTexture2D>(nullptr, TEXT("/Game/ColdSteelData/Icons/bread.bread"));
            else if (FPaths::FileExists(File))
                Texture = FImageUtils::ImportFileAsTexture2D(File);
            if (Texture)
            {
                FSlateBrush& Brush = VillageIcons.Add(ArtworkId);
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
    const bool Done=P.IsComplete(Conversation.Get());
    const bool Upgrade=Selected==TEXT("high_wall");
    const bool Available=P.IsAvailable(Conversation.Get());
    const bool Pending=Conversation.IsValid()&&Conversation->IsPending();
    const bool LegacyPlan=!Done&&Conversation.IsValid()&&Conversation->PlanUnlocked(Selected);
    const int32 Completed=CompletedProjectCount(Conversation.Get()),Total=Projects().Num()-1;
    const FSlateBrush* Artwork = VillageIcons.Find(P.ArtworkId());
    TSharedRef<SWidget> Icon = Artwork
        ? StaticCastSharedRef<SWidget>(SNew(SImage).Image(Artwork))
        : StaticCastSharedRef<SWidget>(SNew(SBorder).BorderImage(&TreeStyle.GlyphBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [ColdSteelTreePanel::Label(P.Glyph,36,Done||Root?HUDGoldLight:TextPrimary,true)]);
    const TCHAR* ProgressNote = Root ? TEXT("选择下方的村庄建设项目。") :
        Upgrade ? (Done ? TEXT("本世界的石砌高墙已落成。") : Available ? TEXT("围墙已修复，可以提升城防。") : TEXT("完成上一级围墙修复后可升级城防。")) :
        Selected==TEXT("bakery")&&!Done ? (Available ? TEXT("磨坊已恢复供粉，可以修复面包屋。") : TEXT("先在村庄建设树中修复风车磨坊。")) :
        Selected==TEXT("gunshop")&&!Done ? (Available ? TEXT("铁匠铺已恢复营业，可以修复南侧的枪店。") : TEXT("先在村庄建设树中重建铁匠铺。")) :
        Selected==VillageBuildDefense::MechanicsPlan ? (Done ? TEXT("马厩对面的机械工坊已落成。") : Available ? TEXT("工坊用地已规划，可研究守备机械。") : TEXT("完成「防御工事」后可研究守备机械。")) :
        P.bResearchOnly ? (Done ? TEXT("全村共享工坊旁的赠塔，玩家可继续建造高塔。") : Available ? TEXT("高墙已建成，可研究塔楼。") : TEXT("完成「升级高墙」后可研究塔楼。")) :
        Done ? TEXT("建筑已恢复，再次进入这个世界时会保留建设成果。") : TEXT("解锁后立即替换场景中的建筑，不消耗资源。");
    auto Body=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[ColdSteelTreePanel::DetailHead(TreeStyle,Icon,P.Branch+TEXT(" · ")+(Root?TEXT("根基"):Selected==VillageBuildDefense::MechanicsPlan?TEXT("城防 IV"):P.bResearchOnly?TEXT("城防 III"):Upgrade?TEXT("城防 II"):Selected==TEXT("wall")?TEXT("城防 I"):!P.Prerequisite.IsNone()?TEXT("修复 II"):TEXT("初级 I")),P.Name,TEXT("永久建设"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,18,0,0)[ColdSteelTreePanel::Label(P.Description,14,TextSecondary,false,true)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,22,0,0)[ColdSteelTreePanel::Progress(TreeStyle,
            Root?TEXT("村庄复兴进度"):P.StateLabel(Done,Available),Root?FString::Printf(TEXT("%d / %d 项"),Completed,Total):Done?TEXT("1 / 1 项"):Available?TEXT("1 / 1 项条件"):TEXT("0 / 1 项条件"),
            ProgressNote,Root?float(Completed)/Total:(Done||Available)?1.f:0.f,Done?HUDGoldLight:TextPrimary,Done||Root?HUDGold:Accent)];
    const FString ConditionText=Root?TEXT("村庄共同起点，所有建设路线共用"):
        !P.Prerequisite.IsNone()?Project(P.Prerequisite).Name+(Available?TEXT(" · 已完成"):TEXT(" · 待完成")):
        Selected==TEXT("windmill")?TEXT("村庄复兴 · 已开启，修复材料消耗为 0"):TEXT("村庄复兴 · 已开启，无额外等级或资源要求");
    auto Conditions=SNew(SBorder).BorderImage(Available?&TreeStyle.RowMetBrush:&TreeStyle.RowBrush).Padding(FMargin(12,9))
        [ColdSteelTreePanel::Label(ConditionText,14,TextSecondary,false,true)];
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("解锁条件"),Root?TEXT("起点"):Available?TEXT("1 / 1"):TEXT("0 / 1"),Conditions)];
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("建设效果"),TEXT("永久"),ColdSteelTreePanel::Label(P.Result,14,TextSecondary,false,true))];
    if(Projects().ContainsByPredicate([this](const FProject& Child){return Child.Id!=TEXT("village")&&Child.Parent()==Selected;}))
    {
        auto Children=SNew(SVerticalBox);
        int32 ChildCount=0;
        for(const auto& Child:Projects())
        {
            if(Child.Id==TEXT("village")||Child.Parent()!=Selected)continue;
            ++ChildCount;
            const FName Id=Child.Id;const bool Complete=Child.IsComplete(Conversation.Get());
            const FSlateBrush* ChildArtwork=VillageIcons.Find(Child.ArtworkId());
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
                            [ColdSteelTreePanel::Label(Child.StateLabel(Complete,Child.IsAvailable(Conversation.Get())),12,Complete?HUDGoldLight:TextPrimary)]]]]];
        }
        Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("后续建设"),FString::Printf(TEXT("%d 项"),ChildCount),Children)];
    }
    Body->AddSlot().AutoHeight().Padding(0,32,0,0)[ColdSteelTreePanel::Section(TEXT("村庄进度"),TEXT("联机共享"),
        ColdSteelTreePanel::Label(TEXT("建筑修复与村庄修建权限保存于当前世界，所有玩家共享。"),14,TextSecondary,false,true))];
    const FName Id=Selected;
    const FString ActionText = Root ? TEXT("请选择建设节点") :
        Upgrade ? (Done ? TEXT("已升级高墙") : !Available ? TEXT("需要先修复城墙") : Pending ? TEXT("正在升级…") : TEXT("升级高墙")) :
        !Done&&!Available ? P.StateLabel(false,false) :
        P.bResearchOnly ? (Done ? TEXT("已解锁")+P.Name : Pending ? FString(TEXT("正在解锁…")) : TEXT("解锁")+P.Name) :
        Done ? TEXT("已完成修复") : Pending ? TEXT("正在修复…") : LegacyPlan ? TEXT("立即修复") : TEXT("解锁并修复");
    auto Actions=ColdSteelTreePanel::Action(ActionText,
        &TreeStyle.Primary,!Root&&Available&&!Done&&!Pending&&Conversation.IsValid(),[this,Id]{if(Conversation.IsValid())Conversation->RequestAction(Id);},Gray(20),true);
    auto Note=SNew(STextBlock).Font(TextFont(12*.75f)).AutoWrapText(true).LineHeightPercentage(1.3f)
        .ColorAndOpacity_Lambda([this,Id]{return FSlateColor(Conversation.IsValid()&&!Conversation->NunActionMessage(Id).IsEmpty()?HUDGoldLight:TextTertiary);})
        .Text_Lambda([this,Id,Root,Done,Available,Upgrade,bResearchOnly=P.bResearchOnly]
        {
            if(Conversation.IsValid()&&!Conversation->NunActionMessage(Id).IsEmpty())return FText::FromString(Conversation->NunActionMessage(Id));
            if(bResearchOnly)return FText::GetEmpty();
            if(Upgrade)
            {
                if(!Available||Done)return FText::GetEmpty();
                return FText::FromString(TEXT("请先让人员和动物离开墙边和村门通道。"));
            }
            return FText::FromString(Root?TEXT("选择要完成的建设项目"):Done?TEXT("建设已完成，无需重复解锁"):TEXT("请让人员和动物离开施工区域，再确认修复"));
        });
    return ColdSteelTreePanel::DetailPage(Body,Actions,Note);
}
