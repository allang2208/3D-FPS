#include "VillageDefenseSection.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "VillageMasonry.h"
#include "SmithYardLamp.h"
#include "Components/ChildActorComponent.h"
#include "VillageDefenseRepairTargets.h"
#include "VillageDefenseState.h"
#include "../Building/VoxelBuildWorld.h"
#include "VillageDefenseDebris.h"
#include "HighVillageCollapse.h"
#include "HighVillageDefense.h"
#include "EngineUtils.h"
#include "TemperateHillsWorld.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "../Monsters/WolfMonster.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/OverlapResult.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

namespace
{
    const FSoftObjectPath GroundWearMaterial = VillageMasonry::CastleMesh(TEXT("M_DefenseGroundWear"));
    const FSoftObjectPath HighTowerMesh(FString(VillageMasonry::CastleFolder) +
        TEXT("SquareKeep/SM_HighWatchtower.SM_HighWatchtower"));
}

AVillageDefenseSection::AVillageDefenseSection()
{
    PrimaryActorTick.bCanEverTick=false;bReplicates=true;bAlwaysRelevant=true;
    // The projected end of a wall walk uses the replicated yaw as its socket frame.
    GetReplicatedMovement_Mutable().RotationQuantizationLevel=ERotatorQuantization::ShortComponents;
    AutoPossessAI=EAutoPossessAI::Disabled;AIControllerClass=nullptr;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Masonry=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Masonry"));Masonry->SetupAttachment(RootComponent);
    Masonry->SetMobility(EComponentMobility::Movable);Masonry->SetCollisionProfileName(TEXT("BlockAll"));
    Masonry->SetGenerateOverlapEvents(false);Masonry->SetReceivesDecals(false);
    Masonry->ComponentTags.Add(TEXT("HillsVillagePerimeter"));Tags.Add(TEXT("VillageDefense"));
    // Damageable wall bays/piers share the ground and airborne traversal path.
    Masonry->ComponentTags.Add(TEXT("Traversal.FixedStructure"));
}
void AVillageDefenseSection::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    if(!IsRunningDedicatedServer())Paths.AddUnique(GroundWearMaterial);
    for(const TCHAR* MeshRole:{TEXT("GateWide"),TEXT("GateNarrow"),TEXT("GateWideRight"),TEXT("GateNarrowRight"),TEXT("GateHingeMount"),TEXT("GateHingeMountRight"),TEXT("WoodShard")})
        Paths.AddUnique(FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_%s.SM_%s"),MeshRole,MeshRole)));
    Paths.AddUnique(VillageMasonry::Mesh(TEXT("SM_StoneChunkA")));
    Paths.AddUnique(VillageMasonry::Mesh(TEXT("SM_StoneChunkB")));
}
void AVillageDefenseSection::Initialize(ATemperateHillsWorld* Hills,int32 Id,const FSoftObjectPath& Mesh,float Maximum,const FGuid& BuiltId)
{
    SetOwner(Hills);WorldId=Hills->WorldId;SectionId=Id;MeshPath=Mesh;MaximumHealth=Maximum;
    PlacedId=BuiltId;
    Health=GetWorld()->GetSubsystem<UVillageDefenseState>()->Restore(WorldId,SectionId,Maximum,PlacedId);
    OnRep_Setup();
}
bool AVillageDefenseSection::IsRepairedCurtain() const
{
    static const auto A=VillageMasonry::CastleMesh(TEXT("SM_VillageWallRepairedA"));
    static const auto B=VillageMasonry::CastleMesh(TEXT("SM_VillageWallRepairedB"));
    return MeshPath==A || MeshPath==B;
}

void AVillageDefenseSection::SetWallInterval(FVector2D Interval)
{
    if(WallInterval==Interval)return;
    FlushNetDormancy();
    WallInterval=Interval;
    OnRep_WallInterval();
    ForceNetUpdate();
}

void AVillageDefenseSection::OnRep_WallInterval()
{
    Masonry->SetRelativeLocation(FVector((WallInterval.X+WallInterval.Y)*.5,0,0));
    Masonry->SetRelativeScale3D(FVector(IsGateCovered()?1.:(WallInterval.Y-WallInterval.X)/300.,1.,1.));
    if(GroundWear)SetupGroundWear();
    ApplyHealth();
}

