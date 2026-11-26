#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "VillageOilSurveySubsystem.generated.h"

class AVillageOilField;

/** Authoritative terrain queue; independent of the local rendering subsystem on a dedicated server. */
UCLASS()
class UVillageOilSurveySubsystem final : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    void Add(AVillageOilField* Field);
    void Remove(AVillageOilField* Field);
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override {return !Fields.IsEmpty();}
    virtual TStatId GetStatId() const override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    TArray<TWeakObjectPtr<AVillageOilField>> Fields;
    int32 Cursor=0;
};
