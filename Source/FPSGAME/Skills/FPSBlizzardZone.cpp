#include "FPSBlizzardZone.h"
#include "../Combat/RangedAttackQuery.h"
#include "BlizzardEnvironment.h"
#include "FireMagicArea.h"
#include "HolyLightTargets.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/SceneComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"

// 组件预热与远端副本自载共用同一张资产清单（顺序固定——InitializeZone 按下标取用）。
const TCHAR* const* AFPSBlizzardZone::ZoneAssetPaths()
{
    static const TCHAR* Paths[]={TEXT("/Game/Skills/StormClouds/RollingV1/NS_BlizzardStormCloud.NS_BlizzardStormCloud"),TEXT("/Game/Skills/Blizzard/IndoorV5/NS_BlizzardPrecipitation.NS_BlizzardPrecipitation"),
        TEXT("/Game/Skills/Blizzard/IndoorV5/NS_BlizzardBoundaryMist.NS_BlizzardBoundaryMist"),TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart.M_BlizzardIceHeart"),
        TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceShell.M_BlizzardIceShell"),TEXT("/Game/Skills/Blizzard/IndoorV5/M_BlizzardGroundFrost.M_BlizzardGroundFrost"),
        TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"),TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),
        TEXT("/Game/Skills/Blizzard/StormV2/S_BlizzardIceLanding.S_BlizzardIceLanding"),
        TEXT("/Game/Skills/StormClouds/RollingV1/NS_BlizzardGatherCloud.NS_BlizzardGatherCloud"),
        TEXT("/Game/Skills/Blizzard/IndoorV5/M_BlizzardAimPreview.M_BlizzardAimPreview"),
        TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_02.SM_IceSpike_02"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_03.SM_IceSpike_03")};
    return Paths;
}
bool AFPSBlizzardZone::HasBasicAssets(const TArray<TObjectPtr<UObject>>& Assets)
{
    return Assets.Num()==15&&(Cast<UNiagaraSystem>(Assets[1])||Cast<UNiagaraSystem>(Assets[2])||Cast<UMaterialInterface>(Assets[7]));
}

AFPSBlizzardZone::AFPSBlizzardZone()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    // 联机：服务端权威生成与伤害结算；远端副本按 NetCast/NetCenter 自建表现壳。
    bReplicates=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
