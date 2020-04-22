#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Current Version: 0.1.
#Version History
#   0.1.0 - 20200420
#       First Attempt at getting this working
#
#   REQUIREMENTS
#       COMMAND LINE TOOLS
#           ffmpeg
#           bwfmetaedit
#           id3v2
#       OTHER REQUIREMENTS
#           Internet Connection
#

# import modules used here -- sys is a very standard one
import os, sys
import datetime
import csv                          # used for creating the csv
import hashlib                      # used for creating the md5 checksum
import subprocess                   # used for running ffmpeg, qcli, and rsync
import shlex                        # used for properly splitting the ffmpeg/rsync strings
import argparse                     # used for parsing input arguments
import re                           # used for getting BARCODE using regular expressions
import config
from simple_salesforce import Salesforce



# Gather our code in a main() function
def main():


    media_info_list = []

    ####init the stuff from the cli########
    parser = argparse.ArgumentParser(description="Transcodes Audio Files and Uploads info to Salesforce")
    parser.add_argument('-i','--input',dest='i', help="the path to the input directory or files")
    parser.add_argument('-o','--output',dest='o', help="the output file path (optional)")
    parser.add_argument('-r','--rsync',action='store_true',dest='r',default=False,help="Rsync mode: enabling this will automatically sync the files to a specified backup directory")
    args = parser.parse_args()


    #handling the input args. This is kind of a mess in this version
    if args.i is None:
        print(bcolors.FAIL + "Please enter an input path!" + bcolors.ENDC)
        sys.exit()
    if args.o is None:
        print(bcolors.OKBLUE +  "No output path defined, using default path" + bcolors.ENDC)
        out_path = ""
    else:
        out_path = args.o
        print(bcolors.OKBLUE +  "User output path defined as " + out_path + bcolors.ENDC)


    # This part can tell if we're processing a file or directory. Handles it accordingly
    inPath = args.i
    inType = fileOrDir(inPath)

    #processDict contains the info the script needs to run each subprocess, inlcuding the options that the user selected, and the paths to the files
    processDict = {}
    processDict = createProcessDict(processDict)

    #init salesforce login#
    try:
        print(bcolors.OKBLUE +  "\nConnecting To Salesforce" + out_path + bcolors.ENDC)
        sf = Salesforce(username=config.username,password=config.password,security_token=config.security_token)
        print(bcolors.OKGREEN +  "\nSalesforce connection succesfull!" + out_path + bcolors.ENDC)
    except:
        print(bcolors.FAIL + "\nSalesforce Connection Failed. Quitting Script" + bcolors.ENDC)
        sys.exit()


    #initialize master file extension in processDict
    processDict['masterExtension'] = ".wav"

    # Initialize CSV output info
    #if args.c is None:
    #    csv_name = "mediainfo.csv"
    #elif ".csv" in args.c:
    #    csv_name = args.c
    #else:
    #    csv_name = args.c + ".csv"

    # If we are processing a single file
    if inType == "F":
        print(bcolors.OKBLUE + "\nProcessing Input File: " + os.path.basename(inPath) + "\n\n" + bcolors.ENDC)

        #Set the paths of the CSV files (took this part out for now, but might put it back in)
        #if out_path == "":
        #    csv_path = os.path.dirname(inPath) + "/" + csv_name
        #else:
        #    csv_path = out_path
        #print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)

        #Process as Audio Files
        #Harvest mediainfo metadata, there is a subprocess in this script that inserts the BWAV metadata
        mediaInfoDict = createMediaInfoDict(inPath, inType, processDict, sf)

        #Transcode the File
        processVideo(inPath, processDict, sf)

        #insert ID3 tags in MP3
        insertID3(mediaInfoDict, inPath.replace(".wav","_access.mp3"))

        #remove audio metadata from CSV Metadata Dict, necessary to keep the output CSV clean
        del mediaInfoDict['audioMetaDict']
        media_info_list.append(mediaInfoDict) # Turns the dicts into lists

        # Rsync the File
        if args.r == True:
            inPathList = []
            inPathList.append(inPath)
            moveToBackup(inPathList, processDict)

        # Make the mediainfo CSV (this is taken out for now, but maybe i'll put it back in later)
        quit()


    # If we are processing an entire directory file
    elif inType == "D":
        print(bcolors.OKBLUE + "Processing Input Directory: " + os.path.dirname(inPath) + "\n\n" + bcolors.ENDC)

        #Set path of output csv file (took this part out for now, but might put it back later)
        #if out_path == "":
        #    csv_path = inPath + "/" + csv_name
        #else:
        #    csv_path = out_path
        #print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)


        # Need this part to get the number of WAV files.
        wavCount = 0
        for root, directories, filenames in os.walk(inPath):
            for filename in filenames:
                tempFilePath = os.path.join(root,filename)
                if tempFilePath.endswith('.wav') and not tempFilePath.endswith('_mezzanine.wav') and not filename.startswith('.'):
                    wavCount = wavCount + 1

        #now we walk through the directory to process each file
        for root, directories, filenames in os.walk(inPath):
            fileNum = 0
            inPathList = []
            for filename in filenames:
                #Process the file
                tempFilePath = os.path.join(root,filename)
                #Process as Audio
                if tempFilePath.endswith('.wav') and not tempFilePath.endswith('_mezzanine.wav') and not filename.startswith('.'):
                    #Harvest mediainfo metadata, there is a subprocess in this script that inserts the BWAV metadata
                    mediaInfoDict = createMediaInfoDict(tempFilePath, inType, processDict, sf)

                    #Transcode the file
                    processVideo(tempFilePath, processDict, sf)

                    #Insert ID3 metadata into MP3
                    insertID3(mediaInfoDict, tempFilePath.replace(".wav","_access.mp3"))

                    #remove audio metadata from CSV Metadata Dict
                    del mediaInfoDict['audioMetaDict']
                    media_info_list.append(mediaInfoDict) # Turns the dicts into lists

                    # Add to the list of paths to be rsynced
                    inPathList.append(tempFilePath)
                    fileNum += 1

                    print(bcolors.OKBLUE + "Done!\n" + bcolors.ENDC)

                    #create CSV
                    #print(bcolors.OKGREEN + "DONE! Creating CSV File " + "\n\n" + bcolors.ENDC)
                    #createCSV(media_info_list,csv_path)	# this instances process the big list of dicts

        # Rsync the Files that were trasncoded
        if args.r == True:
            moveToBackup(inPathList, processDict)

        quit()