void AVillageDefenseSection::BeginPlay()
{
    Super::BeginPlay();
    OnRep_Setup();
    if(HasAuthority())
    {
        // Dynamic spawn rounds scale to tenths. Each generated bay has a site-specific length.
        if(!PlacedId.IsValid())FixedScale=GetActorScale3D();
        if(IsA<AHighVillageWall>() || IsRepairedCurtain())
            for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)It->ApplyGateCutToWall(*this);
        SetNetDormancy(DORM_DormantAll);
    }
}
void AVillageDefenseSection::OnRep_FixedScale()
{
    SetActorScale3D(FixedScale);
    if(GroundWear)SetupGroundWear();
    if(MeshPath==AHighVillageWall::WallMeshPath())
        VillageMasonry::ApplyCurtainPhase(*Masonry,GetActorTransform());
}
void AVillageDefenseSection::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* Targets=GetWorld()->GetSubsystem<UVillageDefenseRepairTargets>()) Targets->Remove(*this);
    Super::EndPlay(Reason);
}
void AVillageDefenseSection::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,MeshPath,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,SectionId,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,FixedScale,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,WorldId,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,PlacedId,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageDefenseSection,MaximumHealth,COND_InitialOnly);
    DOREPLIFETIME(AVillageDefenseSection,Health);
    DOREPLIFETIME(AVillageDefenseSection,WallInterval);
}
void AVillageDefenseSection::OnRep_Setup()
{
    if(MeshPath.IsNull())return;
    if(MeshPath==AHighVillageWall::WallMeshPath())
        VillageMasonry::ApplyCurtainPhase(*Masonry,GetActorTransform());
    else if(MeshPath.GetLongPackageName().StartsWith(VillageMasonry::CastleFolder))
        VillageMasonry::ApplyWallPhase(*Masonry,SectionId);
    if(auto* Mesh=Cast<UStaticMesh>(MeshPath.ResolveObject()))
    {
        Masonry->SetStaticMesh(Mesh);
        SetupGroundWear();
        ApplyHealth();
        return;
    }
    MeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(MeshPath,
        FStreamableDelegate::CreateUObject(this,&AVillageDefenseSection::OnRep_Setup));
}
void AVillageDefenseSection::SetupGroundWear()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(!GroundWear)
    {
        // Building space uses X along the wall, +Y towards the courtyard.
        // One shallow projection covers both wall feet or the entire gate/tower footprint.
        float HalfX,HalfY,Margin,Kind,CenterY=0.f;
        if(MeshPath==AHighVillageWall::WallMeshPath())
        {
            HalfX=150.f; HalfY=100.f; Margin=82.f; Kind=0.f;
        }
        else if(IsA<AHighVillageGate>())
        {
            HalfX=MeshPath==AHighVillageGate::PlacedGrilleMeshPath(true)?534.f:434.f;
            HalfY=HalfX; CenterY=264.f-HalfY; Margin=150.f; Kind=1.f;
        }
        else if(MeshPath==HighTowerMesh)
        {
            HalfX=460.f; HalfY=460.f; Margin=138.f; Kind=.5f;
        }
        else return;

        auto* Material=Cast<UMaterialInterface>(GroundWearMaterial.TryLoad());
        if(!Material)return;
        GroundWear=NewObject<UDecalComponent>(this,NAME_None,RF_Transient);
        AddInstanceComponent(GroundWear);
        GroundWear->SetupAttachment(RootComponent);
        GroundWear->SetAbsolute(false,false,true);
        GroundWear->SetRelativeLocationAndRotation(FVector(0.,CenterY,-12.),FRotator(-90.,0.,0.));
        GroundWear->DecalSize=FVector(77.,HalfY+Margin,HalfX+(Kind==0.f?0.f:Margin));
        GroundWear->SetDecalColor(FLinearColor(HalfX/1024.f,HalfY/1024.f,Margin/256.f,Kind));
        GroundWear->SetDecalMaterial(Material);
        GroundWear->SetSortOrder(-1);
        GroundWear->RegisterComponent();
    }
    // An upright wall can be stretched along its X axis to fit the last bay.
    // After the downward quarter-turn this is the decal's Z axis.
    const FVector Scale=GetActorScale3D().GetAbs();
    const bool Curtain=MeshPath==AHighVillageWall::WallMeshPath();
    if(Curtain)GroundWear->SetRelativeLocation(FVector((WallInterval.X+WallInterval.Y)*.5,0.,-12.));
    GroundWear->SetWorldScale3D(FVector(Scale.Z,Scale.Y,Scale.X*(Curtain && !IsGateCovered()?(WallInterval.Y-WallInterval.X)/300.:1.)));
}

