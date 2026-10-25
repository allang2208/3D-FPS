#include "FurnitureRestAuditCommandlet.h"
#include "FPSFurnitureRestComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerState.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

int32 UFurnitureRestAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(TEXT("FurnitureRestAudit -ColdSteelProfile=SkillNetworkAudit_Furniture_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* Suppress=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.body.WorldBodySuppress"));
    const int32 PreviousSuppress=Suppress?Suppress->GetInt():0;
    if(Suppress)Suppress->Set(1,ECVF_SetByCode);
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FurnitureRestAuthorityAudit"));
    auto* World=GI->GetWorld();if(!World)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("FURNITURE_AUTHORITY %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    const auto Read=[](const FString& Path)
    {
        FString Text;TSharedPtr<FJsonObject> Data;
        if(FFileHelper::LoadFileToString(Text,*Path))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);
        return Data;
    };
    const auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());};
    const FString DataDir=FPaths::ProjectContentDir()/TEXT("ColdSteelData");
    const auto BodyData=Read(DataDir/TEXT("player_body.json"));
    const auto MainData=Read(DataDir/TEXT("furniture_rest.json"));
    const auto ApartmentData=Read(DataDir/TEXT("apartment_furniture_rest.json"));
    if(!BodyData||!MainData||!ApartmentData)return 2;
    TMap<FString,TSharedPtr<FJsonObject>> Types,Timing;
    TArray<TSharedPtr<FJsonValue>> Profiles;
    for(const auto& Library:{MainData,ApartmentData})
    {
        Profiles.Append(Library->GetArrayField(TEXT("furniture")));
        for(const auto& P:Library->GetObjectField(TEXT("types"))->Values)Types.Add(FString(*P.Key),P.Value->AsObject());
        for(const auto& P:Library->GetObjectField(TEXT("clips"))->Values)Timing.Add(FString(*P.Key),P.Value->AsObject());
    }
    auto* Jason=LoadObject<USkeletalMesh>(nullptr,*BodyData->GetStringField(TEXT("body_mesh")));
    TMap<FName,TObjectPtr<UAnimSequence>> JasonClips;
    for(const TCHAR* BodyId:{TEXT("jason"),TEXT("kaitlin")})
    {
        const auto Config=FString(BodyId)==TEXT("jason")?BodyData:BodyData->GetObjectField(TEXT("body_variants"))->GetObjectField(BodyId);
        auto* Body=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
        for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
        {
            const FString Role(*Pair.Key);
            if(!Role.StartsWith(TEXT("Rest.")))continue;
            auto* Sequence=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString());
            const auto* Duration=Timing.Find(Role);
            Check(Body&&Sequence&&Sequence->GetSkeleton()==Body->GetSkeleton()&&Duration&&
                FMath::IsNearlyEqual(Sequence->GetPlayLength(),float((*Duration)->GetNumberField(TEXT("duration"))),.035f),
                FString::Printf(TEXT("native_asset %s %s"),BodyId,*Pair.Key));
            if(FString(BodyId)==TEXT("jason"))JasonClips.Add(FName(*Role),Sequence);
        }
    }
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
#if WITH_EDITOR
    FAssetCompilingManager::Get().FinishAllCompilation();
