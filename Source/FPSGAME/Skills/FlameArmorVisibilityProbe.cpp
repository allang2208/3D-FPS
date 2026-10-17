// Explicit, editor-only diagnosis of the reported invisible flame armor.
// Never invoked by gameplay or by asset preparation.
#if WITH_EDITOR
#include "FlameArmorAssets.h"
#include "FPSFireMagicComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "FXSystem.h"
#include "HAL/IConsoleManager.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSimCache.h"
#include "NiagaraSimCacheFunctionLibrary.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSystemInstanceController.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "UObject/UnrealType.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

namespace
{
void ProbeArmorParticles(const TArray<FString>& Args,UWorld* World)
{
    if(!World||Args.Num()!=1)return;
    auto Report=MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("dispatch_before"),FNiagaraGpuComputeDispatchInterface::Get(World)!=nullptr);
    // UWorld::CreateFXSystem deliberately skips commandlets. This explicit
    // diagnostic owns an empty preview world, without a viewport or gameplay.
    if(!World->FXSystem)World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    Report->SetBoolField(TEXT("dispatch_after"),FNiagaraGpuComputeDispatchInterface::Get(World)!=nullptr);
    for(const TCHAR* Path:{FlameArmorAssets::Body,FlameArmorAssets::Weapon,FlameArmorAssets::Arrow})
    {
        auto Row=MakeShared<FJsonObject>();Report->SetObjectField(Path,Row);
        auto* System=LoadObject<UNiagaraSystem>(nullptr,Path);if(!System)continue;
        System->WaitForCompilationComplete(true,false);
        Row->SetBoolField(TEXT("valid"),System->IsValid());Row->SetBoolField(TEXT("ready"),System->IsReadyToRun());
        Row->SetBoolField(TEXT("scalability"),System->IsAllowedByScalability());
        auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(World,System,FVector(0,0,-100000),FRotator::ZeroRotator,FVector(1),false,false,ENCPoolMethod::None,false);
        Row->SetBoolField(TEXT("component"),FX!=nullptr);if(!FX)continue;
        FX->SetForceSolo(true);FX->SetVisibility(false);
        for(const TCHAR* Name:{TEXT("Fade"),TEXT("Detail"),TEXT("Coverage"),TEXT("MotionEnergy"),TEXT("UpperVisibility")})FX->SetVariableFloat(FName(FString(TEXT("User."))+Name),1.f);
        FX->SetVariableFloat(TEXT("User.WeaponSize"),.7f);FX->SetVariableFloat(TEXT("User.Radius"),40.f);FX->SetVariableFloat(TEXT("User.BodyHeight"),180.f);
        FX->SetVariableVec3(TEXT("User.WeaponEnd"),FVector(100,0,0));FX->SetVariableVec3(TEXT("User.FlameProfile"),FVector(1));
        FX->SetVariableVec3(TEXT("User.Velocity"),FVector(3000,0,0));
        for(const TCHAR* Name:{TEXT("BodyOrigin"),TEXT("WeaponStartWorld"),TEXT("WeaponEndWorld"),TEXT("PreviousStart"),TEXT("PreviousEnd"),TEXT("PreviousPosition"),TEXT("CurrentPosition")})
            FX->SetVariablePosition(FName(FString(TEXT("User."))+Name),FX->GetComponentLocation());
        FX->Activate(true);Row->SetBoolField(TEXT("active_at_start"),FX->IsActive());
        FX->AdvanceSimulation(30,1.f/60.f);
        Row->SetBoolField(TEXT("active_after"),FX->IsActive());Row->SetBoolField(TEXT("complete"),FX->IsComplete());
        Row->SetBoolField(TEXT("controller"),FX->GetSystemInstanceController().IsValid());
        auto* Cache=UNiagaraSimCacheFunctionLibrary::CreateNiagaraSimCache(World);UNiagaraSimCache* Captured=nullptr;
        const bool Capture=UNiagaraSimCacheFunctionLibrary::CaptureNiagaraSimCacheImmediate(Cache,FNiagaraSimCacheCreateParameters::CreateForDebugging(),FX,Captured);
        Row->SetBoolField(TEXT("capture"),Capture);
        if(Capture)for(FName Name:Cache->GetEmitterNames())
        {
            TArray<FVector> Positions;TArray<FLinearColor> Colors;TArray<FVector2D> Sizes;TArray<float> Ages;
            Cache->ReadPositionAttribute(Positions,TEXT("Position"),Name,false);
            Cache->ReadColorAttribute(Colors,TEXT("Color"),Name);Cache->ReadVector2Attribute(Sizes,TEXT("SpriteSize"),Name);
            Cache->ReadFloatAttribute(Ages,TEXT("NormalizedAge"),Name);
            auto Emitter=MakeShared<FJsonObject>();Row->SetObjectField(Name.ToString(),Emitter);
            Emitter->SetNumberField(TEXT("particles"),Positions.Num());
            float MaxAlpha=0;for(const auto& C:Colors)MaxAlpha=FMath::Max(MaxAlpha,C.A);
            Emitter->SetNumberField(TEXT("max_alpha"),MaxAlpha);
            if(Colors.Num())Emitter->SetStringField(TEXT("color"),Colors[0].ToString());
            if(Sizes.Num())Emitter->SetStringField(TEXT("size"),Sizes[0].ToString());
            if(Positions.Num())Emitter->SetStringField(TEXT("position"),Positions[0].ToString());
            if(Ages.Num())Emitter->SetNumberField(TEXT("normalized_age"),Ages[0]);
        }
        FX->DestroyComponent();
    }
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*Args[0]);
    UE_LOG(LogTemp,Display,TEXT("FLAME_VISIBILITY_PROBE %s"),*Text);
}
FAutoConsoleCommandWithWorldAndArgs ArmorProbe(TEXT("fps.FlameArmor.Probe"),TEXT("Explicit hidden particle-data diagnosis; requires an output path."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(ProbeArmorParticles));

void ProbeArmorPresenter(const TArray<FString>& Args,UWorld*)
{
    if(Args.Num()!=1||!IsRunningCommandlet())return;
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("FlameArmorVisibilityAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Slot+TEXT(" -FlameArmorAudit")));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FlameArmorVisibilityAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return;
    if(!World->FXSystem)World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=0;Seed.ActiveProductionTool.Reset();Seed.Health=100;Seed.Mana=10000;
    Seed.Skills.FindOrAdd(TEXT("flameArmor")).Level=1;Model->CommitState(Seed);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    auto* Fists=Pawn->FindComponentByClass<UFPSUnarmedIdleComponent>();
    static_cast<UActorComponent*>(Fists)->BeginPlay();FlushAsyncLoading();
    const TPair<const TCHAR*,const TCHAR*> Resources[]={{TEXT("AuraSystem"),FlameArmorAssets::Body},{TEXT("WeaponSystem"),FlameArmorAssets::Weapon},{TEXT("ArrowSystem"),FlameArmorAssets::Arrow}};
    for(const auto& Entry:Resources)
    {
        auto* System=LoadObject<UNiagaraSystem>(nullptr,Entry.Value);System->WaitForCompilationComplete(true,false);
        FindFProperty<FObjectPropertyBase>(Fire->GetClass(),Entry.Key)->SetObjectPropertyValue_InContainer(Fire,System);
    }
    auto Report=MakeShared<FJsonObject>();FColdSteelNetCastRequest Request;Request.SkillId=TEXT("flameArmor");Request.CastId=1;
    Report->SetBoolField(TEXT("release"),Fire->NetRelease(Pawn,Request,Model,Model->FireMagicStats(TEXT("flameArmor"))));
    Report->SetNumberField(TEXT("remaining_at_start"),Fire->ArmorRemaining());
    for(int32 Frame=0;Frame<40;++Frame)
    {
        static_cast<UActorComponent*>(Fists)->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
        static_cast<UActorComponent*>(Fire)->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
        TArray<UNiagaraComponent*> Components;Pawn->GetComponents(Components);
        for(auto* FX:Components){FX->SetForceSolo(true);FX->AdvanceSimulation(1,1.f/60.f);}
    }
    Report->SetNumberField(TEXT("remaining_after"),Fire->ArmorRemaining());
    TArray<UNiagaraComponent*> Components;Pawn->GetComponents(Components);
    for(auto* FX:Components)
    {
        auto Row=MakeShared<FJsonObject>();Report->SetObjectField(FX->GetName(),Row);
        Row->SetStringField(TEXT("asset"),GetPathNameSafe(FX->GetAsset()));Row->SetStringField(TEXT("transform"),FX->GetComponentTransform().ToString());
        Row->SetBoolField(TEXT("visible"),FX->IsVisible());Row->SetBoolField(TEXT("hidden"),FX->bHiddenInGame);
        Row->SetBoolField(TEXT("active"),FX->IsActive());Row->SetBoolField(TEXT("complete"),FX->IsComplete());Row->SetBoolField(TEXT("rendering"),FX->GetRenderingEnabled());
        bool Valid=false;Row->SetNumberField(TEXT("fade"),FX->GetVariableFloat(TEXT("User.Fade"),Valid));Row->SetNumberField(TEXT("detail"),FX->GetVariableFloat(TEXT("User.Detail"),Valid));
        auto* Cache=UNiagaraSimCacheFunctionLibrary::CreateNiagaraSimCache(World);UNiagaraSimCache* Captured=nullptr;
        if(UNiagaraSimCacheFunctionLibrary::CaptureNiagaraSimCacheImmediate(Cache,FNiagaraSimCacheCreateParameters::CreateForDebugging(),FX,Captured))
        for(FName Name:Cache->GetEmitterNames())
        {TArray<FVector> Positions;Cache->ReadPositionAttribute(Positions,TEXT("Position"),Name);Row->SetNumberField(Name.ToString(),Positions.Num());}
    }
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Args[0]);
    UE_LOG(LogTemp,Display,TEXT("FLAME_PRESENTER_PROBE %s"),*Text);
    Fire->FinishFireMagicForRemoval();static_cast<UActorComponent*>(Fists)->EndPlay(EEndPlayReason::Destroyed);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
}
FAutoConsoleCommandWithWorldAndArgs ArmorPresenterProbe(TEXT("fps.FlameArmor.PresenterProbe"),TEXT("Commandlet-only isolated armor presenter diagnosis."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(ProbeArmorPresenter));
}
#endif