void AVillageDefenseSection::UpdateTowerLights(bool bStanding)
{
    if(MeshPath!=HighTowerMesh || GetNetMode()==NM_DedicatedServer)return;
    if(!bStanding)
    {
        for(UChildActorComponent* Mount:TowerLights)if(IsValid(Mount))Mount->DestroyComponent();
        TowerLights.Reset();
        return;
    }
    if(!TowerLights.IsEmpty() || !Masonry->GetStaticMesh() || !(HasActorBegunPlay() || IsActorBeginningPlay()))return;
    // Three floor joists, the upper chamber's north wall and the inner face of a roof merlon.
    static const FVector Plates[]={{-30,95,330},{-30,95,790},{-30,95,1290},{0,402,1580},{160,454,1912}};
    for(int32 Floor=0;Floor<UE_ARRAY_COUNT(Plates);++Floor)
    {
        auto* Mount=NewObject<UChildActorComponent>(this,NAME_None,RF_Transient);
        AddInstanceComponent(Mount);
        Mount->SetupAttachment(Masonry);
        Mount->SetRelativeLocationAndRotation(Plates[Floor],FRotator(0,-90,0));
        if(Floor<UE_ARRAY_COUNT(Plates)-1)Mount->ComponentTags.Add(AVillageShopChainLamp::AlwaysLit);
        Mount->SetChildActorClass(AVillageShopChainLamp::StaticClass());
        TowerLights.Add(Mount);
        Mount->RegisterComponent();
    }
}

void AVillageDefenseSection::ApplyHealth()
{
    const bool Standing=Health>0.f && !IsGateCovered();
    UpdateTowerLights(Standing);
    if(GroundWear)GroundWear->SetVisibility(Standing || IsA<AHighVillageGate>());
    Masonry->SetVisibility(Standing);
    Masonry->SetCollisionEnabled(Standing?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
    Masonry->SetCanEverAffectNavigation(Standing);
    GetWorld()->GetSubsystem<UVillageDefenseRepairTargets>()->Update(*this);
}
void AVillageDefenseSection::OnRep_Health()
{
    ApplyHealth();
    if((Health<=0.f||Health==MaximumHealth)&&Masonry->ComponentHasTag(TEXT("Traversal.FixedStructure")))
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)It->OnVillageSupportChanged(*this);
}

bool AVillageDefenseSection::IsRepairMeshClear(const UStaticMeshComponent* Part,const FTransform& Placement) const
{
    if(!Part||!Part->GetStaticMesh())return false;
    const FBox Bounds=Part->GetStaticMesh()->GetBoundingBox();
    const FVector Extent=Bounds.GetExtent()*Placement.GetScale3D().GetAbs();
    return !GetWorld()->OverlapAnyTestByObjectType(Placement.TransformPosition(Bounds.GetCenter()),Placement.GetRotation(),
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Extent),FCollisionQueryParams(SCENE_QUERY_STAT(VillageDefenseRepair),false,this));
}
bool AVillageDefenseSection::IsRepairSiteClear() const
{
    return IsRepairMeshClear(Masonry,Masonry->GetComponentTransform());
}

