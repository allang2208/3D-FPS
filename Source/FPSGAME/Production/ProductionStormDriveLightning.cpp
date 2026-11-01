#include "ProductionToolComponent.h"
#include "RuneboundHammerTuning.h"
#include "ThunderHammerCall.h"
#include "ThunderHammerPommel.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"

namespace StormDriveFX
{
constexpr int32 Arcs=8,Steps=18,Sides=4,Rings=Steps+1,Pool=5;
constexpr float BurstSeconds=.46f;
const FSoftObjectPath JiLeiLightning(TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/M_JiLei_BlueWhiteLightning.M_JiLei_BlueWhiteLightning"));
bool IsCallSeat(const UStaticMesh* Mesh)
{
    if(!Mesh)return false;
    const FString Name=Mesh->GetName();
    return Name==TEXT("SM_ThunderGodHammer_head_mount_ji_lei_seat")||
        Name.StartsWith(TEXT("SM_ThunderGodHammer_head_mount_ji_lei_seat_"));
}
UStaticMesh* ResolveSeatMesh(UStaticMeshComponent* Part,const AFPSGAMECharacter* Pawn)
{
    UStaticMesh* Mesh=IsValid(Part)&&Part->IsRegistered()?Part->GetStaticMesh():nullptr;
    if(!IsValid(Mesh)||!Part->IsVisible()||Part->bHiddenInGame||
        (Pawn->IsLocallyControlled()?Part->bOwnerNoSee:Part->bOnlyOwnerSee))return nullptr;
    return Mesh->GetName().Contains(TEXT("Warhammer_StormDrive_"))||
        IsCallSeat(Mesh)?Mesh:nullptr;
}
UE::Geometry::FDynamicMesh3 Topology()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    auto* UV=Mesh.Attributes()->PrimaryUV();auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 A=0;A<Arcs;++A)
    {
        const int32 Base=A*Rings*Sides;
        for(int32 I=0;I<Rings;++I)for(int32 J=0;J<Sides;++J)
        {Mesh.AppendVertex(FVector3d(I*.01,J*.01,A*.01));UV->AppendElement(FVector2f(float(I)/Steps,float(J)/Sides));Normals->AppendElement(FVector3f(0,0,1));}
        for(int32 I=0;I<Steps;++I)for(int32 J=0;J<Sides;++J)
        {
            const int32 V=Base+I*Sides+J,N=Base+I*Sides+(J+1)%Sides;
            for(const FIndex3i& T:{FIndex3i(V,N,V+Sides),FIndex3i(N,N+Sides,V+Sides)})
            {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
        }
    }
    return Mesh;
}
void Tube(UE::Geometry::FDynamicMesh3& Mesh,int32 Arc,const FVector* Points,float Width)
{
    for(int32 I=0;I<Rings;++I)
    {
        const FVector Tangent=(Points[FMath::Min(I+1,Steps)]-Points[FMath::Max(I-1,0)]).GetSafeNormal();
        FVector X,Y;Tangent.FindBestAxisVectors(X,Y);
        const float Radius=Width*FMath::Sin(float(I)/Steps*PI);
        for(int32 J=0;J<Sides;++J)
        {const float Angle=J*2.f*PI/Sides;Mesh.SetVertex(Arc*Rings*Sides+I*Sides+J,FVector3d(Points[I]+Radius*(X*FMath::Cos(Angle)+Y*FMath::Sin(Angle))));}
    }
}
bool Installed(const FColdSteelItem& Item)
{
    // Retired from Thor's equipment; stale save selections must not retain its FX/passive.
    if(Item.Definition==TEXT("ue_thunder_god_hammer"))return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Parts=nullptr;FString Id;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&(*Parts)->TryGetStringField(TEXT("head_mount"),Id)&&Id==TEXT("storm_drive_seat");
}
}

void UProductionToolComponent::RecordStormDriveHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit)
{
    // Called by the existing successful enemy-hit receipt, before awakening's
    // per-attack charge dedupe. Normal, heavy, quick and skill contacts qualify.
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||!Shot.bMelee||Shot.bRicochet)return;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||Item->InstanceId!=Shot.ItemInstance||!RuneboundHammer::HasFinalToll(*Item)||!StormDriveFX::Installed(*Item))return;
    MulticastStormDriveImpact(Hit.GetActor(),Hit.ImpactPoint,Hit.ImpactNormal,Shot.MasteryAttackSerial,RuneboundClock());
}

