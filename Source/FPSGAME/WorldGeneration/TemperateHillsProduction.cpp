#include "TemperateHillsWorld.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionFallingTree.h"
#include "../Production/ProductionHarvestAssets.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../Production/ProductionTreeHealth.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "PCGComponent.h"
#include "Sound/SoundBase.h"
#include "UObject/UObjectIterator.h"

FString ATemperateHillsWorld::ProductionResourceId(int32 Layer,uint64 Candidate) const
{
    return FString::Printf(TEXT("%s:v1:%d:%016llx"),*WorldId.ToString(EGuidFormats::Digits),Layer,Candidate);
}
bool ATemperateHillsWorld::IsProductionDepleted(int32 Layer,uint64 Candidate) const
{
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Profile)return false;
    const FString Id=ProductionResourceId(Layer,Candidate);
    // Regrown trees keep one owner for their whole lifetime, including maturity.
    // PCG must not add a second full-size tree when their harvest counter resets.
    if(Layer==0 && Profile->HasTreeGrowth(Id))return true;
    // 树木与岩块按生命比例判采尽（2026-09-30 岩块统一；旧档在读档换算里按旧命中数折算），
    // 表土仍按挖层计数（一挥一层）。
    if(Layer==0)return Profile->TreeHealthRatio(Id)<=0.f;
    if(Layer==1)return Profile->RockHealthRatio(Id)<=0.f;
    return Profile->HarvestProgress(Id)>=1;
}

bool ATemperateHillsWorld::ResolveProductionResource(const FHitResult& Hit,FProductionResource& Resource,FString& Reason) const
{
    if (!bReady || !Assets || !WorldId.IsValid()) return false;
    const auto* Component=Hit.GetComponent();
    if (!Component) return false;
    if (const auto* TerrainMesh=Cast<UDynamicMeshComponent>(Component);TerrainMesh && Terrain.Contains(TerrainMesh))
    {
        const FVector P=Hit.ImpactPoint;
        if (Hit.ImpactNormal.Z<.65 || (RiverPlan && RiverPlan->Sample(P.X,P.Y).Wet>.05))
        { Reason=TEXT("陡坡或河床不可铲取表土"); return false; }
        const int32 X=FMath::FloorToInt(P.X/250),Y=FMath::FloorToInt(P.Y/250);
        Resource.CandidateId=(uint64(uint32(X))<<32)|uint32(Y);
        Resource.Layer=2; Resource.World=const_cast<ATemperateHillsWorld*>(this);
        Resource.Id=ProductionResourceId(2,Resource.CandidateId); Resource.Name=TEXT("表土");
        Resource.RequiredTool=TEXT("shovel"); Resource.Rewards.Add(TEXT("soil"),2);
        // One swing per 20 cm layer: the excavation below runs on every hit.
        Resource.Transform=FTransform(FVector((X+.5)*250,(Y+.5)*250,Height((X+.5)*250,(Y+.5)*250)));
        return true;
    }
    const auto* MeshComponent=Cast<UStaticMeshComponent>(Component);
    if (!MeshComponent || !MeshComponent->GetStaticMesh()) return false;
    const bool Tree=MeshComponent->GetOwner()==this && MeshComponent->GetStaticMesh()==Assets->TrunkCollisionMesh.Get();
    const int32 Layer=Tree?0:1;
    FTransform Transform=MeshComponent->GetComponentTransform();
    if (const auto* ISM=Cast<UInstancedStaticMeshComponent>(Component))
        if (!ISM->GetInstanceTransform(Hit.Item,Transform,true)) return false;
    FVector Origin=Transform.GetLocation();
    // 树桩碰撞盒（组件带 HarvestStump 标签，由采集子系统随树桩渲染一起维护）：
    // 按盒位置在采尽树桩表里找 ≤5 cm 的唯一桩，解析成独立的树桩资源（bStump）——
    // 有自己的生命，可继续劈；劈尽掉一块木材，不触发倒树。
    if (Tree && MeshComponent->ComponentTags.Contains(TEXT("HarvestStump")))
    {
        TArray<FTemperatePlacement> StumpsNear;
        GetHarvestedStumps(FBox(Origin-FVector(50,50,50000),Origin+FVector(50,50,50000)),StumpsNear);
        for (const auto& Stump:StumpsNear)
        {
            if (FVector2D::DistSquared(FVector2D(Origin),FVector2D(Stump.Transform.GetLocation()))>25) continue;
            Resource.World=const_cast<ATemperateHillsWorld*>(this); Resource.Layer=0; Resource.bStump=true;
            Resource.Transform=Stump.Transform; Resource.Mesh=Stump.Mesh; Resource.Seed=Stump.Key;
            Resource.CandidateId=Stump.CandidateId; Resource.Id=ProductionResourceId(0,Stump.CandidateId);
            Resource.Name=TEXT("树桩"); Resource.RequiredTool=TEXT("axe");
            Resource.Rewards.Add(TEXT("wood"),1);
            Resource.MaxHealth=ProductionTreeHealth::StumpMaxHealth(Resource);
            return true;
        }
        Reason=TEXT("树桩已经劈开过了"); return false;
    }
    if (Tree) Origin.Z-=300*Transform.GetScale3D().Z/6;
    TArray<FTemperatePlacement> Candidates;
    GetPlacements(Layer,FBox(Origin-FVector(50,50,50000),Origin+FVector(50,50,50000)),Candidates,true);
    for (const auto& Candidate:Candidates)
    {
        if (FVector2D::DistSquared(FVector2D(Origin),FVector2D(Candidate.Transform.GetLocation()))>25) continue;
        if (!Tree && Candidate.Mesh.ToString()!=MeshComponent->GetStaticMesh()->GetPathName()) continue;
        if (!Tree && MeshComponent->GetStaticMesh()->GetBounds().SphereRadius*Transform.GetScale3D().GetAbsMax()>500)
        { Reason=TEXT("大型岩壁不可采集，请寻找独立岩块"); return false; }
        Resource.World=const_cast<ATemperateHillsWorld*>(this); Resource.Layer=Layer;
        Resource.Transform=Candidate.Transform; Resource.Mesh=Candidate.Mesh; Resource.Seed=Candidate.Key;
        Resource.CandidateId=Candidate.CandidateId; Resource.Id=ProductionResourceId(Layer,Candidate.CandidateId);
        if(Tree)
            if(const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Profile && !Profile->IsTreeMature(Resource.Id))
            {Reason=TEXT("树木正在生长，成熟后才能砍伐");return false;}
        Resource.RequiredTool=Tree?TEXT("axe"):TEXT("pickaxe");
        // 树木像怪物一样有生命值：上限按树种与实例尺寸取，斧头按伤害扣血、归零才倒。
        // 只在这里算一次，结算与提示栏都读这一份资源快照。
        if (Tree) { Resource.Name=TEXT("树木"); Resource.Rewards.Add(TEXT("wood"),4); Resource.MaxHealth=ProductionTreeHealth::MaxHealth(Resource); }
        else
        {
            const FString Ore=RockOreDefinition(Candidate.Key);
            Resource.Name=Ore==TEXT("iron_ore")?TEXT("含铁岩块"):Ore==TEXT("copper_ore")?TEXT("含铜岩块"):
                Ore==TEXT("silver_ore")?TEXT("含银岩块"):Ore==TEXT("gold_ore")?TEXT("含金岩块"):TEXT("石块");
            Resource.Rewards.Add(TEXT("stone"),Ore.IsEmpty()?3:1);
            if (!Ore.IsEmpty()) Resource.Rewards.Add(Ore,2);
            // 岩块与树木统一生命值口径（2026-09-30）：十字镐按采集伤害扣血，归零才碎。
            // 只在这里算一次，结算与提示栏都读这一份资源快照。
            Resource.MaxHealth=ProductionTreeHealth::RockMaxHealth();
        }
        return true;
    }
    return false;
}

