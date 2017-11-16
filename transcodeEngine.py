#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Version History 
#	0.1.0 - 20171113
#       Got it mostly working. current known issues:
#           Can't handle non BlackMagic mediainfo files (but will fail gracefully and still make checksums)
#           Doesn't output Rsync info as it's happening
#           No logging
#   0.2.0 - 20171114
#       Will ask user for valid input if the user input doesn't match expected
#       Puts out Rsync Output
#       Throws mediainfo parsing errors by the field, rather than by the file
#       No logging, no mediainfo fixing
#   STILL NEEDS
#       Logging
#       User Verification


# import modules used here -- sys is a very standard one
import os, sys
import datetime
import csv							# used for creating the csv
import hashlib						# used for creating the md5 checksum
import subprocess                   # used for running ffmpeg, qcli, and rsync
import shlex                        # used for properly splitting the ffmpeg/rsync strings

# Gather our code in a main() function
def main():
	
	
	media_info_list = []

	#handling the input args. This is kind of a mess in this version
	if len(sys.argv) == 1:
		print "Please enter at least 1 System Argument!"
		print "System Arguement 1 should be path to file or directory to process (required)"
		print "System Arguement 2 should be output path of CSV file (optional)"
		quit()
	elif len(sys.argv) == 2:
		print "No output path defined, using default path"
		out_path = ""
	
	inPath = sys.argv[1]	
	
	processDict = {}
	processDict = createProcessDict(processDict)
	
	# This part can tell if we're processing a file or directory. Handles it accordingly	
	inType = fileOrDir(inPath)

	# If we are processing a single file
	if inType == "F":
		print bcolors.OKBLUE + "\nProcessing Input File: " + os.path.basename(inPath) + "\n\n" + bcolors.ENDC
		media_info_list.append(createMediaInfoDict(inPath, inType, processDict))
		
		# Quick little method to see if we're going to crop the file. This should eventually be its own function that does tons of pre-ffmpeg processing :->
		frameSize = media_info_list[0]['essenceTrackFrameSize__c']
		if "486" in frameSize:
		    processDict['crop'] = 1
		else:
		    processDict['crop'] = 2
        
        # FFmpeg and QCTools tthe file		    
		processVideo(inPath, processDict)
		
		# Rsync the File
		inPathList = []
		inPathList.append(inPath)
		moveToBackup(inPathList, processDict)
		
		# Make the mediainfo CSV
		if out_path == "":
			csv_path = inPath + ".mediainfo.csv"
		else:
			csv_path = out_path
		print bcolors.OKBLUE + "DONE! Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC
		createCSV(media_info_list, csv_path)	# this processes a list with a single dict in it (this is the case that only one file was given as the input)



    # If we are processing an entire directory file
	elif inType == "D":
		print bcolors.OKBLUE + "Processing Input Directory: " + os.path.dirname(inPath) + bcolors.ENDC
		if out_path == "":
			csv_path = inPath + "/mediainfo.csv"
		else:
			csv_path = sys.argv[2]
		print "Output CSV file path is: " + csv_path
		
		# Need this part to get the number of Mov files. 
		movCount = 0
		for root, directories, filenames in os.walk(inPath):
			for filename in filenames:
			    tempFilePath = os.path.join(root,filename)  		    
			    if tempFilePath.endswith('.mov') and not tempFilePath.endswith('_mezzanine.mov') and not tempFilePath.startswith('.'):
			        movCount = movCount + 1
                
		
		for root, directories, filenames in os.walk(inPath):
			fileNum = 0
			inPathList = []
			for filename in filenames:
			    #Process the file   
			    tempFilePath = os.path.join(root,filename) 
			    if tempFilePath.endswith('.mov') and not tempFilePath.endswith('_mezzanine.mov') and not tempFilePath.startswith('.'):
			        
			        media_info_list.append(createMediaInfoDict(tempFilePath, inType, processDict)) # Turns the dicts into lists
			        			        
			        frameSize = media_info_list[0]['essenceTrackFrameSize__c']
			        if "486" in frameSize:
			            processDict['crop'] = 1
			        else:
			            processDict['crop'] = 2
			        
			        # FFmpeg and QCTools the file		    
			        processVideo(tempFilePath, processDict)
			        
			        # Add to the list of paths to be rsynced
			        inPathList.append(tempFilePath)
			        fileNum += 1
			        
		            #Progress bar fun
		            #numFiles = movCount
		            #percentDone = float(float(fileIndex)/float(numFiles)*100.0)
		            #sys.stdout.write('\r')
		            #sys.stdout.write("[%-20s] %d%% %s \n" % ('='*int(percentDone/5.0), percentDone, filename))
		            #sys.stdout.flush()
		            
        print bcolors.OKBLUE + "Done!\n" + bcolors.ENDC
        # Rsync the File
        moveToBackup(inPathList, processDict)
        createCSV(media_info_list,csv_path)	# this instances process the big list of dicts
        quit()

		