# Determine whether input is a file or a Directory, returns F or D respectively, quits otherwise
def fileOrDir(inPath):
    if os.path.isdir(inPath):
        return "D"
    elif os.path.isfile(inPath):
        return "F"
    else:
        print("I couldn't determine or find the input type!")
        quit()

#Process a single file
def createMediaInfoDict(filePath, inType, processDict, sf):
    media_info_text = getMediaInfo(filePath)
    media_info_dict = parseMediaInfo(filePath, media_info_text, processDict['hashType'], processDict['sidecar'], processDict['masterExtension'], sf)
    return media_info_dict

#gets the Mediainfo text
def getMediaInfo(filePath):
    print(bcolors.OKGREEN + "Running Mediainfo and Checksums (If Selected)\n\n" + bcolors.ENDC)
    cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=OLDXML', filePath ]
    media_info_xml = subprocess.Popen( cmd, stdout=subprocess.PIPE ).communicate()[0]
    return media_info_xml.decode('utf-8')

#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text, hashType, sidecar, masterExtension, sf):
    # The following line initializes the dict.
    file_dict = {"Name" : "", \
    "instantiationIdentifierDigital__c" : "", \
    "essenceTrackDuration__c" : "", \
    "instantiationFileSize__c" : "", \
    "instantiationDigital__c" : "", \
    "instantiationDataRateAudio__c" : "", \
    "essenceTrackBitDepthAudio__c" : "", \
    "essenceTrackSamplingRate__c" : "", \
    "essenceTrackEncodingAudio__c" : "", \
    "instantiationChannelConfigDigitalLayout__c" : "", \
    "instantiationChannelConfigurationDigital__c" : "",
    "messageDigest" : "", \
    "messageDigestAlgorithm" : "", \
    "audioMetaDict" : {}}
    file_dict["instantiationIdentifierDigital__c"] = os.path.basename(filePath).split(".")[0]
    barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
    try:
        barcodeTemp = str(barcodeTemp).split("_")[0]
        file_dict["Name"] = barcodeTemp.split("BAVC")[1]
    except:
        print(bcolors.FAIL + "Error parsing filename, No Barcode given for this file!\n\n")

    try:
        mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
        mi_Audio_Text = (media_info_text.split("<track type=\"Audio\">"))[1].split("</track>")[0]
    except:
        try:
            mi_Audio_Text = (media_info_text.split("<track type=\"Audio\" typeorder=\"1\">"))[1].split("</track>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse tracks for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    file_dict = getAudioMetadata(file_dict, filePath, sf)

    # General Stuff
    try:
        file_dict["essenceTrackDuration__c"] = (mi_General_Text.split("<Duration>"))[6].split("</Duration>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Duration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    try:
        fileFormatTemp = (mi_General_Text.split("<Format>"))[1].split("</Format>")[0]
        if fileFormatTemp == "Wave":
            file_dict["instantiationDigital__c"] = "WAV"

    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not File Format for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse File Size for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)


    # Audio Stuff
    try:
        file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
    except:
        try:
            file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Bit_depth>"))[1].split("</Bit_depth>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        samplingRate = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
        if samplingRate == "44100":
            samplingRate = "44.1"
        else:
            samplingRate = int(samplingRate)/1000
        file_dict["essenceTrackSamplingRate__c"] = str(samplingRate) + " kHz"
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Sampling Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Codec>"))[1].split("</Codec>")[0]
        if file_dict["essenceTrackEncodingAudio__c"] == "PCM":
            file_dict["essenceTrackEncodingAudio__c"] = "Linear PCM"
    except:
        try:
            file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Format>"))[1].split("</Format>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        audioDataRate = (mi_Audio_Text.split("<Bit_rate>"))[1].split("</Bit_rate>")[0]
        audioDataRate = int(audioDataRate)/1000
        file_dict["instantiationDataRateAudio__c"] = str(audioDataRate) + " Kbps"
    except:
        try:
            if file_dict["essenceTrackSamplingRate__c"] == "48 kHz" and file_dict["essenceTrackBitDepthAudio__c"] == "24":
                file_dict["instantiationDataRateAudio__c"] = "2304 Kbps"
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["instantiationChannelConfigurationDigital__c"] = (mi_Audio_Text.split("<Channel_s_>"))[2].split("</Channel_s_>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Configuration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["instantiationChannelConfigDigitalLayout__c"] = (mi_Audio_Text.split("<ChannelLayout>"))[1].split("</ChannelLayout>")[0]
    except:
        if file_dict["instantiationChannelConfigurationDigital__c"] == "2 channels":
            file_dict["instantiationChannelConfigDigitalLayout__c"] = "L R"
        else:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Layout for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    #This is where we insert the BWAV metadata. tag value pairs are added the medainfo dict (so we don't need to add more dicts) then rmeoved later on in the script
    insertBWAV(file_dict, filePath)

    try:
        # Checksum
        if hashType == "none":
            file_dict["messageDigest"] = ""
            file_dict["messageDigestAlgorithm"] = ""
        else:
            file_dict["messageDigest"] = hashfile(filePath, hashType, blocksize=65536)
            file_dict["messageDigestAlgorithm"] = hashType
            if sidecar == 1:
                sidecarPath = filePath + "." + hashType
                f = open(sidecarPath,'w')
                f.write(file_dict["messageDigest"])
                f.close()
    except:
        print(bcolors.FAIL + "Error creating checksum for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    return file_dict

# Create a CSV file from a dict
def createCSV(media_info_list, csv_path):
    keys = media_info_list[0].keys()
    with open(csv_path, 'wb') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(media_info_list)

# Generate checksum for the file
def hashfile(filePath, hashalg, blocksize=65536):
    afile = open(filePath,'rb')
    hasher = hashlib.new(hashalg) #grab the hashing algorithm decalred by user
    buf = afile.read(blocksize) # read the file into a buffer cause it's more efficient for big files
    while len(buf) > 0: # little loop to keep reading
        hasher.update(buf) # here's where the hash is actually generated
        buf = afile.read(blocksize) # keep reading
    return hasher.hexdigest()


# Runs the scripting. FFmpeg, QCLI
def processVideo(inPath, processDict, sf):
    processVideoCMD = createString(inPath, processDict)
    runCommand(processVideoCMD)

# Creates the string based off the inputs
def createString(inPath, processDict):

    ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -vsync 0 -i '" + inPath + "' "

    for derivCount in range(len(processDict['derivDetails'])):

        # Figure out the audio filter string, then add to the basepath
        if processDict['derivDetails'][derivCount]['audioMap'] == 1: # keep original
            audioFilterString = " "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 2: # pan left center
            audioFilterString = " -af 'pan=stereo|c0=c0|c1=c0' "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 3: # pan right center
            audioFilterString = " -af 'pan=stereo|c0=c1|c1=c1' "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 4: # sum stereo to mono
            audioFilterString = " -af 'pan=stereo|c0=c0+c1|c1=c0+c1' "
        else:
            audioFilterString = " "

        # Figure out basestring
        if processDict['derivDetails'][derivCount]['mp3Kbps'] == 1:
            mp3kpbs = "320"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 2:
            mp3kpbs = "240"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 3:
            mp3kpbs = "160"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 4:
            mp3kpbs = "128"
        else:
            mp3kpbs = "0"

        baseString = " -c:a libmp3lame -b:a " + mp3kpbs + " -write_xing 0 -ac 2 "
        processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(".wav","_access.mp3")

        ffmpeg_string = ffmpeg_string + baseString + audioFilterString + " -y '" + processDict['derivDetails'][derivCount]['outPath'] + "' "

    cmd = ffmpeg_string
    return cmd


# Runs a command
def runCommand(cmd):
    print(bcolors.OKGREEN + "Running Command: " + cmd + "\n\n" + bcolors.ENDC)
    ffmpeg_out = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]
    return

# Runs the command that will move files to PresRAID via rsync
def moveToBackup(inPathList, processDict):
    if processDict['moveToPresRAID'] == 1:
        print(bcolors.OKBLUE + "Moving to PresRAID!\n\n" + bcolors.ENDC)
        inPathList_String = ""
        for i in range(len(inPathList)):
            inPathList_String = inPathList_String + "'" + inPathList[i] + "' "
            rsync_command = "rsync -avv --progress " + inPathList_String + " /Volumes/presraid/" + processDict['presRaidFolderPath']

        #runCommand(rsync_command)
        run_rsync(rsync_command)
        print(bcolors.OKBLUE + "\n\nDone!\n\n"  + bcolors.ENDC)
        return

# Allows us to see the progress of rsync (on a file-by-file basis)
def run_rsync(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(bcolors.OKGREEN + output.strip() + bcolors.ENDC)
    rc = process.poll()
    return rc

# Used to make colored text
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def querySF(sf,barcode):
    result = sf.query("SELECT messageDigest__c, Audio_Metadata_Album__c, Audio_Metadata_Artist__c, Audio_Metadata_Date__c, Audio_Metadata_Description__c, Audio_Metadata_Title__c, captureHardwareName__c, videoReproducingDevice__c FROM Preservation_Object__c WHERE Name = '" + barcode + "'")
    return result

def querySF_Inventory(sf,ID):
    result = sf.query("SELECT Name FROM Inventory__c WHERE Id = '" + ID + "'")
    return result

def getSFDataFromRecord(sf, sfData, barcode):
    sfDataDict = {"audioMD_Album" : "", \
    "audioMD_Artist" : "", \
    "audioMD_Date" : "", \
    "audioMD_Description" : "", \
    "audioMD_CaptureDeck" : "", \
    "audioMD_CaptureHardware" : "", \
    "audioMD_Title" : ""}

    sfDataDict['audioMD_Album'] = sfData["records"][0].get("Audio_Metadata_Album__c")
    sfDataDict['audioMD_Artist'] = sfData["records"][0].get("Audio_Metadata_Artist__c")
    sfDataDict['audioMD_Date'] = sfData["records"][0].get("Audio_Metadata_Date__c")
    sfDataDict['audioMD_Description'] = sfData["records"][0].get("Audio_Metadata_Description__c")
    sfDataDict['audioMD_Title'] = sfData["records"][0].get("Audio_Metadata_Title__c")
    sfDataDict['audioMD_CaptureHardware'] = sfData["records"][0].get("captureHardwareName__c")
    sfDataDict['audioMD_CaptureDeck'] = sfData["records"][0].get("videoReproducingDevice__c")
    sfDeckData = querySF_Inventory(sf,sfDataDict['audioMD_CaptureDeck'])
    sfDataDict['audioMD_CaptureDeck'] = sfDeckData["records"][0].get("Name")
    
    if sfDataDict['audioMD_Title'] == None:
        print(bcolors.FAIL + "ERROR: No Title Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_Artist'] == None:
        print(bcolors.FAIL + "ERROR: No Artist Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_Album'] == None:
        print(bcolors.FAIL + "ERROR: No Album Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_Date'] == None:
        print(bcolors.FAIL + "ERROR: No Date Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_Description'] == None:
        print(bcolors.FAIL + "ERROR: No Description Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_CaptureDeck'] == None:
        print(bcolors.FAIL + "ERROR: No Capture Deck Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)
    elif sfDataDict['audioMD_CaptureHardware'] == None:
        print(bcolors.FAIL + "ERROR: No Capture Hardware Metadata Entered for Record: " + barcode + ". Quitting Script Now\n\n" + bcolors.ENDC)

    return sfDataDict

# Get audio metadata from user
def getAudioMetadata(file_dict, filePath, sf):
    audioMetaDict = {}
    sfDataDict = {}
    filename = os.path.basename(filePath)

    sfData = querySF(sf,file_dict["Name"])
    sfDataDict = getSFDataFromRecord(sf, sfData, file_dict["Name"])

    audioMetaDict['title'] = sfDataDict['audioMD_Title']
    audioMetaDict['fullDate'] = sfDataDict['audioMD_Date']
    audioMetaDict['creationDate'] = "1969-04-20"
    audioMetaDict['artistName'] = sfDataDict['audioMD_Artist']
    audioMetaDict['yearDate'] = audioMetaDict['fullDate'][:4]
    audioMetaDict['description'] = sfDataDict['audioMD_Description']
    audioMetaDict['album'] = sfDataDict['audioMD_Album']
    audioMetaDict['captureDeck'] = sfDataDict['audioMD_CaptureDeck'].replace(" ", "_")
    audioMetaDict['captureHardware'] = sfDataDict['audioMD_CaptureHardware'].replace(" ", "_")

    file_dict['audioMetaDict'] = audioMetaDict
    return file_dict

# Inserting BWAV metadata in master audio files
def insertBWAV(file_dict, filePath):
    # Formats Descrition to "Title; Date"
    if file_dict['audioMetaDict']['fullDate'] == "" and file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = ""
    elif file_dict['audioMetaDict']['fullDate'] == "":
        bwavDescrition = file_dict['audioMetaDict']['title']
    elif file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = file_dict['audioMetaDict']['fullDate']
    else:
        bwavDescrition = file_dict['audioMetaDict']['title'] + "; " + file_dict['audioMetaDict']['fullDate'] + "; " + file_dict['audioMetaDict']['album'] + "; " + file_dict['audioMetaDict']['description']
    bwavOriginator = "BAVC"
    bwavOriginatorReference = file_dict["Name"]
    bwavOriginationDate = str(datetime.date.today())
    bwavUMID = "0000000000000000000000000000000000000000000000000000000000000000"

    if file_dict["essenceTrackSamplingRate__c"] == "96 kHz":
        codeHistSamplingRate = "96000"
    elif file_dict["essenceTrackSamplingRate__c"] == "88.2 kHz":
        codeHistSamplingRate = "88200"
    elif file_dict["essenceTrackSamplingRate__c"] == "48 kHz":
        codeHistSamplingRate = "48000"
    elif file_dict["essenceTrackSamplingRate__c"] == "44.1 kHz":
        codeHistSamplingRate = "44100"
    elif file_dict["essenceTrackSamplingRate__c"] == "192 kHz":
        codeHistSamplingRate = "192000"
    elif file_dict["essenceTrackSamplingRate__c"] == "176.4 kHz":
        codeHistSamplingRate = "176400"
    else:
        tempRate = file_dict["essenceTrackSamplingRate__c"].split(' ', 1)[0]
        tempRateFl = float(tempRate) * 1000
        codeHistSamplingRate = str(round(tempRateFl))

    bwavCodingHistory = "A=ANALOGUE,M=stereo,T=" + file_dict['audioMetaDict']['captureDeck'] + "\\nA=PCM,F=" + codeHistSamplingRate + ",W=" + file_dict["essenceTrackBitDepthAudio__c"] + ",M=stereo,T=" + file_dict['audioMetaDict']['captureHardware']


#   Pads blank space at end of coding history if the length is odd to make sure there is an even number of characters.
    codeHistLen = len(bwavCodingHistory)
    if codeHistLen % 2 != 0:
        bwavCodingHistory = bwavCodingHistory + " "

    bwfString = "bwfmetaedit --accept-nopadding --specialchars --Description='" + bwavDescrition + "' --Originator='" + bwavOriginator + "' --OriginationDate='" + bwavOriginationDate + "' --OriginatorReference='" + bwavOriginatorReference + "' --UMID='" + bwavUMID + "' --History='" + bwavCodingHistory + "' '" + filePath + "'"
    runCommand(bwfString)

# Inserting ID3 metadata in master audio files
def insertID3(file_dict, filePath):

    id3Artist = file_dict['audioMetaDict']['artistName']
    id3Title = file_dict['audioMetaDict']['title']
    id3Year = file_dict['audioMetaDict']['yearDate']
    id3Comment = file_dict['audioMetaDict']['description']
    id3Album = file_dict['audioMetaDict']['album']

    id3String = "id3v2 -a '" + id3Artist + "' -t '" + id3Title + "' -A '" + id3Album +  "' -c '" + id3Comment + "' -y '" + id3Year + "' '" + filePath + "'"
    runCommand(id3String)

# Used for seeing if a string represents an integer
def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# Creates the dict that holds all of the processing information
def createProcessDict(processDict):
    #Get number of derivatives with error catching
    userChoiceNum = input(bcolors.OKBLUE + "Please enter how many Derivatives will you be making: " + bcolors.ENDC)
    while not RepresentsInt(userChoiceNum):
        print(bcolors.FAIL + "\nIncorrect Input! Please enter a number\n" + bcolors.ENDC)
        userChoiceNum = input(bcolors.OKBLUE + "Please enter how many Derivatives will you be making: " + bcolors.ENDC)
    processDict['numDerivs'] = int(userChoiceNum)

    derivList = []

    # What to do if user selects 0 derivatives (so they just get mediainfo, qctools, presraid)
    if processDict['numDerivs'] == 0:
        processDict['derivDetails'] = "NoDerivs"

    for derivCount in range (1, (processDict.get('numDerivs') + 1)):
        derivDetails = {}
        #initialize variable
        derivDetails['mp3Kbps'] = 0
        derivDetails['wavDerivDetails'] = 0
        #Get derivative types with error catching
        userChoiceType = input(bcolors.OKBLUE + "\nWhich Codec Do You Want Derivatives " + str(derivCount) + " To Be?\n[1] MP3\n[2] WAV\n\n" + bcolors.ENDC)
        while userChoiceType not in ("1","2"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceType = input(bcolors.OKBLUE + "\n[1] MP3\n[2] WAV\n\n" + bcolors.ENDC)
        derivDetails['derivType'] = int(userChoiceType)
        #Get derivative details with error catching
        if derivDetails['derivType'] == 1:
            userChoiceKbps= input(bcolors.OKGREEN + "\nHow many kpbs would you like to make your MP3 " + str(derivCount) + "?\n[1] 320\n[2] 240\n[3] 160\n[4] 128\n\n" + bcolors.ENDC)
            derivDetails['mp3Kbps'] = int(userChoiceKbps)
            while userChoiceKbps not in ("1","2","3","4"):
                print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                userChoiceKbps = input(bcolors.OKGREEN + "\n[1] 320\n[2] 240\n[3] 160\n[4] 128\n\n" + bcolors.ENDC)
                derivDetails['mp3Kbps'] = int(userChoiceKbps)
        elif derivDetails['derivType'] == 2:
            userChoiceKbps= input(bcolors.OKGREEN + "\nWhat Sample Rate and Bit Depth combo do you want your WAV to be? " + str(derivCount) + "?\n[1] 48kHz / 24bit\n[2] 44.1kHz / 24bit\n[3] 48kHz / 16bit\n[4] 44.1kHz / 16bit\n\n" + bcolors.ENDC)
            derivDetails['wavDerivDetails'] = int(userChoiceKbps)
            while userChoiceKbps not in ("1","2","3","4"):
                print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                userChoiceKbps = input(bcolors.OKGREEN + "\n[1] 48kHz / 24bit\n[2] 44.1kHz / 24bit\n[3] 48kHz / 16bit\n[4] 44.1kHz / 16bit\n\n" + bcolors.ENDC)
                derivDetails['wavDerivDetails'] = int(userChoiceKbps)
        #Audio Mapping Options
        userChoiceAudio = input(bcolors.OKGREEN + "\nHow would you like to map the audio for Derivative " + str(derivCount) + "?\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
        while userChoiceAudio not in ("1","2","3","4"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceAudio = input(bcolors.OKGREEN + "\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
        derivDetails['audioMap'] = int(userChoiceAudio)

        #Add deriv details to deriv list
        derivList.append(derivDetails)
        processDict['derivDetails'] = derivList

    #PresRAID options
    #userChoiceRAID = input(bcolors.OKBLUE + "\nDo you want to move the file to the PresRAID?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
    #while userChoiceRAID not in ("1","2"):
    #    print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
    #    userChoiceRAID = input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
    #processDict['moveToPresRAID'] = int(userChoiceRAID)
    #if processDict['moveToPresRAID'] == 1:
        #Make sure PresRaid path exists
    #    processDict['presRaidFolderPath'] = str(input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
    #    while not os.path.isdir("/Volumes/presraid/" + processDict['presRaidFolderPath']):
    #        print(bcolors.FAIL + "\nFolder path does not exist! Please try again!" + bcolors.ENDC)
    #        processDict['presRaidFolderPath'] = str(input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
    #else:
    #    processDict['presRaidFolderPath'] = ""

    #Checksum Options
    userChoiceHash = input(bcolors.OKBLUE + "\nDo you want to create a Checksum for this file?\n[1] Yes \n[2] Yes + Sidecar \n[3] No \n\n" + bcolors.ENDC)
    while userChoiceHash not in ("1","2", "3"):
        print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
        userChoiceHash = input(bcolors.OKBLUE + "\n[1] Yes \n[2] Yes + Sidecar\n[3] No\n\n" + bcolors.ENDC)
    createHash = int(userChoiceHash)
    if createHash == 1 or createHash == 2:
        processDict['sidecar'] = createHash - 1 #Create sidecar will be 0 if no sidecar, 1 if yes sidecar
        userChoiceHashType = input(bcolors.OKGREEN + "\nWhich type of hash would you like to create?\n[1] MD5 \n[2] SHA1 \n[3] SHA256\n\n" + bcolors.ENDC)
        while userChoiceHashType not in ("1","2","3"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceHashType = raw_input(bcolors.OKGREEN + "[1] MD5 \n[2] SHA1 \n[3] SHA256\n\n" + bcolors.ENDC)
        hashNum = int(userChoiceHashType)
        if hashNum == 1:
            processDict['hashType'] = "md5"
        elif hashNum == 2:
            processDict['hashType'] = "sha1"
        elif hashNum == 3:
            processDict['hashType'] = "sha256"
        else:
            processDict['hashType'] = "none"
    else:
        processDict['hashType'] = "none"
        processDict['sidecar'] = ""
    return processDict


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