void ATemperateHillsWorld::CompleteProductionHarvest(const FProductionResource& Resource,const FHitResult& Hit,const FVector& Direction)
{
    // 树桩劈开（2026-09-28）：收走这一个桩的碰撞实例与渲染（标脏重建），木屑特效＋
    // 开裂声；不生成倒树、不再登记新桩——同一候选点的幼树按自己的时钟继续长。
    if (Resource.Layer==0 && Resource.bStump)
    {
        if (auto* ISM=Cast<UInstancedStaticMeshComponent>(Hit.GetComponent())) ISM->RemoveInstance(Hit.Item);
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())
        {
            Harvest->Burst(true,Hit.ImpactPoint,Resource.Seed);
            Harvest->InvalidateStumps(Resource);
        }
        if(auto* Sound=Cast<USoundBase>(ProductionHarvestAssets::TreeSound(false).ResolveObject()))
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Hit.ImpactPoint,.7f,.9f+(Resource.Seed%11)*.01f);
        return;
    }
    if (Resource.Layer==2)
    {
        // Topsoil is real excavation: one completed shovel cycle removes one 20 cm
        // layer over a 240 cm footprint (12 x 12 cells of the 20 cm building grid),
        // then the cell becomes harvestable again so the next cycle digs deeper.
        constexpr double SnapCm=20.0;
        constexpr double HalfCm=120.0;
        constexpr double LayerCm=20.0;
        const double CX=FMath::GridSnap(Resource.Transform.GetLocation().X,SnapCm);
        const double CY=FMath::GridSnap(Resource.Transform.GetLocation().Y,SnapCm);
        // The sink limit lives in ApplyTerrainStep (fps.Hills.MaxDropCm). Once it is hit the
        // dig is refused and the cell stays depleted, so soil cannot be farmed forever.
        auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
        if(ApplyTerrainStep(FVector(CX,CY,Height(CX,CY)),HalfCm,HalfCm,-LayerCm,
            TemperateHillsSurface::Key(int32(CX),int32(CY),uint32(Seed),9111)))
        {if(Profile)Profile->ResetHarvestProgress(Resource.Id);}
        else if(Profile)
        {
            for(const auto& Reward:Resource.Rewards)Profile->ConsumeMaterial(Reward.Key,Reward.Value);
            Profile->PostNotice(TEXT("已到下挖上限"),TEXT("这一格不能再挖，土壤未收入"));
        }
        return;
    }
    if (auto* ISM=Cast<UInstancedStaticMeshComponent>(Hit.GetComponent())) ISM->RemoveInstance(Hit.Item);
    if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())
    {
        Harvest->Burst(Resource.Layer==0,Hit.ImpactPoint,Resource.Seed);
        if(Resource.Layer==0)Harvest->ShowStumpAtCut(Resource);
    }
    if (Resource.Layer==0)
    {
        // Remove only the rendered tree instance. Stable candidate IDs remain in
        // the profile, so subsequent PCG streaming cannot restore the felled tree.
        for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
        {
            auto* Trees=*It;
            if(Trees->GetWorld()!=GetWorld()||Trees->GetSkinnedAsset()!=Resource.Mesh.ResolveObject())continue;
            for(int32 N=Trees->GetInstanceCount()-1;N>=0;--N)
            {
                const auto Id=Trees->GetInstanceId(N);FTransform Transform;
                if(Trees->GetInstanceTransform(Id,Transform,true)&&FVector::DistSquared(Transform.GetLocation(),Resource.Transform.GetLocation())<4)
                {Trees->RemoveInstance(Id);break;}
            }
        }
        FActorSpawnParameters Spawn; Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if (auto* Fall=GetWorld()->SpawnActor<AProductionFallingTree>(Resource.Transform.GetLocation(),Resource.Transform.Rotator(),Spawn))
        {
            Fall->InitializeFall(Resource,Direction);
            // The falling component now owns the mesh; do not retain every tree
            // variant in the preload cache for the rest of the world session.
            if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->ReleasePreparedFall(Resource);
        }
    }
    // No PCG cell regeneration on each harvest; only the affected instances change.
}

