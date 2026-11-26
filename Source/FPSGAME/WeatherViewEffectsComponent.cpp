#include "WeatherViewEffectsComponent.h"
#include "FPSGAMECharacter.h"
#include "WeatherSurfaceComponent.h"
#include "WeaponWeatherStateComponent.h"
#include "Characters/FPSPlayerBodyComponent.h"
#include "Weapons/WeaponPresentationMaterials.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<float> CVarWeaponWetness(TEXT("fps.WeaponWetness"),1.f,TEXT("Weapon wet material strength, 0 disables."),ECVF_Scalability);

namespace
{
const FName WetnessName(TEXT("WeaponWetness"));
const FSoftObjectPath RoutingPath(TEXT("/Game/Weather/WeaponWetIndex20261017/DA_WeaponWetIndex.DA_WeaponWetIndex"));
constexpr int32 MaterialsPerBatch=8;
constexpr double MaterialCacheSeconds=12.;

UObject* SourceMesh(UMeshComponent* Mesh)
{
    if(auto* Skel=Cast<USkeletalMeshComponent>(Mesh))return Skel->GetSkinnedAsset();
    if(auto* Static=Cast<UStaticMeshComponent>(Mesh))return Static->GetStaticMesh();
    return nullptr;
}
void RestoreBinding(FWeatherViewMaterial& Binding)
{
    auto* Mesh=Binding.Mesh.Get();
    if(Mesh&&Mesh->GetMaterial(Binding.Slot)==Binding.Wet)
    {
        // A self-mapped MID is also retained by rune/staff components. Clear its
        // wet layer when detached instead of leaving the last rainy value alive.
        if(SourceMesh(Mesh)!=Binding.MeshAsset.Get())Mesh->SetMaterial(Binding.Slot,nullptr);
        else if(Binding.Original==Binding.Wet)Binding.Wet->SetScalarParameterValue(WetnessName,0.f);
        else Mesh->SetMaterial(Binding.Slot,Binding.Original.Get());
    }
}
}

UWeatherViewEffectsComponent::UWeatherViewEffectsComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UWeatherViewEffectsComponent::Initialize()
{
    if(bInitialized||GetNetMode()==NM_DedicatedServer)return;
    bInitialized=true;
    // This asset contains soft paths only: loading it never loads weapon textures.
    RoutingLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(RoutingPath,
        FStreamableDelegate::CreateUObject(this,&ThisClass::FinishRoutingLoad));
}

void UWeatherViewEffectsComponent::FinishRoutingLoad()
{
    if(!bInitialized)return;
    Routing=Cast<UWeatherPresentationAssets>(RoutingPath.ResolveObject());
    if(!Routing)UE_LOG(LogTemp,Error,TEXT("WeaponWetness routing asset missing: %s"),*RoutingPath.ToString());
    RoutingLoad.Reset();BindCountdown=0.f;
}

void UWeatherViewEffectsComponent::StartMaterialLoad()
{
    if(MaterialLoad||!bInitialized)return;
    LoadingMaterials.Reset();
    for(const auto& Path:WantedMaterials)
        if(!Materials.Contains(Path)&&!FailedMaterials.Contains(Path))
        {LoadingMaterials.Add(Path);if(LoadingMaterials.Num()>=MaterialsPerBatch)break;}
    if(LoadingMaterials.IsEmpty())return;
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(LoadingMaterials,
        FStreamableDelegate::CreateUObject(this,&ThisClass::FinishMaterialLoad));
    if(!MaterialLoad)
    {
        UE_LOG(LogTemp,Warning,TEXT("WeaponWetness could not request %d materials"),LoadingMaterials.Num());
        for(const auto& Path:LoadingMaterials)FailedMaterials.Add(Path);
        LoadingMaterials.Reset();
    }
}

void UWeatherViewEffectsComponent::FinishMaterialLoad()
{
    if(!bInitialized)return;
    const double Now=GetWorld()->GetTimeSeconds();
    for(const auto& Path:LoadingMaterials)
    {
        if(auto* Material=Cast<UMaterialInterface>(Path.ResolveObject()))
        {FWeatherLoadedMaterial Entry;Entry.Material=Material;Entry.LastUsedAt=Now;Materials.Add(Path,Entry);}
        else {FailedMaterials.Add(Path);UE_LOG(LogTemp,Warning,TEXT("WeaponWetness material unavailable: %s"),*Path.ToString());}
    }
    LoadingMaterials.Reset();
    MaterialLoad.Reset();BindCountdown=0.f;
}

