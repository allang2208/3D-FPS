#include "FPSBlizzardZone.h"
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
    static const TCHAR* Paths[]={TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud.NS_BlizzardStormCloud"),TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardPrecipitation.NS_BlizzardPrecipitation"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardBoundaryMist.NS_BlizzardBoundaryMist"),TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart.M_BlizzardIceHeart"),
        TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceShell.M_BlizzardIceShell"),TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardGroundFrost.M_BlizzardGroundFrost"),
        TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"),TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),
        TEXT("/Game/Skills/Blizzard/StormV2/S_BlizzardIceLanding.S_BlizzardIceLanding"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardGatherCloud.NS_BlizzardGatherCloud"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardAimPreview.M_BlizzardAimPreview"),
        TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_02.SM_IceSpike_02"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_03.SM_IceSpike_03")};
    return Paths;
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
    DOREPLIFETIME(AFPSBlizzardZone,bNetActivated);
}
bool AFPSBlizzardZone::InitializeZone(APawn* Shooter,const FBlizzardCast& Spell,const FVector& Point,const FVector& Normal,const FVector& LongAxis,const TArray<TObjectPtr<UObject>>& Assets)
{
    if(!Shooter||Assets.Num()!=15||Assets.Contains(nullptr))return false;
    HitSound=Cast<USoundBase>(Assets[9]);
    LandingSound=Cast<USoundBase>(Assets[10]);
    Caster=Shooter;CastSnapshot=Spell;Center=Point;SurfaceNormal=Normal.GetSafeNormal();AxisX=LongAxis.GetSafeNormal();AxisY=FVector::CrossProduct(SurfaceNormal,AxisX).GetSafeNormal();
    Random.Initialize(int32(GetUniqueID()));CloudHeight=CastSnapshot.RadiusY*2.3f+150;
    FHitResult Roof;
    if(FireMagic::TraceSurface(Shooter,Center+SurfaceNormal*25,Center+SurfaceNormal*CloudHeight,Roof))CloudHeight=FMath::Max(65.f,float(FVector::DotProduct(Roof.ImpactPoint-Center,SurfaceNormal)-45));
    // 联机：权威侧把表现所需的口径写进复制态。
    NetCaster=Shooter;NetCast=Spell;NetCenter=Center;NetNormal=SurfaceNormal;NetAxis=AxisX;NetCloudHeight=CloudHeight;
    auto MakeFX=[&](int32 Index)
    {
        auto* FX=UNiagaraFunctionLibrary::SpawnSystemAttached(Cast<UNiagaraSystem>(Assets[Index]),RootComponent,NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
        if(FX)
        {
            FX->SetAbsolute(false,true,true);FX->SetVariablePosition(TEXT("User.CurrentPosition"),Center);
            FX->SetVariableVec3(TEXT("User.Side"),AxisX);FX->SetVariableVec3(TEXT("User.Up"),AxisY);FX->SetVariableVec3(TEXT("User.SurfaceNormal"),SurfaceNormal);
            FX->SetVariableFloat(TEXT("User.RadiusX"),CastSnapshot.RadiusX);FX->SetVariableFloat(TEXT("User.RadiusY"),CastSnapshot.RadiusY);FX->SetVariableFloat(TEXT("User.CloudHeight"),CloudHeight);
            if(Index==0){FX->SetVariableFloat(TEXT("User.StormDuration"),CastSnapshot.Duration);FX->SetVariableFloat(TEXT("User.CloudEmission"),1.f);}
            const float R=FMath::Max(CastSnapshot.RadiusX,CastSnapshot.RadiusY)*(Index==0?1.75f:1.f)+150;
            FX->SetSystemFixedBounds(FBox(FVector(-R,-R,-120),FVector(R,R,CloudHeight+250)));
            FX->AddTickPrerequisiteActor(this);FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        }
        return FX;
    };
    CloudFX=MakeFX(0);SnowFX=MakeFX(1);MistFX=MakeFX(2);
    Frost=NewObject<UDecalComponent>(this);Frost->SetupAttachment(RootComponent);Frost->RegisterComponent();
    Frost->SetWorldLocation(Center+SurfaceNormal*8);Frost->SetWorldRotation(FRotationMatrix::MakeFromXZ(-SurfaceNormal,AxisY).Rotator());
    Frost->DecalSize=FVector(30,CastSnapshot.RadiusX,CastSnapshot.RadiusY);
    Frost->SetDecalMaterial(Cast<UMaterialInterface>(Assets[7]));FrostMID=Frost->CreateDynamicMaterialInstance();
    auto MakeMesh=[&](const FString& Name,int32 MeshIndex,int32 MaterialIndex,int32 Count)
    {
        auto* Mesh=NewObject<UInstancedStaticMeshComponent>(this,FName(*Name));AddInstanceComponent(Mesh);Mesh->SetupAttachment(RootComponent);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
        Mesh->SetStaticMesh(Cast<UStaticMesh>(Assets[MeshIndex]));Mesh->SetMaterial(0,Cast<UMaterialInterface>(Assets[MaterialIndex]));Mesh->SetCastShadow(false);Mesh->SetCanEverAffectNavigation(false);Mesh->SetReceivesDecals(false);Mesh->RegisterComponent();
        for(int32 I=0;I<Count;++I)Mesh->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
        return Mesh;
    };
    Hail=MakeMesh(TEXT("IceFragments"),4,3,24);
    for(int32 V=0;V<3;++V)
    {
        const int32 Index=V==0?5:12+V;
        SpikeHearts.Add(MakeMesh(FString::Printf(TEXT("IceHeart%d"),V),Index,3,8));
        SpikeShells.Add(MakeMesh(FString::Printf(TEXT("IceShell%d"),V),Index,6,8));
    }
    Spikes=SpikeHearts[0];
    return CloudFX&&SnowFX&&MistFX&&FrostMID&&Hail->GetStaticMesh()&&Spikes->GetStaticMesh();
}
void AFPSBlizzardZone::ActivateZone()
{
    bActivated=true;bNetActivated=true;UpdatePresentation(0);CloudFX->Activate(true);SnowFX->Activate(true);MistFX->Activate(true);
    DamageTick();NextDamage=CastSnapshot.TickSeconds;
}
void AFPSBlizzardZone::DamageTick()
{
    if(!HasAuthority())return; // 伤害结算只在权威端
    auto* Shooter=Caster.Get();auto* Model=NetCast::AuthorityModel(Shooter,GetGameInstance());if(!Shooter||!Model)return;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BlizzardOverlap),false,Shooter);TArray<FOverlapResult> Overlaps;
    const float Radius=FMath::Max(CastSnapshot.RadiusX,CastSnapshot.RadiusY);
    GetWorld()->OverlapMultiByObjectType(Overlaps,Center+SurfaceNormal*150,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius+200),Query);
    TSet<AActor*> Seen;int32 Hits=0,AudibleHits=0;
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();if(!IsValid(Target)||Target==Shooter||Seen.Contains(Target))continue;Seen.Add(Target);
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))continue;
        FVector Origin,Extent;Target->GetActorBounds(true,Origin,Extent);FVector Feet=Origin-FVector(0,0,Extent.Z);float BodyRadius=FMath::Min(Extent.X,Extent.Y);
        if(const auto* Capsule=Target->FindComponentByClass<UCapsuleComponent>())
        {Feet=Capsule->GetComponentLocation()-FVector(0,0,Capsule->GetScaledCapsuleHalfHeight());BodyRadius=Capsule->GetScaledCapsuleRadius();}
        const FVector Offset=Feet-Center;
        if(FMath::Abs(FVector::DotProduct(Offset,SurfaceNormal))>100)continue;
        const float X=FVector::DotProduct(Offset,AxisX)/(CastSnapshot.RadiusX+BodyRadius),Y=FVector::DotProduct(Offset,AxisY)/(CastSnapshot.RadiusY+BodyRadius);
        if(X*X+Y*Y>1)continue;
        FHitResult Block;if(FireMagic::TraceSurface(Shooter,Center+SurfaceNormal*35,Feet+SurfaceNormal*35,Block))continue;
        const int32 Before=Rewards.Hits;if(Model->ApplyBlizzardHit(Shooter,Target,CastSnapshot,Rewards))++AudibleHits;Hits+=Rewards.Hits-Before;
    }
    Rewards.bMultiHit|=Hits>=2;
    if(AudibleHits>0&&HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Center,.45f);
}
void AFPSBlizzardZone::Finish()
{
    if(bFinished)return;bFinished=true;
    if(auto* Model=NetCast::AuthorityModel(Caster.Get(),GetGameInstance()))Model->FinishBlizzardCast(Rewards);
}
void AFPSBlizzardZone::SpawnChunk()
{
    for(int32 I=0;I<24;++I)if(!Chunks[I].bActive)
    {
        auto& C=Chunks[I];const float A=Random.FRand()*2*PI,R=FMath::Sqrt(Random.FRand());
        C.Position=Center+AxisX*(FMath::Cos(A)*R*CastSnapshot.RadiusX)+AxisY*(FMath::Sin(A)*R*CastSnapshot.RadiusY)+SurfaceNormal*(CloudHeight-20);
        C.Velocity=-SurfaceNormal*Random.FRandRange(360,520)+Wind*.18f;C.Age=0;C.Size=Random.FRandRange(38.f,64.f);C.Roll=Random.FRandRange(0.f,2*PI);C.bActive=true;C.bFragment=false;break;
    }
}
void AFPSBlizzardZone::ScatterFragments(const FVector& Point,const FVector& Normal)
{
    int32 Count=0;
    for(int32 I=24;I<48&&Count<3;++I)if(!Chunks[I].bActive)
    {
        auto& C=Chunks[I];C.Position=Point+Normal*5;C.Velocity=Normal*Random.FRandRange(90,150)+AxisX*Random.FRandRange(-80,80)+AxisY*Random.FRandRange(-80,80);
        C.Age=0;C.Size=Random.FRandRange(5,10);C.Roll=Random.FRandRange(0.f,2*PI);C.bActive=C.bFragment=true;++Count;
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
    const float Fade=FMath::Min(FMath::Clamp(Age/.25f,0.f,1.f),FMath::Clamp((CastSnapshot.Duration+.6f-Age)/.6f,0.f,1.f));
    CosmeticClock-=Delta;
    auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    if(CosmeticClock<=0)
    {
        CosmeticClock=.2f;Detail=Fluid?float(Fluid->AllocateDetail(Center,16))/16.f:1.f;
        Wind=Fluid?Fluid->WindAt(Center+SurfaceNormal*35):FVector::ZeroVector;
        // The cloud is a local storm; outside weather only adds a small common drift.
        const FVector StormWind=Wind*.22f+AxisX*30;
        for(auto* FX:{CloudFX.Get(),SnowFX.Get(),MistFX.Get()})if(FX)
        {FX->SetVariableVec3(TEXT("User.Wind"),StormWind);FX->SetVariableFloat(TEXT("User.DetailReduction"),1-Detail);}
    }
    if(CloudFX){CloudFX->SetVariableFloat(TEXT("User.Strength"),Fade);CloudFX->SetVariableFloat(TEXT("User.CloudEmission"),bFinished?0.f:1.f);}
    for(auto* FX:{SnowFX.Get(),MistFX.Get()})if(FX)FX->SetVariableFloat(TEXT("User.Strength"),bFinished?0.f:Fade);
    if(FrostMID)FrostMID->SetScalarParameterValue(TEXT("Fade"),Fade*.45f*(.96f+.04f*FMath::Sin(Age*2)));
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
            if(GetWorld()->LineTraceSingleByChannel(Hit,Previous+TipOffset,C.Position+TipOffset,ECC_Visibility,Query))
            {HitSurface=true;Impact=Hit.ImpactPoint;ImpactNormal=Hit.ImpactNormal;}
        }
        const float Height=FVector::DotProduct(C.Position-Center,SurfaceNormal);
        if(!HitSurface&&Height<=C.Size*.5f){HitSurface=true;Impact=C.Position-SurfaceNormal*Height;}
        if(HitSurface||C.Age>(C.bFragment?.35f:3.f))
        {
            C.bActive=false;
            if(HitSurface&&!C.bFragment&&!bFinished)
            {
                if(Fluid)Fluid->EmitColdImpact(Impact,ImpactNormal);
                PlayLandingSound(Impact,false);
                ScatterFragments(Impact,ImpactNormal);
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
        Age+=Delta;
        UpdatePresentation(Delta);
        if(Age>=CastSnapshot.Duration+.6f)Destroy();
        return;
    }
    const auto* Shooter=Caster.Get();const auto* Health=Shooter?Shooter->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Shooter||(Health&&Health->IsDead())){Destroy();return;}
    if(!bActivated)return;
    Age+=Delta;
    // Match GroundZone's immediate tick and exclude the exact duration endpoint.
    while(NextDamage<CastSnapshot.Duration-UE_KINDA_SMALL_NUMBER&&NextDamage<=Age&&!bFinished)
    {DamageTick();NextDamage+=CastSnapshot.TickSeconds;}
    if(Age>=CastSnapshot.Duration)Finish();
    UpdatePresentation(Delta);if(Age>=CastSnapshot.Duration+.6f)Destroy();
}
// 远端副本初始化：复制字段就位后自载资产并复用 InitializeZone 建表现壳。
void AFPSBlizzardZone::NetInit()
{
    if(bNetInit||!NetCaster||NetCast.RadiusX<=0)return;
    if(NetCloudHeight<=0)return; // 首包可能尚未全到
    TArray<TObjectPtr<UObject>> Assets;
    const TCHAR* const* Paths=ZoneAssetPaths();
    for(int32 I=0;I<15;++I){UObject* Asset=LoadObject<UObject>(nullptr,Paths[I]);if(!Asset)return;Assets.Add(Asset);}
    if(!InitializeZone(NetCaster,NetCast,NetCenter,NetNormal,NetAxis,Assets))return;
    bNetInit=true;
    if(bNetActivated){bActivated=true;CloudFX->Activate(true);SnowFX->Activate(true);MistFX->Activate(true);}
}
void AFPSBlizzardZone::EndPlay(EEndPlayReason::Type Reason)
{
    // Death/scene exit discard unfinished training, as in the original clearZones().
    for(auto* FX:{CloudFX.Get(),SnowFX.Get(),MistFX.Get()})if(FX)FX->DestroyComponent();
    Super::EndPlay(Reason);
}
