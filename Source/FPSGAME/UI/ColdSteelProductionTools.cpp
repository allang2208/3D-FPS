#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../Production/ProductionTreeFallPlan.h"
#include "../Production/ProductionTreeHealth.h"
#include "../FPSGAMECharacter.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::LoadProductionDefinitions()
{
    FString Json; TSharedPtr<FJsonObject> Root;
    if (FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/production_tools.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))
        for (const auto& Pair : Root->Values)
        {
            FString Data;
            FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(), TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));
            Definitions.Add(FString(*Pair.Key), Data);
        }
}

const FColdSteelItem* UColdSteelStatusModel::ActiveProductionTool() const
{
    // Only the shovel overrides the selected weapon from the backpack. Axe and
    // pickaxe are held through the active main-hand equipment slot.
    const auto* Override = FindItem(Current.ActiveProductionTool);
    if(Override && !ColdSteelInventory::IsEquippedProductionTool(*Override) && Override->Place==0 &&
        ColdSteelInventory::Text(*Override,TEXT("category"))==TEXT("tool"))return Override;
    const auto* Item=Equipped();
    return Item && ColdSteelInventory::IsEquippedProductionTool(*Item) ? Item : nullptr;
}

void UColdSteelStatusModel::NormalizeProductionState(FColdSteelProfile& P) const
{
    for(auto& I:P.Items)if(I.Place!=2)I.HarvestWorldId.Invalidate();
    // Refresh presentation, equipment, combat tuning and both tools' phase clocks; saved identity,
    // placement and harvesting progress stay intact.
    for(auto& I:P.Items)
    {
        if(I.Definition!=TEXT("tool_axe")&&I.Definition!=TEXT("tool_pickaxe"))continue;
        const FString* Definition=Definitions.Find(I.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> SavedData,VisualData;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),SavedData)||
           !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),VisualData))continue;
        bool Changed=false;
        for(const TCHAR* Key:{TEXT("tool_mesh"),TEXT("tool_scale"),TEXT("mount_pitch"),TEXT("mount_yaw"),TEXT("mount_roll"),
            TEXT("tool_viewmodel"),TEXT("tool_animation_prefix"),TEXT("tool_swing_sound"),
            TEXT("swing_seconds"),TEXT("contact_seconds"),TEXT("desc"),TEXT("melee_damage"),
            TEXT("combat_reach_cm"),TEXT("combat_sweep_radius_cm"),TEXT("harvest_reach_cm"),TEXT("harvest_sweep_radius_cm"),
            TEXT("grid_w"),TEXT("grid_h"),TEXT("ue_icon"),TEXT("weaponType"),TEXT("weaponTypeTag"),TEXT("equipSlot"),TEXT("isTwoHanded")})
        {
            const auto* Value=VisualData->Values.Find(Key);if(!Value)continue;
            const auto* OldValue=SavedData->Values.Find(Key);
            if(OldValue&&FJsonValue::CompareEqual(**OldValue,**Value))continue;
            SavedData->SetField(Key,*Value);Changed=true;
        }
        if(Changed)
        {
            I.Data.Reset();
            FJsonSerializer::Serialize(SavedData.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
            // 2x3 -> 1x3 only shrinks in either orientation. Keep the saved cell and
            // explicit player rotation; new items use the upright default.
            if(I.Definition==TEXT("tool_axe"))ColdSteelInventory::ApplyOrientation(I,-1);
        }
        I.Magazine=0;I.Reserve=0;
    }
    const auto* Item = P.Items.FindByPredicate([&](const auto& I){return I.InstanceId == P.ActiveProductionTool && I.Place == 0;});
    // Discard legacy backpack selections without relocating either tool.
    if (!Item || ColdSteelInventory::IsEquippedProductionTool(*Item) || ColdSteelInventory::Text(*Item,TEXT("category")) != TEXT("tool")) P.ActiveProductionTool.Reset();
}

