06-13-25 
* SEE MD FILE * 

* Eliminates spaces and unfriendly charaters from filename 
** Python file: does the work 
** Bat file: put this in the path and hardcode the path to the python file 
** Shell file: put in the path and hardcode the path to the python file 

Example: 
Batch file, copy/place in C:\core\installations 
    @echo off
    python "C:\q\arc\projects\filerenamer\filerenamer.py" %* 

    copy filerenamer.bat c:\core\installations\ 

Shell file, copy/place in /home/user/bin (under WSL)
    #!/bin/bash
    python3 /mnt/c/q/arc/projects/filerenamer/filerenamer.py "$@"

    cp filerenamer /home/user/bin/ 




