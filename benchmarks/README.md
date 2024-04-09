# LightningSim benchmarks

LightningSim has been tested on a wide variety of benchmarks. This directory contains the scripts and data needed to reproduce the results.

## System requirements

Ensure your system meets the [LightningSim system requirements.][1]

[1]: ../README.md#system-requirements

## Installation

Create a conda environment from the `environment.yml` file in this directory:

```bash
conda env create --file environment.yml
```

This will create a conda environment named `lightningsimv2-benchmarks`.

## Usage

Activate the conda environment:

```bash
conda activate lightningsimv2-benchmarks
```

Then, run the `benchmark.py` script:

```bash
./benchmark.py
```

This will run all benchmarks. Results will be generated in a single text file `results.txt`.

> **Warning**
>
> Running all benchmarks can take quite some time! Most benchmarks run in parallel, but large ones run sequentially to avoid bogging down the system and skewing the measured performance metrics.
>
> Expect this to take a few hours on a modern system. It is strongly recommended to use a program such as [tmux](https://github.com/tmux/tmux/wiki) or [GNU Screen](https://www.gnu.org/software/screen/) to guard against SSH disconnects killing the script.
