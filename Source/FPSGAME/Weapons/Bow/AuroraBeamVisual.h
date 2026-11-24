#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AuroraBeamVisual.generated.h"

class UInstancedStaticMeshComponent;
struct FStreamableHandle;

namespace AuroraBeamVisual
{
    inline constexpr const TCHAR* MaterialPath=TEXT("/Game/Weapons/FrontierCompoundBow/AuroraLaserR4/M_AuroraLaser.M_AuroraLaser");
    inline constexpr const TCHAR* Cylinder=TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
    inline constexpr const TCHAR* Sphere=TEXT("/Engine/BasicShapes/Sphere.Sphere");
    double Clock(const UWorld* World);
}

USTRUCT()
struct FAuroraBeamContact
{
    GENERATED_BODY()
    UPROPERTY() double At=-1.;
    UPROPERTY() FVector_NetQuantize10 Point=FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Normal=FVector::UpVector;
};

// A local effect can outlive the projectile or collectible. Arrow rain shares one
// pair of instance batches for its guiding pulse, descending beams and motes.
UCLASS(Transient,NotBlueprintable)
class AAuroraBeamVisual : public AActor
{
    GENERATED_BODY()
public:
    AAuroraBeamVisual();
    static AAuroraBeamVisual* Open(AActor* Source,const FVector& Origin);
    void Trace(int32 Lane,const FVector& Origin,double Started,const FVector& Tip,double At,float Scale=1.f);
    void Finish(int32 Lane,const FVector& Origin,double Started,const FAuroraBeamContact& Contact,float Scale=1.f);
    void Burst(const FAuroraBeamContact& Contact,float Scale=1.f);
    void Release();
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    struct FKnot { FVector Point; double At; };
    struct FStroke
    {
        TArray<FKnot> Knots;
        FKnot Tip{};
        double ToNextMote=0.;
        float Scale=1.f;
        bool bClosed=false;
    };
    struct FMote { FVector Origin,Velocity; double Born; float Life,Size; };
    struct FBatch
    {
        TArray<FTransform> Transforms;
        TArray<float> Values;
        int32 Visible=0;
        void Put(const FTransform& Transform,const FVector2f& Tail,const FVector2f& Tip);
        void Flush(UInstancedStaticMeshComponent* Mesh);
    };
    void PrepareMeshes();
    void AddMote(const FVector& Point,const FVector& Direction,double At,float Scale,bool bImpact);
    void DrawSegment(const FKnot& A,const FKnot& B,double Now,float Scale);
    TMap<int32,FStroke> Strokes;
    TArray<FMote> Motes;
    FBatch Lines,Points;
    FRandomStream Random;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Beams;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Sparks;
    TSharedPtr<FStreamableHandle> Load;
    bool bReleased=false;
};