bool UColdSteelStatusModel::GrantProductionTools()
{
    if (Current.ProductionSupplyVersion >= 1) return true;
    SyncRuntime(); auto P = Snapshot();
    for (const FString& Id : {FString(TEXT("tool_axe")), FString(TEXT("tool_pickaxe")), FString(TEXT("tool_shovel"))})
    {
        if (P.Items.ContainsByPredicate([&](const auto& I){return I.Definition == Id && (I.Place == 0 || I.Place == 1 || I.Place == 4);})) continue;
        auto Item = CreateItem(Id);
        if (Item.Data.IsEmpty()) { Message=TEXT("生产工具目录未加载"); return false; }
        if (!ColdSteelInventory::Insert(P.Items, Item))
        {
            if (!ColdSteelWarehouse::Insert(P.Items,Item,WarehouseCapacity()))
            { Message=TEXT("背包和仓库空间不足，腾出空间后按 8 领取工具；伐木斧与矿镐需在背包装备"); return false; }
        }
    }
    P.ProductionSupplyVersion = 1;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::ToggleProductionTool(const FString& InstanceId)
{
    const auto* Item=FindItem(InstanceId);
    if(Item && ColdSteelInventory::IsEquippedProductionTool(*Item))
    {
        if(Item->Place!=1 || (Item->Cell!=6 && Item->Cell!=9))
        {Message=TEXT("请先在背包右键装备此工具，或将它拖入主手武器槽");return false;}
        return MoveItem(InstanceId,1,Item->Cell);
    }
    if (!Item || Item->Place != 0 || ColdSteelInventory::Text(*Item,TEXT("category")) != TEXT("tool")) return false;
    SyncRuntime(); auto P=Snapshot();
    P.ActiveProductionTool = P.ActiveProductionTool == InstanceId ? FString() : InstanceId;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::SelectProductionTool(const FString& Definition)
{
    auto ReportFailure=[this]()
    {
        if(CurrentPawn.IsValid())if(auto* Tools=CurrentPawn->FindComponentByClass<UProductionToolComponent>())Tools->ShowFeedback(Message);
        return false;
    };
    if(Definition==TEXT("tool_axe") || Definition==TEXT("tool_pickaxe"))
    {
        const auto* EquippedTool=Current.Items.FindByPredicate([&](const auto& I){return I.Definition==Definition && I.Place==1 && (I.Cell==6 || I.Cell==9);});
        if(!EquippedTool){Message=TEXT("请先在背包右键装备此工具，再用 G 或滚轮切换武器");return ReportFailure();}
        return ToggleProductionTool(EquippedTool->InstanceId) || ReportFailure();
    }
    if (!GrantProductionTools()) return ReportFailure();
    const auto* Item=Current.Items.FindByPredicate([&](const auto& I){return I.Definition==Definition && I.Place==0;});
    if (!Item) { Message=TEXT("请先从仓库取出工具放入背包"); return ReportFailure(); }
    if(!ToggleProductionTool(Item->InstanceId))return ReportFailure();
    return true;
}

bool UColdSteelStatusModel::StowProductionTool()
{
    if (Current.ActiveProductionTool.IsEmpty()) return false;
    SyncRuntime(); auto P=Snapshot(); P.ActiveProductionTool.Reset();
    return CommitState(MoveTemp(P));
}

int32 UColdSteelStatusModel::HarvestProgress(const FString& Id) const
{
    const int32 Hits=Current.HarvestProgress.FindRef(Id);
    return Hits>=FProductionResource::RequiredHits && HasTreeGrowth(Id) && IsTreeMature(Id) ? 0 : Hits;
}

/**
 * 树木剩余生命比例（2026-09-25）。
 *
 * 存档只存比例，不存绝对值：以后调树种生命、加 CVar 倍率或换树种配置，旧档的「砍了一半」
 * 仍然是砍了一半，既不需要迁移遍历，也不会因为上限变化把半血的树读成满血或濒死。
 * 旧档（只有累计命中 1..3 的 `HarvestProgress`）在这里按同一进度换算，读一次就够。
 *
 * 重生树（砍倒过、又长回来的树）同时有 `TreeGrowth` 与可能残留的 `TreeHealth`：
 * 读档比例优先，只有「比例 0 ＋ 已长成」才当作满血的新树，否则重生树会永远打不动。
 */
float UColdSteelStatusModel::TreeHealthRatio(const FString& Id) const
{
    const bool bRegrownMature=HasTreeGrowth(Id) && IsTreeMature(Id);
    // 有生命记录就以它为准。**这条必须在「成熟重生树＝满血」之前**：砍到一半的重生树如果被
    // 判成满血，每次挥砍都从满血重算、写回同一个数，界面永远不掉血、树永远不倒
    // （2026-09-25 实测：存档里 TreeGrowth 与 TreeHealth 同时有记录的树完全打不动）。
    if(const float* Ratio=Current.TreeHealth.Find(Id))
    {
        const float Stored=FMath::Clamp(*Ratio,0.f,1.f);
        // 只有被砍倒过（比例 0）且已经长成的重生树才读作满血：那是一次全新的树。
        return Stored<=0.f && bRegrownMature ? 1.f : Stored;
    }
    // 旧档（还没有生命记录）：成熟的重生树读作满血，其余按旧的累计命中换算一次。
    if(bRegrownMature)return 1.f;
    const int32 Hits=Current.HarvestProgress.FindRef(Id);
    return FMath::Clamp(1.f-float(Hits)/float(FMath::Max(1,FProductionResource::RequiredHits)),0.f,1.f);
}

/**
 * 岩块剩余生命比例（2026-09-30 与树木统一为伤害驱动）。
 * 存档只存比例（`RockHealth`），调岩块生命不会作废旧档；旧档没有生命记录时按旧的
 * 累计命中（1..3）换算一次，读档即得，不需要迁移遍历。岩块不重生、无成熟门禁。
 */
float UColdSteelStatusModel::RockHealthRatio(const FString& Id) const
{
    if(const float* Ratio=Current.RockHealth.Find(Id))return FMath::Clamp(*Ratio,0.f,1.f);
    const int32 Hits=Current.HarvestProgress.FindRef(Id);
    return FMath::Clamp(1.f-float(Hits)/float(FMath::Max(1,FProductionResource::RequiredHits)),0.f,1.f);
}

bool UColdSteelStatusModel::ResetHarvestProgress(const FString& Id)
{
    // Topsoil excavation digs one 20 cm layer per completed cycle, so the cell has to
    // become harvestable again; trees and rocks keep their single-depletion rule.
    if (Id.IsEmpty() || !Current.HarvestProgress.Contains(Id)) return false;
    SyncRuntime(); auto P=Snapshot();
    P.HarvestProgress.Remove(Id);
    return CommitState(MoveTemp(P));
}

namespace
{
/**
 * 砍倒瞬间登记生长记录（2026-09-28 起含桩/幼树分离的位置规则）：
 * - 树桩留在被砍那棵树当时站的位置（旧记录的 SaplingOffset），等玩家来劈；
 * - 下一棵幼树不在原桩位原地长回，而是在候选点附近随机偏移（半径 2.8–6.5 m）；
 *   随机流按 CandidateId+Generation 播种，最多重掷 5 次避开河岸带、陡坡与世界边缘，
 *   都避不开就用最后一次——宁可位置差一点，也不让幼树叠在树桩上。
 */
void RegisterTreeGrowth(FColdSteelProfile& P,const FProductionResource& Target)
{
    FColdSteelTreeGrowth Growth;
    Growth.CutAtDay=P.TreeGrowthDay;
    if(const auto* Biome=Target.World->Assets.Get())
    {
        Growth.DormantDays=FMath::Max(0.f,Biome->TreeDormantDays);
        Growth.MatureDays=FMath::Max(Growth.DormantDays+.1f,Biome->TreeMatureDays);
    }
    const FColdSteelTreeGrowth* Previous=P.TreeGrowth.Find(Target.Id);
    Growth.Generation=Previous?Previous->Generation+1:1;
    Growth.StumpOffset=Previous?Previous->SaplingOffset:FVector2D::ZeroVector;
    // 候选点基点 ＝ 被砍树位置 − 它自己的偏移；新偏移相对基点存放（世界的树桩/幼树
    // 重建都从候选点出发，只认这份相对偏移）。
    const FVector2D Base=FVector2D(Target.Transform.GetLocation())-Growth.StumpOffset;
    const uint32 SeedA=uint32(Target.CandidateId&0xffffffffu);
    const uint32 SeedB=uint32(Target.CandidateId>>32);
    FRandomStream Stream(int32(SeedA^(SeedB*0x2545F491u)^(uint32(Growth.Generation)*747796405u)));
    FVector2D Offset=FVector2D::ZeroVector;
    if(const auto* World=Target.World.Get())
    {
        const double Half=World->SizeMeters*50-1000;
        for(int32 Attempt=0;Attempt<5;++Attempt)
        {
            const double Angle=Stream.FRandRange(0.f,float(2*PI));
            const double Radius=Stream.FRandRange(280.f,650.f);
            Offset=FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*Radius;
            const double X=Base.X+Offset.X,Y=Base.Y+Offset.Y;
            if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)continue;
            if(World->SurfaceNormal(X,Y).Z<.87)continue;
            if(World->SampleRiver(X,Y).Bank>.02)continue;
            break;
        }
    }
    Growth.SaplingOffset=Offset;
    P.TreeGrowth.Add(Target.Id,MoveTemp(Growth));
}
}

bool UColdSteelStatusModel::CommitHarvestStrike(const FProductionResource& Target, bool& Depleted)
{
    Depleted=false;
    const auto* Tool=ActiveProductionTool();
    if (!Target.World.IsValid() || Target.Id.IsEmpty() || !Tool) return false;
    // 幼树成熟门禁只约束整树目标；树桩是独立目标，任何时候都能劈（2026-09-28）。
    if(Target.Layer==0 && !Target.bStump && HasTreeGrowth(Target.Id) && !IsTreeMature(Target.Id))
    { Message=TEXT("树木正在生长，成熟后才能再次砍伐");return false; }
    if (ColdSteelInventory::Text(*Tool,TEXT("tool_kind")) != Target.RequiredTool)
    { Message=TEXT("工具类型不匹配"); return false; }
    // 改造实值在本次挥动里求一次：产出倍率与额外产出几率共用同一份，
    // 避免提示栏、结算与落地各自换算出不同结果。
    const FProductionToolStats ToolStats=ColdSteelTool::Evaluate(*Tool,this);
    // 树桩走自己的结算（扣 StumpHealthRatio，劈尽掉一块木材，不触树倒）。
    if(Target.bStump)return CommitStumpStrike(Target,ToolStats,Depleted);
    // 树木与岩块都走生命值口径（2026-09-30 岩块统一）：一次挥砍按采集伤害扣血，
    // 归零的那一挥才倒下／破碎。表土保持「一挥一层」的固定挖掘。
    if(Target.Layer==0 && Target.MaxHealth>0.)return CommitTreeStrike(Target,ToolStats,Depleted);
    if(Target.Layer==1 && Target.MaxHealth>0.)return CommitRockStrike(Target,ToolStats,Depleted);
    // 表土挖掘：每挥固定挖一层，掉落直接进背包；挖层计数保留给挖掘循环的复位合同。
    // 上一层的挖掘循环还没复位（含已到下挖上限、复位被跳过）前不可再挖——与旧口径一致，
    // 否则会在下挖上限处陷入「发放→回收」的死循环。
    if(Target.Layer!=2){Message=TEXT("此处资源暂时无法采集");return false;}
    if(HarvestProgress(Target.Id)>=1){Message=TEXT("此处资源已经采尽");return false;}
    SyncRuntime(); auto P=Snapshot();
    TArray<FString> Drops;
    for (const auto& Reward : Target.Rewards)
    {
        const auto Item=CreateItem(Reward.Key,ColdSteelTool::Yield(Reward.Value,ToolStats));
        if (Item.Data.IsEmpty() || !ColdSteelInventory::Insert(P.Items,Item))
        { Message=TEXT("背包空间不足，资源保留；整理后继续采集"); return false; }
    }
    P.HarvestProgress.Add(Target.Id,1);
    // Depletion and every ground pickup are one profile transaction, before visuals.
    if (!CommitState(MoveTemp(P))) return false;
    Depleted=true;
    Message=TEXT("表土已采集，材料收入背包");
    return true;
}

/**
 * 树木结算：像怪物一样按生命值扣血（2026-09-25）。
 *
 * 一次挥砍的伐木伤害来自工具自己的实值快照（`ProductionTreeHealth::StrikeDamage`），
 * 生命值没归零就只提交进度、不产材料、不倒树；归零的那一挥才走原来的倒树事务：
 * 先确认倒树资产就绪，再把生命记录、采尽命中数与掉落放进**同一次** `CommitState`。
 *
 * 明确不做的事：不给树加 Actor、Tick、血条控件或每帧查询；不加暴击与随机浮动，
 * 提示栏的「还需 N 挥」就是真实挥砍数。
 */
bool UColdSteelStatusModel::CommitTreeStrike(const FProductionResource& Target,const FProductionToolStats& ToolStats,bool& Depleted)
{
    Depleted=false;
    const double Damage=ProductionTreeHealth::StrikeDamage(ToolStats);
    const float Before=FMath::Clamp(TreeHealthRatio(Target.Id),0.f,1.f);
    if(Before<=0.f){Message=TEXT("此处资源已经采尽");return false;}
    const double Remaining=double(Before)*Target.MaxHealth-Damage;
    SyncRuntime(); auto P=Snapshot();
    if(Remaining>0.)
    {
        P.TreeHealth.Add(Target.Id,float(Remaining/Target.MaxHealth));
        if(!CommitState(MoveTemp(P)))return false;
        Message=FString::Printf(TEXT("%s  %d / %d · 还需 %d 挥"),*Target.Name,FMath::CeilToInt(Remaining),
            FMath::CeilToInt(Target.MaxHealth),ProductionTreeHealth::SwingsToFell(Remaining,Damage));
        return true;
    }
    // 致命一击：资产未就绪时这一挥不扣血（先确认资源就绪，避免先扣进度却生不出倒树）。
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if(!Harvest){Message=TEXT("当前世界无法生成采集物");return false;}
    Harvest->Prepare(true);
    Harvest->PrepareFall(Target);
    if(!Harvest->ReadyFall(Target)){Message=TEXT("正在准备倒树模型，稍后再挥动一次");return false;}
    if(!Harvest->Ready(true)){Message=TEXT("正在准备采集物模型，稍后再挥动一次");return false;}
    TArray<FString> Drops;
    if(!StageProductionDrops(P,Target,Drops,ToolStats))return false;
    // 生命归零与采尽命中数一起写：世界的 IsProductionDepleted、树桩重建与 PCG 补生
    // 仍按命中数口径读 HarvestProgress，树木成长期的 TreeGrowth 也照旧登记。
    P.TreeHealth.Add(Target.Id,0.f);
    P.HarvestProgress.Add(Target.Id,FProductionResource::RequiredHits);
    RegisterTreeGrowth(P,Target);
    // Depletion and every ground pickup are one profile transaction, before visuals.
    if(!CommitState(MoveTemp(P)))return false;
    Depleted=true;
    if(!Drops.IsEmpty())Harvest->DelayDrops(Drops,FProductionTreeFallPlan::Make(Target).ReleaseSeconds());
    Message=TEXT("树木正在倒下，落地后对准木材按 E 拾取");
    return true;
}

/**
 * 岩块结算（2026-09-30 与树木统一为伤害驱动）：一次挥砍的采集伤害来自同一份实值快照
 * （`ProductionTreeHealth::StrikeDamage`，改造、附魔与角色物攻都已在里面），
 * 生命值没归零就只提交进度、不产材料；归零的那一挥才碎岩掉落。
 * 与树一样：不给岩块加 Actor、Tick、血条控件，不做暴击与随机浮动，
 * 提示栏的「还需 N 击」就是真实挥击数。
 */
bool UColdSteelStatusModel::CommitRockStrike(const FProductionResource& Target,const FProductionToolStats& ToolStats,bool& Depleted)
{
    Depleted=false;
    const double Damage=ProductionTreeHealth::StrikeDamage(ToolStats);
    const float Before=FMath::Clamp(RockHealthRatio(Target.Id),0.f,1.f);
    if(Before<=0.f){Message=TEXT("此处资源已经采尽");return false;}
    const double Remaining=double(Before)*Target.MaxHealth-Damage;
    SyncRuntime(); auto P=Snapshot();
    if(Remaining>0.)
    {
        P.RockHealth.Add(Target.Id,float(Remaining/Target.MaxHealth));
        if(!CommitState(MoveTemp(P)))return false;
        Message=FString::Printf(TEXT("%s  %d / %d · 还需 %d 击"),*Target.Name,FMath::CeilToInt(Remaining),
            FMath::CeilToInt(Target.MaxHealth),ProductionTreeHealth::SwingsToFell(Remaining,Damage));
        return true;
    }
    // 致命一击：资产未就绪时这一挥不扣血（先确认资源就绪，避免先扣进度却生不出碎岩）。
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if(!Harvest){Message=TEXT("当前世界无法生成采集物");return false;}
    Harvest->Prepare(false);
    if(!Harvest->Ready(false)){Message=TEXT("正在准备采集物模型，稍后再挥动一次");return false;}
    TArray<FString> Drops;
    if(!StageProductionDrops(P,Target,Drops,ToolStats))return false;
    // 生命归零与采尽标记一起写：世界的 IsProductionDepleted 已按 RockHealth 判采尽，
    // 采尽标记（HarvestProgress）保留给旧档兼容读取。
    P.RockHealth.Add(Target.Id,0.f);
    P.HarvestProgress.Add(Target.Id,FProductionResource::RequiredHits);
    if(!CommitState(MoveTemp(P)))return false;
    Depleted=true;
    if(!Drops.IsEmpty())Harvest->DelayDrops(Drops,.25f);
    Message=TEXT("岩石已破碎，对准石材或矿石按 E 拾取");
    return true;
}

/**
 * 树桩结算（2026-09-28 用户要求）：桩有自己的生命（同树立满生命的一半），斧头按伐木
 * 伤害扣 `StumpHealthRatio`；劈尽的那一挥在桩边掉一块木材并关闭桩记录（世界随即不再
 * 渲染该桩、收走碰撞）。不触树倒、不动幼树——同一候选点的幼树按自己的时钟继续长。
 */
bool UColdSteelStatusModel::CommitStumpStrike(const FProductionResource& Target,const FProductionToolStats& ToolStats,bool& Depleted)
{
    Depleted=false;
    const double Damage=ProductionTreeHealth::StrikeDamage(ToolStats);
    const float Before=FMath::Clamp(StumpHealthRatio(Target.Id),0.f,1.f);
    if(Before<=0.f){Message=TEXT("树桩已经劈开过了");return false;}
    SyncRuntime(); auto P=Snapshot();
    auto* Record=P.TreeGrowth.Find(Target.Id);
    if(!Record||Record->bStumpCleared){Message=TEXT("树桩已经劈开过了");return false;}
    const double Remaining=double(Before)*Target.MaxHealth-Damage;
    if(Remaining>0.)
    {
        Record->StumpHealthRatio=float(Remaining/Target.MaxHealth);
        if(!CommitState(MoveTemp(P)))return false;
        Message=FString::Printf(TEXT("%s  %d / %d · 还需 %d 挥"),*Target.Name,FMath::CeilToInt(Remaining),
            FMath::CeilToInt(Target.MaxHealth),ProductionTreeHealth::SwingsToFell(Remaining,Damage));
        return true;
    }
    // 劈开：一块木材落在桩边，桩记录关闭；掉落与关闭同一次存档事务。
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if(!Harvest){Message=TEXT("当前世界无法生成采集物");return false;}
    Harvest->Prepare(true);
    if(!Harvest->Ready(true)){Message=TEXT("正在准备采集物模型，稍后再挥动一次");return false;}
    TArray<FString> Drops;
    if(!StageProductionDrops(P,Target,Drops,ToolStats))return false;
    Record->bStumpCleared=true;
    Record->StumpHealthRatio=0.f;
    if(!CommitState(MoveTemp(P)))return false;
    Depleted=true;
    Harvest->DelayDrops(Drops,.3f);
    Message=TEXT("树桩劈开了，木材落在旁边，按 E 拾取");
    return true;
}
