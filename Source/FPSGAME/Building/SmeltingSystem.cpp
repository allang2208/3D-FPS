#include "SmeltingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    /** UTC ticks → 秒。冶炼按真实世界时间推进（关闭游戏也计入），燃料决定能烧多少。 */
    constexpr double TicksToSeconds=1.0/static_cast<double>(ETimespan::TicksPerSecond);

    int64 NowTicks(){return FDateTime::UtcNow().GetTicks();}
}

void UColdSteelSmeltingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    // 与 items.json 同一口径：只在进程启动时读一次，改表要重启（无热重载）。
    FString Json;
    const FString Path=FPaths::ProjectContentDir()/TEXT("ColdSteelData/smelting-recipes.json");
    if(!FFileHelper::LoadFileToString(Json,*Path))
    {UE_LOG(LogTemp,Warning,TEXT("Smelting: recipe catalog missing at %s"),*Path);return;}
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root.IsValid())
    {UE_LOG(LogTemp,Error,TEXT("Smelting: recipe catalog is not valid JSON: %s"),*Path);return;}
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Root->TryGetArrayField(TEXT("recipes"),Rows))
    {UE_LOG(LogTemp,Error,TEXT("Smelting: recipe catalog has no \"recipes\" array: %s"),*Path);return;}
    for(const TSharedPtr<FJsonValue>& Row:*Rows)
    {
        const TSharedPtr<FJsonObject>* O=nullptr;
        if(!Row->TryGetObject(O)||!O||!O->IsValid())continue;
        const FJsonObject& E=**O;
        FColdSteelSmeltingRecipe R;
        FString Id;E.TryGetStringField(TEXT("id"),Id);R.Id=FName(*Id);
        const TSharedPtr<FJsonObject>* In=nullptr,*Out=nullptr;
        if(E.TryGetObjectField(TEXT("input"),In)&&In&&In->IsValid())
        {
            (*In)->TryGetStringField(TEXT("item"),R.Input);
            double N=1.0;(*In)->TryGetNumberField(TEXT("count"),N);R.InputCount=FMath::Max<int64>(1,FMath::RoundToInt64(N));
        }
        if(E.TryGetObjectField(TEXT("output"),Out)&&Out&&Out->IsValid())
        {
            (*Out)->TryGetStringField(TEXT("item"),R.Output);
            double N=1.0;(*Out)->TryGetNumberField(TEXT("count"),N);R.OutputCount=FMath::Max<int64>(1,FMath::RoundToInt64(N));
        }
        E.TryGetNumberField(TEXT("seconds"),R.Seconds);
        // 坏行逐条跳过并点名（与存档"跳过坏记录不整废"同一口径）；重复 id 只留第一条。
        if(R.Id.IsNone()||R.Input.IsEmpty()||R.Output.IsEmpty()||R.Seconds<=0.0
            ||Recipes.ContainsByPredicate([&R](const FColdSteelSmeltingRecipe& X){return X.Id==R.Id;}))
        {UE_LOG(LogTemp,Warning,TEXT("Smelting: skipped malformed/duplicate recipe row: %s"),*Id);continue;}
        Recipes.Add(MoveTemp(R));
    }
    // 顶层 "fuel" 对象：缺省即 wood/60s/600s（10 分钟）；字段坏一条回退默认并点名（面板与结算不判空）。
    const TSharedPtr<FJsonObject>* FuelObj=nullptr;
    if(Root->TryGetObjectField(TEXT("fuel"),FuelObj)&&FuelObj&&FuelObj->IsValid())
    {
        FString Item;(*FuelObj)->TryGetStringField(TEXT("item"),Item);
        double Seconds=Fuel.SecondsPerUnit,Capacity=Fuel.Capacity;
        (*FuelObj)->TryGetNumberField(TEXT("secondsPerUnit"),Seconds);
        (*FuelObj)->TryGetNumberField(TEXT("capacity"),Capacity);
        if(Item.IsEmpty()||Seconds<=0.0||Capacity<=0.0)
        {UE_LOG(LogTemp,Warning,TEXT("Smelting: malformed \"fuel\" block in %s, defaults kept"),*Path);}   // UE_LOG 带 if 结构，else 分支两侧必须加花括号
        else
        {
            Fuel.Item=MoveTemp(Item);
            Fuel.SecondsPerUnit=Seconds;
            // 上限至少装得下一件燃料，否则"添加燃料"永远按不下。
            Fuel.Capacity=FMath::Max(Capacity,Seconds);
        }
    }
    UE_LOG(LogTemp,Display,TEXT("Smelting: loaded %d recipe(s) from smelting-recipes.json, fuel=%s %.1fs/unit cap %.1fs"),
        Recipes.Num(),*Fuel.Item,Fuel.SecondsPerUnit,Fuel.Capacity);
}

