# Contributing to LightningSim

Thank you for your interest in contributing to LightningSim! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [Building from Source](#building-from-source)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Operating System**: 64-bit x86 Linux system (tested on RHEL Server 7.9, but most modern Linux distributions should work)
- **Conda**: Required for managing dependencies ([Installation guide](https://docs.conda.io/projects/conda/en/stable/user-guide/install/linux.html))
- **AMD/Xilinx Vitis HLS**: Part of the [Vitis Unified Software Platform](https://www.xilinx.com/products/design-tools/vitis/vitis-platform.html)
  - Version 2021.1 recommended (other recent versions should work)
  - [Set up the environment](https://docs.xilinx.com/r/en-US/ug1399-vitis-hls/Setting-Up-the-Environment?tocId=5N~0A2HNuVzvrGYgw0ja_A) as described in the Vitis HLS documentation
- **Git**: For version control

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sharc-lab/LightningSim.git
cd LightningSim
```

### 2. Create a Conda Environment

Create a conda environment with all the necessary build dependencies:

```bash
conda create --name lightningsim-dev python=3.12 \
  --channel conda-forge \
  ccache=4 \
  cmake=3 \
  ninja=1 \
  nodejs=18 \
  rust=1.85 \
  libedit \
  libxml2 \
  ncurses \
  zlib \
  zstd \
  pip \
  setuptools-rust \
  binutils
```

**Note**: Python versions 3.10, 3.11, and 3.12 are supported.

### 3. Activate the Environment

```bash
conda activate lightningsim-dev
```

### 4. Install Additional Python Dependencies

```bash
pip install jinja2 llvmlite==0.43 pyelftools python-socketio uvicorn-standard
```

## Building from Source

The LightningSim build process consists of several components that need to be built in order:

### 1. Build Custom LLVM/Clang

LightningSim uses a custom fork of LLVM. Build it with:

```bash
# Create build directory
mkdir -p llvm-project/llvm/build

# Configure with CMake
cmake -S llvm-project/llvm -B llvm-project/llvm/build \
    -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$CONDA_PREFIX/share/lightningsim/llvm" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DLLVM_EXTERNAL_CLANG_SOURCE_DIR=llvm-project/clang \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_ENABLE_PROJECTS=clang \
    -DLLVM_INSTALL_TOOLCHAIN_ONLY=ON \
    -DLLVM_TOOLCHAIN_TOOLS='llvm-link;llvm-extract;opt' \
    -DLLVM_BUILD_LLVM_DYLIB=ON \
    -DLLVM_LINK_LLVM_DYLIB=ON \
    -DCMAKE_BUILD_TYPE=Release

# Build (this will take a while)
cmake --build llvm-project/llvm/build

# Install
cmake --install llvm-project/llvm/build --strip
```

**Note**: This step can take significant time and resources. Using `ccache` (as configured above) will speed up subsequent builds.

### 2. Build SystemC

LightningSim requires SystemC for simulation:

```bash
# Create installation directory
mkdir -p "$CONDA_PREFIX/share/lightningsim/systemc"

# Download and build SystemC
curl -fsSL 'https://www.accellera.org/images/downloads/standards/systemc/systemc-2.3.1a.tar.gz' | tar -xzf -
cd systemc-2.3.1a
./configure --prefix="$CONDA_PREFIX/share/lightningsim/systemc"
make
make install
cd ..
```

### 3. Build LightningSim Templates

Build the runtime templates and libraries:

```bash
mkdir -p "$CONDA_PREFIX/share/lightningsim/templates"
make DESTDIR="$CONDA_PREFIX/share/lightningsim/templates"
```

### 4. Build Frontend

The web interface is built with Node.js and SolidJS:

```bash
cd frontend
npm ci
npm run build -- --outDir="$CONDA_PREFIX/share/lightningsim/public" --emptyOutDir
cd ..
```

For development with hot-reload:

```bash
cd frontend
npm run dev
```

This will start a development server at http://localhost:3000.

### 5. Build and Install Backend

The backend is a Python package with Rust extensions:

```bash
cd backend
python -m pip install --no-deps --editable .
cd ..
```

The `--editable` flag allows you to make changes to Python code without reinstalling.

## Project Structure

```
LightningSim/
├── backend/              # Python backend with Rust core
│   ├── lightningsim/     # Python package
│   │   ├── model/        # Data models
│   │   ├── main.py       # Entry point
│   │   ├── simulator.py  # Simulation logic
│   │   └── ...
│   ├── lightningsim-core/ # Rust simulation core
│   ├── Cargo.toml        # Rust dependencies
│   └── pyproject.toml    # Python package configuration
├── frontend/             # SolidJS web interface
│   ├── src/              # Frontend source code
│   ├── package.json      # Node.js dependencies
│   └── vite.config.ts    # Build configuration
├── llvm-project/         # Custom LLVM/Clang fork
├── src/                  # C++ runtime templates
├── recipe/               # Conda build recipe
│   ├── meta.yaml         # Package metadata
│   ├── conda_build_config.yaml  # Build matrix
│   └── build.sh          # Conda build script
├── Makefile              # Template build configuration
└── README.md             # User documentation
```

## Development Workflow

### Running LightningSim in Development Mode

After building all components, you can run LightningSim directly:

```bash
lightningsim /path/to/vitis_hls_project/solution1
```

### Making Changes

1. **Python Code**: Changes to Python files in `backend/lightningsim/` are immediately reflected if you installed the backend in editable mode.

2. **Rust Code**: After modifying Rust code in `backend/lightningsim-core/`, rebuild the backend:
   ```bash
   cd backend
   python -m pip install --no-deps --editable .
   cd ..
   ```

3. **Frontend**: If running `npm run dev` in the frontend directory, changes are automatically hot-reloaded.

4. **LLVM/Clang Changes**: Rebuild using the cmake commands from step 1 of "Building from Source".

5. **Templates (src/)**: Run `make` again after changes.

## Code Style

### Python

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints where appropriate

### Rust

- Follow standard Rust conventions
- Run `cargo fmt` to format code:
  ```bash
  cd backend
  cargo fmt
  ```
- The project uses a custom rustfmt configuration in `backend/rustfmt.toml`

### TypeScript/JavaScript (Frontend)

- Follow the existing code style in the frontend
- The project uses EditorConfig (`.editorconfig`) for consistent formatting

### C++ (Templates)

- Follow the `.clang-format` style defined in `src/.clang-format`

## Testing

### Running the Full Conda Build

To test the complete build process as it runs in CI:

```bash
# Set up build environment
export CONDA_BLD_PATH="$HOME/conda-bld"
export CCACHE_DIR="$HOME/.ccache"
export CCACHE_BASEDIR="$HOME/conda-bld"

# Build package
conda build --no-anaconda-upload recipe
```

### Manual Testing

Test your changes by running LightningSim with a Vitis HLS solution directory:

```bash
lightningsim /path/to/test/solution1
```

Verify that:
- The web interface loads correctly at http://127.0.0.1:8080/
- Simulation runs complete successfully
- Your changes work as expected

## Submitting Changes

### Before Submitting

1. Test your changes thoroughly
2. Ensure your code follows the project's style guidelines
3. Update documentation if necessary
4. Make sure your commits have clear, descriptive messages

### Creating a Pull Request

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request on GitHub with:
   - A clear title describing the change
   - A detailed description of what the PR does
   - Reference to any related issues (e.g., "Fixes #4")

### PR Guidelines

- Keep PRs focused on a single feature or fix
- Include relevant tests if applicable
- Respond to review feedback promptly
- Ensure CI checks pass

## Getting Help

- **Issues**: Open an issue on GitHub for bug reports or feature requests
- **Questions**: Feel free to ask questions in issue discussions
- **Contact**: Reach out to [Rishov Sarkar](mailto:rishov.sarkar@gatech.edu) for project-related inquiries

## License

By contributing to LightningSim, you agree that your contributions will be licensed under the [AGPL-3.0-only License](LICENSE).

---

Thank you for contributing to LightningSim! 🚀⚡
