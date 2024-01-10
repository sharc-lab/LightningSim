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
#include "llvm/Transforms/Utils/LoopUtils.h"

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

            if(int tc = getConstantTripCount(L)){
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
                        Instruction *FirstInst = BB->getFirstNonPHIOrDbg();
                        if (!FirstInst) { continue; }

                        //get block number and log it in the preheader
                        int bb_id = getBlockNumMD(FirstInst);
                        SmallVector<char> trace_line_buf_2;
                        StringRef trace_line_str_bb = ("loop_bb\t" +  BB->getParent()->getName() + "\t" + Twine(bb_id) + "\n").toStringRef(trace_line_buf_2);
                        Value* trace_line_bb = builder.CreateGlobalStringPtr(trace_line_str_bb);
                        InsertPoint = builder.CreateCall(fputs_func, {trace_line_bb});
                        InsertPoint = InsertPoint->getNextNode(); 
                        builder.SetInsertPoint(InsertPoint);

                        //remove the hlslitesim_fputs call
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
            return modified;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Fixed Loop Iteration Trace Pass";
        }

        void getAnalysisUsage(AnalysisUsage &AU) const override {
            getLoopAnalysisUsage(AU);
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

        int getBlockNumMD(Instruction* Inst){
            Metadata *MD = Inst->getMetadata("bb_id");
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

        unsigned int getConstantTripCount(Loop* L) {
            ScalarEvolution &SE = getAnalysis<ScalarEvolutionWrapperPass>().getSE();
            BasicBlock *ExitingBlock = L->getExitingBlock();
            if (!ExitingBlock) {
                return 0;
            }
            unsigned TripCount = SE.getSmallConstantTripCount(L, ExitingBlock);
            if (!TripCount) {
                return 0;
            }
            return TripCount - 1;
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

            LLVMContext &Context = F.getContext();
            MDString *MDKeyStr = MDString::get(Context, "bb_id");

            StringRef func_name = F.getName();
            uint32_t bb_id = 0;

            for (BasicBlock& BB : F) {
                SmallVector<char> trace_line_buf;
                StringRef trace_line_str = ("trace_bb\t" + func_name + "\t" + Twine(bb_id) + "\n").toStringRef(trace_line_buf);
                IRBuilder<> builder(&BB, BB.getFirstInsertionPt());
                Value* trace_line = builder.CreateGlobalStringPtr(trace_line_str);
                CallInst *fputs_call = builder.CreateCall(fputs_func, {trace_line});

                // Insert the block number as metadata on the fputs call at key bb_id
                // Create metadata nodes
                ConstantAsMetadata *ValueMetadata = ConstantAsMetadata::get(ConstantInt::get(Type::getInt32Ty(Context), bb_id));
                Metadata *MDNodeOps[] = {MDKeyStr, ValueMetadata};
                MDNode *MetadataNode = MDNode::get(Context, MDNodeOps);
                // Add metadata to the basic block
                fputs_call->setMetadata("bb_id", MetadataNode);

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
            PM.add(createPromoteMemoryToRegisterPass());
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