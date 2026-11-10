#include "EnhancementRitualEffect.h"
#include "Camera/CameraComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "StaticMeshResources.h"

namespace
{
    constexpr int32 ContourBins=48, CoreCount=ContourBins*2, HaloCount=32;
    constexpr int32 MoteCount=CoreCount+HaloCount, MaxParts=32, SamplesPerPart=96;
    constexpr float Duration=3.6f;
    const FSoftObjectPath GlowPath(TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter"));
}

AEnhancementRitualEffect::AEnhancementRitualEffect()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    SetReplicates(false);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    for(int32 I=0;I<MoteCount;++I)
    {
        auto* Sprite=CreateDefaultSubobject<UMaterialBillboardComponent>(*FString::Printf(TEXT("Mote%d"),I));
        Sprite->SetupAttachment(RootComponent);
        Sprite->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Sprite->SetGenerateOverlapEvents(false);
        Sprite->SetCastShadow(false);
        Sprite->bReceivesDecals=false;
        Sprite->SetVisibility(false);
        Sprites.Add(Sprite);
    }
}

void AEnhancementRitualEffect::BeginPlay()
{
    Super::BeginPlay();
    // Prepare on opening the workbench, not through synchronous loads in Tick/Play.
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(GlowPath,
        FStreamableDelegate::CreateUObject(this,&AEnhancementRitualEffect::PrepareMaterial));
}

void AEnhancementRitualEffect::PrepareMaterial()
{
    auto* Base=Cast<UMaterialInterface>(GlowPath.ResolveObject());
    if(!Base)return;
    Material=UMaterialInstanceDynamic::Create(Base,this);
    HaloMaterial=UMaterialInstanceDynamic::Create(Base,this);
    for(int32 I=0;I<Sprites.Num();++I)
    {
        const float Size=Motes.IsValidIndex(I)?Motes[I].Size:.65f;
        Sprites[I]->AddElement(Material,nullptr,false,Size,Size,nullptr);
    }
}

void AEnhancementRitualEffect::Play(AActor* Weapon,UCameraComponent* Camera,bool bEnchant,UStaticMeshComponent* Table)
{
    Stop();
    if(!IsValid(Weapon)||!IsValid(Camera))return;
    Source=Weapon;PendingCamera=Camera;bBlue=bEnchant;bPending=true;
    PrepareRunes(Table);
    ReadyDeadline=FPlatformTime::Seconds()+1.2;
    // The refreshed display may still be completing its asynchronous mesh setup.
    // Keep the exact request, and bound both geometry retries and material waiting.
    SetActorTickInterval(0.f);SetActorTickEnabled(true);
}

