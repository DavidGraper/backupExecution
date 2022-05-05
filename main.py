import subprocess
import csv
import datetime
import os
import glob
import re
import argparse
import selectors
import sys
import string
import stat

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

# Name of local configuration file
configfile = ""

# Set up local log file
def createlocallogfile(agent):
    today_short = datetime.today().strftime('%Y%m%d')
    today_long = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

    # Initialize logfile
    logfile_name = "rsync_{0}_{1}.txt".format(agent["agentname"], today_short)
    logfile = open(logfile_name, "a")
    logfile.write("\n\n* * * * * *\nLogfile initialized " + today_long + "\n* * * * * *\n")
    logfile.close()

    return logfile_name


# Scan this computer's destination media to see what's already there
def LoadBackupDriveDirectoryList(localbackupdrivemountpath):

    # Insure that backup path exists
    if not os.path.exists(localbackupdrivemountpath):
        raise Exception("Backup destination path '{0}' does not exist".format(localbackupdrivemountpath))

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

# Read master list from BackupDistributor and get paths assigned to this agent
def LoadSourceDirectoryList(directorypathstobackup, localbackupdrivemountpath, logfile):
    source_directory_list = []
    try:
        with open (directorypathstobackup, newline='') as f:
            reader = csv.reader(f, delimiter = '\t')
            for row in reader:

                filetobackup_agentname = row[0]
                filetobackup_fullpath = row[1]
                filetobackup_size = int(row[2])

                if filetobackup_agentname != agent["agentname"]:
                    continue

                # Only back up listings with size > 0
                if filetobackup_size > 0:
                    logfile.write("\nQueued for rsync backup:  {0}".format(filetobackup_fullpath))
                    source_directory_list.append(filetobackup_fullpath)

        return source_directory_list
    except Exception as e:
        raise Exception("Fail on LoadSourceDirectoryList: {0}".format(e.message))

# Delete extraneous directories on destination drive
def RemoveDirectoriesNotToRsync(DeleteDirectoryList, localbackupdrivemountpath, logfile):
    logfile.write("\n")
    for item in DeleteDirectoryList:
        fullpath = localbackupdrivemountpath + item

        # Remove any double-slashes in the pathname
        fullpath = fullpath.replace("//","/")

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

# RSYNC each path assigned to this agent
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

# Get paths in a destination list that are *not* in a source list
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
            print(destination_directory_list[i])
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

def ReadConfigurationFile(configfileName):

    # Does file exist
    if not os.path.exists(configfileName):
        raise Exception("Specified config file does not exist")

    # Config file is a series of strings with 3 arguments separated with colons

    f = open(configfileName, "r")
    fileline = f.readline()
    while fileline:
        lineparts = fileline.split(':')
        arg = lineparts[0].upper().replace("\"","")
        val0 = lineparts[1].replace("\n", "").replace("\"","")

        agentpattern = r"^AGENT\d.*$"

        # Arguments have only two parts
        if len(lineparts) == 2:
            if arg == "DRYRUN":
                dryrun = val0
            elif arg == "LISTOFALLFILESTOBACKUP":
                listofallfilestobackup = val0
            elif arg == "BACKUPAGENTSMOUNTPATH":
                backupagentsmountpath = val0
        if len(lineparts) == 3:
            val1 = lineparts[2].replace("\n", "").replace("\"", "")
            if re.match(agentpattern, arg):
                agentinfo.append({'agentname': val0, 'agentbackupdevice': val1})

        fileline = f.readline()
    f.close()

    if len(agentinfo) == 0:
        raise Exception("No agents specified")
    elif len(agentinfo) > 4:
        raise Exception(r"Too many agents (>4) specified")

    returnvals = [dryrun, listofallfilestobackup, backupagentsmountpath, agentinfo]
    return returnvals

def create_tobedone_files(inputfilename, agent):

    # Read the full "backupjobdivisions.txt" file and pull out only lines belonging to this agent,
    # save to another text file ("tobedone.txt" file)

    file_output = open("{0}_tobedone.txt".format(agent["agentname"]), "w", encoding='latin-1')

    with open(inputfilename, encoding='latin-1') as file_input:
        for inputline in file_input:

            # Do a regex filter on files assigned to this agent
            regexpression = "^{0}\t(.*)\t\d+\t\d+$".format(agent["agentname"])
            match = re.search(regexpression, inputline)
            if not match is None:
                print(match.group(1))
                file_output.write(match.group(1) + "\n")

    file_output.close()


