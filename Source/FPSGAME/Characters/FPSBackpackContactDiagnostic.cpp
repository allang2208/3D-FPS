#if WITH_EDITOR
#include "FPSBackpackMotionComponent.h"
#include "FPSBodyOutfitResources.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace BackpackContactAudit20261024
{
TArray<TSharedPtr<FJsonValue>> Numbers(std::initializer_list<double> Values)
{
    TArray<TSharedPtr<FJsonValue>> Result;for(double Value:Values)Result.Add(MakeShared<FJsonValueNumber>(Value));return Result;
}
FVector Location(const TSharedPtr<FJsonObject>& Rigid,FName Shirt)
{
    const auto* Values=&Rigid->GetArrayField(TEXT("location"));const TSharedPtr<FJsonObject>* ByShirt=nullptr;
    if(!Shirt.IsNone()&&Rigid->TryGetObjectField(TEXT("location_by_shirt"),ByShirt))
    {
        const TArray<TSharedPtr<FJsonValue>>* Variant=nullptr;
        if((*ByShirt)->TryGetArrayField(Shirt.ToString(),Variant))Values=Variant;
    }
    return FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber());
}
}

int32 RunBackpackContactDiagnostic(const FString& Params)
{
    using namespace BackpackContactAudit20261024;
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))
       ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config))return 2;
    TMap<FString,TSharedPtr<FJsonObject>> Rigs;Rigs.Add(TEXT("Jason"),Config);
    const TSharedPtr<FJsonObject>* Variants=nullptr;
    if(Config->TryGetObjectField(TEXT("body_variants"),Variants))for(const auto& Pair:(*Variants)->Values)
        if(Pair.Value->Type==EJson::Object&&Pair.Value->AsObject()->HasField(TEXT("body_mesh")))Rigs.Add(FString(*Pair.Key),Pair.Value->AsObject());
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).RequiresHitProxies(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("BackpackContactDiagnostic"),nullptr,true,ERHIFeatureLevel::Num,&Init);
    if(!World)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;bool Passed=true;int32 FallbackCases=0;
    for(const auto& Rig:Rigs)
    {
        auto* BodyAsset=LoadObject<USkeletalMesh>(nullptr,*Rig.Value->GetStringField(TEXT("body_mesh")));
        if(!BodyAsset){World->DestroyWorld(false);return 2;}
        const auto Outfits=Rig.Value->GetObjectField(TEXT("outfits"));
        for(const auto& Pair:Outfits->Values)
        {
            if(Pair.Value->Type!=EJson::Object)continue;const auto Outfit=Pair.Value->AsObject();
            if(!Outfit->HasField(TEXT("backpack_motion")))continue;
            TArray<FString> Shirts;Shirts.Add(TEXT(""));
            const TSharedPtr<FJsonObject>* ByShirt=nullptr;
            if(Outfit->TryGetObjectField(TEXT("world_mesh_by_shirt"),ByShirt))for(const auto& Entry:(*ByShirt)->Values)Shirts.Add(FString(*Entry.Key));
            Shirts.Sort();
            const FName Unknown(TEXT("__unfitted_probe__"));const FName Default=FPSBodyOutfitResources::FittedShirt(Outfit,Unknown);
            bool Fallback=Default.IsNone()&&FPSBodyOutfitResources::StringForShirt(Outfit,TEXT("world_mesh"),Default)==Outfit->GetStringField(TEXT("world_mesh"));
            Passed&=Fallback;++FallbackCases;
            for(const FString& Shirt:Shirts)
            {
                const FName Fit=FPSBodyOutfitResources::FittedShirt(Outfit,FName(*Shirt));
                const FString Path=FPSBodyOutfitResources::StringForShirt(Outfit,TEXT("world_mesh"),Fit);
                auto* StrapAsset=LoadObject<USkeletalMesh>(nullptr,*Path);
                if(!StrapAsset){World->DestroyWorld(false);return 2;}
                auto* Pawn=World->SpawnActor<ACharacter>();auto* Body=Pawn->GetMesh();Body->SetSkeletalMeshAsset(BodyAsset);
                Body->SetRelativeTransform(FTransform::Identity);Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Body->RefreshBoneTransforms();
                auto* Strap=NewObject<USkeletalMeshComponent>(Pawn);Pawn->AddInstanceComponent(Strap);Strap->SetSkeletalMeshAsset(StrapAsset);Strap->SetupAttachment(Body);Strap->RegisterComponent();Strap->SetLeaderPoseComponent(Body);
                auto* Motion=NewObject<UFPSBackpackMotionComponent>(Pawn);Pawn->AddInstanceComponent(Motion);Motion->RegisterComponent();Motion->Configure(Body,Strap,Outfit,Fit);
                UStaticMeshComponent* Pouch=nullptr;FString RigidPath;const TSharedPtr<FJsonObject>* Rigid=nullptr;
                if(Outfit->TryGetObjectField(TEXT("rigid_pack"),Rigid))
                {
                    RigidPath=FPSBodyOutfitResources::StringForShirt(*Rigid,TEXT("mesh"),Fit);
                    auto* Asset=LoadObject<UStaticMesh>(nullptr,*RigidPath);if(!Asset){World->DestroyWorld(false);return 2;}
                    const auto& Q=(*Rigid)->GetArrayField(TEXT("rotation_quat"));
                    Pouch=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(Pouch);Pouch->SetStaticMesh(Asset);Pouch->SetupAttachment(Body,TEXT("spine_03"));Pouch->RegisterComponent();
                    Motion->AttachRigidBody(Pouch,FTransform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),Location(*Rigid,Fit)));
                }
                for(int32 Step=0;Step<240;++Step)Motion->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
                auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("rig"),Rig.Key);Row->SetStringField(TEXT("item"),Pair.Key);Row->SetStringField(TEXT("shirt"),Shirt);
                Row->SetStringField(TEXT("harness"),Path);Row->SetStringField(TEXT("rigid_mesh"),RigidPath);Row->SetBoolField(TEXT("gravity_contact"),Motion->Hanging.Enabled);
                Row->SetStringField(TEXT("gravity_mode"),Motion->Hanging.Enabled?TEXT("tether_and_torso_contact"):TEXT("supported_gravity"));
                Row->SetNumberField(TEXT("configured_sag_cm"),Motion->GravitySag);
                TArray<TSharedPtr<FJsonValue>> Field;for(float Value:Strap->GetCustomPrimitiveData().Data){Passed&=FMath::IsFinite(Value);Field.Add(MakeShared<FJsonValueNumber>(Value));}
                Row->SetArrayField(TEXT("current_and_previous_wpo"),Field);Passed&=Field.Num()==30;
                if(Pouch)
                {
                    Pouch->UpdateComponentToWorld();const FTransform Relative=Pouch->GetComponentTransform().GetRelativeTransform(Body->GetComponentTransform());
                    const FVector V=Relative.GetLocation();const FQuat Q=Relative.GetRotation();
                    Row->SetArrayField(TEXT("rigid_location"),Numbers({V.X,V.Y,V.Z}));Row->SetArrayField(TEXT("rigid_rotation_quat"),Numbers({Q.X,Q.Y,Q.Z,Q.W}));
                }
                TSet<FSoftObjectPath> Needed;FPSBodyOutfitResources::GatherOutfit(Pair.Value,FName(*Shirt),Needed);
                Passed&=Needed.Contains(FSoftObjectPath(Path));if(!RigidPath.IsEmpty())Passed&=Needed.Contains(FSoftObjectPath(RigidPath));
                Row->SetNumberField(TEXT("selected_resource_count"),Needed.Num());
                if(FParse::Param(*Params,TEXT("GravityCheck")))
                {
                    const auto RestField=Strap->GetCustomPrimitiveData().Data;
                    const double Drop=RestField.Num()>=15?-RestField[14]:0.;
                    bool Applied=Drop>.03&&(Motion->Hanging.Enabled||FMath::Abs(Drop-Motion->GravitySag)<.03);
                    double PeakSeparation=0.;FVector Position=FVector::ZeroVector;
                    for(int32 Step=0;Step<120;++Step)
                    {
                        const double Time=Step/60.;
                        const double Speed=Time<.2?3000.*Time:(Time<1.2?600.:(Time<1.4?3000.*(1.4-Time):0.));
                        const double Heading=Time<1.4?20.*FMath::Sin(2.*UE_PI*Time/1.4):0.;
                        const FQuat Turn(FVector::UpVector,FMath::DegreesToRadians(Heading));
                        const FVector Velocity=Turn.RotateVector(FVector(0,Speed,0));Position+=Velocity/60.;
                        Pawn->SetActorLocationAndRotation(Position,Turn);Pawn->GetCharacterMovement()->Velocity=Velocity;
                        Body->UpdateComponentToWorld();Body->RefreshBoneTransforms();Motion->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
                        const auto& Data=Strap->GetCustomPrimitiveData().Data;
                        const FTransform Carrier=Motion->InverseBind*Body->GetBoneTransform(Motion->Spine);
                        const FVector Shift=Carrier.InverseTransformVectorNoScale(FVector(Data[12],Data[13],Data[14]));
                        PeakSeparation=FMath::Max(PeakSeparation,-Shift.Y);
                    }
                    Pawn->SetActorRotation(FQuat::Identity);Pawn->GetCharacterMovement()->Velocity=FVector::ZeroVector;
                    Body->UpdateComponentToWorld();Body->RefreshBoneTransforms();
                    for(int32 Step=0;Step<180;++Step)Motion->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
                    const auto& Stopped=Strap->GetCustomPrimitiveData().Data;
                    double RestError=0.;for(int32 Index=3;Index<15;++Index)RestError=FMath::Max(RestError,double(FMath::Abs(Stopped[Index]-RestField[Index])));
                    const bool Settled=Motion->Hanging.Enabled?Motion->Hanging.Velocity.Size()<10.:RestError<.03;
                    const bool Attached=Motion->Hanging.Enabled||PeakSeparation<=Motion->MaxSeparation+.03;
                    Row->SetNumberField(TEXT("settled_drop_cm"),Drop);Row->SetNumberField(TEXT("peak_outward_correction_cm"),PeakSeparation);
                    Row->SetNumberField(TEXT("stop_rest_field_max_error"),RestError);Row->SetBoolField(TEXT("gravity_applied"),Applied);
                    Row->SetBoolField(TEXT("stop_settled"),Settled);Row->SetBoolField(TEXT("separation_within_limit"),Attached);
                    Passed&=Applied&&Settled&&Attached;
                }
                Rows.Add(MakeShared<FJsonValueObject>(Row));Motion->Clear();Pawn->Destroy();
            }
        }
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);Report->SetNumberField(TEXT("fallback_cases"),FallbackCases);Report->SetArrayField(TEXT("cases"),Rows);
    Report->SetBoolField(TEXT("gravity_movement_check"),FParse::Param(*Params,TEXT("GravityCheck")));
    Report->SetStringField(TEXT("scope"),TEXT("Current saved meshes, native reference pose, real backpack component settled for 4 seconds; optional start/turn/stop carrier motion and 3-second settling check; paired recipe/preload selection; no GameInstance, player saves, animation or networking"));
    FString Dir;FParse::Value(*Params,TEXT("ReportDir="),Dir);if(Dir.IsEmpty())Dir=FPaths::ProjectSavedDir()/TEXT("BackpackContactAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("native_contacts.json")));
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("BACKPACK_CONTACT_NATIVE cases=%d fallback=%d passed=%d"),Rows.Num(),FallbackCases,Passed);return Passed?0:1;
}
#endif
