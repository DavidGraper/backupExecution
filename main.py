import subprocess
import csv
import datetime
import os
import glob
import re
import argparse
import selectors

from datetime import datetime

destination_root = ""
segment_to_backup = ""


def LoadBackupDriveDirectoryList():
    destination_directory_list = [x[0] for x in os.walk(destination_root)]
    for i, item in enumerate(destination_directory_list):
        destination_directory_list[i] = item.replace(destination_root,"")

    #     Clean the listing of TRASH and other non-directory entries
    returnlist = []
    for item in destination_directory_list:
        if item == "" or item.__contains__('Trash'):
            continue
        returnlist.append(item)

    return returnlist


def LoadSourceDirectoryList(backupsegment, logfile):
    source_directory_list = []
    # with open ("directory_breakdown.csv", newline='') as f:
    with open (path_to_list_of_files, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] != backupsegment:
                continue
            logfile.write("\nQueued for rsync backup:  {0}".format(row[1]))
            source_directory_list.append(row[1])
    return source_directory_list


def RemoveDirectoriesNotToRsync(DeleteDirectoryList, logfile):
    logfile.write("\n")
    for item in DeleteDirectoryList:
        fullpath = destination_root + item
        logmessage = str(datetime.now()) + ": Deleting " + fullpath +"\n"
        logfile.write(logmessage)

        process = subprocess.Popen(['rm', '-rf', fullpath], stdout=subprocess.PIPE)


def ExecuteRsyncBackup(sourcepath, destinationroot, logfile):
    # process = subprocess.Popen(['rsync', '-a', '-v', row[1], '//media//dgraper//240GB'], stdout=subprocess.PIPE)
    # stdout, stderr = process.communicate()

    logmessage = "\nRSYNC of {0} starting {1}\n".format(sourcepath, str(datetime.now()))
    logfile.write(logmessage)

    # ls_lines = subprocess.check_output(['ls', '-l']).splitlines()
    ls_lines = subprocess.check_output(['rsync', '-avzhR', sourcepath, destinationroot, '--delete']).splitlines()
    # process = subprocess.Popen(['rsync', '-avzhR', sourcepath, destinationroot, '--delete'], stdout=subprocess.PIPE)
    # result = subprocess.run(['rsync', '-avzhR', sourcepath, destinationroot, '--delete'], capture_output=True)
    # stdout, stderr = process.communicate()

    for line in ls_lines:
        try:
            ascii_line = line.decode('UTF-8')
        except:
            ascii_line = "<decode_err>"
        ascii_line += "\n"
        logfile.write(ascii_line)

    # logfile.write("* stdout")
    # logfile.write(result.stdout)
    # logfile.write("* stderr")
    # logfile.write(result.stderr)

    # stdoutreader = csv.reader(stdout.decode('ascii').splitlines(), delimiter='\t', quotechar="'")
    #
    # for stdoutrow in stdoutreader:
    #     if len(stdoutrow) > 0:
    #         try:
    #             logfile.write(stdoutrow[0] + "\n")
    #         except:
    #             print("error")

    # sel = selectors.DefaultSelector()
    # sel.register(process.stdout, selectors.EVENT_READ)
    # sel.register(process.stderr, selectors.EVENT_READ)
    #
    # while True:
    #     for key, _ in sel.select():
    #         data = key.fileobj.read1().decode()
    #         if not data:
    #             exit()
    #         if key.fileobj is process.stdout:
    #             logfile.write(data, end="")
    #             logfile.write("\n")
    #         else:
    #             print(data, end="", file=sys.stderr)

    logmessage = "\nRSYNC of {0} ending {1}\n".format(sourcepath, str(datetime.now()))
    logfile.write(logmessage)

def GetAllSubpaths(listofpaths):

    returnlist = []

    for path in listofpaths:

        subsections = path.split('/')
        subpath = ''
        first = True
        for subsection in subsections:
            if first:
                subpath = subsection
                first = False
            else:
                subpath = subpath + '/' + subsection

            if not subpath in returnlist:
                returnlist.append(subpath)

    return returnlist


def ClearPermissiblePaths(source_directory_list, destination_directory_list):
    returnlist = []

    # Get all source subpaths for source paths
    source_subpaths = GetAllSubpaths(source_directory_list)

    # First, clear any destination subdirectory that has a source directory as its parent
    for i in range(0, len(destination_directory_list)):
        for sourcepath in source_directory_list:
            matchpattern = "^" + sourcepath
            if re.match(matchpattern, destination_directory_list[i]):
                destination_directory_list[i] = ""

        for subpath in source_subpaths:
            if subpath == destination_directory_list[i]:
                destination_directory_list[i] = ""

    # Generate list of directories to delete
    for item in destination_directory_list:
        if item != "" :
            returnlist.append(item)

    return returnlist


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    import sys

    # create parser
    parser = argparse.ArgumentParser(add_help=True)

    # add arguments to the parser
    parser.add_argument("segmenttobackup")
    parser.add_argument("pathtolistoffiles")
    parser.add_argument("destinationpath")

    # parse the arguments
    try:
        args = parser.parse_args()
    except:
        print("error 1")

    destination_root = args.destinationpath
    segment_to_backup = args.segmenttobackup
    path_to_list_of_files = args.pathtolistoffiles

# Set up log file
logfile_name = "rsync_backup_segment_" + segment_to_backup + ".txt"
logfile = open(logfile_name, "a")
logfile.write("\n\n* * * * * *\nStarting rsync task at " + str(datetime.now()) + "\n* * * * * *\n")

# Get directories from source to backup
source_directory_list = LoadSourceDirectoryList(segment_to_backup, logfile)

# Get directories currently on backup drive
destination_directory_list = LoadBackupDriveDirectoryList()

# Get directories to clean off backup drive
extraneous_paths_list = ClearPermissiblePaths(source_directory_list, destination_directory_list)

# Remove extraneous directories from backup drive
RemoveDirectoriesNotToRsync(extraneous_paths_list, logfile)

# Backup all source directories
for sourcepath in source_directory_list:
    print("Rsyncing path '{0}'".format(sourcepath))
    ExecuteRsyncBackup(sourcepath, destination_root, logfile)

logfile.write("\n* * * * * *\nEnding rsync task at " + str(datetime.now()) + "\n* * * * * *\n\n")