def create_backupmedia_logfile(agent):

    mediapathname = agent["agentbackupdevice"]
    outputfilename = "{0}_media.txt".format(agent["agentname"])

    command = "du {0} | tee {1}".format(mediapathname, outputfilename)
    os.system(command)

    lines = []
    with open(outputfilename, "r") as fp:
        for line in fp:
            lines.append(re.sub("^[0-9]*\t"+agent["agentbackupdevice"],"",line))

    lines.sort()

    with open(outputfilename, "w") as fp:
        for line in lines:
            if (line != "\n"):
                fp.write(line)

    # command1 = r"du /media/dgraper/PATRIOT/ | sed 's/^[0-9]*\t\/media\/dgraper\/PATRIOT\///' | sort | tee BackupDevice1_media.txt"
    # command1 = "diff {0}_tobedone.txt BackupDevice1_media.txt -u | sed '/^+/!d' | sed 's/^+//' > BackupDevice1_directoriestodelete.sh".format(m)

def removelinesfrommedialistingfile(agent, rootpathtoavoid, pathstoavoid):

    # Break down rootpath into component paths to avoid, add those to "pathstoavoid"
    rootpaths = rootpathtoavoid.split("/")
    del rootpaths[0]

    pathtoavoid = ""
    for rootpath in rootpaths:
        pathtoavoid += "/" + rootpath
        pathstoavoid.append(pathtoavoid)

    filename = "{0}_media.txt".format(agent["agentname"])

    lines = []
    with open(filename, "r") as fp:
        for line in fp:
            lines.append(line.replace("\n",""))

    with open(filename, "w") as fp:
        for line in lines:
            if not line in pathstoavoid:
                fp.write(line + "\n")


def create_directoriestodelete_shellfile(agent):

    # Get differences between the list of directories to be backed up and directories currently on backup media drive
    # command = r"diff {0}_tobedone.txt {0}_media.txt -u | sed '/^\+/!d' | sed 's/^\+//' > {0}_directoriestodelete.sh".format(agent['agentname'])
    command = r"diff {0}_tobedone.txt {0}_media.txt -u > {0}_directoriestodelete.sh".format(agent['agentname'])
    os.system(command)

    filename ="{0}_directoriestodelete.sh".format(agent["agentname"])
    lines = []

    # First, remove all lines that don't begin with a "+"
    lines = []
    with open(filename, "r") as fp:
        for line in fp:
            if line[:2] == "+/":
                line = line[1:]
                lines.append(line)

    with open(filename, "w") as fp:
        for line in lines:
            fp.write(line)

    # Next, properly escape all reserved characters
    lines = []
    with open(filename, "r") as fp:
        for line in fp:

            line = line.replace(" ","\\ ")
            line = line.replace("&","\\&")
            line = line.replace("'","\\'")
            line = line.replace("(","\\(")
            line = line.replace(")","\\)")
            line = "rm -rf {0}{1}".format(agent["agentbackupdevice"], line)

            lines.append(line)

    with open(filename, "w") as fp:
        for line in lines:
            fp.write(line)


def create_backup_shellfile(agent, fastbackup):

    lines = []

    inputfilename ="{0}_tobedone.txt".format(agent["agentname"])
    outputfilename = "{0}_backup.sh".format(agent["agentname"])

    destinationdrive = agent["agentbackupdevice"]

    with open(outputfilename, "w") as fileout:
        with open(inputfilename, "r") as filein:
            for line in filein:

                line = line.replace(" ", "\\ ")
                line = line.replace("&", "\\&")
                line = line.replace("'", "\\'")
                line = line.replace("(", "\\(")
                line = line.replace(")", "\\)")

                if fastbackup == True:
                    fileout.write("rsync -Rhvp --ignore-existing {0}/* {1}\n".format(line.replace("\n",""), destinationdrive))
                else:
                    fileout.write("rsync -Rhvp {0}/* {1}\n".format(line.replace("\n",""), destinationdrive))


def execute_backupmediacleanup(logfilename, agent):

    today_long = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

    # Initialize logfile
    logfile = open(logfilename, "a")
    logfile.write("\n\n* * * * * *\nStart cleanup of destination drive " + today_long + "\n* * * * * *\n")
    logfile.close()

    # pathname = "{0}_directoriestodelete.sh".format(agent["agentname"])
    # os.chmod(pathname, stat.S_IRWXU or stat.S_IRWXG or stat.S_IRWXO)


    command = "chmod 777 {0}_directoriestodelete.sh".format(agent["agentname"])
    os.system(command)

    command = "./{0}_directoriestodelete.sh | tee {1}".format(agent["agentname"], logfilename)
    os.system(command)


def execute_backup(logfilename, agent):

    today_long = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

    # Initialize logfile
    logfile = open(logfilename, "a")
    logfile.write("\n\n* * * * * *\nStart backup " + today_long + "\n* * * * * *\n")
    logfile.close()

    command = "chmod 777 {0}_backup.sh".format(agent["agentname"])
    os.system(command)

    command = "./{0}_backup.sh | tee {1}".format(agent["agentname"], logfilename)
    os.system(command)