bool AEnhancementRitualEffect::PrepareContour(AActor* Weapon,UCameraComponent* Camera)
{
    Motes.Reset();
    // CPU copies are optional in cooked meshes: never force a readback or scan all vertices.
    // Only visible authored geometry contributes; no bounds-box outline fallback.
    TInlineComponentArray<UMeshComponent*> Parts(Weapon);
    TArray<FVector> Points;Points.Reserve(MaxParts*SamplesPerPart);
    int32 PartCount=0;
    for(auto* Part:Parts)
    {
        if(!Part->IsVisible()||Part->bHiddenInGame)continue;
        if(++PartCount>MaxParts)break;
        const FTransform Pose=Part->GetComponentTransform();
        if(auto* Static=Cast<UStaticMeshComponent>(Part);Static&&Static->GetStaticMesh())
        {
            const auto* Render=Static->GetStaticMesh()->GetRenderData();
            if(!Render||Render->LODResources.IsEmpty())continue;
            const auto& Vertices=Render->LODResources[0].VertexBuffers.PositionVertexBuffer;
            const uint32 Count=Vertices.GetNumVertices();
            if(!Count||!Vertices.GetVertexData())continue;
            const uint32 Samples=FMath::Min(uint32(SamplesPerPart),Count);
            for(uint32 I=0;I<Samples;++I)
                Points.Add(Pose.TransformPosition(FVector(Vertices.VertexPosition(uint32(uint64(I)*Count/Samples)))));
        }
        else if(auto* Skin=Cast<USkinnedMeshComponent>(Part))
        {
            const auto* Render=Skin->GetSkeletalMeshRenderData();
            if(!Render||Render->LODRenderData.IsEmpty())continue;
            const auto& LOD=Render->LODRenderData[0];
            const auto& Vertices=LOD.StaticVertexBuffers.PositionVertexBuffer;
            auto* Weights=Skin->GetSkinWeightBuffer(0);
            if(!Weights||!Vertices.GetVertexData()||!Weights->GetDataVertexBuffer()->GetWeightData()||Weights->GetNumVertices()!=Vertices.GetNumVertices())continue;
            TArray<FMatrix44f> Matrices;Skin->GetCurrentRefToLocalMatrices(Matrices,0);
            uint32 VisibleCount=0;
            for(const auto& Section:LOD.RenderSections)
                if(Skin->IsMaterialSectionShown(Section.MaterialIndex,0))VisibleCount+=Section.NumVertices;
            const uint32 Samples=FMath::Min(uint32(SamplesPerPart),VisibleCount);
            for(uint32 I=0;I<Samples;++I)
            {
                uint32 Index=uint32(uint64(I)*VisibleCount/Samples);
                for(const auto& Section:LOD.RenderSections)
                {
                    if(!Skin->IsMaterialSectionShown(Section.MaterialIndex,0))continue;
                    if(Index>=Section.NumVertices){Index-=Section.NumVertices;continue;}
                    Points.Add(Pose.TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(
                        Skin,Section.BaseVertexIndex+Index,LOD,*Weights,Matrices))));
                    break;
                }
            }
        }
    }
    if(Points.IsEmpty())return false;
    const FVector Eye=Camera->GetComponentLocation(),Forward=Camera->GetForwardVector();
    const FVector Right=Camera->GetRightVector(),Up=Camera->GetUpVector();
    TArray<FVector2D> Projected;Projected.Reserve(Points.Num());
    FVector2D Min(DBL_MAX,DBL_MAX),Max(-DBL_MAX,-DBL_MAX);
    for(const FVector& Point:Points)
    {
        const FVector V=Point-Eye;const double Depth=FMath::Max(1.,FVector::DotProduct(V,Forward));
        const FVector2D P(FVector::DotProduct(V,Right)/Depth,FVector::DotProduct(V,Up)/Depth);
        Projected.Add(P);Min.X=FMath::Min(Min.X,P.X);Min.Y=FMath::Min(Min.Y,P.Y);
        Max.X=FMath::Max(Max.X,P.X);Max.Y=FMath::Max(Max.Y,P.Y);
    }
    const int32 Along=(Max.X-Min.X>=Max.Y-Min.Y)?0:1,Across=1-Along;
    int32 Low[ContourBins],High[ContourBins];
    for(int32 B=0;B<ContourBins;++B){Low[B]=INDEX_NONE;High[B]=INDEX_NONE;}
    for(int32 I=0;I<Points.Num();++I)
    {
        const int32 Bin=FMath::Clamp(int32((Projected[I][Along]-Min[Along])/FMath::Max(1.e-6,Max[Along]-Min[Along])*ContourBins),0,ContourBins-1);
        if(Low[Bin]==INDEX_NONE||Projected[I][Across]<Projected[Low[Bin]][Across])Low[Bin]=I;
        if(High[Bin]==INDEX_NONE||Projected[I][Across]>Projected[High[Bin]][Across])High[Bin]=I;
    }
    FRandomStream Random(int32(GetUniqueID())^int32(FPlatformTime::Cycles()));
    const FTransform Frame=Weapon->GetActorTransform();
    for(int32 B=0;B<ContourBins;++B)for(int32 Side=0;Side<2;++Side)
    {
        const int32 Index=Side?High[B]:Low[B];if(Index==INDEX_NONE)continue;
        auto& Mote=Motes.AddDefaulted_GetRef();
        // Small camera-facing offset keeps converged motes visible on the actual contour.
        Mote.Target=Frame.InverseTransformPosition(Points[Index]-Forward*.65f);
        const float Angle=Random.FRandRange(0,2*PI);
        Mote.Offset=Right*(FMath::Cos(Angle)*Random.FRandRange(18,40))+Up*(FMath::Sin(Angle)*Random.FRandRange(14,30));
        Mote.Delay=Random.FRandRange(0,.18f);Mote.Size=Random.FRandRange(1.15f,2.15f);Mote.Phase=Angle;
    }
    // A separate soft halo layer follows the real contour, not a bounds rectangle.
    const int32 Cores=Motes.Num();
    for(int32 I=0;I<HaloCount&&Cores>0;++I)
    {
        FMote Halo=Motes[I*Cores/HaloCount];
        Halo.bHalo=true;Halo.Size=Random.FRandRange(3.2f,5.3f);
        Halo.Delay*=.5f;Motes.Add(Halo);
    }
    for(int32 I=0;I<Motes.Num();++I)if(!Sprites[I]->Elements.IsEmpty())
    {
        Sprites[I]->Elements[0].Material=Motes[I].bHalo?HaloMaterial:Material;
        Sprites[I]->Elements[0].BaseSizeX=Motes[I].Size;
        Sprites[I]->Elements[0].BaseSizeY=Motes[I].Size;
        Sprites[I]->MarkRenderStateDirty();
    }
    return !Motes.IsEmpty();
}

