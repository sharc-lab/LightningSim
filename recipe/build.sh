# Build LightningSim LLVM fork
mkdir -p "$PREFIX/share/lightningsim/llvm"
mkdir llvm-project/llvm/build
cmake -S llvm-project/llvm -B llvm-project/llvm/build \
    -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX/share/lightningsim/llvm" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DLLVM_EXTERNAL_CLANG_SOURCE_DIR=llvm-project/clang \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_ENABLE_PROJECTS=clang \
    -DLLVM_INSTALL_TOOLCHAIN_ONLY=ON \
    -DLLVM_TOOLCHAIN_TOOLS='llvm-link;opt' \
    -DLLVM_BUILD_LLVM_DYLIB=ON \
    -DLLVM_LINK_LLVM_DYLIB=ON \
    -DCMAKE_BUILD_TYPE=Release
cmake --build llvm-project/llvm/build
cmake --install llvm-project/llvm/build --strip

# Build SystemC
mkdir -p "$PREFIX/share/lightningsim/systemc"
curl -fsSL 'https://www.accellera.org/images/downloads/standards/systemc/systemc-2.3.1a.tar.gz' | tar -xzf -
(cd systemc-2.3.1a && ./configure --prefix="$PREFIX/share/lightningsim/systemc" && make && make install)

# Build LightningSim templates
mkdir -p "$PREFIX/share/lightningsim/templates"
make DESTDIR="$PREFIX/share/lightningsim/templates"

# Build LightningSim frontend
npm ci --prefix=frontend
npm run --prefix=frontend build -- --outDir="$PREFIX/share/lightningsim/public" --emptyOutDir

# Install LightningSim
"$PYTHON" -m pip install --no-deps --ignore-installed ./backend
