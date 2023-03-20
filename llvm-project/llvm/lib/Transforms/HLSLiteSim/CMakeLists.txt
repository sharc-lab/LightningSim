if(WIN32 OR CYGWIN)
  set(LLVM_LINK_COMPONENTS Core Support)
endif()

add_llvm_library(LLVMHLSLiteSim MODULE INSTALL_WITH_TOOLCHAIN
  HLSLiteSim.cpp

  DEPENDS
  intrinsics_gen
  PLUGIN_TOOL
  opt
  )