# Start
if __name__ == '__main__':

    # CSV file containing all paths to backup and agents assigned to each (output from "BackupDistributor")
    listofallfilestobackup = ""

    # List of agents that this computer represents as well as devices on this computer used for backups
    agentinfo = []

    dryrun = False

    # Get command-line arguments
    parser = argparse.ArgumentParser(add_help=True)

    # add arguments to the parser
    parser.add_argument('--dryrun', action="store_true", default=False)
    parser.add_argument("--configfile", help="Configuration file")
    parser.add_argument("--verbose", help="Show verbose output", default=False)
    parser.add_argument("--masterpath", help="Path to be backed up", default="")

    try:
        args = parser.parse_args()
    except Exception as e:
        print("Error on argument parser: {0}".format(e))
        exit()

    dryrun = args.dryrun
    configfile = args.configfile
    verbose = args.verbose

    # Start program

    # Check to see if config file exists; if so, it is source of all config info (command line arguments ignored)
    if configfile != "":
        returnvals = ReadConfigurationFile(configfile)

        dryrun = returnvals[0]
        listofallfilestobackup = returnvals[1]
        backupagentsmountpath = returnvals[2]
        agentinfo = returnvals[3]
    else:
        print("No config file specified")
        exit()

    # DIAGNOSTIC - Override and use local file during debugging
    listofallfilestobackup = "/home/dgraper/Documents/backupjobdivisions.txt"

    # Handle multiple agents (if specified)
    for agent in agentinfo:

        # Extract lists of files to be backed up by each backup server
        # 1.  Create <BackupDeviceName>_tobedone.txt file for this agent
        # (the list of paths to be backed up by this agent)
        create_tobedone_files(listofallfilestobackup, agent)

        # 2.  Create <BackupDeviceName>_media.txt file which lists all directories currently on this device
        # assigned to this backup agent
        create_backupmedia_logfile(agent)

        # 3.  Remove all "root" directories from the <BackupDeviceName>_media.txt file. In the next
        # step we'll be comparing the directories on the _media.txt file with the list of directories to be backed
        # up, seeking "extraneous" directories in the _media.txt file that don't have matches in the list of
        # directories to be backed up.
        #
        # These are directories that will be removed before starting backups -- since they're not in the list of
        # directories to be backed up, we want to save space and remove them from the destination drive.
        #
        # We want to avoid leaving the source "root" directories in the media listing file because if we leave them in
        # the root will be marked for cleanup, it'll basically clear the whole thing out, requiring a
        # redundant re-backing up of all the files targeted for this agent.

        # These are fixed paths on the destination drive we know we don't want to remove
        backupmediadrivepathstoavoid = ['/System Volume Information', '/']

        # Remove the root directories from the media listing file
        removelinesfrommedialistingfile(agent, backupagentsmountpath, backupmediadrivepathstoavoid)

        # Create a shell file of files to delete
        create_directoriestodelete_shellfile(agent)

        # Modify the "to be done" file into a shell file
        create_backup_shellfile(agent, True)

        # Set up the local logfile that contains status messages
        local_logfilename = createlocallogfile(agent)

        # Run directory cleanup
        execute_backupmediacleanup(local_logfilename, agent)

        # Run backups
        execute_backup(local_logfilename, agent)

        #
        # # Get directory paths from the masterlist for this agent to backup
        # directorypaths_to_backup = LoadSourceDirectoryList(listofallfilestobackup, agent, local_logfile)
        #
        # # Get the directories currently on the backup drive
        # try:
        #     destination_directory_list = LoadBackupDriveDirectoryList(agent["agentbackupdevice"])
        # except Exception as e:
        #     print("Error on accessing the backup drive: {0}".format(e))
        #     exit()
        #
        # # Compare the directories currently on the backup drive with the paths this agent is supposed to back up
        # try:
        #     extraneous_paths_list = IdentifyBackedupDirectoriesNoLongerNeeded(directorypaths_to_backup, destination_directory_list)
        # except Exception as e:
        #     print("Error on identifying backed up directories no longer needed: {0}".format(e))
        #     exit()
        #
        # local_logfile.write("\n\nSystem will delete these paths on the backup drive before continuing:\n\n")
        # for string1 in extraneous_paths_list:
        #     local_logfile.write("\t{0}\n".format(string1))
        #
        # print("Dryrun = {0}".format(str(dryrun)))
        #
        # if not dryrun:
        #
        #     # Remove extraneous directories from backup drive
        #     RemoveDirectoriesNotToRsync(extraneous_paths_list, agent["agentbackupdevice"], local_logfile)
        #
        #     # Backup all source directories
        #     for sourcepath in directorypaths_to_backup:
        #         print("Rsyncing path '{0}'".format(sourcepath))
        #         ExecuteRsyncBackup(sourcepath, agent["agentbackupdevice"], local_logfile)
        #
        #     local_logfile.write("\n* * * * * *\nEnding rsync task at " + str(datetime.now()) + "\n* * * * * *\n\n")
        # else:
        #     local_logfile.write("\n* * * * * *\nEnding dryrun rsync task at " + str(datetime.now()) + "\n* * * * * *\n\n")