# Determine whether input is a file or a Directory, returns F or D respectively, quits otherwise
def fileOrDir(inPath):
	if os.path.isdir(inPath):
		return "D"
	elif os.path.isfile(inPath):
		return "F"
	else:
		print "I couldn't determine or find the input type!"
		quit()

#Process a single file
def createMediaInfoDict(filePath, inType, processDict):
	media_info_text = getMediaInfo(filePath)
	media_info_dict = parseMediaInfo(filePath, media_info_text, processDict['hashType'])
	return media_info_dict
	
#gets the Mediainfo text
def getMediaInfo(filePath):	
	print bcolors.OKGREEN + "Running Mediainfo and Checksums (If Selected)\n\n" + bcolors.ENDC
	cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=XML', filePath ]
	media_info = subprocess.Popen( cmd, stdout=subprocess.PIPE ).communicate()[0]
	return media_info
	
#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text, hashType):
	# The following line initializes the dict. 
	file_dict = {"Name" : "", "instantiationIdentifierDigital__c" : "", "essenceTrackDuration__c" : "", "instantiationFileSize__c" : "", "instantiationDigital__c" : "", "essenceTrackEncodingVideo__c" : "", "essenceTrackBitDepthVideo__c" : "", "essenceTrackCompressionMode__c" : "", "essenceTrackScanType__c" : "", "essenceTrackFrameRate__c" : "", "essenceTrackFrameSize__c" : "", "essenceTrackAspectRatio__c" : "", "instantiationDataRateVideo__c" : "", "instantiationDigitalColorMatrix__c" : "", "instantiationDigitalColorSpace__c" : "", "instantiationDigitalChromaSubsampling__c" : "", "instantiationDataRateAudio__c" : "", "essenceTrackBitDepthAudio__c" : "", "essenceTrackSamplingRate__c" : "", "essenceTrackEncodingAudio__c" : "", "instantiationChannelConfigDigitalLayout__c" : "", "instantiationChannelConfigurationDigital__c" : "", "messageDigest" : "", "messageDigestAlgorithm" : ""}
	file_dict["instantiationIdentifierDigital__c"] = os.path.basename(filePath)
	barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
	try:
		barcodeTemp = str(barcodeTemp).split("_")[0]
		file_dict["Name"] = barcodeTemp.split("BAVC")[1]
	except:
		print bcolors.FAIL + "Error parsing filename, No Barcode given for this file!\n\n"
	
	try:
		mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
		mi_Video_Text = (media_info_text.split("<track type=\"Video\">"))[1].split("</track>")[0]
		mi_Audio_Text = (media_info_text.split("<track type=\"Audio\">"))[1].split("</track>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse tracks for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	
		# General Stuff
	
	try:	
		file_dict["essenceTrackDuration__c"] = (mi_General_Text.split("<Duration>"))[6].split("</Duration>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Duration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		fileFormatTemp = (mi_General_Text.split("<Format>"))[1].split("</Format>")[0]
		if fileFormatTemp == "MPEG-4":
		    file_dict["instantiationDigital__c"] = "MOV"
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not File Format for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse File Size for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	
		# Video Stuff
	
	try:
		file_dict["essenceTrackEncodingVideo__c"] = (mi_Video_Text.split("<Codec_ID>"))[1].split("</Codec_ID>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:	
		file_dict["essenceTrackBitDepthVideo__c"] = (mi_Video_Text.split("<Bit_depth>"))[2].split("</Bit_depth>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:	
		file_dict["essenceTrackCompressionMode__c"] = (mi_Video_Text.split("<Compression_mode>"))[1].split("</Compression_mode>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Compression Mode for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["essenceTrackScanType__c"] = (mi_Video_Text.split("<Scan_type>"))[1].split("</Scan_type>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Scan Type for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["essenceTrackFrameRate__c"] = (mi_Video_Text.split("<Frame_rate>"))[1].split("</Frame_rate>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		frame_width = (mi_Video_Text.split("<Width>"))[1].split("</Width>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Width for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		frame_height = (mi_Video_Text.split("<Height>"))[1].split("</Height>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Height for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	file_dict["essenceTrackFrameSize__c"] = frame_width + " x " + frame_height
	try:	
		file_dict["essenceTrackAspectRatio__c"] = (mi_Video_Text.split("<Display_aspect_ratio>"))[2].split("</Display_aspect_ratio>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Display Aspect Rastio for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationDataRateVideo__c"] = (mi_Video_Text.split("<Bit_rate>"))[2].split("</Bit_rate>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationDigitalColorMatrix__c"] = (mi_Video_Text.split("<Color_primaries>"))[1].split("</Color_primaries>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Matrix for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationDigitalColorSpace__c"] = (mi_Video_Text.split("<Color_space>"))[1].split("</Color_space>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Space for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationDigitalChromaSubsampling__c"] = (mi_Video_Text.split("<Chroma_subsampling>"))[1].split("</Chroma_subsampling>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Chroma Subsampling for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	    
		# Audio Stuff
	try:
		file_dict["instantiationDataRateAudio__c"] = (mi_Audio_Text.split("<Bit_rate>"))[1].split("</Bit_rate>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["essenceTrackSamplingRate__c"] = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Sampling Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Codec>"))[1].split("</Codec>")[0]
		if file_dict["essenceTrackEncodingAudio__c"] == "PCM":
			file_dict["essenceTrackEncodingAudio__c"] = "Linear PCM"
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationChannelConfigDigitalLayout__c"] = (mi_Audio_Text.split("<Channel_s_>"))[2].split("</Channel_s_>")[0]
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Layout for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	try:
		file_dict["instantiationChannelConfigurationDigital__c"] = (mi_Audio_Text.split("<ChannelLayout>"))[1].split("</ChannelLayout>")[0]	
	except:
	    print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Configuration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
	
	try:
		# Checksum
		if hashType == "none":
		    file_dict["messageDigest"] = ""
		    file_dict["messageDigestAlgorithm"] = ""
		else:
		    file_dict["messageDigest"] = hashfile(filePath, hashType, blocksize=65536)
		    file_dict["messageDigestAlgorithm"] = hashType	
	except:
		print bcolors.FAIL + "Error creating checksum for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

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
def processVideo(inPath, processDict):
    processVideoCMD = createString(inPath, processDict)
    runCommand(processVideoCMD)

# Creates the string based off the inputs
def createString(inPath, processDict):
    
    ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -vsync 0 -i '" + inPath + "' "
    
    for derivCount in range(len(processDict['derivDetails'])):
        
        # See if user opted to not crop MP4s
        
        if processDict['derivDetails'][derivCount]['frameSize'] == 2:
            processDict['crop'] = 2
        
        # Figure out the video filter string, then add to the basepath
        if processDict['crop'] == 1 and processDict['derivDetails'][derivCount]['doInterlace'] == 1: # if de-interlace and crop
            videoFilterString = " -vf crop=720:480:0:4,yadif "
        elif processDict['crop'] == 2 and processDict['derivDetails'][derivCount]['doInterlace'] == 1: # if de-interlace and no crop
            videoFilterString = " -vf yadif "
        elif processDict['crop'] == 1 and processDict['derivDetails'][derivCount]['doInterlace'] == 2: # if no de-interlace and crop
            videoFilterString = " -vf crop=720:480:0:4 "
        elif processDict['crop'] == 2 and processDict['derivDetails'][derivCount]['doInterlace'] == 2: # if no de-interlace and no crop
            videoFilterString = " "
        else:
            videoFilterString = " "
                    
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
        if processDict['derivDetails'][derivCount]['derivType'] == 1: # Basestring for H264/MP4
            baseString = " -c:v libx264 -pix_fmt yuv420p -movflags faststart -b:v 3500000 -b:a 160000 -ar 48000 -s 640x480 "
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(".mov","_access.mp4")
        if processDict['derivDetails'][derivCount]['derivType'] == 2: # Basestring for ProRes/MOV
            baseString = " -c:v prores -profile:v 3 -c:a pcm_s24le "
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(".mov","_mezzanine.mov")
        if processDict['derivDetails'][derivCount]['derivType'] == 3: # Basestring for FFv1/MKV
            baseString = " -map 0 -dn -c:v ffv1 -level 3 -coder 1 -context 1 -g 1 -slicecrc 1 -slices 24 -field_order bb -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -c:a copy "
            videoFilterString = videoFilterString.replace("-vf ", "-vf setfield=bff,setdar=4/3,")
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(".mov",".mkv")
          
        ffmpeg_string = ffmpeg_string + baseString + videoFilterString + audioFilterString + " -y '" + processDict['derivDetails'][derivCount]['outPath'] + "' "
        
    if processDict['createQCT'] == 1:
        qctString = " && qcli -i '" + inPath + "'"
    else:
        qctString = ""
        
    cmd = ffmpeg_string + qctString
    return cmd
      

# Runs a command
def runCommand(cmd):
    print bcolors.OKGREEN + "Running Command: " + cmd + "\n\n" + bcolors.ENDC
    ffmpeg_out = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]
    return

# Runs the command that will move files to PresRAID via rsync
def moveToBackup(inPathList, processDict):
    if processDict['moveToPresRAID'] == 1:
        print bcolors.OKBLUE + "Moving to PresRAID!\n\n" + bcolors.ENDC
        inPathList_String = ""
        for i in range(len(inPathList)):
            inPathList_String = inPathList_String + "'" + inPathList[i] + "' "
            rsync_command = "rsync -avv --progress " + inPathList_String + " /Volumes/presraid/" + processDict['presRaidFolderPath']
    
        #runCommand(rsync_command)    
        run_rsync(rsync_command)
        print bcolors.OKBLUE + "\n\nDone!\n\n"  + bcolors.ENDC 
        return

# Allows us to see the progress of rsync (on a file-by-file basis)
def run_rsync(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print bcolors.OKGREEN + output.strip() + bcolors.ENDC
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
	userChoiceNum = raw_input(bcolors.OKBLUE + "Please enter how many Derivatitves will you be making: " + bcolors.ENDC)
	while not RepresentsInt(userChoiceNum):
	    print bcolors.FAIL + "\nIncorrect Input! Please enter a number\n" + bcolors.ENDC
	    userChoiceNum = raw_input(bcolors.OKBLUE + "Please enter how many Derivatitves will you be making: " + bcolors.ENDC)
	processDict['numDerivs'] = int(userChoiceNum)

	derivList = []
	for derivCount in range (1, (processDict.get('numDerivs') + 1)):
	    derivDetails = {}

        #Get derivative types with error catching
	    userChoiceType = raw_input(bcolors.OKBLUE + "\nWhich Codec Do You Want Derivatives " + str(derivCount) + " To Be?\n[1] H.264/MP4\n[2] ProRes/MOV\n[3] FFv1/MKV\n[4] J2K/MXF\n\n" + bcolors.ENDC)
	    while userChoiceType not in ("1","2","3","4"):
	        print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	        userChoiceType = raw_input(bcolors.OKBLUE + "\n[1] H.264/MP4\n[2] ProRes/MOV\n[3] FFv1/MKV\n[4] J2K/MXF\n\n" + bcolors.ENDC)
	    derivDetails['derivType'] = int(userChoiceType)
        #Get derivative details with error catching
	    if derivDetails['derivType'] == 1 or derivDetails['derivType'] == 2:   
	        #Interlacing Options
	        userChoiceInterlace = raw_input(bcolors.OKGREEN + "\nDo you want to De-Interlace Derivative " + str(derivCount) + "?\n[1] De-interlace\n[2] Leave Interlaced\n\n" + bcolors.ENDC)
	        while userChoiceInterlace not in ("1","2"):
	            print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	            userChoiceInterlace = raw_input(bcolors.OKGREEN + "\n[1] De-interlace\n[2] Leave Interlaced\n\n" + bcolors.ENDC)
	        derivDetails['doInterlace'] = int(userChoiceInterlace)
	        #Audio Mapping Options
	        userChoiceAudio = raw_input(bcolors.OKGREEN + "\nHow would you like to map the audio for Derivative " + str(derivCount) + "?\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
	        while userChoiceAudio not in ("1","2","3","4"):
	            print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	            userChoiceAudio = raw_input(bcolors.OKGREEN + "\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
	        derivDetails['audioMap'] = int(userChoiceAudio)            
	    else:
	        derivDetails['doInterlace'] = 2
	        derivDetails['audioMap'] = 1
	    if derivDetails['derivType'] == 1:
	    #Frame Size Options for MP4
	        userChoiceSize = raw_input(bcolors.OKGREEN + "\nWhat frame size do you want the MP4 to be?\n[1] 640x480\n[2] 720x486\n\n" + bcolors.ENDC)
	        while userChoiceSize not in ("1","2"):
	            print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	            userChoiceSize = raw_input(bcolors.OKGREEN + "\n[1] 640x480\n[2] 720x486\n\n" + bcolors.ENDC)
	        derivDetails['frameSize'] = int(userChoiceSize)
	    else:
	        derivDetails['frameSize'] = 2
	    derivList.append(derivDetails)
	    processDict['derivDetails'] = derivList
	
	#PresRAID options
	userChoiceRAID = raw_input(bcolors.OKBLUE + "\nDo you want to move the file to the PresRAID?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	while userChoiceRAID not in ("1","2"):
	    print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	    userChoiceRAID = raw_input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	processDict['moveToPresRAID'] = int(userChoiceRAID)	
	if processDict['moveToPresRAID'] == 1:
	    #Make sure PresRaid path exists
	    processDict['presRaidFolderPath'] = str(raw_input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
	    while not os.path.isdir("/Volumes/presraid/" + processDict['presRaidFolderPath']):
	        print bcolors.FAIL + "\nFolder path does not exist! Please try again!" + bcolors.ENDC
	        processDict['presRaidFolderPath'] = str(raw_input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
	else:
	    processDict['presRaidFolderPath'] = ""
	
	#QCTools Options
	userChoiceQC = raw_input(bcolors.OKBLUE + "\nDo you want to create a QCTools Report for this file?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	while userChoiceQC not in ("1","2"):
	    print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	    userChoiceQC = raw_input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	processDict['createQCT'] = int(userChoiceQC)
	
	#Checksum Options
	userChoiceHash = raw_input(bcolors.OKBLUE + "\nDo you want to create a Checksum for this file?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	while userChoiceHash not in ("1","2"):
	    print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
	    userChoiceHash = raw_input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
	createHash = int(userChoiceHash)
	if createHash == 1:
	    userChoiceHashType = raw_input(bcolors.OKGREEN + "\nWhich type of hash would you like to create?\n[1] MD5 \n[2] SHA1 \n[3] SHA256\n\n" + bcolors.ENDC)
	    while userChoiceHashType not in ("1","2","3"):
	        print bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC
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
	return processDict


# Standard boilerplate to call the main() function to begin
# the program.	
if __name__ == '__main__':
	main()
	