#endif
    auto* Floor=World->SpawnActor<AStaticMeshActor>();
    Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);Floor->SetActorScale3D(FVector(100,100,1));
    Floor->SetActorLocation(FVector(0,0,-50));Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
    const auto SpawnPawn=[&](AFurnitureRestAuditController*& PC)
    {
        PC=World->SpawnActor<AFurnitureRestAuditController>();
        PC->SetPlayerState(World->SpawnActor<APlayerState>());
        FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AFurnitureRestAuditPawn>(FVector(3000,3000,100),FRotator::ZeroRotator,Spawn);
        PC->Possess(Pawn);Pawn->DispatchBeginPlay();
        Pawn->GetMesh()->SetSkeletalMeshAsset(Jason);Pawn->GetMesh()->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
        if(auto* Anim=Cast<UFPSPlayerBodyAnimInstance>(Pawn->GetMesh()->GetAnimInstance()))Anim->Clips=JasonClips;
        for(auto* C:Pawn->GetComponents())if(C)C->SetComponentTickEnabled(false);
        return Pawn;
    };
    AFurnitureRestAuditController *PC=nullptr,*OtherPC=nullptr;
    auto* Pawn=SpawnPawn(PC);auto* Other=SpawnPawn(OtherPC);
    auto* Rest=Pawn->FindComponentByClass<UFPSFurnitureRestComponent>();
    auto* OtherRest=Other->FindComponentByClass<UFPSFurnitureRestComponent>();
    auto* Survival=Pawn->FindComponentByClass<UFPSSurvivalComponent>();
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    auto* StateField=FindFProperty<FStructProperty>(Rest->GetClass(),TEXT("State"));
    auto* State=StateField->ContainerPtrToValuePtr<FFurnitureRestState>(Rest);
    const auto Step=[&](){Rest->TickComponent(.01f,LEVELTICK_All,nullptr);};
    const auto Elapse=[&](float Seconds){State->Started-=Seconds;Step();};
    const auto SanityStep=[&](){static_cast<UActorComponent*>(Survival)->TickComponent(1.f,LEVELTICK_All,nullptr);};
    int32 ModelIndex=0,SlotsChecked=0;
    for(const auto& Value:Profiles)
    {
        const auto Profile=Value->AsObject();auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Profile->GetStringField(TEXT("mesh")));
        Check(Mesh!=nullptr,FString::Printf(TEXT("mesh %d"),ModelIndex));if(!Mesh){++ModelIndex;continue;}
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
#endif
        auto* Furniture=World->SpawnActor<AStaticMeshActor>();auto* Component=Furniture->GetStaticMeshComponent();
        Component->SetMobility(EComponentMobility::Movable);Component->SetStaticMesh(Mesh);Component->SetCollisionProfileName(TEXT("BlockAll"));
        const FVector Scale=Profile->HasTypedField<EJson::Array>(TEXT("scale"))?Vec(Profile->GetArrayField(TEXT("scale"))):FVector::OneVector;
        Furniture->SetActorScale3D(Scale);
        int32 SlotIndex=0;
        for(const auto& SlotValue:Profile->GetArrayField(TEXT("slots")))
        {
            const auto Slot=SlotValue->AsObject();const FString Kind=Slot->GetStringField(TEXT("kind"));const auto Type=Types.FindChecked(Kind);
            const FString Label=FString::Printf(TEXT("model=%d slot=%d kind=%s"),ModelIndex,SlotIndex,*Kind);
            const FVector Seat=Furniture->GetActorTransform().TransformPosition(Vec(Slot->GetArrayField(TEXT("seat"))));
            const FVector Anchor=Seat-FVector(0,0,Type->GetNumberField(TEXT("surface_height")));
            const FRotator Facing(0,Slot->GetNumberField(TEXT("yaw")),0);
            const FVector Offset=Vec(Type->GetArrayField(TEXT("entry_offset")));
            const FVector Entry=Facing.RotateVector(FVector(Offset.Y,-Offset.X,Offset.Z));
            const auto Place=[&](AFurnitureRestAuditPawn* P,AFurnitureRestAuditController* C)
            {
                P->SetActorLocation(Anchor+Entry+Entry.GetSafeNormal2D()*25.f+FVector(0,0,P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f));
                P->SetActorRotation(Facing);P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
                const FVector AimPoint=Seat+(Type->GetBoolField(TEXT("lying"))?Entry.GetSafeNormal2D()*65.f:FVector::ZeroVector);
                C->SetControlRotation((AimPoint-P->GetMeleeAimTransform().GetLocation()).Rotation());
            };
            Other->SetActorLocation(FVector(3000,3000,100));Place(Pawn,PC);Health->Health=Health->MaxHealth;
            auto Saved=Survival->GetState();Saved.Sanity=20.f;Survival->RestoreState(Saved);
            const bool Focused=Rest->Interact();const bool Entered=Focused&&State->Phase==1;
            Check(Entered&&State->Kind==FName(Kind),TEXT("actual_entry_authoritative_eye ")+Label);
            if(!Entered)
            {
                FHitResult Hit;const FVector Eye=Pawn->GetMeleeAimTransform().GetLocation();
                FCollisionQueryParams Q(SCENE_QUERY_STAT(FurnitureAuditDiagnostic),false,Pawn);
                World->LineTraceSingleByChannel(Hit,Eye,Eye+PC->GetControlRotation().Vector()*250.f,ECC_Visibility,Q);
                FHitResult Ground;World->LineTraceSingleByChannel(Ground,Anchor+Entry+FVector(0,0,100),Anchor+Entry-FVector(0,0,220),ECC_Visibility,Q);
                UE_LOG(LogTemp,Display,TEXT("FURNITURE_FIXTURE_DIAG %s focused=%d hit=%s ground=%s eye=%s seat=%s physics=%d ground_mode=%d clips=%d controller=%d"),
                    *Label,Focused,*GetNameSafe(Hit.GetComponent()),*GetNameSafe(Ground.GetComponent()),*Eye.ToString(),*Seat.ToString(),Component->IsPhysicsStateCreated(),
                    Pawn->GetCharacterMovement()->IsMovingOnGround(),Cast<UFPSPlayerBodyAnimInstance>(Pawn->GetMesh()->GetAnimInstance())?1:0,Pawn->GetController()!=nullptr);
                ++SlotIndex;continue;
            }
            ++SlotsChecked;
            SanityStep();Check(FMath::IsNearlyEqual(Survival->GetState().Sanity,20.f,.01f),TEXT("no_san_during_entry ")+Label);
            Place(Other,OtherPC);OtherRest->Interact();Check(!OtherRest->IsResting(),TEXT("occupied_slot_rejected ")+Label);
            Other->SetActorLocation(FVector(3000,3000,100));
            Elapse(.61f);Elapse(float(Timing.FindChecked(TEXT("Rest.")+Kind+TEXT(".Enter"))->GetNumberField(TEXT("duration")))+.01f);
            Check(State->Phase==3,TEXT("settled_idle ")+Label);
            SanityStep();const float Expected=Type->GetBoolField(TEXT("lying"))?25.f:20.f;
            Check(FMath::IsNearlyEqual(Survival->GetState().Sanity,Expected,.01f),TEXT("san_authority_5_per_second ")+Label);
            State->Started-=20.f;Health->Health-=1.f;Step();
            Check(State->Phase==4,TEXT("damage_starts_full_exit_not_instant_finish ")+Label);
            SanityStep();Check(FMath::IsNearlyEqual(Survival->GetState().Sanity,Expected,.01f),TEXT("no_san_during_exit ")+Label);
            Elapse(float(Timing.FindChecked(TEXT("Rest.")+Kind+TEXT(".Exit"))->GetNumberField(TEXT("duration")))+.01f);
            Check(!Rest->IsResting()&&Pawn->GetCharacterMovement()->MovementMode==MOVE_Walking&&!PC->IsMoveInputIgnored(),TEXT("exit_restores_movement ")+Label);
            ++SlotIndex;
        }
        Furniture->Destroy();++ModelIndex;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetNumberField(TEXT("models"),Profiles.Num());Report->SetNumberField(TEXT("slots_entered"),SlotsChecked);
    Report->SetBoolField(TEXT("real_network_transport_tested"),false);Report->SetBoolField(TEXT("visual_tested"),false);
    Report->SetStringField(TEXT("boundary"),TEXT("Real authority Interact/phase/collision/SAN code; remote controller camera intentionally stale. Phase age advanced explicitly. No client RPC, rendering or user profile."));
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/FurnitureRest20261022/CompletionAudit20261025/authority.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));const bool Saved=FFileHelper::SaveStringToFile(Text,*Out);
    TArray<AActor*> Begun;for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())Begun.Add(*It);
    for(auto* A:Begun){A->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;A->GetComponents(Components);
        for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();
    if(Suppress)Suppress->Set(PreviousSuppress,ECVF_SetByCode);FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("FURNITURE_AUTHORITY_DONE checks=%d failures=%d slots=%d saved=%d"),Rows.Num(),Failures,SlotsChecked,Saved);
    return Failures||!Saved?1:0;
}
