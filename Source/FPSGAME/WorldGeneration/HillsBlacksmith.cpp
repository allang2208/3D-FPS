#include "HillsBlacksmith.h"
#include "SmithSignMotion.h"
#include "VillageInteriorLighting.h"
#include "VillageChimneySmoke.h"
#include "HillsCarpenterWorkshop.h"
#include "VillageShopFacing.h"
#include "VillageShopTorches.h"
#include "TemperateHillsWorld.h"
#include "../NPC/VillageBlacksmithResident.h"
#include "../Building/VoxelBuildWorld.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"

namespace
{
// Ground-floor coordinates from the authored loft assembly, in centimetres.
const FVector StationInHouse(120., 40., 6.);
const FVector ReceptionTableInHouse(-15., -270., 0.);

void UpdateForgeLight(AHillsBlacksmith& Shop, bool bRepaired)
{
    if (Shop.GetNetMode() == NM_DedicatedServer) return;
    static const FName LightName(TEXT("SmithHearthGlow"));
    if (auto* Light = FindObjectFast<UPointLightComponent>(&Shop, LightName))
    {
        Light->SetVisibility(bRepaired);
        return;
    }
    if (!bRepaired) return;

    TInlineComponentArray<UNiagaraComponent*> Effects(&Shop);
    for (UNiagaraComponent* Fuel : Effects)
    {
        if (!Fuel->ComponentHasTag(TEXT("VillageShop.HearthFire"))) continue;
        auto* Light = NewObject<UPointLightComponent>(&Shop, LightName);
        Light->SetupAttachment(Shop.GetRootComponent());
        // The dressed coals rise 3–6 cm above the grate. Keep the fill just clear
        // of their top faces and the flame low enough to expose their glowing edges.
        const FVector Grate = Shop.GetActorTransform().InverseTransformPosition(Fuel->GetComponentLocation());
        Fuel->SetRelativeScale3D(FVector(.58, .58, .30));
        Light->SetRelativeLocation(Grate + FVector(0,0,7));
        Light->SetMobility(EComponentMobility::Movable);
        UVillageInteriorLighting::Configure(Light, .32f);
        Light->SetLightColor(FLinearColor(1.f, .24f, .052f));
        Light->SetAttenuationRadius(240.f);
        Light->SetSourceRadius(5.f);
        Light->SetSoftSourceRadius(9.f);
        Light->SetSpecularScale(.32f);
        Light->SetVolumetricScatteringIntensity(.035f);
        Light->SetMaxDrawDistance(2200.f);
        Light->SetMaxDistanceFadeRange(450.f);
        Shop.AddInstanceComponent(Light);
        Light->RegisterComponent();
        return;
    }
}
}

AHillsBlacksmith::AHillsBlacksmith()
{
    PrimaryActorTick.bCanEverTick=false;
    bAlwaysRelevant=true;
}

void AHillsBlacksmith::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode()!=NM_DedicatedServer)
    {
        UStaticMeshComponent* Links=nullptr;
        UStaticMeshComponent* Board=nullptr;
        for (AActor* Assembly:ShopAssemblies)
        {
            if (!IsValid(Assembly)) continue;
            TInlineComponentArray<UStaticMeshComponent*> Parts(Assembly);
            for (auto* Part:Parts)
            {
                if (Part->ComponentHasTag(TEXT("VillageShop.SmithSuspension"))) Links=Part;
                if (Part->ComponentHasTag(TEXT("VillageShop.SmithSwingBoard"))) Board=Part;
            }
        }
        if (Links && Board)
        {
            auto* Motion=NewObject<USmithSignMotion>(this,NAME_None,RF_Transient);
            AddInstanceComponent(Motion);
            Motion->RegisterComponent();
            Motion->Mount(*Links,*Board);
        }
    }
    BindVillage();
}

void AHillsBlacksmith::BindVillage()
{
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    if(HasAuthority()&&!GetOwner())
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady()){SetOwner(*It);break;}
    if(Hills.IsValid()&&GetOwner())
    {GetWorldTimerManager().ClearTimer(BindTimer);ApplyVillageState();return;}
    // Building initialization waits for terrain streaming; no fixed loading-time cutoff.
    GetWorldTimerManager().SetTimer(BindTimer,this,&AHillsBlacksmith::BindVillage,1.f,false);
}

bool AHillsBlacksmith::IsSceneStationAvailable() const
{return Hills.IsValid()&&Hills->IsVillageBlacksmithRepaired()&&PrefabId()==VoxelCastingStationId&&!IsFalling();}

void AHillsBlacksmith::RegisterStation()
{
    if(auto* Building=Cast<AVoxelBuildWorld>(GetOwner()))
    {
        if(IsSceneStationAvailable())Building->RegisterSceneStation(this);
        else Building->UnregisterSceneStation(this);
    }
}

