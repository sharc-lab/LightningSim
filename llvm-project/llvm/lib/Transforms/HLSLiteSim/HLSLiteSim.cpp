#include "llvm/Pass.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/Analysis/ScalarEvolution.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Value.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Dominators.h"
#include "llvm/Transforms/Utils.h"



using namespace llvm;
using namespace std;

namespace {

    struct FixedLoopAnalysisPass : public LoopPass {
        static char ID;
        FunctionCallee fputs_func;

        FixedLoopAnalysisPass() : LoopPass(ID) {}
        
        bool doInitialization(Loop *L, LPPassManager &LPM) override {
            Module* M = L->getHeader()->getParent()->getParent();
            fputs_func = M->getOrInsertFunction(
                "__hlslitesim_fputs",
                FunctionType::get(
                    Type::getVoidTy(M->getContext()),
                    {Type::getInt8PtrTy(M->getContext())},
                    false
                )
            );
            return true;
        }

        bool runOnLoop(Loop *L, LPPassManager &LPM) override {
            bool modified = false;
            if(!isSingleSuccessorLoop(L)){ return modified; }

            if(int tc = getTCFromMD(L)){
                if(BasicBlock* PH = L->getLoopPreheader()){
                    IRBuilder<> builder(PH, PH->getFirstInsertionPt());
                    //move insert point after fputs for preheader trace_bb
                    Instruction *InsertPoint = PH->getTerminator();
                    builder.SetInsertPoint(InsertPoint);
                    //loop start
                    SmallVector<char> trace_line_buf;
                    StringRef trace_line_str = ("loop\t" + L->getName() + "\t" + Twine(tc) + "\n").toStringRef(trace_line_buf);
                    Value* trace_line = builder.CreateGlobalStringPtr(trace_line_str);
                    builder.CreateCall(fputs_func, {trace_line});
                    modified = true;
                    //add each block in the loop to the loop
                    for (BasicBlock *BB : L->blocks()) {
                        //get block number and log it in the preheader
                        int bb_id = getBlockNumMD(BB);
                        SmallVector<char> trace_line_buf_2;
                        StringRef trace_line_str_bb = ("loop_bb\t" +  BB->getParent()->getName() + "\t" + Twine(bb_id) + "\n").toStringRef(trace_line_buf_2);
                        Value* trace_line_bb = builder.CreateGlobalStringPtr(trace_line_str_bb);
                        InsertPoint = builder.CreateCall(fputs_func, {trace_line_bb});
                        InsertPoint = InsertPoint->getNextNode(); 
                        builder.SetInsertPoint(InsertPoint);

                        //remove the hlslitesim_fputs call
                        Instruction *FirstInst = &*(BB->getFirstNonPHIOrDbg());
                        FirstInst->eraseFromParent();
                    }
                    
                    SmallVector<char> trace_line_buf_3;
                    StringRef trace_line_str_endloopblocks = ("end_loop_blocks\t" + L->getName() + "\t" + Twine(tc) + "\n").toStringRef(trace_line_buf_3);
                    Value* trace_line_endloopblocks = builder.CreateGlobalStringPtr(trace_line_str_endloopblocks);
                    builder.CreateCall(fputs_func, {trace_line_endloopblocks});

                    if(BasicBlock* EB = L->getExitBlock()){
                        IRBuilder<> EB_builder(EB, EB->getFirstInsertionPt());
                        SmallVector<char> trace_line_buf_4;
                        StringRef trace_line_str_endloop = ("end_loop\t" + L->getName() + "\t" + Twine(tc) + "\n").toStringRef(trace_line_buf_4);
                        Value* trace_line_endloop = builder.CreateGlobalStringPtr(trace_line_str_endloop);
                        EB_builder.CreateCall(fputs_func, {trace_line_endloop});
                    }
                }
            }
            if(modified)
                return true;
            return false;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Fixed Loop Iteration Trace Pass";
        }