const FColdSteelSmeltingRecipe* UColdSteelSmeltingSystem::Find(FName Id) const
{
    return Recipes.FindByPredicate([Id](const FColdSteelSmeltingRecipe& R){return R.Id==Id;});
}

UColdSteelStatusModel* UColdSteelSmeltingSystem::Model() const
{
    return GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}

double UColdSteelSmeltingSystem::SpeedMultiplier(int32 Level)
{   return 1.0+.25*(FMath::Clamp(Level,1,VoxelFurnaceMaxLevel)-1);   }

int64 UColdSteelSmeltingSystem::UpgradeCostFor(int32 Level)
{
    // 从 Lv.N 升上去恒为 10×N；满级判定由调用方按轴封顶（VoxelFurnaceAxisMax：燃料仓 6 档）。
    // 以前这里写死 VoxelFurnaceMaxLevel(5) 归零，燃料仓 Lv5→6 那一次会被算成 0 锭（2026-09-24 回头审查发现）。
    return 10*FMath::Max<int64>(1,Level);
}

double UColdSteelSmeltingSystem::FurnaceCapacity(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    const int32 L=IsValid(World)?World->FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisFuelCapacity):1;
    return Fuel.Capacity*L;   // 2026-09-24 数值调参：初始 10 分钟，每级 +10 分钟，Lv6＝60 分钟
}

double UColdSteelSmeltingSystem::JobTotalSeconds(const AVoxelBuildWorld* World,const FVoxelSmeltingJob& Job,
    const FColdSteelSmeltingRecipe& R) const
{
    // 批量与等级都只进分母/分子这一个口径：结算、进度条、剩余时间不会再各算各的。
    const double Mul=IsValid(World)?SpeedMultiplier(World->FurnaceLevel(Job.Cell)):1.0;
    return FMath::Max(.001,R.Seconds*FMath::Max<int64>(1,Job.BatchCount)/Mul);
}

