#include "FluidPresentationSubsystem.h"
#include "RiverPilotFXSubsystem.h"
#include "../FPSWeatherManager.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/SmeltingSystem.h"   // JobTotalSeconds/SpeedMultiplier/FuelConfig：整批边界与 Heat 段一律复用既有结算口径（不新造）
#include "../Production/ProductionHarvestAssets.h"   // 凝固锭的 MI_<def> 路径：与 AColdSteelPickup 同一口径（不另抄一份字符串）
#include "../Movement/FPSFootstepAudioComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "EngineUtils.h"
#include "NiagaraComponent.h"
#include "Scalability.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/WorldSettings.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "NiagaraSystem.h"

bool UFluidPresentationSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}

void UFluidPresentationSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if(World.GetNetMode()==NM_DedicatedServer)return;
    for(ULevel* Level:World.GetLevels())RegisterLevel(Level,&World);
    SpawnHandle=World.AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateUObject(this,&UFluidPresentationSubsystem::RegisterActor));
    LevelHandle=FWorldDelegates::LevelAddedToWorld.AddUObject(this,&UFluidPresentationSubsystem::RegisterLevel);
    LastBudgetTime=World.GetTimeSeconds();bReady=true;
    ColdLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(ColdTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareColdPool();ColdLoad.Reset();}));
    // 高炉黑烟系统常驻（一个 Niagara 资产句柄）；异步预载完成前不起烟，避免热路径同步 LoadObject。
    FurnaceLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(FurnaceTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){FurnaceAsset=FurnaceTemplate.Get();FurnaceLoad.Reset();}));
    // 出铁口熔融金属流＋凝固锭：一次请求把 NS 与 SM_Ingot、四个 MI_<def>Ingot 全部预载到内存，
    // 首次完成上升沿前就绪；仍是异步软引用，缺资产时静默跳过（零回归锚点：没有同步 LoadObject）。
    {
        TArray<FSoftObjectPath> Wants;
        Wants.Add(TapTemplate.ToSoftObjectPath());
        Wants.Add(CastingTemplate.ToSoftObjectPath());
        Wants.Add(FSoftObjectPath(TEXT("/Game/Fluids/FurnaceCasting20260926/M_CastingStreamBuffered.M_CastingStreamBuffered")));
        Wants.Add(FSoftObjectPath(TEXT("/Game/Fluids/FurnaceCasting20260926/M_CastingPoolBuffered.M_CastingPoolBuffered")));
        Wants.Add(FSoftObjectPath(TEXT("/Game/Items/Smelting/Ingot/SM_Ingot.SM_Ingot")));
        for(const TCHAR* Def:{TEXT("ironIngot"),TEXT("copperIngot"),TEXT("silverIngot"),TEXT("goldIngot")})
            Wants.Add(FSoftObjectPath(FString::Printf(TEXT("/Game/Items/Smelting/Ingot/MI_%s.MI_%s"),Def,Def)));
        TapMeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Wants,
            FStreamableDelegate::CreateWeakLambda(this,[this](){TapAsset=TapTemplate.Get();}));
    }
}

void UFluidPresentationSubsystem::RegisterLevel(ULevel* Level,UWorld* World)
{
    if(World!=GetWorld()||!Level)return;
    for(AActor* Actor:Level->Actors)if(IsValid(Actor))RegisterActor(Actor);
}

void UFluidPresentationSubsystem::RegisterActor(AActor* Actor)
{
    if(auto* Manager=Cast<AFPSWeatherManager>(Actor))Weather=Manager;
    // 高炉不在这里登记：构件的 Id 由 Configure() 在 SpawnActor() 返回之后才写入，
    // 生成事件触发时 PrefabId() 仍是 NAME_None，按 Id 判定永远漏。改由 UpdateFurnaceSmoke
    // 用 TActorIterator 有节律对齐（覆盖放置/存档装载/预置关卡三种时机，1Hz 足够便宜）。
    TInlineComponentArray<UPrimitiveComponent*> Bodies(Actor);
    for(auto* Body:Bodies)if(Body->IsSimulatingPhysics())RegisterWaterBody(Body);
    if(auto* Character=Cast<ACharacter>(Actor))
    {
        for(const auto& Walker:Walkers)if(Walker.Character.Get()==Character)return;
        FWalker Walker;Walker.Character=Character;Walkers.Add(Walker);
    }
}

