import subprocess
import csv
import datetime
import os
import glob
import re
import argparse
import selectors
import sys

from os.path import exists
from datetime import datetime

# Program for backing up very large amounts of media to multiple devices with drives of varying sizes

# The program runs on a backup agent and references a file created by the "BackupDistributor" program.  The file
# lists all the paths that should be backed up and marks each one with the agent that should back them up.
#
# This agent program reads that file, gets the paths it should back up, and uses "rsync" to back those paths up to a
# local drive
#
# It features a "dryrun" flag to show what it will do before actually doing it
#
# Command-line arguments
# 0 - section/segment of files in logfile to backup
# 1 - path to list of files to backup
# 2 - destination path (root directory of media to backup to)

localbackupdrivemountpath = ""
localsourcedrivemountpath = ""
agentname = ""
dryrun = False

# Set up local log file
def setuplocallogfile():
    today_short = datetime.today().strftime('%Y%m%d')
    today_long = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

    # Initialize logfile
    logfile_name = "rsync_backup_segment_{0}_{1}.txt".format(agentname, today_short)
    logfile = open(logfile_name, "a")
    logfile.write("\n\n* * * * * *\nStarting rsync task at " + today_long + "\n* * * * * *\n")

    return logfile

# Scan destination media, assemble list of paths (destination_directory_list)
def LoadBackupDriveDirectoryList():

    # Insure that backup path exists
    if not os.path.exists(localbackupdrivemountpath):
        raise Exception("Backup destination path does not exist")

    # Walk the destination backup drive getting a treelisting of directories
    destination_directory_list = [x[0] for x in os.walk(localbackupdrivemountpath)]
    for i, item in enumerate(destination_directory_list):
        destination_directory_list[i] = item.replace(localbackupdrivemountpath, "/")

    #  Clean the listing of TRASH and other non-directory entries
    returnlist = []
    for item in destination_directory_list:
        if item == "" or item.__contains__('Trash'):
            continue
        returnlist.append(item)

    return returnlist

# Load the paths-to-backup assigned to this agent
def LoadSourceDirectoryList(directorypathstobackup, backupagent, logfile):
    source_directory_list = []
    with open (directorypathstobackup, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] != backupagent:
                continue
            logfile.write("\nQueued for rsync backup:  {0}{1}".format(localsourcedrivemountpath,row[2]))
            source_directory_list.append(localsourcedrivemountpath + row[2])
    return source_directory_list

# Delete directories on destination drive no longer needed for sync
def RemoveDirectoriesNotToRsync(DeleteDirectoryList, logfile):
    logfile.write("\n")
    for item in DeleteDirectoryList:
        fullpath = localbackupdrivemountpath + item
        logmessage = str(datetime.now()) + ": Deleting " + fullpath +"\n"

        print(logmessage)

        logfile.write(logmessage)

        try:
            if exists(fullpath):
                process = subprocess.Popen(['rm', '-rf', fullpath], stdout=subprocess.PIPE)
            else:
                raise Exception("Path {0} does not exist".format(fullpath))
        except Exception as e:
            print("Remove Directories Error:")
            print(e)

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


# Given a list of directory ('/home/dgraper/movie1', 'home/dgraper/movie2') create a list of all the legitimate combinations of directories
# in a tree of those directories ('/home', 'home/dgraper', 'home/dgraper/movie1', 'home/dgraper/movie2'
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

def ConvertStringToRegexPattern(stringin):
    stringout = stringin.replace("/","\/")
    stringout = stringout.replace(")","\)")
    stringout = stringout.replace("(","\(")
    return stringout

def IdentifyBackedupDirectoriesNoLongerNeeded(source_directory_list, destination_directory_list):
    returnlist = []

    # Get all source subpaths for source paths
    source_subpaths = GetAllSubpaths(source_directory_list)

    # Remove all destination paths matching source subpaths
    for sourcepath in source_subpaths:
        for i in range(0, len(destination_directory_list)):
            if sourcepath == destination_directory_list[i]:
                destination_directory_list[i] = ""

    # Remove all destination patterns which have a parent in the list of source directories
    for sourcepath in source_directory_list:
        matchpattern = "^" + ConvertStringToRegexPattern(sourcepath)

        for i in range(0, len(destination_directory_list)):
            result = re.match(matchpattern, destination_directory_list[i])
            if result:
                destination_directory_list[i] = ""


    # Clear the entry for the root directory
    for i in range(0, len(destination_directory_list)):

        if destination_directory_list[i] == '/':
            destination_directory_list[i] = ""
            continue

    # Generate list of directories to delete
    for item in destination_directory_list:
        if item != "" :
            returnlist.append(item)

    return returnlist


if __name__ == '__main__':

    # Get command-line arguments
    parser = argparse.ArgumentParser(add_help=True)

    # add arguments to the parser
    parser.add_argument("--agentname", help="Name of this agent")
    parser.add_argument("--masterpathlist", help="Path to list of files to be backed up")
    parser.add_argument("--localbackupdrivemountpath", help="Local mount path to attached drive to back files up up to")
    parser.add_argument("--localsourcedrivemountpath", help="Local mount path to source files to be backed up")
    parser.add_argument('--dryrun', action="store_true", default=False)

    try:
        args = parser.parse_args()
    except Exception as e:
        print("Error on argument parser: {0}".format(e))
        exit()

    dryrun = args.dryrun
    localsourcedrivemountpath = args.localsourcedrivemountpath
    localbackupdrivemountpath = args.localbackupdrivemountpath
    agentname = args.agentname
    masterlist_allpathstobackup = args.masterpathlist

    # Start program

    # Set up the local logfile that contains status messages
    local_logfile = setuplocallogfile()

    # Get directory paths from the masterlist for this agent to backup
    directorypaths_to_backup = LoadSourceDirectoryList(masterlist_allpathstobackup, agentname, local_logfile)

    # Get the directories currently on the backup drive
    try:
        destination_directory_list = LoadBackupDriveDirectoryList()
    except Exception as e:
        print("Error on accessing the backup drive: {0}".format(e))
        exit()

    # Compare the directories currently on the backup drive with the paths this agent is supposed to back up
    extraneous_paths_list = IdentifyBackedupDirectoriesNoLongerNeeded(directorypaths_to_backup, destination_directory_list)

    local_logfile.write("\n\nSystem will delete these paths on the backup drive before continuing:\n\n")
    for string1 in extraneous_paths_list:
        local_logfile.write("\t{0}\n".format(string1))

    if not dryrun:

        # Remove extraneous directories from backup drive
        RemoveDirectoriesNotToRsync(extraneous_paths_list, local_logfile)

        # Backup all source directories
        for sourcepath in directorypaths_to_backup:
            print("Rsyncing path '{0}'".format(sourcepath))
            ExecuteRsyncBackup(sourcepath, localbackupdrivemountpath, local_logfile)

        local_logfile.write("\n* * * * * *\nEnding rsync task at " + str(datetime.now()) + "\n* * * * * *\n\n")
    else:

        local_logfile.write("\n* * * * * *\nEnding rsync task at " + str(datetime.now()) + "\n* * * * * *\n\n")

