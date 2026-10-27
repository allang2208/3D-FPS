#include "CampfireCookingPresentation.h"
#include "ColdSteelCampfire.h"
#include "../Items/CampfireFoodCatalog.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundNodeWavePlayer.h"
#include "Sound/SoundWave.h"

void UCampfireCookingPresentation::LoadAssets()
{
    if(LoadHandle||!Meshes.IsEmpty())return;
    TArray<FSoftObjectPath> Paths;
    for(const auto& V:CampfireFood::Catalog()){Paths.Add(FSoftObjectPath(V.RawMesh));Paths.Add(FSoftObjectPath(V.CookedMesh));}
    const int32 FoodCount=Paths.Num();
    Paths.Add(FSoftObjectPath(TEXT("/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam.NS_WaterImpactSteam")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/FreeGameSoundsVol1/SFX/Sizzle_Bacon_Frying/Sizzle_Bacon_Frying_01.Sizzle_Bacon_Frying_01")));
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths,FoodCount]()
    {
        for(int32 I=0;I<FoodCount;++I)Meshes.Add(Cast<UStaticMesh>(Paths[I].ResolveObject()));
        SteamAsset=Cast<UNiagaraSystem>(Paths[FoodCount].ResolveObject());
        if(auto* Wave=Cast<USoundWave>(Paths[FoodCount+1].ResolveObject()))
        {
            // A per-instance cue loops the existing wave without mutating the shared asset.
            SizzleLoop=NewObject<USoundCue>(this,NAME_None,RF_Transient);
            auto* Player=NewObject<USoundNodeWavePlayer>(SizzleLoop,NAME_None,RF_Transient);
            Player->SetSoundWave(Wave);Player->bLooping=true;SizzleLoop->FirstNode=Player;
            SizzleLoop->Duration=INDEFINITELY_LOOPING_DURATION;
        }
        Update(bAdmitted);
    }));
}

void UCampfireCookingPresentation::StopEffects()
{
    if(Sizzle)Sizzle->Stop();
    if(Steam)Steam->DeactivateImmediate();
    NextSteam=0;
}