void AEnhancementRitualEffect::PrepareRunes(UStaticMeshComponent* Table)
{
    if(!IsValid(Table))return;
    RuneTable=Table;
    // Only the two authored rune materials have this parameter. Preserve every
    // wood/stone/metal channel, including the carved surface's actual emissive mask.
    const int32 Count=FMath::Min(Table->GetNumMaterials(),32);
    for(int32 Slot=0;Slot<Count;++Slot)
    {
        auto* Original=Table->GetMaterial(Slot);float DefaultPulse=0;
        if(!Original||!Original->GetScalarParameterValue(FMaterialParameterInfo(TEXT("ArcanePulse")),DefaultPulse))continue;
        auto* Dynamic=UMaterialInstanceDynamic::Create(Original,this);
        if(!Dynamic)continue;
        Dynamic->SetVectorParameterValue(TEXT("ArcanePulseColor"),bBlue?FLinearColor(.035f,.32f,1.f):FLinearColor(1.f,.52f,.025f));
        Dynamic->SetScalarParameterValue(TEXT("ArcanePulse"),0.f);
        RuneSlots.Add(Slot);OriginalRuneMaterials.Add(Original);RuneMaterials.Add(Dynamic);
        Table->SetMaterial(Slot,Dynamic);
    }
}

void AEnhancementRitualEffect::UpdateRunes(float DeltaSeconds)
{
    RuneAge+=DeltaSeconds;
    const float Attack=FMath::SmoothStep(0.f,.28f,RuneAge);
    const float Fade=1.f-FMath::SmoothStep(2.25f,Duration,RuneAge);
    const float Seal=FMath::Exp(-FMath::Square((RuneAge-.95f)/.22f));
    const float Pulse=Attack*Fade*(.62f+.38f*Seal);
    for(const auto& Rune:RuneMaterials)if(Rune)Rune->SetScalarParameterValue(TEXT("ArcanePulse"),Pulse);
}