bool UColdSteelSmeltingSystem::SettleFurnace(AVoxelBuildWorld* World,FIntVector Cell)
{
    if(!IsValid(World))return false;
    FVoxelSmeltingJob* Job=World->FindSmeltingMutable(Cell);
    const FColdSteelSmeltingRecipe* R=Job?Find(Job->Recipe):nullptr;
    bool bDirty=false;
    double FuelSeconds=World->FuelAt(Cell);   // 局部名避开成员 Fuel（FColdSteelSmeltingFuel）
    const int64 Now=NowTicks();
    bool bJobBurning=false;
    if(Job&&R)
    {
        const double Total=JobTotalSeconds(World,*Job,*R);
        if(Job->BurnStartTicks>0)
        {
            if(Job->BurnStartTicks>Now){Job->BurnStartTicks=0;bDirty=true;}   // UTC 回拨保护：冻结本段
            else
            {
                const double Elapsed=static_cast<double>(Now-Job->BurnStartTicks)*TicksToSeconds;
                const double Need=FMath::Max(0.0,Total-Job->ProgressSeconds);
                const double Burn=FMath::Min(FMath::Min(Elapsed,Need),FuelSeconds);
                if(Burn>0){Job->ProgressSeconds+=Burn;FuelSeconds-=Burn;bDirty=true;}
                // 段被燃料或配方封顶 → 段终（停燃）。整段烧完则必须把段起点推到 Now：
                // LiveProgress 是在 ProgressSeconds 之上再加 (Now-BurnStart)，落账后不推进
                // 会把同一段挂钟计两次——20 秒配方 10 秒就"完成"（2026-09-24 用户实测）。
                if(Burn<Elapsed){Job->BurnStartTicks=0;bDirty=true;}
                else if(Burn>0){Job->BurnStartTicks=Now;bDirty=true;}
            }
        }
        // 有料未燃且配方未完（刚添燃料、刚起炉或读档续燃）：开新燃烧段。
        if(Job->BurnStartTicks==0&&FuelSeconds>0&&Job->ProgressSeconds<Total)
        {Job->BurnStartTicks=Now;bDirty=true;}
        bJobBurning=Job->BurnStartTicks>0;   // 本拍起任务段在烧料（进度与存料 1:1，上面已扣）
    }
    // —— 空闲火种（2026-09-24 用户截图定稿："存料 10 秒"挂机不动＝不对；炉内有料就随挂钟
    // 持续燃烧，没矿也烧，烧完即熄）。任务在烧时料已被任务段扣掉，这里只把火种戳钉到
    // Now 防止任务结束后把任务时段重复扣一遍；无任务/完成/配方下架时才独立扣料。——
    if(FuelSeconds>0)
    {
        const int64 Fire=World->FurnaceFireTicks(Cell);
        if(bJobBurning){ if(Fire!=Now)World->SetFurnaceFireTicks(Cell,Now); }
        else if(Fire<=0||Fire>Now){World->SetFurnaceFireTicks(Cell,Now);}   // 起燃/回拨重钉：本拍起算
        else
        {
            const double Burn=FMath::Min(static_cast<double>(Now-Fire)*TicksToSeconds,FuelSeconds);
            if(Burn>0){FuelSeconds-=Burn;bDirty=true;}
            World->SetFurnaceFireTicks(Cell,FuelSeconds>0?Now:0);           // 烧尽即熄
        }
    }
    else if(World->FurnaceFireTicks(Cell)!=0)World->SetFurnaceFireTicks(Cell,0);
    World->SetFuel(Cell,FuelSeconds);   // SetFuel 值未变自动跳过标脏；清零时随等级决定留档/删条
    if(bDirty)World->MarkSmeltingDirty();
    return bDirty;
}

double UColdSteelSmeltingSystem::LiveProgress(const AVoxelBuildWorld* World,FIntVector Cell,
    const FColdSteelSmeltingRecipe*& OutRecipe) const
{
    OutRecipe=nullptr;
    if(!IsValid(World))return -1.0;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    if(!Job)return -1.0;
    const FColdSteelSmeltingRecipe* R=Find(Job->Recipe);
    if(!R)return -1.0;
    OutRecipe=R;
    const double Total=JobTotalSeconds(World,*Job,*R);
    double P=FMath::Clamp(Job->ProgressSeconds,0.0,Total);
    if(Job->BurnStartTicks>0)
    {
        const int64 Now=NowTicks();
        if(Now>Job->BurnStartTicks)
        {
            const double Elapsed=static_cast<double>(Now-Job->BurnStartTicks)*TicksToSeconds;
            const double Need=FMath::Max(0.0,Total-P);
            P+=FMath::Min(FMath::Min(Elapsed,Need),FMath::Max(0.0,World->FuelAt(Cell)));
        }
    }
    return P;
}

float UColdSteelSmeltingSystem::Progress(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    const FColdSteelSmeltingRecipe* R=nullptr;
    const double P=LiveProgress(World,Cell,R);
    if(P<0.0||!R||R->Seconds<=0.0)return 0.f;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    return FMath::Clamp(static_cast<float>(P/JobTotalSeconds(World,*Job,*R)),0.f,1.f);
}

bool UColdSteelSmeltingSystem::IsDone(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    const FColdSteelSmeltingRecipe* R=nullptr;
    const double P=LiveProgress(World,Cell,R);
    if(P<0.0||!R)return false;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    return P>=JobTotalSeconds(World,*Job,*R)-KINDA_SMALL_NUMBER;
}

bool UColdSteelSmeltingSystem::IsBurning(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    if(!IsValid(World))return false;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    return Job&&Job->BurnStartTicks>0&&World->FuelAt(Cell)>0&&!IsDone(World,Cell);
}

double UColdSteelSmeltingSystem::RemainingSeconds(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    const FColdSteelSmeltingRecipe* R=nullptr;
    const double P=LiveProgress(World,Cell,R);
    if(P<0.0||!R)return 0.0;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    return FMath::Max(0.0,JobTotalSeconds(World,*Job,*R)-P);
}