int32 UFluidPresentationSubsystem::AllocateDetail(const FVector& Position,int32 Requested,bool bImportant)
{
    if(!bReady||Requested<=0)return 0;
    if(!bHasView)
        if(auto* PC=GetWorld()->GetFirstPlayerController())
        {FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);bHasView=true;}
    if(!bHasView)return 0;
    const float Distance=FVector::Distance(Position,Eye);
    if(Distance>8500)return 0;
    const int32 Quality=Scalability::GetQualityLevels().EffectsQuality;
    const float QualityScale=Quality<=0?.4f:(Quality==1?.65f:1.f);
    const float DistanceScale=Distance>3500?.5f:1.f;
    const double Now=GetWorld()->GetTimeSeconds();
    Tokens=FMath::Min(72.f,Tokens+float(FMath::Max(0.,Now-LastBudgetTime))*180.f);LastBudgetTime=Now;
    // Reserve a part of each burst for impacts/player movement instead of far trails.
    const int32 Available=FMath::FloorToInt(FMath::Max(0.f,Tokens-(bImportant?0.f:12.f)));
    DetailRemainder+=Requested*QualityScale*DistanceScale;
    const int32 Desired=FMath::FloorToInt(DetailRemainder);DetailRemainder-=Desired;
    const int32 Result=FMath::Min(Available,Desired);
    Tokens-=Result;return Result;
}

FVector UFluidPresentationSubsystem::WindAt(const FVector& Position,float* OutShelter)
{
    if(!Weather.IsValid()){if(OutShelter)*OutShelter=1.f;return FVector::ZeroVector;}
    const FIntVector Key(FMath::FloorToInt(Position.X/400),FMath::FloorToInt(Position.Y/400),FMath::FloorToInt(Position.Z/200));
    const double Now=GetWorld()->GetTimeSeconds();
    FShelter* Cached=Shelter.Find(Key);
    if(RoofFrame!=GFrameCounter){RoofFrame=GFrameCounter;RoofQueries=0;}
    if((!Cached||Now-Cached->Time>2.)&&RoofQueries<2)
    {
        ++RoofQueries;
        FHitResult Roof;FCollisionQueryParams Query(SCENE_QUERY_STAT(FluidShelter),false);
        FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
        const bool Covered=GetWorld()->LineTraceSingleByObjectType(Roof,Position+FVector(0,0,25),Position+FVector(0,0,1400),Objects,Query);
        if(Shelter.Num()>=128&&!Cached)
        {
            double Time=TNumericLimits<double>::Max();FIntVector OldKey=Key;
            for(auto It=Shelter.CreateConstIterator();It;++It)if(It.Value().Time<Time){Time=It.Value().Time;OldKey=It.Key();}
            Shelter.Remove(OldKey);
        }
        Cached=&Shelter.FindOrAdd(Key);Cached->Factor=Covered?.12f:1.f;Cached->Time=Now;
    }
    // An unsampled cell starts sheltered until a query slot becomes available.
    const float Factor=Cached?Cached->Factor:.12f;
    if(OutShelter)*OutShelter=Factor;
    FVector Wind=Weather->GetWeatherWind();Wind.Z=0;
    return Wind.GetClampedToMaxSize(180.f)*(.45f*Factor);
}

void UFluidPresentationSubsystem::ConfigureSmoke(UNiagaraComponent* FX,int32 Requested,bool bWet)
{
    if(!FX)return;
    const FVector Position=FX->GetComponentLocation();
    const int32 Count=AllocateDetail(Position,Requested,true);
    FX->SetVariableFloat(TEXT("User.DetailReduction"),1.f-float(Count)/FMath::Max(1,Requested));
    FX->SetVariableFloat(TEXT("User.WetImpact"),bWet?1.f:0.f);
    FX->SetVariableVec3(TEXT("User.Wind"),FX->GetComponentTransform().InverseTransformVector(WindAt(Position)));
    Smoke.RemoveAll([FX](const FSmoke& S){return !S.FX.IsValid()||S.FX.Get()==FX;});
    for(int32 I=0;I<5;++I)FX->SetVariableVec4(FName(*FString::Printf(TEXT("User.SmokePlane%d"),I)),FVector4(0,0,0,0));
    if(Smoke.Num()<32)
    {
        FSmoke Entry;Entry.FX=FX;Entry.Expires=GetWorld()->GetTimeSeconds()+4.;
        Smoke.Add(Entry);UpdateSmokeGeometry(Smoke.Last(),5);
    }
}