bool AVillageDefenseSection::QueryRepairEnemies(APawn* Viewer) const
{
    if (!IsValid(Viewer) || Viewer->GetWorld()!=GetWorld()) return false;
    // Use the smith's 15 m alert distance, measured from the reconstruction
    // surface. In particular the far end of a wide gate is not its pivot.
    constexpr float Radius = 1500.f;
    const FCollisionObjectQueryParams Pawns(ECC_Pawn);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageRepairEnemies), false, this);
    auto EnemyAtPart = [&](const UStaticMeshComponent* Part)
    {
        if (!Part || !Part->GetStaticMesh()) return false;
        const FTransform& Pose=Part->GetComponentTransform();
        const FBox Bounds=Part->GetStaticMesh()->GetBoundingBox();
        const FVector Center=Pose.TransformPosition(Bounds.GetCenter());
        const FVector Extent=Bounds.GetExtent()*Pose.GetScale3D().GetAbs();
        const FBox LocalBox(-Extent,Extent);
        TArray<FOverlapResult> Hits;
        GetWorld()->OverlapMultiByObjectType(Hits,Center,Pose.GetRotation(),Pawns,
            FCollisionShape::MakeBox(Extent+FVector(Radius)),Query);
        for (const FOverlapResult& Hit : Hits)
        {
            APawn* Unit=Cast<APawn>(Hit.GetActor());
            if (!Unit || !Unit->HasActorBegunPlay() || Unit->IsHidden() ||
                Unit->ActorHasTag(TEXT("NPC")) || Unit->ActorHasTag(TEXT("WildlifeSpawned")) ||
                !UFPSMeleeLightningComponent::IsEnemy(Unit,Viewer)) continue;
            // The wild hills wolf shares its native base with hostile variants.
            if (Unit->IsA<AWolfMonster>() && UWildlifeSubsystem::IsCatalogClass(FSoftObjectPath(Unit->GetClass()))) continue;
            const FVector Local=Pose.GetRotation().UnrotateVector(Unit->GetActorLocation()-Center);
            const FVector Nearest=Center+Pose.GetRotation().RotateVector(LocalBox.GetClosestPointTo(Local));
            const auto* Body=Hit.GetComponent();
            FVector Surface;
            const float Distance=Body ? Body->GetClosestPointOnCollision(Nearest,Surface) : -1.f;
            if (Distance>=0.f ? Distance<=Radius : LocalBox.ComputeSquaredDistanceToPoint(Local)<=FMath::Square(Radius))
                return true;
        }
        return false;
    };
    if (EnemyAtPart(Masonry)) return true;
    const auto* Gate=Cast<AVillageDefenseGate>(this);
    return Gate && EnemyAtPart(Gate->GetRightLeaf());
}

bool AVillageDefenseSection::HasNearbyRepairEnemy(APawn* Viewer) const
{
    if (!IsValid(Viewer) || !GetWorld() || !NeedsRepair()) return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if (LastThreatViewer.Get()!=Viewer || Now<ThreatSampleTime || Now-ThreatSampleTime>=.25)
    {
        bSampledThreat=QueryRepairEnemies(Viewer);
        ThreatSampleTime=Now;
        LastThreatViewer=Viewer;
    }
    return bSampledThreat;
}