    private:
        bool isTraceable(Function &F) {
            if (F.isDeclaration()) {
                return false;
            }
            if (F.getName().startswith("_ssdm_op_")) {
                return false;
            }
            return true;
        }
        bool isSingleSuccessorLoop(Loop* L) {
            return L->getNumBackEdges() == 1 && L->getNumBlocks() == 2;
        }
        int getTCFromMD(Loop* L){
            MDNode *LoopID = L->getLoopID();
            if (!LoopID) return 0; 

            for (auto OpIt = LoopID->op_end(); OpIt != LoopID->op_begin();) {  //reverse search since its most likely the last operand
                --OpIt;
                MDNode *Operand = dyn_cast<MDNode>(*OpIt);
                if (Operand && Operand->getNumOperands() == 2) {
                    if (MDString *Key = dyn_cast<MDString>(Operand->getOperand(0))) {
                        if (Key->getString() == "ssdm_op_tripcount") {
                            if (ConstantAsMetadata *ValueMD = dyn_cast<ConstantAsMetadata>(Operand->getOperand(1))) {
                                if (ConstantInt *Value = dyn_cast<ConstantInt>(ValueMD->getValue())) {
                                    return Value->getSExtValue();
                                }
                            }
                        }
                    }
                }
            }

            return 0; 
        }
        int getBlockNumMD(BasicBlock* BB){
            Metadata *MD = BB->front().getMetadata("bb_id");
            if(!MD){ return 0; }
            MDNode *MD_Node = dyn_cast<MDNode>(MD);
            if (MD_Node && MD_Node->getOperand(1)) {
                if(ConstantAsMetadata *CAM = dyn_cast<ConstantAsMetadata>(MD_Node->getOperand(1))){
                    if(ConstantInt* val = dyn_cast<ConstantInt>(CAM->getValue())){
                        return val->getSExtValue();
                    }
                }
            }
            return 0; // Default value if metadata not found or not an integer
        }


};

    struct BBTracePass : public FunctionPass {
        static char ID;
        FunctionCallee fputs_func;

        BBTracePass() : FunctionPass(ID) {}

        bool doInitialization(Module &M) override {
            fputs_func = M.getOrInsertFunction(
                "__hlslitesim_fputs",
                FunctionType::get(
                    Type::getVoidTy(M.getContext()),
                    {Type::getInt8PtrTy(M.getContext())},
                    false
                )
            );
            return true;
        }