void ATemperateHillsWorld::GetHarvestedStumps(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    // Reconstruct from the same seeded candidates and persisted depletion IDs.
    // No second stump save schema, and no tree/PCG regeneration on each chop.
    // 2026-09-28：树桩可能带偏移（被砍的树不在候选点基点上，最多 ±6.5 m）——枚举各扩
    // 一格，入盒判定与扎根高度都用偏移后的桩位。
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/1200)-1;Y<=FMath::FloorToInt(Bounds.Max.Y/1200)+1;++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/1200)-1;X<=FMath::FloorToInt(Bounds.Max.X/1200)+1;++X)
    {
        FTemperatePlacement P;
        if(!TreeCandidate(X,Y,P)||!IsProductionDepleted(0,P.CandidateId))continue;
        const FString Id=ProductionResourceId(0,P.CandidateId);
        const float Scale=Profile?Profile->TreeStumpScale(Id):1;
        if(Scale<=.01f)continue;
        const FVector2D Offset=Profile?Profile->TreeStumpOffset(Id):FVector2D::ZeroVector;
        const double SX=P.Transform.GetLocation().X+Offset.X,SY=P.Transform.GetLocation().Y+Offset.Y;
        if(!Bounds.IsInsideXY(FVector(SX,SY,P.Transform.GetLocation().Z)))continue;
        P.Transform.SetScale3D(P.Transform.GetScale3D()*Scale);
        P.Transform.SetLocation(FVector(SX,SY,Height(SX,SY)-10));
        Out.Add(P);
    }
}

void ATemperateHillsWorld::GetRegrowingTrees(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Profile)return;
    // 2026-09-28 用户规则：幼树不长在原桩位，而在生长记录的随机偏移处（半径 2.8–6.5 m）；
    // 枚举各扩一格，入盒判定与扎根高度都用偏移后的树位，缩放仍绕根（原 10 cm 嵌入按比例）。
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/1200)-1;Y<=FMath::FloorToInt(Bounds.Max.Y/1200)+1;++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/1200)-1;X<=FMath::FloorToInt(Bounds.Max.X/1200)+1;++X)
    {
        FTemperatePlacement P;if(!TreeCandidate(X,Y,P))continue;
        const FString Id=ProductionResourceId(0,P.CandidateId);
        if(!Profile->HasTreeGrowth(Id))continue;
        const float Scale=Profile->TreeGrowthScale(Id);if(Scale<=0)continue;
        const FVector2D Offset=Profile->TreeSaplingOffset(Id);
        const double SX=P.Transform.GetLocation().X+Offset.X,SY=P.Transform.GetLocation().Y+Offset.Y;
        if(SX<Bounds.Min.X||SX>=Bounds.Max.X||SY<Bounds.Min.Y||SY>=Bounds.Max.Y)continue;
        P.Transform.SetScale3D(P.Transform.GetScale3D()*Scale);
        P.Transform.SetLocation(FVector(SX,SY,Height(SX,SY)-10));
        P.Transform.AddToTranslation(FVector(0,0,10*(1-Scale)));
        Out.Add(P);
    }
}
