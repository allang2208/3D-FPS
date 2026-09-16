// 2026-09-16: Z 键范围拾取、残骸转体素块、以及屏幕上方的通用提示栏。
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "../FPSGAMECharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

using namespace ColdSteelInventory;

namespace
{
    /** 玩家能迈过去的障碍高度：<= 40 cm 视为不阻挡（2026-09-16 用户指定）。 */
    constexpr float StepOverHeightCm=40.f;

    /**
     * 视线可达判定：从玩家胸口朝物品顶面画线。被打断时，只有阻挡点不高于玩家脚下 40 cm（能走/迈
     * 过去）才算通过；更高的东西（墙、隔层、箱子）就算阻挡。
     */
    bool ReachableOnFoot(const UWorld* World,const APawn* Pawn,const FVector& ItemPosition)
    {
        if(!World||!Pawn)return false;
        const UCapsuleComponent* Capsule=Pawn->FindComponentByClass<UCapsuleComponent>();
        const float HalfHeight=Capsule?Capsule->GetScaledCapsuleHalfHeight():88.f;
        const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,HalfHeight);
        const FVector Start=Feet+FVector(0,0,HalfHeight*.6f);
        const FVector End=ItemPosition+FVector(0,0,10.f);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAreaPickup),false,Pawn);
        TArray<FHitResult> Hits;
        World->LineTraceMultiByChannel(Hits,Start,End,ECC_Visibility,Query);
        for(const FHitResult& Hit:Hits)
        {
            if(!Hit.GetActor())continue;
            if(Hit.ImpactPoint.Z-Feet.Z<=StepOverHeightCm)continue;   // 能迈过去
            return false;
        }
        return true;
    }
}

void UColdSteelStatusModel::PostNotice(const FString& Title,const FString& Detail,const FString& Icon,float Duration)
{
    if(Title.IsEmpty())return;
    FColdSteelProgressNotice Notice;
    Notice.Title=Title;Notice.Detail=Detail;Notice.Icon=Icon;
    Notice.Duration=FMath::Max(.8f,Duration);
    ProgressNotices.Add(MoveTemp(Notice));
}

bool UColdSteelStatusModel::GrantWorldBlocks(const TMap<FString,int64>& Blocks,const FVector& Position)
{
    if(!GetWorld()||Blocks.IsEmpty())return false;
    if(!Definitions.Num())return false;
    SyncRuntime();auto P=Snapshot();
    if(P.Items.Num()>=10000){Message=TEXT("地面物品已达存档上限，残骸暂未转换");return false;}
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    int32 Created=0;int64 Total=0;
    for(const TPair<FString,int64>& Entry:Blocks)
    {
        if(Entry.Value<=0||!Definitions.Contains(Entry.Key))continue;
        auto Item=CreateItem(Entry.Key,Entry.Value);
        if(Item.Data.IsEmpty())continue;
        // A world drop the ordinary pickup path can collect: Place 2 and no harvest-world stamp, so
        // RefreshDrops owns the actor and E / Z can both take it.
        Item.Place=2;Item.Cell=-1;Item.BackpackCell=-1;Item.Map=Map;
        Item.Position=Position+FVector(0,0,12);
        Item.WorldRotation=FRotator(0,FMath::FRandRange(0.f,360.f),0);
        Total+=Entry.Value;P.Items.Add(MoveTemp(Item));++Created;
    }
    if(!Created){Message=TEXT("材料目录缺失，残骸未转换");return false;}
    if(!CommitState(P)){Message=TEXT("保存失败，残骸保留");return false;}
    RefreshDrops();
    Message=FString::Printf(TEXT("残骸已转成 %lld 块体素"),Total);
    return true;
}

bool UColdSteelStatusModel::ConsumeItem(const FString& Definition,int64 Count,FString& OutReason)
{
    if(Count<=0||!Definitions.Contains(Definition)){OutReason=TEXT("物品目录缺少该材料");return false;}
    SyncRuntime();auto P=Snapshot();
    int64 Available=0;
    for(const FColdSteelItem& Item:P.Items)
        if(Item.Definition==Definition&&(Item.Place==0||Item.Place==4))Available+=Item.Count;
    if(Available<Count)
    {
        OutReason=FString::Printf(TEXT("缺少 %lld 块（背包+仓库共 %lld）"),Count-Available,Available);
        return false;
    }
    // 背包先扣，再扣仓库；两类都按"后来者先扣"的顺序，保持堆叠状态稳定。
    int64 Left=Count;
    for(int32 Place: {0,4})
    {
        for(int32 Index=P.Items.Num()-1;Index>=0&&Left>0;--Index)
        {
            FColdSteelItem& Item=P.Items[Index];
            if(Item.Definition!=Definition||Item.Place!=Place)continue;
            const int64 Used=FMath::Min(Left,Item.Count);
            Item.Count-=Used;Left-=Used;
            if(Item.Count<=0)P.Items.RemoveAt(Index);
        }
    }
    if(!CommitState(P)){OutReason=TEXT("保存失败，材料未扣除");return false;}
    return true;
}

int32 UColdSteelStatusModel::PickupNearby(float RadiusCm)
{
    if(!CurrentPawn.IsValid()||!GetWorld())return 0;
    SyncRuntime();auto P=Snapshot();
    const FVector Origin=CurrentPawn->GetActorLocation();
    const double RadiusSq=FMath::Square(double(FMath::Max(25.f,RadiusCm)));
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    int32 Moved=0,Left=0;
    for(int32 Index=0;Index<P.Items.Num();++Index)
    {
        const FColdSteelItem Entry=P.Items[Index];
        if(Entry.Place!=2||Entry.Map!=Map)continue;
        if(FVector::DistSquared(Origin,Entry.Position)>RadiusSq)continue;
        // 隔墙/隔层不吸：只有"玩家能走过去"的物品才算在范围内（<=40 cm 的障碍可迈过）。
        if(!ReachableOnFoot(GetWorld(),CurrentPawn.Get(),Entry.Position))continue;
        P.Items.RemoveAt(Index);--Index;
        if(Insert(P.Items,Entry)){++Moved;continue;}
        // No room for this one: it stays on the ground exactly where it was.
        P.Items.Insert(Entry,Index+1);++Left;
    }
    if(Moved>0)
    {
        if(!CommitState(P)){Message=TEXT("保存失败，物品仍在原处");return 0;}
        RefreshDrops();
    }
    Message=Moved>0?FString::Printf(TEXT("已拾取 %d 件物品"),Moved):TEXT("附近没有可拾取的物品");
    if(Left>0)PostNotice(TEXT("背包已满"),FString::Printf(TEXT("已拾取 %d 件 · %d 件留在地面"),Moved,Left));
    return Moved;
}
