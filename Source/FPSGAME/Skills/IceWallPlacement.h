#pragma once
#include "CoreMinimal.h"
#include "IceWallTypes.h"

class UWorld;
class AActor;
class UNiagaraComponent;
struct FCollisionQueryParams;
struct FHitResult;

/** Bounded local queries shared by placement, collision, impact and the slope FX. */
namespace IceWallPlacement
{
    bool TraceWithoutCreatures(UWorld* World,const FVector& Start,const FVector& End,
        const FCollisionQueryParams& Query,FHitResult& Hit);
    bool Build(UWorld* World,FIceWallPlacement& Plan,const FIceWallCast& Cast,FString& Reason);
    bool Validate(UWorld* World,const FIceWallPlacement& Plan,const FIceWallCast& Cast,FString& Reason);
    float GroundAt(const FIceWallPlacement& Plan,float Across,float Along);
    TSet<AActor*> Monsters(UWorld* World,const FIceWallPlacement& Plan,const FIceWallCast& Cast,float Margin=0);
    bool Occupies(const AActor* Actor,const FIceWallPlacement& Plan,const FIceWallCast& Cast);
    bool Displace(UWorld* World,AActor* Target,AActor* Wall,const FIceWallPlacement& Plan,
        const FIceWallCast& Cast,const TSet<AActor*>& Occupants,TArray<FVector4>& Reserved);
    void SetEffectProfile(UNiagaraComponent* Effect,const FIceWallPlacement& Plan);
}