void UProductionToolComponent::MulticastStormDriveImpact_Implementation(AActor* Target,FVector Point,FVector Normal,uint32 Seed,double ServerAt)
{
    if(GetNetMode()==NM_DedicatedServer||RuneboundClock()-ServerAt>StormDriveFX::BurstSeconds)return;
    int32 Slot=0;for(int32 I=1;I<4;++I)if(StormDriveBursts[I].ServerAt<StormDriveBursts[Slot].ServerAt)Slot=I;
    auto& Burst=StormDriveBursts[Slot];Burst.Target=Target;Burst.WorldPoint=Point;
    Burst.LocalPoint=IsValid(Target)?Target->GetActorTransform().InverseTransformPosition(Point):Point;
    Burst.Normal=Normal.IsNearlyZero()?FVector::UpVector:Normal.GetSafeNormal();Burst.ServerAt=ServerAt;Burst.Seed=Seed;
}

void UProductionToolComponent::UpdateStormDriveLightning(float Delta)
{
    using namespace StormDriveFX;
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    StormDriveSeatRefresh-=Delta;
    if(StormDriveSeatRefresh<=0.f)
    {
        StormDriveSeatRefresh=.25f;StormDriveSeat.Reset();
        TInlineComponentArray<UStaticMeshComponent*> Parts(Pawn);
        for(auto* Part:Parts)
        {
            if(ResolveSeatMesh(Part,Pawn))StormDriveSeat=Part;
            // Remote bodies have no local tool pivot. Use the replicated buff
            // on their actual visible assembly during the existing discovery pass.
            if(Part->IsVisible()&&!Part->bHiddenInGame&&
                (Pawn->IsLocallyControlled()?!Part->bOwnerNoSee:!Part->bOnlyOwnerSee))
                ThunderHammerPommel::RefreshWorldCore(Pawn,Part);
        }
    }
    auto* Seat=StormDriveSeat.Get();
    // Equipment refresh can reuse a live component while clearing/replacing its mesh.
    // A valid weak component pointer does not keep the cached seat asset valid.
    auto* SeatAsset=ResolveSeatMesh(Seat,Pawn);
    if(Seat&&!SeatAsset){StormDriveSeat.Reset();StormDriveSeatRefresh=0.f;Seat=nullptr;}
    const bool CallSeat=IsCallSeat(SeatAsset);
    auto* Viewer=UGameplayStatics::GetPlayerCameraManager(Pawn,0);
    const double Now=RuneboundClock();
    const bool ShowSeat=SeatAsset&&(!CallSeat||bThunderCallCharging)&&Viewer&&
        FVector::DistSquared(Viewer->GetCameraLocation(),Seat->GetComponentLocation())<FMath::Square(3500.f);
    bool HasBurst=false;for(const auto& Burst:StormDriveBursts)HasBurst|=Now-Burst.ServerAt>=0.&&Now-Burst.ServerAt<BurstSeconds;
    if(!ShowSeat&&!HasBurst){for(const auto& Mesh:StormDriveMeshes)if(Mesh)Mesh->SetVisibility(false);return;}
    if(!StormDriveMaterial||(CallSeat&&(!JiLeiLightning.ResolveObject()||!ThunderCallChargeSound)))
    {
        if(!StormDriveLoad||StormDriveLoad->HasLoadCompleted())
        {
            const FSoftObjectPath Path(RuneboundHammer::FinalTollLightning);
            const FSoftObjectPath CallAudio(ThunderHammerCall::ChargeSound);
            TWeakObjectPtr<UProductionToolComponent> Weak(this);
            StormDriveLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Path,JiLeiLightning,CallAudio},FStreamableDelegate::CreateLambda([Weak,Path,CallAudio]()
            {if(Weak.IsValid())
                {Weak->StormDriveMaterial=Cast<UMaterialInterface>(Path.ResolveObject());Weak->ThunderCallChargeSound=Cast<USoundBase>(CallAudio.ResolveObject());}
            }));
        }
        return;
    }
    if(StormDriveMeshes.IsEmpty()){StormDriveMeshes.SetNum(Pool);StormDriveMIDs.SetNum(Pool);}
    const auto Ensure=[&](int32 Slot)
    {
        if(StormDriveMeshes[Slot])return;
        auto* Mesh=NewObject<UDynamicMeshComponent>(Pawn);Pawn->AddInstanceComponent(Mesh);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);Mesh->SetCanEverAffectNavigation(false);
        Mesh->SetCastShadow(false);Mesh->SetReceivesDecals(false);Mesh->bVisibleInRayTracing=false;Mesh->bAffectDistanceFieldLighting=false;
        Mesh->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);Mesh->RegisterComponent();Mesh->SetMesh(Topology());
        StormDriveMeshes[Slot]=Mesh;StormDriveMIDs[Slot]=UMaterialInstanceDynamic::Create(StormDriveMaterial,this);Mesh->SetMaterial(0,StormDriveMIDs[Slot]);
    };
    StormDriveShapeRefresh-=Delta;const bool Shape=StormDriveShapeRefresh<=0.f;
    if(Shape)StormDriveShapeRefresh=1.f/30.f;
    const float Time=float(FMath::Fmod(Now,1200.));
    if(ShowSeat)
    {
        Ensure(0);auto* Mesh=StormDriveMeshes[0].Get();Mesh->SetVisibility(true);
        auto* SeatMaterial=CallSeat?Cast<UMaterialInterface>(JiLeiLightning.ResolveObject()):StormDriveMaterial.Get();
        if(SeatMaterial&&StormDriveMIDs[0]->Parent!=SeatMaterial)
        {
            StormDriveMIDs[0]=UMaterialInstanceDynamic::Create(SeatMaterial,this);
            Mesh->SetMaterial(0,StormDriveMIDs[0]);
        }
        Mesh->SetOnlyOwnerSee(Seat->bOnlyOwnerSee);Mesh->SetOwnerNoSee(Seat->bOwnerNoSee);
        Mesh->SetWorldTransform(Seat->GetComponentTransform());
        const float Charge=CallSeat?ThunderCallChargeProgress():0.f;
        const float Energy=FMath::SmoothStep(0.f,1.f,Charge);
        const float Flash=FMath::Pow(FMath::Max(0.f,FMath::Sin(Time*27.f)),8.f);
        StormDriveMIDs[0]->SetScalarParameterValue(TEXT("Strength"),CallSeat?(.35f+5.65f*Energy+2.4f*Flash*Energy*Energy):.75f);
        if(Shape)
        {
            const FBox Box=SeatAsset->GetBoundingBox();const FVector C=Box.GetCenter();FVector E=Box.GetExtent();
            if(CallSeat){E.X*=FMath::Lerp(1.15f,3.35f,Energy);E.Y*=FMath::Lerp(1.05f,1.65f,Energy);E.Z*=FMath::Lerp(.85f,1.45f,Energy);}
            Mesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Geo)
            {
                for(int32 A=0;A<Arcs;++A)
                {
                    FVector Points[Rings];const float Beat=Time*(CallSeat?8.f:6.f)+A*.29f,Seed=FMath::FloorToFloat(Beat)*3.71f+A*2.13f;
                    const float ArcGain=CallSeat?(A<2?1.f:FMath::SmoothStep(0.f,1.f,(Charge-(A-1)*.10f)/.24f)):1.f;
                    const float Pulse=CallSeat?.32f+.68f*FMath::Clamp((.78f-FMath::Frac(Beat))*8.f,0.f,1.f):FMath::Clamp((.66f-FMath::Frac(Beat))*8.f,0.f,1.f);
                    for(int32 I=0;I<Rings;++I)
                    {
                        const float U=float(I)/Steps,Angle=U*PI*1.25f+Seed*.35f;
                        const float J=.45f*FMath::Sin(I*2.31f+Seed)+.23f*FMath::Sin(I*5.17f-Seed);
                        if(CallSeat)
                        {
                            const float Wrap=U*PI*1.75f+A*PI*.5f+Time*(A%2?1.8f:-1.6f);
                            const float Jag=J*(A<4?2.8f:1.8f)*FMath::Lerp(.28f,1.15f,Energy);
                            if(A<4)
                                Points[I]=C+FVector(FMath::Cos(Wrap)*(E.X+1.6f)+Jag,
                                    FMath::Sin(Wrap)*(E.Y+1.3f)+Jag*.6f,(U-.5f)*E.Z*1.7f+Jag);
                            else if(A<6)
                                Points[I]=C+FVector((U-.5f)*E.X*2.15f+Jag,
                                    (A%2?-1.f:1.f)*(E.Y+.9f)+Jag*.6f,FMath::Sin(U*PI*2.f+Seed)*E.Z*.65f+Jag);
                            else
                                Points[I]=C+FVector(FMath::Cos(Wrap)*(3.4f+U*2.4f)+Jag,
                                    FMath::Sin(Wrap)*(3.4f+U*2.4f)+Jag*.55f,-U*(E.Z+28.f)+Jag);
                        }
                        else if(A<4)Points[I]=C+FVector(FMath::Cos(Angle)*(E.X+.6f)+J,(A%2?-1.f:1.f)*(E.Y+.5f)+J*.4f,FMath::Sin(Angle)*(E.Z*.90f)+J);
                        else Points[I]=C+FVector((U-.5f)*E.X*.75f+J,(A%2?-1.f:1.f)*(E.Y+.25f)+J*.4f,(U*2.f-1.f)*E.Z*.67f+J);
                    }
                    Tube(Geo,A,Points,(CallSeat?(A<4?.32f:.19f):(A<4?.048f:.032f))*Pulse*(CallSeat?.16f+.84f*Energy:1.f)*ArcGain);
                }
            },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
        }
    }
    else if(StormDriveMeshes[0])StormDriveMeshes[0]->SetVisibility(false);
    for(int32 Slot=1;Slot<Pool;++Slot)
    {
        const auto& Burst=StormDriveBursts[Slot-1];const float Age=float(Now-Burst.ServerAt);
        const FVector Origin=Burst.Target.IsValid()?Burst.Target->GetActorTransform().TransformPosition(Burst.LocalPoint):Burst.WorldPoint;
        if(Age<0.f||Age>=BurstSeconds||!Viewer||FVector::DistSquared(Viewer->GetCameraLocation(),Origin)>FMath::Square(4500.f))
        {if(StormDriveMeshes[Slot])StormDriveMeshes[Slot]->SetVisibility(false);continue;}
        Ensure(Slot);auto* Mesh=StormDriveMeshes[Slot].Get();Mesh->SetVisibility(true);Mesh->SetWorldLocation(Origin+Burst.Normal*2.f);
        StormDriveMIDs[Slot]->SetScalarParameterValue(TEXT("Strength"),2.2f*FMath::Pow(1.f-Age/BurstSeconds,1.4f));
        if(!Shape)continue;
        Mesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Geo)
        {
            FVector X,Y;Burst.Normal.FindBestAxisVectors(X,Y);
            const float Flicker=.7f+.3f*FMath::Abs(FMath::Sin(Age*100.f));
            for(int32 A=0;A<Arcs;++A)
            {
                FVector Points[Rings];const int32 Parent=A%4;
                const float Angle=Parent*PI*.5f+float(Burst.Seed%31)*.203f;
                const FVector Radial=X*FMath::Cos(Angle)+Y*FMath::Sin(Angle),Across=-X*FMath::Sin(Angle)+Y*FMath::Cos(Angle);
                for(int32 I=0;I<Rings;++I)
                {
                    const float U=float(I)/Steps,Length=28.f+7.f*FMath::Sin(Parent*2.f+Burst.Seed%17);
                    const float J=(FMath::Sin(I*2.37f+A*1.9f+FMath::FloorToFloat(Age*35.f))*2.f+FMath::Sin(I*5.7f+A)) * FMath::Sin(U*PI);
                    if(A<4)Points[I]=Radial*(U*Length)+Across*J+Burst.Normal*(FMath::Sin(U*PI)*5.f);
                    else Points[I]=Radial*(Length*(.43f+U*.29f))+Across*(U*11.f+J*.6f)+Burst.Normal*(3.f+U*5.f);
                }
                Tube(Geo,A,Points,(A<4?.12f:.065f)*Flicker*(1.f-Age/BurstSeconds));
            }
        },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    }
}

void UProductionToolComponent::ClearStormDriveLightning()
{
    if(StormDriveLoad)StormDriveLoad->CancelHandle();StormDriveLoad.Reset();
    for(const auto& Mesh:StormDriveMeshes)if(IsValid(Mesh))Mesh->DestroyComponent();
    StormDriveMeshes.Reset();StormDriveMIDs.Reset();StormDriveMaterial=nullptr;StormDriveSeat.Reset();
    for(auto& Burst:StormDriveBursts)Burst=FStormDriveBurst{};
}