UMaterialInterface* UWeatherViewEffectsComponent::ResolveWet(UMaterialInterface* Original)
{
    UMaterialInterface* Source=Original;
    while(auto* MID=Cast<UMaterialInstanceDynamic>(Source))
    {
        if(!MID->Parent)break;
        Source=MID->Parent;
    }
    if(!Source||!Source->IsAsset())return nullptr;
    if(RoutingLoad)return nullptr;
    const FName Path(*Source->GetPathName());
    if(const auto* Replacement=Routing?Routing->WetMaterialPaths.Find(Path):nullptr)
    {
        const FSoftObjectPath Target=Replacement->ToSoftObjectPath();
        if(Target==FSoftObjectPath(Source))return Source;
        WantedMaterials.Add(Target);
        if(auto* Entry=Materials.Find(Target))
        {Entry->LastUsedAt=GetWorld()->GetTimeSeconds();return Entry->Material;}
        return nullptr;
    }
    // Includes modern weapon masters, authored melee layers and world copies
    // whose persistent parent is already a wet material. No unrelated catalogs
    // are needed to drive a layer that is present on the material itself.
    float ExistingWetness=0.f;
    if(Source->GetScalarParameterValue(FMaterialParameterInfo(WetnessName),ExistingWetness))return Source;
    return nullptr;
}

UMaterialInstanceDynamic* UWeatherViewEffectsComponent::AcquireWet(AFPSGAMECharacter* Pawn,uint8 Hand,
    UMaterialInterface* Original,UMaterialInterface* Replacement)
{
    // Keep live self-wet MIDs so retained rune/staff pointers still animate the
    // material on the mesh. Copied world equipment uses asset-backed originals.
    if(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Original))
        if(Dynamic->GetBaseMaterial()==Replacement->GetBaseMaterial())return Dynamic;
    const bool bPoolable=Original&&Original->IsAsset();
    if(bPoolable)
        for(auto& Shared:SharedWet)
            if(Shared.Pawn==Pawn&&Shared.Hand==Hand&&Shared.Original==Original)return Shared.Wet;
    auto* Wet=UMaterialInstanceDynamic::Create(Replacement,this);
    if(!Wet)return nullptr;
    Wet->CopyMaterialUniformParameters(Original);
    if(bPoolable)
    {
        FSharedWetMaterial Shared;Shared.Pawn=Pawn;Shared.Hand=Hand;Shared.Original=Original;Shared.Wet=Wet;
        SharedWet.Add(Shared);
    }
    return Wet;
}

void UWeatherViewEffectsComponent::RestoreMaterials()
{
    for(auto& Binding:Bindings)RestoreBinding(Binding);
    Bindings.Reset();SharedWet.Reset();LastPushed.Reset();
}