void AHillsBlacksmith::ApplyVillageState()
{
    if(!Hills.IsValid())return;
    const bool Repaired=Hills->IsVillageBlacksmithRepaired();
    TArray<UPrimitiveComponent*> Parts;
    for(const auto& Assembly:ShopAssemblies)if(IsValid(Assembly.Get()))
    {TInlineComponentArray<UPrimitiveComponent*> Components(Assembly.Get());Parts.Append(Components);}
    for(auto* Part:Parts)
    {
        const bool Ruin=Part->ComponentHasTag(TEXT("VillageShop.Ruined"));
        const bool Repair=Part->ComponentHasTag(TEXT("VillageShop.Repaired"));
        if(!Ruin&&!Repair)continue;
        const bool Visible=Ruin?!Repaired:Repaired;
        Part->SetVisibility(Visible);Part->SetHiddenInGame(!Visible);
        Part->SetCollisionEnabled(Visible&&!Part->ComponentHasTag(TEXT("VillageShop.NoCollision"))?
            ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
    }
    if(HasAuthority())
    {
        const FVector P=GetActorLocation();
        const FIntVector Key(FMath::FloorToInt(P.X/20.),FMath::FloorToInt(P.Y/20.),FMath::FloorToInt(P.Z/20.));
        Configure(Repaired?VoxelCastingStationId:NAME_None,Key,0,StationMesh,nullptr,nullptr);
        Body()->SetReceivesDecals(false);
        UpdateResident(Repaired);
        ForceNetUpdate();
    }
    UpdateSmeltingYard(Repaired);
    VillageChimneySmoke::Apply(*this,Repaired);
    UpdateForgeLight(*this, Repaired);
    VillageShopTorches::Apply(*this,VillageShopTorches::EShop::Blacksmith,Repaired);
    RegisterStation();
}

void AHillsBlacksmith::UpdateResident(bool bRepaired)
{
    if (!bRepaired)
    {
        if (Resident.IsValid())
        {
            Resident->Destroy();
            Resident.Reset();
        }
        return;
    }
    if (Resident.IsValid()) return;

    // Keep the standing spot beside the reception table, clear of the stool and arcade.
    const FVector Center = ReceptionTableInHouse - StationInHouse
        + FVector(-115., 0., AVillageBlacksmithResident::CapsuleHalfHeight);
    FTransform StandingPose = FTransform(Center) * GetActorTransform();
    VillageShop::FaceAcrossStreet<AHillsCarpenterWorkshop>(*this, -GetActorRightVector(), StandingPose);
    FActorSpawnParameters Spawn;
    Spawn.Owner = this;
    Spawn.OverrideLevel = GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Resident = GetWorld()->SpawnActor<AVillageBlacksmithResident>(
        AVillageBlacksmithResident::StaticClass(), StandingPose, Spawn);
}

void AHillsBlacksmith::OnRep_Owner()
{Super::OnRep_Owner();if(Hills.IsValid())RegisterStation();else BindVillage();}

void AHillsBlacksmith::OnRep_Configuration()
{Super::OnRep_Configuration();RegisterStation();}

bool AHillsBlacksmith::RepairAreaOccupied() const
{
    return GetWorld()->OverlapAnyTestByObjectType(GetActorTransform().TransformPosition(RepairAreaCenter),GetActorQuat(),
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(RepairAreaHalfExtent),FCollisionQueryParams(SCENE_QUERY_STAT(VillageShopRepair),false,this));
}

void AHillsBlacksmith::EndPlay(const EEndPlayReason::Type Reason)
{
    UpdateSmeltingYard(false);
    if (HasAuthority()) UpdateResident(false);
    GetWorldTimerManager().ClearTimer(BindTimer);
    if(auto* Building=Cast<AVoxelBuildWorld>(GetOwner()))Building->UnregisterSceneStation(this);
    Super::EndPlay(Reason);
}

void ATemperateHillsWorld::OnRep_VillageBlacksmith()
{
    ApplySmithYardGround();
    for(TActorIterator<AHillsBlacksmith> It(GetWorld());It;++It)It->ApplyVillageState();
}

bool ATemperateHillsWorld::CompleteVillageBlacksmithRepair(FText& FailureReason)
{
    FailureReason=FText::GetEmpty();
    if(!HasAuthority()||Slot.IsEmpty()||!WorldId.IsValid()||!VillageSite.bPlaced)
    {FailureReason=FText::FromString(TEXT("村庄尚未准备好修复铁匠铺。"));return false;}
    if(bVillageBlacksmithRepaired)return true;
    AHillsBlacksmith* Shop=nullptr;
    for(TActorIterator<AHillsBlacksmith> It(GetWorld());It;++It){Shop=*It;break;}
    const auto* Building=Shop?Cast<AVoxelBuildWorld>(Shop->GetOwner()):nullptr;
    if(!Building||!Shop->StationMesh)
    {FailureReason=FText::FromString(TEXT("铁匠铺还未准备好，请稍后重试。"));return false;}
    if(Shop->RepairAreaOccupied())
    {FailureReason=FText::FromString(TEXT("铁匠铺内有人或动物，请先离开房屋再完成修复。"));return false;}
    if(Building->HasPrefabAt(Shop->AnchorCell()))
    {FailureReason=FText::FromString(TEXT("铸造台的位置被建造构件占用，请移开后再修复。"));return false;}
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save||Save->WorldId!=WorldId||Save->Seed!=Seed||Save->Version>6||Save->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion)
    {FailureReason=FText::FromString(TEXT("无法读取当前丘陵的修复存档。"));return false;}
    Save->Version=6;Save->bVillageBlacksmithRepaired=true;
    Save->VillagePlansUnlocked=Save->SavedVillagePlans()|2;
    Save->VillagePlanVersion=FMath::Max(2,Save->VillagePlanVersion);
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
    {FailureReason=FText::FromString(TEXT("铁匠铺修复未能保存，请重试。"));return false;}
    VillagePlansUnlocked=Save->VillagePlansUnlocked;
    bVillageBlacksmithRepaired=true;OnRep_VillageBlacksmith();ForceNetUpdate();
    return true;
}