void AFPSBlizzardZone::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSBlizzardZone,NetCaster);
    DOREPLIFETIME(AFPSBlizzardZone,NetCast);
    DOREPLIFETIME(AFPSBlizzardZone,NetCenter);
    DOREPLIFETIME(AFPSBlizzardZone,NetNormal);
    DOREPLIFETIME(AFPSBlizzardZone,NetAxis);
    DOREPLIFETIME(AFPSBlizzardZone,NetCloudHeight);
    DOREPLIFETIME(AFPSBlizzardZone,NetCloudThickness);
    DOREPLIFETIME(AFPSBlizzardZone,NetRoomCells);
    DOREPLIFETIME(AFPSBlizzardZone,NetStartedAt);
    DOREPLIFETIME(AFPSBlizzardZone,bNetFinished);
    DOREPLIFETIME(AFPSBlizzardZone,bNetActivated);
}
bool AFPSBlizzardZone::InitializeZone(APawn* Shooter,const FBlizzardCast& Spell,const FVector& Point,const FVector& Normal,const FVector& LongAxis,const TArray<TObjectPtr<UObject>>& Assets)
{
    if(!Shooter||!HasBasicAssets(Assets))return false;
    HitSound=Cast<USoundBase>(Assets[9]);
    LandingSound=Cast<USoundBase>(Assets[10]);
    Caster=Shooter;CastSnapshot=Spell;Center=Point;SurfaceNormal=FVector::UpVector;AxisX=FVector::VectorPlaneProject(LongAxis,SurfaceNormal).GetSafeNormal();AxisY=FVector::CrossProduct(SurfaceNormal,AxisX).GetSafeNormal();
    Random.Initialize(int32(GetUniqueID()));
    // 联机：权威侧把表现所需的口径写进复制态。
    if(HasAuthority())
    {
        RewardModel=NetCast::AuthorityModel(Shooter,GetGameInstance());
        NetCaster=Shooter;NetCast=Spell;NetCenter=Center;NetNormal=SurfaceNormal;NetAxis=AxisX;
        UpdateCloudClearance(true);
    }
    else {CloudHeight=NetCloudHeight;CloudThickness=NetCloudThickness;}
    if(NetRoomCells.Num()!=BlizzardEnvironment::VolumeCellCount||NetRoomCells[12].Z<=0)return false;
    if(GetNetMode()==NM_DedicatedServer)return true;
    auto MakeFX=[&](int32 Index)
    {
        if(!Cast<UNiagaraSystem>(Assets[Index]))return static_cast<UNiagaraComponent*>(nullptr);
        auto* FX=UNiagaraFunctionLibrary::SpawnSystemAttached(Cast<UNiagaraSystem>(Assets[Index]),RootComponent,NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
        if(FX)
        {
            FX->SetAbsolute(false,true,true);FX->SetVariablePosition(TEXT("User.CurrentPosition"),Center);
            FX->SetVariableVec3(TEXT("User.Side"),AxisX);FX->SetVariableVec3(TEXT("User.Up"),AxisY);FX->SetVariableVec3(TEXT("User.SurfaceNormal"),SurfaceNormal);
            FX->SetVariableFloat(TEXT("User.RadiusX"),CastSnapshot.RadiusX);FX->SetVariableFloat(TEXT("User.RadiusY"),CastSnapshot.RadiusY);FX->SetVariableFloat(TEXT("User.CloudHeight"),CloudHeight);
            FX->SetVariableFloat(TEXT("User.StormDuration"),FMath::Max(0.f,CastSnapshot.Duration-Age));
            if(Index==0){FX->SetVariableFloat(TEXT("User.StormDuration"),FMath::Max(0.f,CastSnapshot.Duration-Age));FX->SetVariableFloat(TEXT("User.CloudEmission"),1.f);FX->SetVariableFloat(TEXT("User.CloudThickness"),CloudThickness);}
            const float R=FMath::Max(CastSnapshot.RadiusX,CastSnapshot.RadiusY)*(Index==0?1.75f:1.f)+150;
            const float Height=BlizzardEnvironment::VerticalReach(CastSnapshot.RadiusY);
            FX->SetSystemFixedBounds(FBox(FVector(-R,-R,-Height-200),FVector(R,R,Height*2.f+200)));
            FX->AddTickPrerequisiteActor(this);FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        }
        return FX;
    };
    VisualLayers.SetNum(BlizzardEnvironment::MaxLayers);
    for(auto& Layer:VisualLayers)
    {
        Layer.Cloud=MakeFX(0);Layer.Snow=MakeFX(1);Layer.Mist=MakeFX(2);
        Layer.Frost=NewObject<UDecalComponent>(this);Layer.Frost->SetupAttachment(RootComponent);Layer.Frost->RegisterComponent();
        Layer.Frost->SetWorldLocation(Center+SurfaceNormal*8);Layer.Frost->SetWorldRotation(FRotationMatrix::MakeFromXZ(-SurfaceNormal,AxisY).Rotator());
        Layer.Frost->DecalSize=FVector(BlizzardEnvironment::VerticalReach(CastSnapshot.RadiusY)*2.f+100,CastSnapshot.RadiusX,CastSnapshot.RadiusY);
        Layer.Frost->SetDecalMaterial(Cast<UMaterialInterface>(Assets[7]));Layer.FrostMaterial=Layer.Frost->CreateDynamicMaterialInstance();
        Layer.Frost->SetVisibility(false);
    }
    auto MakeMesh=[&](const FString& Name,int32 MeshIndex,int32 MaterialIndex,int32 Count)
    {
        auto* Mesh=NewObject<UInstancedStaticMeshComponent>(this,FName(*Name));AddInstanceComponent(Mesh);Mesh->SetupAttachment(RootComponent);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
        Mesh->SetStaticMesh(Cast<UStaticMesh>(Assets[MeshIndex]));Mesh->SetMaterial(0,Cast<UMaterialInterface>(Assets[MaterialIndex]));Mesh->SetCastShadow(false);Mesh->SetCanEverAffectNavigation(false);Mesh->SetReceivesDecals(false);Mesh->RegisterComponent();
        for(int32 I=0;I<Count;++I)Mesh->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
        return Mesh;
    };
    bHasIce=Assets[3]&&Assets[4]&&Assets[5]&&Assets[6]&&Assets[13]&&Assets[14];
    if(bHasIce)
    {
    Hail=MakeMesh(TEXT("IceFragments"),4,3,24);
    for(int32 V=0;V<3;++V)
    {
        const int32 Index=V==0?5:12+V;
        SpikeHearts.Add(MakeMesh(FString::Printf(TEXT("IceHeart%d"),V),Index,3,8));
        SpikeShells.Add(MakeMesh(FString::Printf(TEXT("IceShell%d"),V),Index,6,8));
    }
    Spikes=SpikeHearts[0];
    }
    return VisualLayers[0].Snow||VisualLayers[0].Mist||VisualLayers[0].FrostMaterial;
}
void AFPSBlizzardZone::ActivateZone()
{
    NetStartedAt=GetWorld()->GetTimeSeconds();
    bActivated=true;bNetActivated=true;UpdatePresentation(0);
    ForceNetUpdate();
    DamageTick();NextDamage=CastSnapshot.TickSeconds;
}
void AFPSBlizzardZone::DamageTick()
{
    if(!HasAuthority())return; // 伤害结算只在权威端
    auto* Shooter=Caster.Get();auto* Model=RewardModel.Get();if(!Shooter||!Model)return;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BlizzardOverlap),false,Shooter);TArray<FOverlapResult> Overlaps;
    const float Height=BlizzardEnvironment::VerticalReach(CastSnapshot.RadiusY);
    const FQuat Orientation=FRotationMatrix::MakeFromX(AxisX).ToQuat();
    GetWorld()->OverlapMultiByObjectType(Overlaps,Center,Orientation,Objects,
        FCollisionShape::MakeBox(FVector(CastSnapshot.RadiusX,CastSnapshot.RadiusY,Height)),Query);
    TArray<FVector,TInlineAllocator<3>> Origins;BlizzardEnvironment::SightOrigins(Shooter,Center,Origins);
    TSet<AActor*> Seen;int32 Hits=0,AudibleHits=0;
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();if(!IsValid(Target)||Target==Shooter||Seen.Contains(Target))continue;Seen.Add(Target);
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Shooter,Target))continue;
        // Gameplay is a bounded 3D volume. It is independent of cosmetic floor
        // grids, feet touching ground, particle collisions and visual budgets.
        if(!BlizzardEnvironment::VolumeExposure(Shooter,Target,Center,AxisX,CastSnapshot.RadiusX,CastSnapshot.RadiusY,Origins))continue;
        const int32 Before=Rewards.Hits;if(Model->ApplyBlizzardHit(Shooter,Target,CastSnapshot,Rewards))++AudibleHits;Hits+=Rewards.Hits-Before;
    }
    Rewards.bMultiHit|=Hits>=2;
    if(AudibleHits>0&&HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Center,.45f);
}
void AFPSBlizzardZone::Finish()
{
    if(bFinished)return;bFinished=true;
    if(HasAuthority())
    {
        bNetFinished=true;ForceNetUpdate();
        auto Batch=MoveTemp(Rewards);Rewards={};
        auto* Model=RewardModel.Get();RewardModel.Reset();
        const auto* Health=Caster.IsValid()?Caster->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(Model&&(!Health||!Health->IsDead()))Model->FinishBlizzardCast(Batch);
    }
}
void AFPSBlizzardZone::FinishForRemoval()
{
    if(HasAuthority()&&bActivated)Finish();
}
void AFPSBlizzardZone::UpdateCloudClearance(bool bForce)
{
    if(!HasAuthority()||(!bForce&&Age<NextCloudProbe))return;
    NextCloudProbe=Age+.5f;
    auto* Shooter=Caster.Get();if(!Shooter)return;
    BlizzardEnvironment::BuildVolumeCells(Shooter,Center,AxisX,CastSnapshot.RadiusX,CastSnapshot.RadiusY,NetRoomCells);
    CloudHeight=BlizzardEnvironment::VerticalReach(CastSnapshot.RadiusY);
    CloudThickness=FMath::Clamp(CloudHeight*.46f,8.f,240.f);
    NetCloudHeight=CloudHeight;NetCloudThickness=CloudThickness;
    bRoomGridDirty=true;
}
void AFPSBlizzardZone::SpawnChunk()
{
    if(!bHasIce||NetRoomCells.Num()!=BlizzardEnvironment::VolumeCellCount)return;
    for(int32 I=0;I<24;++I)if(!Chunks[I].bActive)
    {
        TArray<int32,TInlineAllocator<BlizzardEnvironment::VolumeCellCount>> ActiveCells;
        for(int32 J=0;J<NetRoomCells.Num();++J)if(NetRoomCells[J].Z>0.f)ActiveCells.Add(J);
        if(ActiveCells.IsEmpty())return;
        const int32 Index=ActiveCells[Random.RandRange(0,ActiveCells.Num()-1)],Cell=Index%BlizzardEnvironment::CellCount;
        FVector Room=NetRoomCells[Index];Room.Y=FMath::Min(Room.Y,double(CloudHeight));
        auto& C=Chunks[I];C.FloorZ=Center.Z+Room.X;C.Layer=Index/BlizzardEnvironment::CellCount;
        C.Size=FMath::Min(Random.FRandRange(38.f,64.f),float(Room.Y)*.22f);
        C.Position=Center+BlizzardEnvironment::CellOffset(Cell,CastSnapshot.RadiusX,CastSnapshot.RadiusY,AxisX)+
            AxisX*Random.FRandRange(-.13f,.13f)*CastSnapshot.RadiusX*Room.Z+AxisY*Random.FRandRange(-.13f,.13f)*CastSnapshot.RadiusY*Room.Z;
        C.Position.Z=C.FloorZ+Room.Y-C.Size*.5f-4;
        C.Velocity=-SurfaceNormal*FMath::Min(Random.FRandRange(360,520),float(Room.Y)*2.f);
        C.Age=0;C.Roll=Random.FRandRange(0.f,2*PI);C.bActive=true;C.bFragment=false;break;
    }
}
void AFPSBlizzardZone::ScatterFragments(const FVector& Point,const FVector& Normal,int32 Layer)
{
    if(!bHasIce)return;
    int32 Count=0;
    for(int32 I=24;I<48&&Count<3;++I)if(!Chunks[I].bActive)
    {
        auto& C=Chunks[I];C.Position=Point+Normal*5;C.Velocity=Normal*Random.FRandRange(90,150)+AxisX*Random.FRandRange(-80,80)+AxisY*Random.FRandRange(-80,80);
        C.FloorZ=Point.Z;C.Layer=Layer;C.Age=0;C.Size=Random.FRandRange(5,10);C.Roll=Random.FRandRange(0.f,2*PI);C.bActive=C.bFragment=true;++Count;
    }
}
void AFPSBlizzardZone::PlayLandingSound(const FVector& Point,bool bSnowball)
{
    if(!LandingSound||Age<NextLandingSound)return;
    NextLandingSound=Age+.14f;
    UGameplayStatics::PlaySoundAtLocation(this,LandingSound,Point,bSnowball?.36f:.58f,
        Random.FRandRange(bSnowball?.86f:.97f,bSnowball?.98f:1.07f));
}
void AFPSBlizzardZone::UpdatePresentation(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(!HasAuthority()){CloudHeight=NetCloudHeight;CloudThickness=NetCloudThickness;}
    if(NetRoomCells.Num()!=BlizzardEnvironment::VolumeCellCount)return;
    if(CloudRoomCells.Num()!=NetRoomCells.Num())CloudRoomCells=NetRoomCells;
    for(int32 L=0;L<VisualLayers.Num();++L)
    {
        auto& Layer=VisualLayers[L];bool Active=false,CloudChanged=bRoomGridDirty;
        TArray<FVector> LocalCells;LocalCells.Reserve(BlizzardEnvironment::CellCount);
        for(int32 I=0;I<BlizzardEnvironment::CellCount;++I)
        {
            const int32 Index=L*BlizzardEnvironment::CellCount+I;
            const FVector Target=NetRoomCells[Index];FVector& Current=CloudRoomCells[Index];
            FVector Next=Current.Z<=0||Target.Z<=0||FMath::Abs(Current.X-Target.X)>180.f?Target:FMath::VInterpTo(Current,Target,Delta,7.f);
            // A newly lowered ceiling clips immediately; easing never raises
            // clouds through a solid roof or carries a cloud into a closed cell.
            Next.Z=Target.Z;
            Next.Y=FMath::Max(0.,FMath::Min(Next.X+Next.Y,Target.X+Target.Y)-Next.X);
            if(!Current.Equals(Next,.05f)){Current=Next;CloudChanged=true;}
            Active|=Target.Z>0.f;
            LocalCells.Add(FVector(Target.X,FMath::Min(Target.Y,double(CloudHeight)),Target.Z));
        }
        if(bRoomGridDirty)
        {
            for(auto* FX:{Layer.Snow.Get(),Layer.Mist.Get()})if(FX)
                for(int32 I=0;I<BlizzardEnvironment::CellCount;++I)FX->SetVariableVec3(BlizzardEnvironment::CellParameter(I,true),LocalCells[I]);
            BlizzardEnvironment::MaterialCells(Layer.FrostMaterial,Center,AxisX,CastSnapshot.RadiusX,CastSnapshot.RadiusY,LocalCells);
            for(auto* FX:{Layer.Cloud.Get(),Layer.Snow.Get()})if(FX)FX->SetVariableFloat(TEXT("User.CloudHeight"),CloudHeight);
            if(Layer.Cloud)Layer.Cloud->SetVariableFloat(TEXT("User.CloudThickness"),CloudThickness);
        }
        if(CloudChanged&&Layer.Cloud)
            for(int32 I=0;I<BlizzardEnvironment::CellCount;++I)Layer.Cloud->SetVariableVec3(BlizzardEnvironment::CellParameter(I,true),CloudRoomCells[L*BlizzardEnvironment::CellCount+I]);
        // Room parameters must exist before a one-shot cloud spawn is activated.
        if(Layer.bActive!=Active)
        {
            Layer.bActive=Active;
            for(auto* FX:{Layer.Cloud.Get(),Layer.Snow.Get(),Layer.Mist.Get()})if(FX)
            {if(Active&&!bFinished)FX->Activate(true);else FX->DeactivateImmediate();}
            if(Layer.Frost)Layer.Frost->SetVisibility(Active);
        }
    }
    bRoomGridDirty=false;
    const float Fade=FMath::Min(FMath::Clamp(Age/.25f,0.f,1.f),FMath::Clamp((CastSnapshot.Duration+.6f-Age)/.6f,0.f,1.f));
    CosmeticClock-=Delta;
    auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    if(CosmeticClock<=0)
    {
        CosmeticClock=.2f;Detail=Fluid?float(Fluid->AllocateDetail(Center,16))/16.f:1.f;
        Wind=Fluid?Fluid->WindAt(Center+SurfaceNormal*35):FVector::ZeroVector;
        // The cloud is a local storm; outside weather only adds a small common drift.
        const FVector StormWind=Wind*.22f+AxisX*30;
        for(auto& Layer:VisualLayers)
            for(auto* FX:{Layer.Cloud.Get(),Layer.Snow.Get(),Layer.Mist.Get()})if(FX)
            {FX->SetVariableVec3(TEXT("User.Wind"),StormWind);FX->SetVariableFloat(TEXT("User.DetailReduction"),1-Detail);}
    }
    for(auto& Layer:VisualLayers)if(Layer.bActive)
    {
        if(Layer.Cloud){Layer.Cloud->SetVariableFloat(TEXT("User.Strength"),Fade);Layer.Cloud->SetVariableFloat(TEXT("User.CloudEmission"),bFinished?0.f:1.f);}
        for(auto* FX:{Layer.Snow.Get(),Layer.Mist.Get()})if(FX)FX->SetVariableFloat(TEXT("User.Strength"),bFinished?0.f:Fade);
        if(Layer.FrostMaterial)Layer.FrostMaterial->SetScalarParameterValue(TEXT("Fade"),Fade*.45f*(.96f+.04f*FMath::Sin(Age*2)));
    }
    SpawnClock+=Delta;
    if(SpawnClock>=.05f)
    {SpawnClock=FMath::Fmod(SpawnClock,.05f);if(!bFinished&&Random.FRand()<Detail)SpawnChunk();}
    bool DirtyHail=false;bool DirtyVariant[3]={false,false,false};
    for(int32 I=0;I<48;++I)
    {
        auto& C=Chunks[I];if(!C.bActive)continue;
        const FVector Previous=C.Position;C.Age+=Delta;C.Velocity-=SurfaceNormal*(780*Delta);C.Position+=C.Velocity*Delta;
        bool HitSurface=false;FVector Impact,ImpactNormal=SurfaceNormal;
        if(!C.bFragment&&Fluid&&Fluid->ReserveGeometryQueries(1))
        {
            FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(BlizzardHail),false,this);
            // Match the current IceSpike mesh: tip along local +X, 54 cm length.
            const FVector TipOffset=C.Velocity.GetSafeNormal()*(C.Size*.5f);
            if(RangedAttackQuery::LineTraceSingle(GetWorld(), Caster.Get(), Hit,Previous+TipOffset,C.Position+TipOffset,ECC_Visibility,Query))
            {HitSurface=true;Impact=Hit.ImpactPoint;ImpactNormal=Hit.ImpactNormal;}
        }
        const int32 XYCell=BlizzardEnvironment::CellAt(C.Position-Center,CastSnapshot.RadiusX,CastSnapshot.RadiusY,AxisX);
        const int32 Cell=XYCell==INDEX_NONE?INDEX_NONE:C.Layer*BlizzardEnvironment::CellCount+XYCell;
        if(!NetRoomCells.IsValidIndex(Cell)||NetRoomCells[Cell].Z<=0)C.Age=4.f;
        else if(C.Position.Z>Center.Z+NetRoomCells[Cell].X+NetRoomCells[Cell].Y)C.Age=4.f;
        const float Height=C.Position.Z-C.FloorZ;
        if(!HitSurface&&Height<=C.Size*.5f){HitSurface=true;Impact=C.Position-SurfaceNormal*Height;}
        if(HitSurface||C.Age>(C.bFragment?.35f:3.f))
        {
            C.bActive=false;
            if(HitSurface&&!C.bFragment&&!bFinished)
            {
                if(Fluid)Fluid->EmitColdImpact(Impact,ImpactNormal);
                PlayLandingSound(Impact,false);
                ScatterFragments(Impact,ImpactNormal,C.Layer);
            }
        }
        const FVector Direction=C.Velocity.GetSafeNormal();
        const FQuat Rotation=FRotationMatrix::MakeFromX(Direction.IsNearlyZero()?-SurfaceNormal:Direction).ToQuat()*FQuat(FVector::ForwardVector,C.Roll);
        const float Scale=C.Size/(C.bFragment?100.f:54.f)*(bFinished?Fade:1.f);
        const FVector Size=C.bActive?FVector(Scale):FVector::ZeroVector;
        if(I<24)
        {
            const int32 Variant=I%3,Slot=I/3;
            SpikeHearts[Variant]->UpdateInstanceTransform(Slot,FTransform(Rotation,C.Position,Size*FVector(.965f,.78f,.78f)),true,false,true);
            SpikeShells[Variant]->UpdateInstanceTransform(Slot,FTransform(Rotation,C.Position,Size),true,false,true);
            DirtyVariant[Variant]=true;
        }
        else
        {
            Hail->UpdateInstanceTransform(I-24,FTransform(Rotation,C.Position,Size),true,false,true);DirtyHail=true;
        }
    }
    if(DirtyHail)Hail->MarkRenderStateDirty();
    for(int32 V=0;V<3;++V)if(DirtyVariant[V]){SpikeHearts[V]->MarkRenderStateDirty();SpikeShells[V]->MarkRenderStateDirty();}
}
void AFPSBlizzardZone::Tick(float Delta)
{
    Super::Tick(Delta);
    // 远端副本：等复制字段就位后自建表现壳；只演风暴，不跑伤害。
    if(!HasAuthority())
    {
        NetInit();
        if(!bNetInit)return;
        const auto* State=GetWorld()->GetGameState<AGameStateBase>();
        if(!State)return;
        Age=FMath::Max(Age,float(State->GetServerWorldTimeSeconds()-NetStartedAt));
        if(bNetFinished||Age>=CastSnapshot.Duration)Finish();
        UpdatePresentation(Delta);
        if(Age>=CastSnapshot.Duration+.6f)Destroy();
        return;
    }
    const auto* Shooter=Caster.Get();const auto* Health=Shooter?Shooter->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Shooter||(Health&&Health->IsDead())){Destroy();return;}
    if(!bActivated)return;
    Age=FMath::Max(Age,float(GetWorld()->GetTimeSeconds()-NetStartedAt));
    UpdateCloudClearance();
    // Match GroundZone's immediate tick and exclude the exact duration endpoint.
    while(NextDamage<CastSnapshot.Duration-UE_KINDA_SMALL_NUMBER&&NextDamage<=Age&&!bFinished)
    {DamageTick();NextDamage+=CastSnapshot.TickSeconds;}
    if(Age>=CastSnapshot.Duration)Finish();
    UpdatePresentation(Delta);if(Age>=CastSnapshot.Duration+.6f)Destroy();
}
// Remote regions request assets once; cold caches never synchronously load in Tick.
void AFPSBlizzardZone::NetInit()
{
    if(bNetInit||!NetCaster||NetCast.RadiusX<=0||!bNetActivated||NetRoomCells.Num()!=BlizzardEnvironment::VolumeCellCount)return;
    const auto* State=GetWorld()->GetGameState<AGameStateBase>();if(!State)return;
    Age=FMath::Max(0.f,float(State->GetServerWorldTimeSeconds()-NetStartedAt));
    if(Age>=NetCast.Duration+.6f){Destroy();return;}
    if(!bNetAssetsRequested)
    {
        bNetAssetsRequested=true;TArray<FSoftObjectPath> Requests;
        const TCHAR* const* Paths=ZoneAssetPaths();for(int32 I=0;I<15;++I)Requests.Emplace(Paths[I]);
        NetAssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Requests,FStreamableDelegate::CreateWeakLambda(this,[this,Requests]()
        {
            for(const auto& Path:Requests)NetAssets.Add(Path.ResolveObject());
            bNetAssetsReady=HasBasicAssets(NetAssets);
            if(!bNetAssetsReady)Destroy();
        }));
    }
    if(!bNetAssetsReady)return;
    if(!InitializeZone(NetCaster,NetCast,NetCenter,NetNormal,NetAxis,NetAssets)){Destroy();return;}
    bNetInit=true;
    bActivated=true;bFinished=bNetFinished||Age>=CastSnapshot.Duration;UpdatePresentation(0);
}
void AFPSBlizzardZone::EndPlay(EEndPlayReason::Type Reason)
{
    // Disconnect/travel settle before saving; destruction is an idempotent fallback.
    // Finish retains the existing policy of discarding the batch on caster death.
    FinishForRemoval();
    for(auto& Layer:VisualLayers)
        for(auto* FX:{Layer.Cloud.Get(),Layer.Snow.Get(),Layer.Mist.Get()})if(FX)FX->DestroyComponent();
    if(NetAssetLoad)NetAssetLoad->CancelHandle();NetAssetLoad.Reset();NetAssets.Reset();
    Super::EndPlay(Reason);
}