void UFluidPresentationSubsystem::UpdateWalker(FWalker& Walker)
{
    ACharacter* Character=Walker.Character.Get();
    if(!Character||Character->IsHidden())return;
    if(Character->GetMesh()&&Character->GetMesh()->IsSimulatingPhysics())RegisterWaterBody(Character->GetMesh());
    // The local player's audio stride already supplies exact step events.
    if(Character->IsLocallyControlled()&&Character->FindComponentByClass<UFPSFootstepAudioComponent>())return;
    const FVector Position=Character->GetActorLocation();
    if(!bHasView||FVector::DistSquared(Position,Eye)>FMath::Square(4000.f)){Walker.Initialized=false;return;}
    auto* Move=Character->GetCharacterMovement();auto* Water=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>();
    if(!Move||!Water)return;
    const FVector Feet=Position-FVector(0,0,Character->GetSimpleCollisionHalfHeight());
    FFluidWaterContact Contact;
    const bool Wet=Water->SampleWater(Feet,180,Contact);
    const bool Grounded=Move->IsMovingOnGround();
    if(Wet)Water->UpdateWake(Character,Contact,Move->Velocity,Character->GetSimpleCollisionRadius());
    const float Travel=FVector::Dist2D(Position,Walker.Previous);
    if(Walker.Initialized&&Travel<500)
    {
        const bool Landing=Grounded&&!Walker.Grounded&&Walker.Vertical< -200;
        Walker.Stride+=Travel;
        const float Stride=FMath::Clamp(Character->GetSimpleCollisionRadius()*5.f,80.f,170.f);
        if(Wet&&((!Walker.Wet&&Move->Velocity.Z<0)||Landing||Walker.Stride>=Stride))
        {
            Water->CharacterWater(Contact,Move->Velocity,Landing?FMath::Abs(Walker.Vertical):0,false);
            Walker.Stride=FMath::Fmod(Walker.Stride,Stride);
        }
        if(!Wet)Walker.Stride=0;
    }
    Walker.Initialized=true;Walker.Previous=Position;Walker.Vertical=Move->Velocity.Z;Walker.Grounded=Grounded;Walker.Wet=Wet;
}

void UFluidPresentationSubsystem::Tick(float Delta)
{
    UpdateClock+=Delta;WindClock+=Delta;FurnaceClock+=Delta;
    if(UpdateClock<.025f)return;UpdateClock=0;
    bHasView=false;
    if(auto* PC=GetWorld()->GetFirstPlayerController()){FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);bHasView=true;}
    for(int32 I=0,Count=FMath::Min(8,WaterBodies.Num());I<Count&&!WaterBodies.IsEmpty();++I)
    {
        BodyCursor%=WaterBodies.Num();
        if(!WaterBodies[BodyCursor].Body.IsValid()){WaterBodies.RemoveAtSwap(BodyCursor);continue;}
        UpdateWaterBody(WaterBodies[BodyCursor++]);
    }
    const int32 Work=FMath::Min(8,Walkers.Num());
    for(int32 I=0;I<Work&&!Walkers.IsEmpty();++I)
    {
        WalkerCursor%=Walkers.Num();
        if(!Walkers[WalkerCursor].Character.IsValid()){Walkers.RemoveAtSwap(WalkerCursor);continue;}
        UpdateWalker(Walkers[WalkerCursor++]);
    }
    if(WindClock>=.2f)
    {
        WindClock=0;const double Now=GetWorld()->GetTimeSeconds();
        Smoke.RemoveAll([Now](const FSmoke& S){return !S.FX.IsValid()||Now>=S.Expires||!S.FX->IsActive();});
        for(auto& S:Smoke)if(auto* FX=S.FX.Get())
        {
            if(S.bOwnWind)continue;   // 炉烟风场由 UpdateFurnaceSmoke 接管（雨天阵风需与 Rainfall 同拍写）
            FX->SetVariableVec3(TEXT("User.Wind"),FX->GetComponentTransform().InverseTransformVector(WindAt(FX->GetComponentLocation())));
        }
        for(int32 I=0,Count=FMath::Min(6,Smoke.Num());I<Count;++I)
        {
            SmokeCursor%=Smoke.Num();UpdateSmokeGeometry(Smoke[SmokeCursor++],2);
        }
    }
    if(FurnaceClock>=.2f){FurnaceClock=0;UpdateFurnaceSmoke();}
}