void AEnhancementRitualEffect::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!Source.IsValid()||Source->IsActorBeingDestroyed()){Stop();return;}
    UpdateRunes(DeltaSeconds);
    if(bPending)
    {
        const double Now=FPlatformTime::Seconds();
        if(!PendingCamera.IsValid()||Now>=ReadyDeadline||PrepareAttempts>=8)
        {
            // Missing CPU mesh data must not suppress the successful tabletop pulse.
            bPending=false;PendingCamera.Reset();
        }
        else if(Material&&Now>=NextPrepareTime)
        {
            ++PrepareAttempts;NextPrepareTime=Now+.15;
            if(PrepareContour(Source.Get(),PendingCamera.Get()))
            {bPending=false;PendingCamera.Reset();Age=0;}
        }
        if(bPending)return;
    }
    if(Motes.IsEmpty()||!Material)
    {if(RuneAge>=Duration)Stop();return;}
    Age+=DeltaSeconds;
    if(Age>=Duration){Stop();return;}
    const FLinearColor Color=bBlue?FLinearColor(.045f,.3f,1.f):FLinearColor(1.f,.55f,.025f);
    const float Envelope=FMath::SmoothStep(0.f,.16f,Age)*(1.f-FMath::SmoothStep(2.6f,Duration,Age));
    const float Impact=FMath::Exp(-FMath::Square((Age-.9f)/.18f));
    Material->SetVectorParameterValue(TEXT("LootColor"),Color);
    Material->SetScalarParameterValue(TEXT("Intensity"),(12.f+14.f*Impact)*Envelope);
    HaloMaterial->SetVectorParameterValue(TEXT("LootColor"),Color);
    HaloMaterial->SetScalarParameterValue(TEXT("Intensity"),(2.8f+4.2f*Impact)*Envelope);
    const FTransform Frame=Source->GetActorTransform();
    for(int32 I=0;I<Motes.Num();++I)
    {
        const auto& Mote=Motes[I];const float Time=Age-Mote.Delay;
        auto* Sprite=Sprites[I].Get();Sprite->SetVisibility(Time>=0);if(Time<0)continue;
        FVector Position=Frame.TransformPosition(Mote.Target);
        if(Time<.85f)
        {
            const float Remaining=1.f-Time/.85f;
            Position+=Mote.Offset*(Remaining*Remaining);
        }
        else if(Time>1.45f&&!Mote.bHalo&&I%3!=0)
        {
            const float Rise=Time-1.45f;
            Position+=FVector(FMath::Sin(Mote.Phase+Rise*3)*Rise*3,FMath::Cos(Mote.Phase+Rise*3)*Rise*3,Rise*(18.f+7.f*FMath::Sin(Mote.Phase)));
        }
        // Keep one third of the sparks and all soft halos on the weapon while
        // staggered embers lift off. Each sprite has a smooth, distinct shimmer.
        const float Shimmer=.88f+.12f*FMath::Sin(Time*5.f+Mote.Phase);
        Sprite->SetWorldScale3D(FVector(Shimmer*(1.f+.25f*Impact)));
        Sprite->SetWorldLocation(Position);
    }
}

void AEnhancementRitualEffect::Stop()
{
    SetActorTickEnabled(false);
    if(RuneTable.IsValid())for(int32 I=0;I<RuneSlots.Num();++I)
    {
        // Do not overwrite a material installed by another owner while we played.
        if(RuneTable->GetMaterial(RuneSlots[I])==RuneMaterials[I])
            RuneTable->SetMaterial(RuneSlots[I],OriginalRuneMaterials[I]);
    }
    RuneTable.Reset();RuneSlots.Reset();RuneMaterials.Reset();OriginalRuneMaterials.Reset();
    Source.Reset();PendingCamera.Reset();Motes.Reset();Age=0;RuneAge=0;NextPrepareTime=0;
    bPending=false;PrepareAttempts=0;ReadyDeadline=0;
    for(const auto& Sprite:Sprites)Sprite->SetVisibility(false);
}

void AEnhancementRitualEffect::EndPlay(const EEndPlayReason::Type Reason)
{
    Stop();if(MaterialLoad)MaterialLoad->CancelHandle();MaterialLoad.Reset();
    Super::EndPlay(Reason);
}
