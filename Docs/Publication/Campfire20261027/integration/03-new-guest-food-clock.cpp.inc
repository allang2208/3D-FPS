        auto FoodMigrated=Guest;
        ColdSteelFood::RebaseProfile(FoodMigrated,ColdSteelFood::Clock(this));
        ShadowModel = HostModel->CreateShadowModel(FoodMigrated);
