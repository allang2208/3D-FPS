#include "ColdSteelStatusModel.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionHarvestAssets.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionTreeFallPlan.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

bool UColdSteelStatusModel::StageProductionDrops(FColdSteelProfile& State,const FProductionResource& Target,TArray<FString>& Ids,const FProductionToolStats& ToolStats)
{
    auto* World=Target.World.Get();if(!World||!World->WorldId.IsValid())return false;
    FVector Forward=Target.Direction;Forward.Z=0;if(!Forward.Normalize())Forward=FVector::ForwardVector;
    const FVector Side=FVector::CrossProduct(FVector::UpVector,Forward);
    // 树桩（bStump）没有倒树轴向：不做倒树计划，掉落像岩块那样绕目标散落。
    const bool bTreeFall=Target.Layer==0&&!Target.bStump;
    const FProductionTreeFallPlan Fall=bTreeFall?FProductionTreeFallPlan::Make(Target):FProductionTreeFallPlan();
    const FVector FallenAxis=FQuat(Fall.Axis,FMath::DegreesToRadians(Fall.LandingAngle)).RotateVector(FVector::UpVector);
    FRandomStream Random(Target.Seed);int32 Index=0;
    TArray<FString> RewardDefinitions;Target.Rewards.GetKeys(RewardDefinitions);RewardDefinitions.Sort();
    // 一份完整收获：产出倍率作用在出厂数量上，木材仍按根散落、石材／矿石仍是一个堆叠拾取物。
    auto StageSet=[&]()
    {
        for(const auto& Definition:RewardDefinitions)
        {
            const int64 Amount=ColdSteelTool::Yield(Target.Rewards[Definition],ToolStats);
            // Four short logs; stone/ore stacks stay small without multiplying physics by count.
            const int32 Pieces=Definition==TEXT("wood")?int32(Amount):1;
            for(int32 N=0;N<Pieces;++N)
            {
                auto Item=CreateItem(Definition,Definition==TEXT("wood")?1:Amount);
                if(Item.Data.IsEmpty()){Message=TEXT("材料目录缺失，原资源保留");return false;}
                FVector Position=Target.Transform.GetLocation();
                if(bTreeFall)Position=Fall.Pivot+FallenAxis*(90+Index*95)+Side*Random.FRandRange(-22,22);
                else Position+=FVector(Random.FRandRange(-65,65),Random.FRandRange(-65,65),0);
                FVector Normal=World->SurfaceNormal(Position.X,Position.Y);
                if(Normal.Z<.65f){Position=Target.Transform.GetLocation()+Side*(Index*35);Normal=World->SurfaceNormal(Position.X,Position.Y);}
                Position.Z=World->Height(Position.X,Position.Y)+(bTreeFall?28:45);
                // New logs are authored along local +X, with complete end caps.
                const float YawSpread=bTreeFall?9.f:(Target.bStump?40.f:180.f);
                const float Yaw=Forward.Rotation().Yaw+Random.FRandRange(-YawSpread,YawSpread);
                Item.WorldRotation=(FQuat::FindBetweenNormals(FVector::UpVector,Normal)*FRotator(0,Yaw,0).Quaternion()).Rotator();
                Item.Place=2;Item.Cell=-1;Item.Position=Position;Item.HarvestWorldId=World->WorldId;
                Item.Map=UGameplayStatics::GetCurrentLevelName(this,true);
                Ids.Add(Item.InstanceId);State.Items.Add(MoveTemp(Item));++Index;
            }
        }
        return true;
    };
    if(!StageSet())return false;
    // 额外产出几率：命中结算时判定一次，成功则整份材料再落一次，
    // 期望产出 = 产出倍率 ×（1 + 几率）。位置沿用同一条随机流，不会重叠。
    if(ToolStats.BonusHarvestChance>0.&&FMath::FRand()<float(ToolStats.BonusHarvestChance)&&!StageSet())return false;
    if(State.Items.Num()>10000){Message=TEXT("地面物品已达存档上限，请先拾取部分材料");return false;}
    return true;
}
void UColdSteelStatusModel::StampProductionDrop(FColdSteelItem& Item) const
{
    Item.HarvestWorldId.Invalidate();
    if(!ProductionHarvestAssets::IsMaterial(Item.Definition))return;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->WorldId.IsValid()){Item.HarvestWorldId=It->WorldId;break;}
}