bool AVillageDefenseSection::TryRepair(APawn* Payer,FText& Failure)
{
    const auto* Hills=Cast<ATemperateHillsWorld>(GetOwner());
    if(!HasAuthority()||IsActorBeingDestroyed()||ActorHasTag(TEXT("VoxelDetached"))||!IsValid(Payer)||!Payer->IsPlayerControlled()||
        Payer->GetWorld()!=GetWorld()||!Hills||!WorldId.IsValid()||Hills->WorldId!=WorldId||SectionId==INDEX_NONE)
    {Failure=FText::FromString(TEXT("当前无法修复这处防御工事。"));return false;}
    if(const auto* Vitals=Payer->FindComponentByClass<UFPSCombatHealthComponent>();Vitals&&Vitals->IsDead())
    {Failure=FText::FromString(TEXT("倒地时无法修复。"));return false;}
    if(!NeedsRepair())
    {Failure=FText::FromString(TEXT("这处防御工事尚未被摧毁。"));return false;}
    if(QueryRepairEnemies(Payer))
    {Failure=FText::FromString(TEXT("附近有敌方单位，无法修复。"));return false;}
    const bool bRebuilding=Health<=0.f;
    if(bRebuilding && !IsRepairSiteClear())
    {Failure=FText::FromString(TEXT("请让人员和动物离开修复位置。"));return false;}
    if(!GetWorld()->GetSubsystem<UVillageDefenseState>()->PurchaseRepair(WorldId,SectionId,Payer,RepairSoulCost,Failure,PlacedId,Health))return false;
    FlushNetDormancy();
    if (auto* Status=FindComponentByClass<UCombatStatusFormula>()) Status->PurgeTransient();
    if (auto* Effects=FindComponentByClass<UStatusEffectsComponent>()) Effects->Clear();
    Health=MaximumHealth;
    ApplyHealth();
    if(Masonry->ComponentHasTag(TEXT("Traversal.FixedStructure")))
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)It->OnVillageSupportChanged(*this);
    if(bRebuilding)MulticastClearRepairedDebris();
    ForceNetUpdate();
    return true;
}
FVector AVillageDefenseSection::GetNavAgentLocation() const {return IsGateCut()?Masonry->GetComponentLocation():GetActorLocation();}
FVector AVillageDefenseSection::TargetPoint(const FVector& From) const
{
    FVector Result=GetActorLocation()+FVector(0,0,100);
    Masonry->GetClosestPointOnCollision(From,Result);
    Result.Z=FMath::Clamp(From.Z,GetActorLocation().Z+25.,GetActorLocation().Z+160.);return Result;
}
float AVillageDefenseSection::TakeDamage(float Amount,const FDamageEvent&,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||IsGateCovered()||Health<=0.f||!FMath::IsFinite(Amount)||Amount<=0.f)return 0.f;
    // Includes delayed effects, projectiles and objects owned by a player after a weapon switch.
    if(EventInstigator && EventInstigator->IsPlayerController())return 0.f;
    for(const AActor* Source=Causer;Source;Source=Source->GetOwner())
    {
        if(Source->IsA<APlayerController>())return 0.f;
        if(const APawn* Pawn=Cast<APawn>(Source);Pawn && (Pawn->IsPlayerControlled() || Pawn->IsA<AFPSGAMECharacter>()))return 0.f;
        if(const APawn* Shooter=Source->GetInstigator();Shooter && (Shooter->IsPlayerControlled() || Shooter->IsA<AFPSGAMECharacter>()))return 0.f;
    }
    const float Applied=FMath::Min(Health,Amount);FlushNetDormancy();Health-=Applied;
    if(Health<=0.f)
    {
        const FVector Direction=Causer?(GetActorLocation()-Causer->GetActorLocation()).GetSafeNormal2D():GetActorRightVector();
        MulticastCollapse(Direction,SectionId^int32(GetWorld()->GetTimeSeconds()*100),GateTravelAtCollapse());
    }
    ApplyHealth();ForceNetUpdate();GetWorld()->GetSubsystem<UVillageDefenseState>()->Record(WorldId,SectionId,Health,PlacedId);
    if(Health<=0.f)SetNetDormancy(DORM_DormantAll);
    if(Health<=0.f&&Masonry->ComponentHasTag(TEXT("Traversal.FixedStructure")))
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)It->OnVillageSupportChanged(*this);
    UE_LOG(LogTemp,Display,TEXT("VILLAGE_DEFENSE damage id=%d amount=%.1f hp=%.1f causer=%s"),SectionId,Applied,Health,*GetNameSafe(Causer));
    return Applied;
}
void AVillageDefenseSection::MulticastCollapse_Implementation(FVector_NetQuantizeNormal Direction,int32 Seed,float GateTravel)
{PresentCollapse(Direction,Seed,GateTravel);}
void AVillageDefenseSection::MulticastClearRepairedDebris_Implementation()
{
    // The same reliable channel orders this after collapse even if health went
    // zero -> full within one replication update on a client.
    if(GetNetMode()==NM_DedicatedServer)return;
    for(TActorIterator<AHighVillageCollapse> It(GetWorld());It;++It)
        if(It->GetOwner()==this)It->Destroy();
    for(TActorIterator<AVillageDefenseDebris> It(GetWorld());It;++It)
        if(It->GetOwner()==this)It->Destroy();
}
void AVillageDefenseSection::PresentCollapse(const FVector& Direction,int32 Seed,float)
{
    if(!Masonry->GetStaticMesh())return;
    FVector Size=Masonry->GetStaticMesh()->GetBoundingBox().GetSize()*Masonry->GetComponentScale().GetAbs();
    Size.Y=FMath::Min(Size.Y,60.);
    FTransform T(Masonry->GetComponentQuat(),Masonry->GetComponentLocation());
    AVillageDefenseDebris::Spawn(*this,T,Size,Direction,Seed,false);
}