void UFluidPresentationSubsystem::Deinitialize()
{
    bReady=false;
    if(GetWorld())GetWorld()->RemoveOnActorSpawnedHandler(SpawnHandle);
    FWorldDelegates::LevelAddedToWorld.Remove(LevelHandle);
    if(ColdLoad){ColdLoad->CancelHandle();ColdLoad.Reset();}
    if(FurnaceLoad){FurnaceLoad->CancelHandle();FurnaceLoad.Reset();}
    if(TapMeshLoad){TapMeshLoad->CancelHandle();TapMeshLoad.Reset();}
    for(auto& FX:TapPool)if(FX)
    {
        FX->DeactivateImmediate();if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);FX->DestroyComponent();
    }
    TapPool.Reset();
    for(auto& Ingot:IngotPool)if(Ingot)
    {
        if(auto* Owner=Ingot->GetOwner())Owner->RemoveInstanceComponent(Ingot);Ingot->DestroyComponent();
    }
    IngotPool.Reset();TapAsset=nullptr;
    for(auto& Casting:CastingPool)if(Casting)
    {
        if(auto* Owner=Casting->GetOwner())Owner->RemoveInstanceComponent(Casting);Casting->DestroyComponent();
    }
    CastingPool.Reset();
    for(auto& Rack:CastingRackPool)if(Rack)
    {
        if(auto* RackOwner=Rack->GetOwner())RackOwner->RemoveInstanceComponent(Rack);
        Rack->DestroyComponent();
    }
    CastingRackPool.Reset();
    for(auto& E:Furnaces)if(auto* FX=E.FX.Get())FX->DestroyComponent();
    Furnaces.Reset();
    for(auto& FX:ColdPool)if(FX)
    {
        FX->DeactivateImmediate();if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);FX->DestroyComponent();
    }
    ColdPool.Reset();WaterBodies.Reset();
    Walkers.Reset();Smoke.Reset();Shelter.Reset();Weather.Reset();Super::Deinitialize();
}
TStatId UFluidPresentationSubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(FluidPresentation,STATGROUP_Tickables);}

// Separate hazard allowance prevents cosmetic smoke from starving poison footprint updates.
bool UFluidPresentationSubsystem::ReserveGeometryQueries(int32 Count,bool bHazard)
{
    if(GeometryFrame!=GFrameCounter){GeometryFrame=GFrameCounter;CosmeticQueries=0;HazardQueries=0;}
    int32& Used=bHazard?HazardQueries:CosmeticQueries;
    if(Used+Count>(bHazard?16:12))return false;
    Used+=Count;return true;
}

void UFluidPresentationSubsystem::UpdateSmokeGeometry(FSmoke& Entry,int32 Count)
{
    auto* FX=Entry.FX.Get();if(!FX||!bHasView||FVector::DistSquared(FX->GetComponentLocation(),Eye)>FMath::Square(3500.f))return;
    const FTransform Transform=FX->GetComponentTransform();
    const FVector Origin=Transform.GetLocation()+FVector(0,0,16);
    const FVector Directions[5]={FVector(1,0,0),FVector(-1,0,0),FVector(0,1,0),FVector(0,-1,0),FVector(0,0,1)};
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FluidSmokeBounds),false,FX->GetOwner());
    for(int32 I=0;I<Count&&ReserveGeometryQueries(1);++I)
    {
        const int32 Index=Entry.Probe++%5;FHitResult Hit;FVector4 Plane(0,0,0,0);
        const float Reach=FMath::Clamp(float(Transform.GetScale3D().GetMax())*260.f,140.f,650.f);
        if(GetWorld()->LineTraceSingleByObjectType(Hit,Origin,Origin+Directions[Index]*Reach,Objects,Query))
        {
            const FVector N=Transform.InverseTransformVectorNoScale(Hit.ImpactNormal).GetSafeNormal();
            const FVector Point=Transform.InverseTransformPosition(Hit.ImpactPoint+Hit.ImpactNormal*18);
            Plane=FVector4(N,FVector::DotProduct(N,Point));
        }
        FX->SetVariableVec4(FName(*FString::Printf(TEXT("User.SmokePlane%d"),Index)),Plane);
    }
}

