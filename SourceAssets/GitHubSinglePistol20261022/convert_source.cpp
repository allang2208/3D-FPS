#include <fbxsdk.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>
static void Describe(FbxNode* node,int depth=0)
{
    auto* attr=node->GetNodeAttribute();
    if(attr)std::cout<<std::string(depth,' ')<<node->GetName()<<" type="<<int(attr->GetAttributeType())<<"\n";
    if(auto* mesh=node->GetMesh())std::cout<<"MESH vertices="<<mesh->GetControlPointsCount()<<" polygons="<<mesh->GetPolygonCount()<<" skins="<<mesh->GetDeformerCount(FbxDeformer::eSkin)<<"\n";
    for(int i=0;i<node->GetChildCount();++i)Describe(node->GetChild(i),depth+1);
}
int main(int argc,char** argv)
{
    if(argc!=3)return 2;
    auto* manager=FbxManager::Create();manager->SetIOSettings(FbxIOSettings::Create(manager,IOSROOT));
    auto* scene=FbxScene::Create(manager,"GitHubSinglePistol");
    auto* importer=FbxImporter::Create(manager,"");
    if(!importer->Initialize(argv[1],-1,manager->GetIOSettings())||!importer->Import(scene))
    {std::cerr<<importer->GetStatus().GetErrorString()<<"\n";manager->Destroy();return 3;}
    importer->Destroy();
    // Legacy takes contain an independent weapon bone beside the character.
    // An identity parent gives UE a single skeleton root without altering any
    // original local transform, skin bind matrix or animation channel.
    auto* unified=FbxNode::Create(scene,"GitHubRoot");
    auto* rootAttr=FbxSkeleton::Create(scene,"GitHubRoot");rootAttr->SetSkeletonType(FbxSkeleton::eRoot);
    unified->SetNodeAttribute(rootAttr);
    auto* root=scene->GetRootNode();
    for(int i=root->GetChildCount()-1;i>=0;--i)
    {auto* child=root->GetChild(i);if(child->GetSkeleton()){root->RemoveChild(child);unified->AddChild(child);}}
    root->AddChild(unified);
    // These animation-only FBX takes contain weighted points but zero faces.
    // UE requires a mesh to host the donor skeleton. Add an authoring proxy
    // with one tiny rigid triangle per bone, preserving every original track.
    std::vector<FbxNode*> bones;
    for(int i=0;i<scene->GetNodeCount();++i)if(scene->GetNode(i)->GetSkeleton())bones.push_back(scene->GetNode(i));
    for(int i=scene->GetNodeCount()-1;i>=0;--i)
    {auto* n=scene->GetNode(i);if(n->GetMesh()&&n->GetMesh()->GetPolygonCount()==0)n->Destroy();}
    for(int i=scene->GetPoseCount()-1;i>=0;--i){auto* pose=scene->GetPose(i);scene->RemovePose(i);pose->Destroy();}
    auto* proxyNode=FbxNode::Create(scene,"DonorSkeletonProxy");root->AddChild(proxyNode);
    auto* proxy=FbxMesh::Create(scene,"DonorSkeletonProxy");proxyNode->SetNodeAttribute(proxy);
    proxy->InitControlPoints(int(bones.size()*3));
    auto* skin=FbxSkin::Create(scene,"ProxySkin");proxy->AddDeformer(skin);
    auto* bind=FbxPose::Create(scene,"DonorBind");bind->SetIsBindPose(true);
    FbxAMatrix identity;identity.SetIdentity();bind->Add(proxyNode,identity);
    for(size_t i=0;i<bones.size();++i)
    {
        auto matrix=bones[i]->EvaluateGlobalTransform(FBXSDK_TIME_INFINITE);auto point=matrix.GetT();
        proxy->GetControlPoints()[i*3]=point;
        proxy->GetControlPoints()[i*3+1]=point+FbxVector4(.2,0,0,0);
        proxy->GetControlPoints()[i*3+2]=point+FbxVector4(0,.2,0,0);
        proxy->BeginPolygon();for(int j=0;j<3;++j)proxy->AddPolygon(int(i*3+j));proxy->EndPolygon();
        auto* cluster=FbxCluster::Create(scene,bones[i]->GetName());cluster->SetLink(bones[i]);cluster->SetLinkMode(FbxCluster::eNormalize);
        cluster->SetTransformMatrix(identity);cluster->SetTransformLinkMatrix(matrix);
        for(int j=0;j<3;++j)cluster->AddControlPointIndex(int(i*3+j),1.);
        skin->AddCluster(cluster);bind->Add(bones[i],matrix);
    }
    scene->AddPose(bind);proxy->GenerateNormals(true);
    std::cout<<"SOURCE "<<argv[1]<<" stacks="<<scene->GetSrcObjectCount<FbxAnimStack>()<<"\n";
    Describe(scene->GetRootNode());
    for(int i=0;i<scene->GetSrcObjectCount<FbxAnimStack>();++i)
    {
        auto* stack=scene->GetSrcObject<FbxAnimStack>(i);auto span=stack->GetLocalTimeSpan();
        std::cout<<"TAKE "<<stack->GetName()<<" seconds="<<span.GetStart().GetSecondDouble()<<","<<span.GetStop().GetSecondDouble()<<"\n";
    }
    auto* exporter=FbxExporter::Create(manager,"");
    if(!exporter->Initialize(argv[2],-1,manager->GetIOSettings())||!exporter->SetFileExportVersion(FBX_2014_00_COMPATIBLE)||!exporter->Export(scene))
    {std::cerr<<exporter->GetStatus().GetErrorString()<<"\n";manager->Destroy();return 4;}
    exporter->Destroy();manager->Destroy();return 0;
}
