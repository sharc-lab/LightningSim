# :zap: LightningSim

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7823073.svg)](https://doi.org/10.5281/zenodo.7823073) [![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/sharc-lab/LightningSim/conda-build.yml?branch=main)](https://github.com/sharc-lab/LightningSim/actions/workflows/conda-build.yml?query=branch%3Amain)

Welcome to the LightningSim project!

LightningSim is a fast, accurate trace-based simulator for High-Level Synthesis. It is developed and maintained by [Rishov Sarkar][1] from [Sharc Lab][2] at [Georgia Tech][3].

[1]: mailto:rishov.sarkar@gatech.edu
[2]: https://sharclab.ece.gatech.edu/
[3]: https://www.gatech.edu/

## System requirements

LightningSim has been tested on a server with a 64-core Intel Xeon Gold 6226R CPU and 502 GiB of RAM running RHEL Server 7.9. However, we expect it to run on most 64-bit x86 systems running a modern Linux distribution.

LightningSim expects AMD/Xilinx Vitis HLS (a part of the [Vitis Unified Software Platform][4]) to be present on the machine it is running on. This includes [setting up the environment, as described in the Vitis HLS documentation.][5]

All testing has been performed using Vitis HLS 2021.1, though we expect any recent version of Vitis HLS to work.

[Conda][6] is required to install LightningSim. Conda may be installed following the instructions at [this link.][7] (We recommend using the [Miniconda installer.][8])

[4]: https://www.xilinx.com/products/design-tools/vitis/vitis-platform.html
[5]: https://docs.xilinx.com/r/en-US/ug1399-vitis-hls/Setting-Up-the-Environment
[6]: https://docs.conda.io/projects/conda/en/stable/
[7]: https://docs.conda.io/projects/conda/en/stable/user-guide/install/linux.html
[8]: https://docs.conda.io/en/latest/miniconda.html#linux-installers

## Installation

Create a new conda environment and install LightningSim using the following command, replacing `$ENV_NAME` with the name of the environment you wish to create:

```bash
conda create --yes --name $ENV_NAME --channel https://sharc-lab.github.io/LightningSim/repo --channel conda-forge lightningsim
```

## Usage

If not already activated, activate the conda environment you created when installing LightningSim:

```bash
conda activate $ENV_NAME
```

Then, simply run the `lightningsim` command with the path to a Vitis HLS solution directory as the first argument. For example:

```bash
lightningsim /path/to/vitis_hls_project/solution1
```

> **Warning**
>
> Please note that LightningSim is expecting the path to a _solution_ directory, not a _project_ directory. The solution directory resides directly under the project directory, alongside the file `hls.app`, and is usually named `solution1`.

By default, the LightningSim web server interface will start on http://127.0.0.1:8080/. You can change the port number by passing the `--port` argument to the `lightningsim` command.

> **Note**
>
> If running LightningSim on a remote server, you may need to tunnel the web server port to your local machine in order to view the web interface.
>
> For example, if you are running LightningSim on a server with hostname `server.example.com`, you can tunnel the default LightningSim port 8080 to your local machine using the following command:
>
> ```bash
> ssh -L 8080:127.0.0.1:8080 server.example.com
> ```
>
> This will make the web interface available on your local machine at http://127.0.0.1:8080/.

By default, LightningSim will wait for Vitis HLS to start its next C synthesis run before starting simulation. This is indicated on the web interface by the status message &ldquo;Waiting for next C synthesis run&hellip;&rdquo; alongside a link labeled &ldquo;(skip),&rdquo; which can be clicked to start simulation immediately using the results of the last C synthesis run.

You can also start simulation immediately by passing the `--skip-wait-for-synthesis` argument to the `lightningsim` command.

All available command-line options can be viewed by running `lightningsim --help`.