bool UFluidPresentationSubsystem::MoveMist(FVector& Position,FVector& Velocity,const FVector& Previous,float Radius)
{
    if(!bHasView||FVector::DistSquared(Position,Eye)>FMath::Square(2500.f)||!ReserveGeometryQueries(1))return false;
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(FluidMistSlide),false);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    if(!GetWorld()->SweepSingleByObjectType(Hit,Previous,Position,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius),Query))return false;
    Position=Hit.Location+Hit.ImpactNormal*1.5;
    Velocity=FVector::VectorPlaneProject(Velocity,Hit.ImpactNormal)*.65f;
    return true;
}

void UFluidPresentationSubsystem::PrepareColdPool()
{
    auto* Asset=ColdTemplate.Get();if(!Asset||!ColdPool.IsEmpty())return;
    auto* Owner=GetWorld()->GetWorldSettings();
    for(int32 I=0;I<8;++I)
    {
        auto* FX=NewObject<UNiagaraComponent>(Owner,NAME_None,RF_Transient);Owner->AddInstanceComponent(FX);
        FX->SetAutoActivate(false);FX->SetAutoDestroy(false);FX->SetAsset(Asset);FX->SetCastShadow(false);
        FX->SetCanEverAffectNavigation(false);FX->RegisterComponent();ColdPool.Add(FX);
    }
}
void UFluidPresentationSubsystem::EmitColdImpact(const FVector& Position,const FVector& Normal)
{
    for(auto& FX:ColdPool)if(FX&&!FX->IsActive())
    {
        FX->SetWorldLocationAndRotation(Position+Normal*10,FRotationMatrix::MakeFromZ(Normal).Rotator());
        FX->SetVariableVec3(TEXT("User.LocalUp"),FX->GetComponentTransform().InverseTransformVectorNoScale(FVector::UpVector));
        FX->SetVariableFloat(TEXT("User.SteamCount"),5);
        FX->SetVariableFloat(TEXT("User.ImpactGrowth"),0);
        ConfigureSmoke(FX,5);FX->Activate(true);break;
    }
}

// 雨天阵风（炉烟 v3）：无理数比正弦叠加 → 平滑伪随机方向+脉动强度（周期在分钟级，不露循环），
// 竖直分量小剪切。幅值乘雨量，配合资产端 Rainfall 项把烟柱撕散、吹斜、快散。
static FVector RainGust(double T,float R)
{
    const float t=float(T);
    const float Ang=t*0.55f+3.f*sin(t*0.23f)+1.7f*sin(t*0.41f+2.1f);
    const float Mag=FMath::Max(20.f,60.f+45.f*sin(t*0.83f+1.3f)+30.f*sin(t*1.7f+0.4f));
    return FVector(FMath::Cos(Ang),FMath::Sin(Ang),0.12f*sin(t*0.9f))*Mag*R;
}

FVector UFluidPresentationSubsystem::WindWithGustAt(const FVector& Position)
{
    if(GustFrame!=GFrameCounter)
    {
        GustFrame=GFrameCounter;
        const float Rain=Weather.IsValid()?FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f):0.f;
        SharedRainGust=Rain>.01f?RainGust(GetWorld()->GetTimeSeconds(),Rain):FVector::ZeroVector;
    }
    float ShelterFactor=1.f;
    const FVector BaseWind=WindAt(Position,&ShelterFactor);
    return (BaseWind+SharedRainGust*ShelterFactor).GetClampedToMaxSize(260.f);
}

