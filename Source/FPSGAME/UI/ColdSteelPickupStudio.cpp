#include "ColdSteelPickupStudio.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"

FString UColdSteelPickupStudio::Key(const FColdSteelItem& Item) const
{
    const auto Parts=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(Item);
    TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();FString Result=Item.Definition;
    for(const auto& Name:Names)Result+=TEXT("|")+Name+TEXT("=")+Parts[Name];return Result;
}
AFPSGAMECharacter* UColdSteelPickupStudio::Acquire(const FString& Definition,bool& Created)
{
    Created=false;if(auto* Existing=Rigs.Find(Definition))return *Existing;
    if(!Studio)Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetCreateDefaultLighting(false).SetForceMipsResident(false).AllowAudioPlayback(false));
    FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Rig=Studio->GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
    if(Rig){Rig->SetActorTickEnabled(false);Rig->SetActorEnableCollision(false);Rigs.Add(Definition,Rig);Created=true;}return Rig;
}
void UColdSteelPickupStudio::Warm(const FColdSteelItem& Item)
{
    if(Item.Definition!=TEXT("ue_m4a1")&&Item.Definition!=TEXT("ue_akm"))return;
    if(Bounds.Contains(Key(Item)))return;
    // The icon studio has already loaded this recipe. Prepare collision bounds before mouse release.
    // Acquire/build must initialize a new rig together, so only create the world here.
    if(!Studio)Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetCreateDefaultLighting(false).SetForceMipsResident(false).AllowAudioPlayback(false));
    auto* Preview=Studio->GetWorld()->SpawnActor<AColdSteelPickup>();
    if(Preview){Preview->SetActorTickEnabled(false);Preview->BuildWeapon(Item,GetGameInstance());Preview->Destroy();}
}
void UColdSteelPickupStudio::Deinitialize()
{
    for(auto& Pair:Rigs)if(IsValid(Pair.Value))Pair.Value->Destroy();
    Rigs.Empty();Bounds.Empty();Studio.Reset();Super::Deinitialize();
}