        bool runOnFunction(Function &F) override {
            if (!isTraceable(F)) {
                return false;
            }
            llvm::DominatorTree* DT = new llvm::DominatorTree();         
            DT->recalculate(F);
            //generate the LoopInfoBase for the current function
            llvm::LoopInfoBase<llvm::BasicBlock, llvm::Loop>* KLoop = new llvm::LoopInfoBase<llvm::BasicBlock, llvm::Loop>();
            KLoop->releaseMemory();
            KLoop->analyze(*DT); 

            StringRef func_name = F.getName();
            uint32_t bb_id = 0;

            for (BasicBlock& BB : F) {
                SmallVector<char> trace_line_buf;
                StringRef trace_line_str = ("trace_bb\t" + func_name + "\t" + Twine(bb_id) + "\n").toStringRef(trace_line_buf);
                IRBuilder<> builder(&BB, BB.getFirstInsertionPt());
                Value* trace_line = builder.CreateGlobalStringPtr(trace_line_str);
                builder.CreateCall(fputs_func, {trace_line});

                //Insert the block number as metadata on the fputs call at key bb_id
                Instruction *InsertPt = &BB.front();
                LLVMContext &Context = BB.getContext();

                //Create metadata nodes
                MDString *KeyString = MDString::get(Context, "bb_id");
                ConstantAsMetadata *ValueMetadata = ConstantAsMetadata::get(ConstantInt::get(Type::getInt32Ty(Context), bb_id));
                Metadata *MDNodeOps[] = {KeyString, ValueMetadata};
                MDNode *MetadataNode = MDNode::get(Context, MDNodeOps);

                // Add metadata to the basic block
                InsertPt->setMetadata("bb_id", MetadataNode);
                
                //if this basic block is in a loop, check if the loop has a constant trip count and set the metadata accordingly
                Loop *L = KLoop->getLoopFor(&BB);
                if(L){
                    if(!LoopMDSsdmOpTripCountExists(L)){
                        for (Instruction &I : BB) {
                            if (CallInst *CI = dyn_cast<CallInst>(&I)) {
                                Function *CalledFunction = CI->getCalledFunction();
                                if (CalledFunction && CalledFunction->getName().equals("_ssdm_op_SpecLoopTripCount")) {
                                    int64_t constTC;
                                    if (areAllTCArgsSame(CI, constTC)) {
                                        uint64_t userProvidedTC = getTCFromLoopMD(L);
                                        //add the tripcount to the loop metadata
                                        if(constTC != userProvidedTC){
                                            //we found a constant trip count that meets our goals. add metadata to the loop
                                            setMDCorrectTC(L, constTC);
                                            break; //there wont be 2 ssdm_op_tripcount functions in one basic block
                                        }else{
                                            setMDCorrectTC(L, 0); //trip count we got is the user provided one, assume we dont know trip count and set as 0
                                            break;
                                        }
                                    }else{
                                        setMDCorrectTC(L, 0); //trip count we got is not constant, set as 0
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                bb_id++;
            }

            return true;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Basic Block Trace Pass";
        }

    private:
        bool isTraceable(Function &F) {
            if (F.isDeclaration()) {
                return false;
            }
            if (F.getName().startswith("_ssdm_op_")) {
                return false;
            }
            return true;
        }
        bool areAllTCArgsSame(CallInst *CI, int64_t& value) {
            unsigned numArgs = CI->getNumOperands();

            if (numArgs < 4) // Assuming the first 3 operands are the inputs
                return false;

            Value* firstArg = CI->getOperand(0);
            Value* secondArg = CI->getOperand(1);
            Value* thirdArg = CI->getOperand(2);

            ConstantInt* firstArgConst = dyn_cast<ConstantInt>(firstArg);
            ConstantInt* secondArgConst = dyn_cast<ConstantInt>(secondArg);
            ConstantInt* thirdArgConst = dyn_cast<ConstantInt>(thirdArg);

            if (!firstArgConst || !secondArgConst || !thirdArgConst)
                return false;

            int64_t firstValue = firstArgConst->getSExtValue();
            if (firstValue != secondArgConst->getSExtValue() || firstValue != thirdArgConst->getSExtValue())
                return false;

            value = firstValue;
            return true;
        }

        uint64_t getTCFromLoopMD(Loop* L){
            MDNode *LoopID = L->getLoopID();
            if (!LoopID || LoopID->getNumOperands() < 1) {
                return false;
            }
            for (unsigned i = 1, e = LoopID->getNumOperands(); i < e; ++i) {
                Metadata *operand = LoopID->getOperand(i);
                MDNode *MD = dyn_cast<MDNode>(operand);
                if (MD && MD->getNumOperands() >= 4) {
                    MDString *MD_2 = dyn_cast<MDString>(MD->getOperand(0).get());
                    if(MD_2 && MD_2->getString().equals("llvm.loop.tripcount\n")){
                        ConstantAsMetadata *MD_3 = dyn_cast<ConstantAsMetadata>(MD->getOperand(1).get());
                        ConstantAsMetadata *MD_4 = dyn_cast<ConstantAsMetadata>(MD->getOperand(2).get());
                        ConstantAsMetadata *MD_5 = dyn_cast<ConstantAsMetadata>(MD->getOperand(3).get());
                        if(MD_3 && MD_4 && MD_5 && MD_3 == MD_4 && MD_3 == MD_5){
                            ConstantInt *tripCnt = dyn_cast<ConstantInt>(MD_3->getValue());    
                            if(tripCnt){
                                return *tripCnt->getValue().getRawData();
                            }
                        }
                    }
                }
            }
            return 0;
        }

        bool LoopMDSsdmOpTripCountExists(Loop* L){
            MDNode *LoopID = L->getLoopID();
            if (!LoopID || LoopID->getNumOperands() < 1) {
                return false;
            }
            auto OperandEnd = LoopID->op_end();
            auto OperandBegin = LoopID->op_begin(); 

            for (auto OpIt = OperandEnd; OpIt != OperandBegin;) {  //reverse search since its most likely the last operand
                --OpIt;
                MDNode *MD = dyn_cast<MDNode>(*OpIt);
                if (MD && MD->getNumOperands() >= 4) {
                    MDString *MD_2 = dyn_cast<MDString>(MD->getOperand(0).get());
                    if(MD_2 && MD_2->getString().equals("ssdm_op_tripcount")){
                        return true;
                    }
                    
                }
            }
            return false;
        }

        bool setMDCorrectTC(Loop *L, int constTC) {
            MDNode* LoopID = L->getLoopID();
            if (!LoopID) return false; // Handle if LoopID doesn't exist

            TempMDTuple Temp = MDNode::getTemporary(LoopID->getContext(), None);
            SmallVector<Metadata*> Args({ Temp.get() });
            for (unsigned i = 1, e = LoopID->getNumOperands(); i < e; ++i) {
                Metadata *operand = LoopID->getOperand(i);
                Args.push_back(operand);
            }

            // Create metadata nodes
            MDString *KeyString = MDString::get(LoopID->getContext(), "ssdm_op_tripcount");
            ConstantAsMetadata *ValueMetadata = ConstantAsMetadata::get(ConstantInt::get(Type::getInt32Ty(LoopID->getContext()), constTC));
            Metadata *MDNodeOps[] = {KeyString, ValueMetadata};
            MDNode *MetadataNode = MDNode::get(LoopID->getContext(), MDNodeOps);
            Args.push_back(MetadataNode);

            LoopID = MDNode::get(LoopID->getContext(), Args);
            LoopID->replaceOperandWith(0, LoopID);
            L->setLoopID(LoopID);
            return true;
        }
    };

    struct FixLoopMDPass : public LoopPass {
        static char ID;

        FixLoopMDPass() : LoopPass(ID) {}

        bool runOnLoop(Loop *L, LPPassManager &LPM) override {
            MDNode *LoopID = L->getLoopID();
            if (!LoopID || LoopID->getNumOperands() < 1) {
                return false;
            }

            bool modified = false;
            TempMDTuple Temp = MDNode::getTemporary(LoopID->getContext(), None);
            SmallVector<Metadata*> Args({ Temp.get() });
            for (unsigned i = 1, e = LoopID->getNumOperands(); i < e; ++i) {
                Metadata *operand = LoopID->getOperand(i);
                MDNode *MD = dyn_cast<MDNode>(operand);
                if (!MD || MD->getNumOperands() >= 1) {
                    Args.push_back(operand);
                } else {
                    modified = true;
                }
            }
            if (!modified) {
                return false;
            }

            LoopID = MDNode::get(LoopID->getContext(), Args);
            LoopID->replaceOperandWith(0, LoopID);
            L->setLoopID(LoopID);
            return true;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Fix Loop Metadata Pass";
        }
    };

    struct HLSLiteSimPassManager : public ModulePass {
        static char ID;

        HLSLiteSimPassManager() : ModulePass(ID) {}

        bool runOnModule(Module &M) override {
            legacy::PassManager PM;
            PM.add(new BBTracePass());
            PM.add(new FixLoopMDPass());
            PM.add(new FixedLoopAnalysisPass());
            return PM.run(M);
        }
    };
}

char BBTracePass::ID = 0;
char FixLoopMDPass::ID = 0;
char FixedLoopAnalysisPass::ID = 0;
char HLSLiteSimPassManager::ID = 0;
static RegisterPass<HLSLiteSimPassManager> X("hlslitesim", "HLSLiteSim Pass");