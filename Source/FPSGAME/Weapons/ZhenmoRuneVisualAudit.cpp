#include "ZhenmoRuneComponent.h"

#if !UE_BUILD_SHIPPING
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/NurseZombie.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraActor.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"
#include "UnrealClient.h"

namespace
{
void ZhenmoVisualAudit(UWorld* World)
{
    if(!World||!FParse::Param(FCommandLine::Get(),TEXT("ZhenmoVisualAudit")))return;
    auto* Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerCharacter(World,0));
    if(!Profile||!Player||!Profile->ProfileSlot().StartsWith(TEXT("ColdSteel_ZhenmoVisualAudit")))return;
    // Stabilize this rendering comparison independently of unrelated startup streams.
    LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3/M_ZhenmoSoftGround.M_ZhenmoSoftGround"));
    auto* AuditSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold.NS_ZhenmoRisingGold"));
    AuditSystem->bDumpDebugSystemInfo=FParse::Param(FCommandLine::Get(),TEXT("ZhenmoAuditDump"));
    FString Label=TEXT("baseline");FParse::Value(FCommandLine::Get(),TEXT("ZhenmoAuditLabel="),Label);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("ZhenmoVisualAudit20261006")/Label;
    IFileManager::Get().MakeDirectory(*Out,true);
    auto State=Profile->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;
    State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    auto Sword=Profile->CreateItem(TEXT("ue_xuanchi_zhenyue"));Sword.Place=1;Sword.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Sword.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_2"),TEXT("zhenmo_rune"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Sword.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Sword.Data));
    State.Items.Add(Sword);
    if(!Profile->CommitState(State))return;
    Player->ApplyColdSteelProfile(Profile);
    Player->SetActorLocation(FVector(-1100,-400,150));
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* PC=Cast<APlayerController>(Player->GetController()))
    {
        const FVector Focus(-1100,-400,20),View=Focus+FVector(0,-1500,2400);
        auto* Camera=World->SpawnActor<ACameraActor>(View,(Focus-View).Rotation(),Spawn);
        PC->SetViewTarget(Camera);PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);
    }
    auto* Target=World->SpawnActor<ANurseZombie>(FVector(-650,-400,160),FRotator(0,180,0),Spawn);
    if(!Target)return;
    Target->SetActorTickEnabled(false);Target->GetCharacterMovement()->DisableMovement();
    Target->Tags.AddUnique(TEXT("NoSkillTraining"));
    auto Later=[World,Player](float Delay,TFunction<void()> Work)
    {FTimerHandle Timer;World->GetTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(Player,MoveTemp(Work)),Delay,false);};
    Later(12.f,[World,Player,Target,Profile]()
    {
        UWidgetLayoutLibrary::RemoveAllWidgets(World);
        auto Shot=ColdSteelSkills::Snapshot(Player);
        Shot.CriticalChance=100000.f;
        FHitResult Hit(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),FVector::UpVector);
        Hit.BoneName=TEXT("head");FWeaponDamageResult Result;
        const float Applied=Profile->ApplySkillWeaponHit(Player,Hit,1.f,FVector::ForwardVector,Shot,&Result);
        auto* Rune=Player->FindComponentByClass<UZhenmoRuneComponent>();
        UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT hit critical=%d damage=%.3f source=%s remaining=%.3f"),
            Result.bCritical,Applied,*Shot.ZhenmoSourceInstance,Rune?Rune->Remaining():-1.f);
        auto* System=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold.NS_ZhenmoRisingGold"));
        if(System)
        {
            System->bDumpDebugSystemInfo=FParse::Param(FCommandLine::Get(),TEXT("ZhenmoAuditDump"));
            UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT Niagara valid=%d ready=%d handles=%d"),System->IsValid(),System->IsReadyToRun(),System->GetEmitterHandles().Num());
            for(const auto& Handle:System->GetEmitterHandles())
                UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT Emitter name=%s enabled=%d data=%d mode=%d"),*Handle.GetName().ToString(),Handle.GetIsEnabled(),Handle.GetInstance().GetEmitterData()!=nullptr,int(Handle.GetEmitterMode()));
        }
    });
    Later(15.f,[World,Player]()
    {
#if WITH_EDITOR
        if(!FParse::Param(FCommandLine::Get(),TEXT("ZhenmoAuditRecompile")))return;
        auto* System=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold.NS_ZhenmoRisingGold"));
        System->RequestCompile(true);System->WaitForCompilationComplete(true,false);
        TArray<UNiagaraComponent*> Motes;Player->GetComponents(Motes);
        for(auto* Mote:Motes)if(Mote->GetFName()==TEXT("ZhenmoRisingGold"))Mote->ReinitializeSystem();
        UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT forced recompile valid=%d"),System->IsValid());
#endif
    });
    for(float Delay:{12.2f,14.f,19.f,26.f,28.5f})Later(Delay,[World,Player,Out,Delay]()
    {
        auto* Rune=Player->FindComponentByClass<UZhenmoRuneComponent>();
        TArray<UDynamicMeshComponent*> Surfaces;Player->GetComponents(Surfaces);
        for(auto* Surface:Surfaces)if(Surface->GetFName()==TEXT("ZhenmoSoftGround"))
        {
            float Opacity=-1;auto* MID=Cast<UMaterialInstanceDynamic>(Surface->GetMaterial(0));
            if(MID)MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("FieldOpacity")),Opacity);
            UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT frame=%.1f remaining=%.3f tick=%d triangles=%d opacity=%.3f visible=%d location=%s material=%s"),
                Delay,Rune?Rune->Remaining():-1.f,Rune&&Rune->IsComponentTickEnabled(),Surface->GetMesh()->TriangleCount(),Opacity,
                Surface->IsVisible(),*Surface->GetComponentLocation().ToString(),*GetNameSafe(MID));
        }
        TArray<UNiagaraComponent*> Motes;Player->GetComponents(Motes);
        for(auto* Mote:Motes)if(Mote->GetFName()==TEXT("ZhenmoRisingGold"))
            UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT motes active=%d complete=%d"),
                Mote->IsActive(),Mote->IsComplete());
        if(Delay==14.f)UKismetSystemLibrary::ExecuteConsoleCommand(World,TEXT("fx.Niagara.DumpComponents full filter=Zhenmo"));
        FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("field-%.1f.png"),Delay),true,false);
    });
    if(FParse::Param(FCommandLine::Get(),TEXT("ZhenmoAuditExit")))
        Later(29.f,[](){FPlatformMisc::RequestExit(false);});
    UE_LOG(LogTemp,Display,TEXT("ZHENMO_AUDIT fixture ready isolated_profile=%s output=%s"),*Profile->ProfileSlot(),*Out);
}
FAutoConsoleCommandWithWorld ZhenmoAuditCommand(TEXT("fps.Zhenmo.VisualAudit"),
    TEXT("Explicit Zhenmo visual diagnosis; requires -ZhenmoVisualAudit and an isolated audit profile."),
    FConsoleCommandWithWorldDelegate::CreateStatic(&ZhenmoVisualAudit));
}
#endif
