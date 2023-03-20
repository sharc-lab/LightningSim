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

This will create a conda environment named `lightningsim-benchmarks`.

## Usage

Activate the conda environment:

```bash
conda activate lightningsim-benchmarks
```

Then, run the `benchmark.py` script:

```bash
./benchmark.py
```

This will run all benchmarks. Results will be generated in CSV format in `output.csv` in each benchmark directory.

> **Warning**
>
> Running all benchmarks can take quite some time! Even though benchmarks are run in parallel, certain individual benchmarks can take a long time to complete; for example, `29_flowgnn_gin` and `32_flowgnn_pna` took over an hour to complete on our system. This is because each benchmark runs Vitis HLS cosimulation for comparison with LightningSim.
>
> Refer to Table III in the paper for the timings of each benchmark on our system, which you can use as a reference point to estimate how long each benchmark will take to run on your system.