void UFluidPresentationSubsystem::UpdateFurnaceSmoke()
{
    // 高炉工作黑烟（2026-09-24）：构件登记驱动、5Hz 限流轮询；工作＝有在炼任务或炉内存料
    // （同 VoxelBuildWorld 护炉谓词）。起步匀加速补烟、停燃限流断供、末团散尽才停用
    //（与 FPSWeaponFXComponent 持续烟同一语义）；风/接触平面/细节预算全部走共享 ConfigureSmoke。
    Furnaces.RemoveAll([this](FFurnaceSmoke& E)
    {
        if(E.Piece.IsValid())return false;
        ReleaseFurnaceTap(E);ReleaseFurnaceIngot(E);ReleaseCastingRack(E);
        return true;
    });
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now>=FurnaceScanAt)
    {   // 1Hz 对账登记：构件的 Id/Cell 由 Configure() 在 SpawnActor 返回之后写入，生成事件触发时
        // PrefabId() 仍是 None，事件式登记对新放/存档装载/预置关卡三种炉子恒漏（零烟根因，2026-09-24）。
        FurnaceScanAt=Now+1.;
        for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
            if(auto* Piece=*It;Piece&&Piece->PrefabId()==VoxelSmeltingFurnaceId)
            {
                bool Seen=false;for(const auto& E:Furnaces)if(E.Piece.Get()==Piece){Seen=true;break;}
                if(!Seen&&Furnaces.Num()<32){FFurnaceSmoke Entry;Entry.Piece=Piece;Entry.LastSeen=Now;Furnaces.Add(Entry);}
            }
    }
    if(!bHasView||Furnaces.IsEmpty())return;
    constexpr float MaxRate=16.f;          // 与 author_furnace_black_smoke.py 的额定 User.SpawnRate 同底（v2 加密）
    constexpr double Dissipate=3.9;        // 最大粒子寿命 3.6s + 补发余量（v2）
    // 雨量 0..1（AFPSWeatherManager 有效雨量），驱动炉烟 v3 的"被随机方向阵风快速吹散/加速消散"。
    const float Rain=Weather.IsValid()?FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f):0.f;
    int32 Alive=0;for(const auto& E:Furnaces)if(E.FX.IsValid())++Alive;
    for(auto& E:Furnaces)
    {
        auto* Piece=E.Piece.Get();if(!Piece)continue;
        auto* Build=Cast<AVoxelBuildWorld>(Piece->GetOwner());
        auto* Body=Piece->Body();
        const FIntVector Cell=Piece->AnchorCell();
        // 出烟口＝实测喉口：SM_BlastFurnace 网格局部 (-18,0,208)（口心＝manifest ChargingMouth，
        // 半径 18.4cm 天空洞，碗内底 184、凸缘顶 220——Blender 投射实测，Saved/furnace_throat.json）。
        // z=208 取碗内上段＝烟从斗里涌出而非炉顶外冒；经 Body 组件变换换算，炉子 Yaw 旋转自动跟随。
        // （旧版取世界 AABB 顶面中心：XY 偏口心 18cm、旋转后错位、且高于凸缘——"不匹配出口"根因。）
        const FVector Mouth=Body?Body->GetComponentTransform().TransformPosition(FVector(-18.f,0.f,208.f))
            :Piece->GetActorLocation()+FVector(0,0,208.f);
        bool bWorking=Build&&Body&&Body->IsRegistered()&&!Piece->IsFalling()
            &&((Build->FindSmelting(Cell)&&!Build->FindSmelting(Cell)->Recipe.IsNone())||Build->FuelAt(Cell)>0.);
        if(bWorking)bWorking=FVector::DistSquared(Mouth,Eye)<=FMath::Square(8500.f);
        const float dt=FMath::Clamp(float(Now-E.LastSeen),0.f,.5f);E.LastSeen=Now;
        // —— v5 状态驱动（Docs/Fluids/furnace-smoke-optimization-plan-20260925.md §2）——
        // 全部在既有 5Hz 同拍内算完：无新遍历、无新容器、无分配、无字符串拼接（参数名是编译期常量）。
        // 结算口径一律复用 UColdSteelSmeltingSystem 既有的公开 helper，本文件不新造一套。
        // 恒等锚点（零回归）：在炼任务∧燃料燃烧中 ⇒ Heat=1；此时 L0 的 SpawnRate/色/α 与 v4 逐式恒等。
        const FVoxelSmeltingJob* Job=Build?Build->FindSmelting(Cell):nullptr;
        const auto* Smelt=GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;   // UWorldSubsystem 无裸 GetGameInstance()（C3861 修复）
        // Casting must run even when the six smoke slots are full or smoke is not loaded.
        const bool bTapDone=Build&&Smelt&&Smelt->IsDone(Build,Cell);
        UpdateFurnaceTap(E,Build,Job,Body,Mouth,bTapDone,Now);
        const bool bJobBurning=Job&&Job->BurnStartTicks>0&&Build->FuelAt(Cell)>0.;
        // Heat：在炼任务∧燃料燃烧中=1（恒等锚点）；仅燃料火种=.25；有任务但燃料耗尽段＝批量档与燃烧状态合成。
        float Heat=0.f;
        if(bJobBurning)Heat=1.f;
        else if(Build&&Build->FuelAt(Cell)>0.)Heat=.25f;
        if(Job&&!Job->Recipe.IsNone()&&!bJobBurning)
        {   // 燃料耗尽段：批量越大余热越足（.55..1.0），再按燃烧状态降档合成
            const int64 Batch=FMath::Clamp(Job->BatchCount,(int64)1,(int64)5);
            const float Fade=.55f+.15f*float(Batch)/5.f;
            Heat=FMath::Max(Heat,Fade*(Job->BurnStartTicks>0?.75f:.5f));
        }
        Heat=FMath::Clamp(Heat,0.f,1.f);
        // 升档即时（点火/投料马上变浓），降档限速：断供/熄火时火力档沿既有 5Hz 拍平滑回落，
        // 不在资产端出现"啪"地掉档。anchors 不受影响（升档路径 Heat 直接取值，恒等锚点仍是 1）。
        E.Heat=Heat>E.Heat?Heat:FMath::FInterpConstantTo(E.Heat,Heat,dt,2.5f);
        Heat=E.Heat;   // 写进 User.Heat 的是限速后的档位（升档逐式不变，锚点仍为 1）
        // Ignition：now−max(BurnStartTicks,FireStartTicks) 归一化 4s；熄火段不写（资产端沿用断供曲线）。
        // 取“较新的有效者”＝当前燃烧段或火种段的实际起点；两者都无效时不覆盖上一拍值（写 Heat 已足够表达）。
        float Ignition=0.f,bHaveIgnition=false;
        if(Build)
        {
            const int64 BurnTicks=Job?Job->BurnStartTicks:0;
            const int64 FireTicks=Build->FurnaceFireTicks(Cell);
            const int64 StartTicks=BurnTicks>FireTicks?BurnTicks:FireTicks;   // 较新有效者（大的戳更晚）
            if(StartTicks>0)
            {
                const int64 UtcNow=FDateTime::UtcNow().GetTicks();
                if(UtcNow>StartTicks)
                {   // 与 UColdSteelSmeltingSystem 同一换算口径（1/ETimespan::TicksPerSecond），不自造 1e-7 近似
                    constexpr double TicksToSeconds=1.0/static_cast<double>(ETimespan::TicksPerSecond);
                    Ignition=FMath::Clamp(float(double(UtcNow-StartTicks)*TicksToSeconds/4.0),0.f,1.f);
                }
                else Ignition=0.f;   // UTC 回拨：当作刚点火（结算侧同款回拨保护口径）
                bHaveIgnition=true;
            }
        }
        // Puff：ProgressSeconds 跨越整批边界（配方秒×批量÷速度倍率，全部走既有 JobTotalSeconds）→ 写 1，
        // 再在 1.2s 内线性衰减回 0。用 LastProgress 比较，不新增事件系统、不新增 tick。
        float Puff=0.f;
        constexpr double PuffDecay=1.2;
        if(Job&&Smelt)
        {
            if(const FColdSteelSmeltingRecipe* Recipe=Smelt->Find(Job->Recipe))
            {
                const double Total=Smelt->JobTotalSeconds(Build,*Job,*Recipe);
                const double P=Job->ProgressSeconds;
                if(E.LastProgress>=0.&&P>E.LastProgress)
                {   // 本拍跨过整批边界（含一次跨多批，只在跨过的最后一拍写一次）
                    const double PrevBatch=Total>0.?FMath::FloorToDouble(E.LastProgress/Total):0.;
                    const double NowBatch=Total>0.?FMath::FloorToDouble(P/Total):0.;
                    if(NowBatch>PrevBatch)E.PuffAt=Now;
                }
                E.LastProgress=P;
            }
            else E.LastProgress=Job->ProgressSeconds;   // 配方下架：只记进度，不产脉冲
        }
        else if(!Job)E.LastProgress=-1.;   // 任务结束：下一批从头比较，不误判跨批
        if(E.PuffAt>0.&&Now-E.PuffAt<PuffDecay)Puff=float(1.-(Now-E.PuffAt)/PuffDecay);
        else if(E.PuffAt>0.)E.PuffAt=0.;   // 1.2s 到期即归零，不留给下一批误判
        // L1Gate：距 Eye<3500cm 且画质≥中（与 AllocateDetail 同一画质来源 Scalability::GetQualityLevels().EffectsQuality）。
        const float L1Gate=(Scalability::GetQualityLevels().EffectsQuality>=1
            &&FVector::DistSquared(Mouth,Eye)<=FMath::Square(3500.f))?1.f:0.f;
        if(!E.FX.IsValid())
        {
            if(!bWorking||!FurnaceAsset)continue;
            if(Alive>=6)
            {   // 池位满：置换离本机位最远、已断供且已散尽的一炉（无可见突变）。
                FFurnaceSmoke* Victim=nullptr;float Best=-1.f;
                for(auto& O:Furnaces)if(O.FX.IsValid()&&O.Rate<=0.f&&!O.FX->IsActive())
                {const float D=FVector::DistSquared(Mouth,O.FX->GetComponentLocation());if(D>Best){Best=D;Victim=&O;}}
                if(!Victim)continue;
                Victim->FX->DestroyComponent();Victim->FX.Reset();--Alive;
            }
            auto* FX=NewObject<UNiagaraComponent>(Piece,NAME_None,RF_Transient);
            Piece->AddInstanceComponent(FX);
            FX->SetAutoActivate(false);FX->SetAutoDestroy(false);FX->SetAsset(FurnaceAsset);
            FX->SetCastShadow(false);FX->SetCanEverAffectNavigation(false);FX->RegisterComponent();
            E.FX=FX;++Alive;
        }
        auto* FX=E.FX.Get();if(!FX)continue;
        FX->SetWorldLocation(Mouth);
        const float Target=bWorking?MaxRate:0.f;
        E.Rate=FMath::FInterpConstantTo(E.Rate,Target,dt,bWorking?18.f:6.f);   // 起烟≈0.7s 到位，停燃≈2.2s 缓断
        if(E.Rate<.05f)E.Rate=0.f;
        if(bWorking&&Now>=E.NextConfigure)
        {   ConfigureSmoke(FX,16);E.NextConfigure=Now+2.5;
            for(FSmoke& S:Smoke)if(S.FX.Get()==FX)S.bOwnWind=true; }   // 风场由此路接管（见下），共享风扫不再覆写
        FX->SetVariableFloat(TEXT("User.SpawnRate"),E.Rate);
        // v3 接管风场：基风（含屋檐遮蔽衰减）＋雨天随机方向低频阵风；User.Rainfall 同拍 5Hz 写，
        // 资产端用它在雨来时撕散摆动、压浮力、提前淡出、加速摊薄（Docs/Fluids/furnace-black-smoke-20260924.md）。
        const FVector Wind=WindWithGustAt(Mouth);
        FX->SetVariableVec3(TEXT("User.Wind"),FX->GetComponentTransform().InverseTransformVector(Wind));
        FX->SetVariableFloat(TEXT("User.Rainfall"),Rain);
        // v5 状态驱动：连续火力／点火年龄／整批脉冲／内芯层距离画质门（参数名均为编译期常量，热路径无字符串拼接）。
        FX->SetVariableFloat(TEXT("User.Heat"),Heat);
        if(bHaveIgnition)FX->SetVariableFloat(TEXT("User.Ignition"),Ignition);   // 熄火段不写＝资产端沿用断供曲线
        FX->SetVariableFloat(TEXT("User.Puff"),Puff);
        FX->SetVariableFloat(TEXT("User.L1Gate"),L1Gate);
        if(E.Rate>0.f)
        {
            if(!FX->IsActive())FX->Activate(true);
            E.LastFeed=Now;
        }
        else if(FX->IsActive()&&Now-E.LastFeed>Dissipate)FX->Deactivate();
    }
}