void UCampfireCookingPresentation::Update(bool bWithinBudget)
{
    auto* Fire=Cast<AColdSteelCampfire>(GetOwner());
    bAdmitted=bWithinBudget&&IsValid(Fire)&&Fire->IsAvailable()&&!Fire->ActorHasTag(TEXT("VoxelDetached"))
        &&GetWorld()->GetNetMode()!=NM_DedicatedServer;
    if(!bAdmitted)
    {
        StopEffects();
        for(const auto& Part:Display)if(Part)Part->SetVisibility(false);
        return;
    }
    const auto& State=Fire->SharedState();
    TArray<int32,TInlineAllocator<5>> Wanted;
    const auto& Foods=CampfireFood::Catalog();
    for(int32 I=0;I<Foods.Num();++I)if(State.Recipe==Foods[I].Recipe&&State.Batch>State.Produced){Wanted.Add(I*2);break;}
    for(int32 I=0;I<Foods.Num()&&Wanted.Num()<5;++I)
        if(State.Products.ContainsByPredicate([&](const FCampfireProduct& P){return P.Item==Foods[I].Cooked&&P.Count>0;}))Wanted.Add(I*2+1);
    if(Wanted.IsEmpty())
    {
        StopEffects();for(const auto& Part:Display)if(Part)Part->SetVisibility(false);return;
    }
    LoadAssets();
    if(Meshes.Num()!=Foods.Num()*2)return;
    // One representative per unfinished batch/product type. Inventory quantities
    // remain in the station UI; five meshes is the hard per-station maximum.
    while(Display.Num()<Wanted.Num())
    {
        auto* Part=NewObject<UStaticMeshComponent>(Fire,NAME_None,RF_Transient);
        Fire->AddInstanceComponent(Part);Part->SetupAttachment(Fire->GetRootComponent());
        Part->SetMobility(EComponentMobility::Movable);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);Part->SetCastShadow(false);Part->bReceivesDecals=false;
        Part->RegisterComponent();Display.Add(Part);
    }
    for(int32 I=0;I<Display.Num();++I)
    {
        auto* Part=Display[I].Get();auto* Mesh=Wanted.IsValidIndex(I)?Meshes[Wanted[I]].Get():nullptr;
        Part->SetVisibility(Mesh!=nullptr);if(!Mesh)continue;
        if(Part->GetStaticMesh()!=Mesh)Part->SetStaticMesh(Mesh);
        const auto Bounds=Mesh->GetBounds();
        const float Scale=FMath::Min(1.f,52.f/(Wanted.Num()*FMath::Max(1.f,float(Bounds.BoxExtent.X*2))));
        // Use a point inside the meat, not the rack's bounds centre (which is
        // in the empty space between the large lamb's exposed ribs).
        FVector SpitAnchor=Bounds.Origin;
        const int32 Family=Wanted[I]/2;
        if(Foods[Family].bCustomSpit)SpitAnchor=FVector(Bounds.Origin.X,Foods[Family].SpitAnchor.Y,Foods[Family].SpitAnchor.Z);
        const float X=(I-(Wanted.Num()-1)*.5f)*(54.f/Wanted.Num());
        Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector(X,0,70.2f)-SpitAnchor*Scale,FVector(Scale)));
    }
    const bool Cooking=State.BurnTicks>0&&!State.bSaveBlocked&&!State.Recipe.IsNone()
        &&State.Batch>State.Produced&&Fire->DisplayFuel()>0&&Fire->IsProvidingWarmth()&&!GetWorld()->IsPaused();
    if(!Cooking){StopEffects();return;}
    if(!Sizzle&&SizzleLoop)
    {
        Sizzle=NewObject<UAudioComponent>(Fire,NAME_None,RF_Transient);
        Fire->AddInstanceComponent(Sizzle);Sizzle->SetupAttachment(Fire->GetRootComponent());
        Sizzle->SetRelativeLocation(FVector(0,0,70.2f));Sizzle->SetAutoActivate(false);Sizzle->bAutoDestroy=false;
        Sizzle->bStopWhenOwnerDestroyed=true;Sizzle->bAllowSpatialization=true;Sizzle->bIsUISound=false;
        Sizzle->bOverrideAttenuation=true;Sizzle->AttenuationOverrides.bAttenuate=true;
        Sizzle->AttenuationOverrides.bSpatialize=true;
        Sizzle->AttenuationOverrides.AttenuationShapeExtents=FVector(100,0,0);
        Sizzle->AttenuationOverrides.FalloffDistance=650.f;
        Sizzle->SetSound(SizzleLoop);Sizzle->SetVolumeMultiplier(.22f);Sizzle->RegisterComponent();
    }
    if(Sizzle&&!Sizzle->IsPlaying())Sizzle->Play();
    if(!Steam&&SteamAsset)
    {
        Steam=NewObject<UNiagaraComponent>(Fire,NAME_None,RF_Transient);
        Fire->AddInstanceComponent(Steam);Steam->SetupAttachment(Fire->GetRootComponent());
        Steam->SetAutoActivate(false);Steam->SetAutoDestroy(false);Steam->SetAsset(SteamAsset);
        Steam->SetRelativeLocation(FVector(0,0,73));Steam->SetRelativeScale3D(FVector(.16f));
        Steam->SetCollisionEnabled(ECollisionEnabled::NoCollision);Steam->SetCanEverAffectNavigation(false);
        Steam->RegisterComponent();Steam->SetVariableFloat(TEXT("User.SteamCount"),2.f);
        Steam->SetVariableFloat(TEXT("User.DetailReduction"),0.f);Steam->SetVariableVec3(TEXT("User.LocalUp"),FVector::UpVector);
        Steam->SetVariableVec3(TEXT("User.Wind"),FVector::ZeroVector);
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(Steam&&Now>=NextSteam){Steam->Activate(true);NextSteam=Now+1.6;}
}

void UCampfireCookingPresentation::EndPlay(const EEndPlayReason::Type Reason)
{
    bAdmitted=false;StopEffects();LoadHandle.Reset();Super::EndPlay(Reason);
}