void UWeatherViewEffectsComponent::BindWeapons(bool bScanAll)
{
    if(!bInitialized)return;
    bool bPruned=false;
    for(int32 I=Bindings.Num()-1;I>=0;--I)
    {
        auto& B=Bindings[I];auto* Mesh=B.Mesh.Get();
        if(!B.Pawn.IsValid()||!B.State.IsValid()||!Mesh||SourceMesh(Mesh)!=B.MeshAsset.Get()||Mesh->GetMaterial(B.Slot)!=B.Wet)
        {
            RestoreBinding(B);LastPushed.Remove(B.Wet.Get());Bindings.RemoveAtSwap(I);bPruned=true;
        }
    }
    if(!bScanAll&&!bPruned)return;

    WantedMaterials.Reset();
    const double Now=GetWorld()->GetTimeSeconds();
    for(const auto& B:Bindings)
    {
        if(auto* Entry=Materials.Find(B.TargetPath))
        {WantedMaterials.Add(B.TargetPath);Entry->LastUsedAt=Now;}
    }

    TSet<UMeshComponent*> EquippedMeshes;
    TArray<FFPSWeatherWeaponMesh> Equipment;
    for(TActorIterator<AFPSGAMECharacter> It(GetWorld());It;++It)
    {
        auto* Pawn=*It;
        auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
        auto* State=Pawn->FindComponentByClass<UWeaponWeatherStateComponent>();
        if(!Body||!State)continue;
        Body->GetWeatherWeaponMeshes(Equipment);
        for(const auto& Entry:Equipment)
        {
            auto* Mesh=Entry.Mesh;
            EquippedMeshes.Add(Mesh);
            // A weapon can move between hands or be replaced by another copy
            // without changing its mesh asset. Do not retain the old item's key.
            for(int32 I=Bindings.Num()-1;I>=0;--I)
                if(Bindings[I].Mesh==Mesh&&(Bindings[I].Instance!=Entry.Instance||Bindings[I].Hand!=Entry.Hand))
                {
                    RestoreBinding(Bindings[I]);LastPushed.Remove(Bindings[I].Wet.Get());Bindings.RemoveAtSwap(I);
                }
            const auto SlotNames=Mesh->GetMaterialSlotNames();
            for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
            {
                if(SlotNames.IsValidIndex(Slot)&&WeaponPresentationMaterials::IsArmName(SlotNames[Slot].ToString()))continue;
                if(Bindings.ContainsByPredicate([Mesh,Slot](const auto& B){return B.Mesh==Mesh&&B.Slot==Slot;}))continue;
                auto* Original=Mesh->GetMaterial(Slot);
                if(!Original)continue;
                auto* Target=ResolveWet(Original);
                if(!Target)continue;
                auto* Wet=AcquireWet(Pawn,Entry.Hand,Original,Target);
                if(!Wet)continue;
                FWeatherViewMaterial B;B.Pawn=Pawn;B.State=State;B.Mesh=Mesh;B.MeshAsset=SourceMesh(Mesh);
                B.Original=Original;B.Wet=Wet;B.Slot=Slot;B.Hand=Entry.Hand;B.Instance=Entry.Instance;
                B.TargetPath=FSoftObjectPath(Target);
                Bindings.Add(B);
                if(Original!=Wet)Mesh->SetMaterial(Slot,Wet);
                LastPushed.Remove(Wet);
            }
        }
    }
    // Restore unequipped sources too: weapons hidden in the inventory must not
    // accumulate the new held item's wetness through a stale material binding.
    for(int32 I=Bindings.Num()-1;I>=0;--I)if(!EquippedMeshes.Contains(Bindings[I].Mesh.Get()))
    {
        RestoreBinding(Bindings[I]);LastPushed.Remove(Bindings[I].Wet.Get());Bindings.RemoveAtSwap(I);
    }
    const auto IsBound=[&](const UMaterialInstanceDynamic* Wet)
    {return Bindings.ContainsByPredicate([Wet](const auto& B){return B.Wet==Wet;});};
    SharedWet.RemoveAll([&](const auto& Shared){return !Shared.Pawn.IsValid()||!IsBound(Shared.Wet);});
    for(auto It=LastPushed.CreateIterator();It;++It)if(!It.Key().IsValid()||!IsBound(It.Key().Get()))It.RemoveCurrent();
    for(auto It=Materials.CreateIterator();It;++It)
        if(Now-It.Value().LastUsedAt>MaterialCacheSeconds&&!WantedMaterials.Contains(It.Key()))It.RemoveCurrent();
    StartMaterialLoad();
}

void UWeatherViewEffectsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    BindCountdown-=Delta;
    const bool bScan=BindCountdown<=0.f;
    if(bScan)BindCountdown=.2f;
    BindWeapons(bScan);
    const float Strength=UWeatherSurfaceComponent::GetQuality()>0?FMath::Clamp(CVarWeaponWetness.GetValueOnGameThread(),0.f,1.f):0.f;
    constexpr float WetStep=1.f/255.f;
    ActiveWeaponWetness=0.f;
    for(auto& B:Bindings)
    {
        auto* State=B.State.Get();
        if(!State||!B.Wet)continue;
        const float Value=State->GetWetness(B.Hand,B.Instance);
        if(B.Hand==0&&B.Pawn.IsValid()&&B.Pawn->IsLocallyControlled())ActiveWeaponWetness=Value;
        const float Target=FMath::RoundToFloat(Value*Strength/WetStep)*WetStep;
        const float* Previous=LastPushed.Find(B.Wet.Get());
        // Cache per actual MID, including zero: shared slots enqueue one render
        // update, and new/rebound materials receive stable weather immediately.
        if(!Previous||FMath::Abs(Target-*Previous)>=WetStep*.5f)
        {B.Wet->SetScalarParameterValue(WetnessName,Target);LastPushed.Add(B.Wet.Get(),Target);}
    }
}

void UWeatherViewEffectsComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bInitialized=false;
    if(RoutingLoad){RoutingLoad->CancelHandle();RoutingLoad.Reset();}
    if(MaterialLoad){MaterialLoad->CancelHandle();MaterialLoad.Reset();}
    RestoreMaterials();Materials.Reset();Routing=nullptr;WantedMaterials.Reset();LoadingMaterials.Reset();FailedMaterials.Reset();
    Super::EndPlay(Reason);
}