bool UColdSteelSmeltingSystem::BeginSmelting(AVoxelBuildWorld* World,FIntVector Cell,FName Recipe,FString& Reason,int64 Batch)
{
    if(!IsValid(World)){Reason=TEXT("建筑世界未就绪");return false;}
    const FColdSteelSmeltingRecipe* R=Find(Recipe);
    if(!R){Reason=TEXT("该配方不存在");return false;}
    if(World->FindSmelting(Cell)){Reason=TEXT("这座高炉正在冶炼");return false;}
    if(World->FuelAt(Cell)<=0.0){Reason=TEXT("炉内没有燃料，先添加燃料");return false;}
    Batch=FMath::Clamp(Batch,1LL,FMath::Min<int64>(99,BatchCapFor(World->FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisBatch))));   // 面板按持有量夹，这里按批量轴封顶兜底
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model){Reason=TEXT("角色数据未就绪");return false;}
    // 全有或全无：不足时 ConsumeItem 不扣任何东西并给出"缺少 N（背包+仓库共 M）"文案。
    const int64 Ore=R->InputCount*Batch;
    if(!Model->ConsumeItem(R->Input,Ore,Reason))return false;
    FString StartReason;
    if(!World->BeginSmelting(Cell,Recipe,StartReason,Batch))
    {
        // 校验后仍失败（理论上只剩竞态）：把矿料原样退回，不留无主消耗。
        Model->AddItem(R->Input,Ore);
        Reason=StartReason;return false;
    }
    SettleFurnace(World,Cell);   // 起炉即起燃（存料>0 已由上面的门槛保证）
    return true;
}

bool UColdSteelSmeltingSystem::AddFuel(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason)
{
    if(!IsValid(World)){Reason=TEXT("建筑世界未就绪");return false;}
    if(!World->IsFurnaceAt(Cell)){Reason=TEXT("目标不是已放置的冶炼高炉");return false;}
    SettleFurnace(World,Cell);   // 先把挂钟落账，容量判定才准
    const double Stored=World->FuelAt(Cell);
    const double Cap=FurnaceCapacity(World,Cell);
    if(Stored+Fuel.SecondsPerUnit>Cap+1e-6)
    {Reason=FString::Printf(TEXT("燃料仓剩余不足（上限 %d 分钟）"),FMath::RoundToInt32(Cap/60.0));return false;}
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model){Reason=TEXT("角色数据未就绪");return false;}
    if(!Model->ConsumeItem(Fuel.Item,1,Reason))return false;
    World->SetFuel(Cell,Stored+Fuel.SecondsPerUnit);
    SettleFurnace(World,Cell);   // 停炉待燃的任务：添料瞬间续燃
    return true;
}

bool UColdSteelSmeltingSystem::CanAddFuel(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    if(!IsValid(World)||!World->IsFurnaceAt(Cell))return false;
    if(World->FuelAt(Cell)+Fuel.SecondsPerUnit>FurnaceCapacity(World,Cell)+1e-6)return false;
    auto* Model=this->Model();
    return Model&&Model->CountMaterial(Fuel.Item)>=1;
}

bool UColdSteelSmeltingSystem::CollectSmelting(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason)
{
    if(!IsValid(World)){Reason=TEXT("建筑世界未就绪");return false;}
    SettleFurnace(World,Cell);   // 取出前结算：挂钟能兑现的最后几秒不落空
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    if(!Job){Reason=TEXT("炉内没有矿料");return false;}
    const FColdSteelSmeltingRecipe* R=Find(Job->Recipe);
    if(!R){Reason=TEXT("配方已下架，炉内矿料无法结算");return false;}
    if(!IsDone(World,Cell)){Reason=TEXT("冶炼尚未完成");return false;}
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model){Reason=TEXT("角色数据未就绪");return false;}
    // 背包放不下就不清空任务：产物留在炉内，整理背包后可重试（不静默丢件）。
    if(!Model->AddItem(R->Output,R->OutputCount*FMath::Max<int64>(1,Job->BatchCount))){Reason=TEXT("背包放不下，先整理背包");return false;}
    World->ClearSmelting(Cell);   // 存料留在炉里：下一批直接开炉
    return true;
}

