#if WITH_EDITOR
#include "FPSBackpackMotionComponent.h"
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

// No GameInstance, player profile, networking driver or map gameplay. Model the
// CMC correction invariant (capsule moves, rendered mesh stays) against a twin.
int32 RunBackpackLifecycleDiagnostic(const FString& Params)
{
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config))return 2;
    auto* BodyAsset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));if(!BodyAsset)return 2;
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).RequiresHitProxies(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("BackpackLifecycleDiagnostic"),nullptr,true,ERHIFeatureLevel::Num,&Init);
    if(!World)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;bool AllPassed=true;
    const TArray<FString> Shirts={TEXT(""),TEXT("ue_field_sweater_charcoal"),TEXT("ue_field_sweater"),TEXT("ue_chainmail_shirt"),TEXT("ue_blue_mage_robe"),TEXT("ue_st6_sleeves")};
    for(const TCHAR* Item:{TEXT("ue_simple_sling_bag"),TEXT("ue_portable_backpack"),TEXT("ue_mountain_backpack"),TEXT("ue_expedition_backpack"),TEXT("ue_pathfinder_backpack")})
    for(const FString& Shirt:Shirts)
    {
        const auto Outfit=Config->GetObjectField(TEXT("outfits"))->GetObjectField(Item);
        FString Path=Outfit->GetStringField(TEXT("world_mesh"));
        if(!Shirt.IsEmpty())Outfit->GetObjectField(TEXT("world_mesh_by_shirt"))->TryGetStringField(Shirt,Path);
        auto* StrapAsset=LoadObject<USkeletalMesh>(nullptr,*Path);if(!StrapAsset){World->DestroyWorld(false);return 2;}
        ACharacter* Pawns[2];UFPSBackpackMotionComponent* Motions[2];USkeletalMeshComponent* Straps[2];
        for(int32 I=0;I<2;++I)
        {
            auto* Pawn=World->SpawnActor<ACharacter>();Pawns[I]=Pawn;auto* Body=Pawn->GetMesh();
            Body->SetSkeletalMeshAsset(BodyAsset);Body->SetRelativeTransform(FTransform::Identity);
            Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
            Body->RefreshBoneTransforms();
            auto* Strap=NewObject<USkeletalMeshComponent>(Pawn);Straps[I]=Strap;Pawn->AddInstanceComponent(Strap);
            Strap->SetSkeletalMeshAsset(StrapAsset);Strap->SetupAttachment(Body);Strap->RegisterComponent();Strap->SetLeaderPoseComponent(Body);
            auto* Motion=NewObject<UFPSBackpackMotionComponent>(Pawn);Motions[I]=Motion;Pawn->AddInstanceComponent(Motion);Motion->RegisterComponent();
            Motion->Configure(Body,Strap,Outfit,FName(*Shirt));
            const TSharedPtr<FJsonObject>* Rigid=nullptr;
            if(Outfit->TryGetObjectField(TEXT("rigid_pack"),Rigid))
            {
                auto* Mesh=LoadObject<UStaticMesh>(nullptr,*(*Rigid)->GetStringField(TEXT("mesh")));if(!Mesh){World->DestroyWorld(false);return 2;}
                const auto* L=&(*Rigid)->GetArrayField(TEXT("location"));
                if(!Shirt.IsEmpty())L=&(*Rigid)->GetObjectField(TEXT("location_by_shirt"))->GetArrayField(Shirt);
                const auto& Q=(*Rigid)->GetArrayField(TEXT("rotation_quat"));
                auto* Pouch=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(Pouch);Pouch->SetStaticMesh(Mesh);
                Pouch->SetupAttachment(Body,TEXT("spine_03"));Pouch->RegisterComponent();
                Motion->AttachRigidBody(Pouch,FTransform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),
                    FVector((*L)[0]->AsNumber(),(*L)[1]->AsNumber(),(*L)[2]->AsNumber())));
            }
        }
        const float Dt=1.f/60.f;
        // Excite the actual spring before the correction; the gravity branch
        // instead establishes its hanging state under its authored constraints.
        for(int32 Step=0;Step<16;++Step)for(int32 I=0;I<2;++I)
        {
            Pawns[I]->GetCharacterMovement()->Velocity=Step==15?FVector(400,0,0):FVector::ZeroVector;
            Motions[I]->TickComponent(Dt,LEVELTICK_All,nullptr);
        }
        const FTransform Visible=Pawns[1]->GetMesh()->GetComponentTransform();
        Pawns[1]->SetActorLocation(FVector(200,0,0));Pawns[1]->GetMesh()->SetWorldTransform(Visible);
        Pawns[1]->GetMesh()->RefreshBoneTransforms();
        for(auto* Motion:Motions)Motion->TickComponent(Dt,LEVELTICK_All,nullptr);
        const auto& A=Straps[0]->GetCustomPrimitiveData().Data;const auto& B=Straps[1]->GetCustomPrimitiveData().Data;
        double Error=0;bool Corrected=A.Num()==30&&B.Num()==30;
        for(int32 I=0;Corrected&&I<30;++I){if(!FMath::IsFinite(B[I]))Corrected=false;else Error=FMath::Max(Error,double(FMath::Abs(A[I]-B[I])));}
        Corrected&=Error<.001;
        auto* M=Motions[1];
        // An actual visible teleport must still clear all stale deformation,
        // including previous-frame WPO (no velocity streak across the jump).
        Pawns[1]->SetActorLocation(FVector(1000,0,0));Pawns[1]->GetMesh()->RefreshBoneTransforms();M->TickComponent(Dt,LEVELTICK_All,nullptr);
        const auto& Teleport=Straps[1]->GetCustomPrimitiveData().Data;bool Reset=Teleport.Num()==30;
        for(int32 I=0;Reset&&I<15;++I)Reset&=FMath::IsNearlyEqual(Teleport[I],Teleport[I+15],.0001f)&&(I<3||FMath::IsNearlyZero(Teleport[I],.0001f));
        M->Clear();bool Cleared=!M->IsComponentTickEnabled()&&!M->Hanging.Enabled&&!M->RigidBody.IsValid();
        for(float V:Straps[1]->GetCustomPrimitiveData().Data)Cleared&=FMath::IsNearlyZero(V);
        // Rebinding after unequip must use the new shirt's proxy, not cached
        // hulls/center from the old garment. ApplyOutfit invokes this same pair.
        const FString Next=Shirts[(Shirts.Find(Shirt)+1)%Shirts.Num()];
        M->Configure(Pawns[1]->GetMesh(),Straps[1],Outfit,FName(*Next));
        bool Rebound=M->IsComponentTickEnabled()&&!M->Hanging.Initialized;
        if(M->Hanging.Enabled)
        {
            const auto H=Next.IsEmpty()?Outfit->GetObjectField(TEXT("hanging_pack")):Outfit->GetObjectField(TEXT("hanging_pack_by_shirt"))->GetObjectField(Next);
            const auto& C=H->GetArrayField(TEXT("center"));Rebound&=M->Pivot.Equals(FVector(C[0]->AsNumber(),C[1]->AsNumber(),C[2]->AsNumber()),.001);
        }
        const bool Pass=Corrected&&Reset&&Cleared&&Rebound;AllPassed&=Pass;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("item"),Item);Row->SetStringField(TEXT("shirt"),Shirt);
        Row->SetBoolField(TEXT("passed"),Pass);Row->SetBoolField(TEXT("smoothed_correction"),Corrected);Row->SetNumberField(TEXT("correction_field_error"),Error);
        Row->SetBoolField(TEXT("visible_teleport_reset"),Reset);Row->SetBoolField(TEXT("unequip_clear"),Cleared);Row->SetBoolField(TEXT("shirt_rebind"),Rebound);Rows.Add(MakeShared<FJsonValueObject>(Row));
        for(int32 I=0;I<2;++I){Motions[I]->Clear();Pawns[I]->Destroy();}
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),AllPassed);Report->SetArrayField(TEXT("cases"),Rows);
    Report->SetStringField(TEXT("scope"),TEXT("Real-asset component fixtures; simulated CMC capsule/mesh correction, visible teleport, clear/rebind; no sockets, GameInstance, profile or rendered/gameplay acceptance"));
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FString Dir;FParse::Value(*Params,TEXT("ReportDir="),Dir);
    if(Dir.IsEmpty())Dir=FPaths::ProjectSavedDir()/TEXT("BackpackLifecycleAudit20261023");IFileManager::Get().MakeDirectory(*Dir,true);
    FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("native_lifecycle.json")));World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_LIFECYCLE cases=%d passed=%d"),Rows.Num(),AllPassed);return AllPassed?0:1;
}
#endif
