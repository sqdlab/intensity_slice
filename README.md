# Intensity Slice

This module allows for visualization of .dat files created using [uqtools](https://github.com/sqdlab/uqtools).

## Installation and usage

* Create a folder to use, open a terminal
* Clone this repository with 'git clone https://github.com/sqdlab/intensity_slice.git'
* Open an Anaconda Prompt, and cd to the previous folder.
* Run 'conda env create -f intensity_env.yml'
* Run 'conda activate intensity_slices'

Now you can open the intensity_slices with no problem.

In order to setup the automatic opening of .dat files, there are extra steps.

* Open run_intensity_v1.bat and change the following:
** Change the path to your Anaconda installation on the first line
** Change path to intensity_slice_gui.py to the current installation path.
* Change the default program to open .dat files with the above .dat file.
* Now it should be ready. Try running any .dat file.