void UFluidPresentationSubsystem::RegisterWaterBody(UPrimitiveComponent* Body)
{
    if(!Body)return;
    for(const auto& Entry:WaterBodies)if(Entry.Body.Get()==Body)return;
    WaterBodies.RemoveAll([](const FWaterBody& Entry){return !Entry.Body.IsValid();});
    if(WaterBodies.Num()<256){FWaterBody Entry;Entry.Body=Body;WaterBodies.Add(Entry);}
}
void UFluidPresentationSubsystem::UpdateWaterBody(FWaterBody& Entry)
{
    auto* Body=Entry.Body.Get();if(!Body)return;
    const FVector Position=Body->Bounds.Origin-FVector(0,0,Body->Bounds.BoxExtent.Z);
    if(!Body->IsSimulatingPhysics()||!bHasView||FVector::DistSquared(Position,Eye)>FMath::Square(5000.f))
    {Entry.Initialized=false;return;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(Entry.Initialized&&Now>=Entry.NextHit&&FVector::DistSquared(Position,Entry.Previous)<FMath::Square(1600.f))
    {
        if(auto* Water=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
            if(Water->BodyWater(Entry.Previous,Position,Body->GetPhysicsLinearVelocity(),Body->Bounds.BoxExtent,Body->GetMass()))Entry.NextHit=Now+.65;
    }
    Entry.Previous=Position;Entry.Initialized=true;
}