bool UColdSteelSmeltingSystem::RefundForTeardown(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason)
{
    if(!IsValid(World)){Reason=TEXT("建筑世界未就绪");return false;}
    SettleFurnace(World,Cell);
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    const double Stored=World->FuelAt(Cell);
    if(!Job&&Stored<=0.0)return true;   // 炉内本就没有矿料和存料，拆除照常。
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model){Reason=TEXT("角色数据未就绪");return false;}
    const FColdSteelSmeltingRecipe* R=Job?Find(Job->Recipe):nullptr;
    // 存料按整件折回木材（不足一件的零头随炉损失——封顶整数件，口径与投入一致）。
    const int64 WoodUnits=FMath::FloorToInt(Stored/Fuel.SecondsPerUnit);
    const int64 Batch=Job?FMath::Max<int64>(1,Job->BatchCount):1;
    TArray<TPair<FString,int64>> Gives;
    if(Job&&R)
    {
        const bool bDone=IsDone(World,Cell);
        Gives.Add({bDone?R->Output:R->Input,(bDone?R->OutputCount:R->InputCount)*Batch});
    }
    else if(Job&&!R)UE_LOG(LogTemp,Warning,TEXT("Smelting teardown: recipe %s removed, ore lost @格(%d,%d,%d)"),
        *Job->Recipe.ToString(),Cell.X,Cell.Y,Cell.Z);   // 配方下架：矿料无法折算，只退燃料（不留卡死的炉子）
    if(WoodUnits>0)Gives.Add({Fuel.Item,WoodUnits});
    auto Probe=Model->Snapshot();
    for(const auto& Give:Gives)if(!ColdSteelInventory::Insert(Probe.Items,Model->CreateItem(Give.Key,Give.Value)))
    {Reason=TEXT("炉内有物料，背包放不下退料");return false;}
    int32 Given=0;
    for(;Given<Gives.Num();++Given)if(!Model->AddItem(Gives[Given].Key,Gives[Given].Value))break;
    if(Given<Gives.Num())
    {
        bool bRolledBack=true;
        for(int32 i=0;i<Given;++i){FString Rollback;if(!Model->ConsumeItem(Gives[i].Key,Gives[i].Value,Rollback))bRolledBack=false;}
        if(!bRolledBack)UE_LOG(LogTemp,Error,TEXT("Smelting teardown rollback failed @格(%d,%d,%d)"),Cell.X,Cell.Y,Cell.Z);
        Reason=TEXT("炉内有物料，背包放不下退料");
        return false;
    }
    World->ClearSmelting(Cell);
    World->SetFuel(Cell,0);
    return true;
}

bool UColdSteelSmeltingSystem::UpgradeFurnace(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason,int32 Axis)
{
    if(!IsValid(World)){Reason=TEXT("建筑世界未就绪");return false;}
    if(!World->IsFurnaceAt(Cell)){Reason=TEXT("目标不是已放置的冶炼高炉");return false;}
    const int32 Level=World->FurnaceUpgradeLevel(Cell,Axis);
    if(Level>=VoxelFurnaceAxisMax(Axis)){Reason=TEXT("这座高炉已满级");return false;}
    const int64 Cost=UpgradeCostFor(Level);
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model){Reason=TEXT("角色数据未就绪");return false;}
    if(!Model->ConsumeItem(TEXT("ironIngot"),Cost,Reason))return false;   // 全有或全无，与投料同口径
    World->SetFurnaceUpgradeLevel(Cell,Axis,Level+1);
    SettleFurnace(World,Cell);   // 速度轴：在炼任务的剩余秒数按新倍率即时缩短；其余轴顺带落账
    return true;
}

bool UColdSteelSmeltingSystem::CanUpgrade(const AVoxelBuildWorld* World,FIntVector Cell,int32 Axis) const
{
    if(!IsValid(World)||!World->IsFurnaceAt(Cell))return false;
    const int32 Level=World->FurnaceUpgradeLevel(Cell,Axis);
    if(Level>=VoxelFurnaceAxisMax(Axis))return false;
    auto* Model=this->Model();
    return Model&&Model->CountMaterial(TEXT("ironIngot"))>=UpgradeCostFor(Level);
}
