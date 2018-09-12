Getting started:
You can either run FishVisualizer.py with python or download a compiled binary for your operating system in the /bin folder. There are binaries for Linux, Windows, and MacOS.

Option 1 - Run with Python:
You will need to install the needed python2 modules. Most python installs include all of the modules except for tkinter and Pillow. How you do this will depend on your OS:

    Linux - To install tkinter on a debian system use "sudo apt-get install python-tk" and on a red hat based system use "dnf install python-tkinter" with superuser privaleges. You can install Pillow with pip using "pip install --user Pillow". You can install pip using "sudo apt-get install python-pip" on debian systems and "dnf install python-pip" on red hat based systems. MacOS users will need to install pip using brew 

    MacOS - First install tkinter with brew using (if not already installed) "brew install tcl-tk" to install tkinter". If you already have a python install then you will need to reinstall it with tkinter support. Use "brew uninstall python" to uninstall and "brew install python --with-tcl-tk" to install with tkinter support. If brew isn't installed on your computer you can install it with "/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)". You can install Pillow via pip using "pip install --user Pillow". To install pip (if not already installed) use "curl https://bootstrap.pypa.io/get-pip.py -o ~/Downloads/get-pip.py" to download pip and "python ~/Downloads/get-pip.py --user" to install pip to ~/Library/Python/2.7/bin. Then add pip to your $PATH using by adding "PATH=$PATH:~/Library/Python/2.7/bin" to ~/.bashrc. Use "source ~/.bashrc" to apply the path changes. 

    Windows - All Windows python installs come with Tkinter. You might need pip to install Pillow. Download get-pip.py from "https://bootstrap.pypa.io/get-pip.py" and install it using "python get-pip.py". Then run "pip install Pillow" to install pillow.
 
Option 2 - Run with compiled binary:
    Linux - Download FishVisualizerLinux in the /bin folder and run it using "./FishVisualizerLinux" in a terminal
    MacOS - Download FishVisualizerMacOS in the /bin folder and run it by right clicking it in finder and selecting Open With -> Terminal. Then click "Open Anyway" when prompted. This will add a security exception so that in the future you can just double click FishVisualizerMacOS in finder. You can also run it from the terminal the same as Linux. 
    Windows - Download FishVisualizerWindows in the /bin folder and double click it. 
