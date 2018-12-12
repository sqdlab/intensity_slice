::This instruction explains how to setup batch file if you have Anaconda installation
::
::ADDITING PYTHON TO SYSTEM PATH 
::
::Check that the python.exe is added to the systems paths: open command prompt and type "python" it should return the python version which corresponds to the Anaconda installation (like "Python 2.7.15|Anaconda,Inc.| ...")
::In this case the path is already added. 
::Otherwise type "where python" in the Anaconda prompt and it will return the path to the "python.exe" file. Add this path to the system variable "Path" 
::(type "system variables" in Windows search and go to "Edit System Variables" option. Got to "Environment Variables" in the "System variables" click on "Path" and a new path copied from Anaconda prompt.
::
::INSTALLING VIRTUAL ENVIRONMENT
::
::run "conda env create -f intensity_env.yml" to install
::
::After that you can use the bath file as default program to open ".dat" files. Replace the path "C:\Software\intensity_slice-master\intensity_slice\intensity_slice_gui.py" with the correpsonding path on your computer
::"%~1" is used to supply the name of the file even if there are spaces in the path

call activate intensity_slice
python.exe C:\Software\intensity_slice-master\intensity_slice\intensity_slice_gui.py "%~1"
pause
