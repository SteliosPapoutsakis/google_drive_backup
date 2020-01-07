# google_drive_backup

This script helps me back up my files to google drive from the command line
It is based on google drive v3 API

## Getting Started

You may specify as many files to back up as you wish 

```
env/bin/python3 back_up_google.py PATH_TO_FILE1 PATH_TO_FILE2 ... PATH_TO_FILEN
```
you may also specify a specific directory for the files to be backup in with the -d flag

```
env/bin/python3 back_up_google.py -d DIRECTORY PATH_TO_FILE1 PATH_TO_FILE2 ... PATH_TO_FILEN
```
This directory can simply be the name of the directory and not the path.

For example, if I want to store files in MyDrive/foo/bar, I can specify 
-d bar or -d MyDrive/foo/bar, either will select the bar directory

However, if there are multiple directories with the same name the user will be prompted to select the correct one.

To list all the files in the a directory
```
env/bin/python3 back_up_google.py -l DIRECTORY
```
This again follows the same rules as the -d flag

Additionily, the --fileonly and --directoryonly flags can be used to display those types of files

### Prerequisites

To use this script you must have pip install the packages in requirements.txt

```
env2/bin/pip install -r requirements.txt
```

Additionly, you must register with the google api and store a credentials.json file in the same directory as the script


## Authors

* **Stelios Papoutsakis** - *Initial work* 





