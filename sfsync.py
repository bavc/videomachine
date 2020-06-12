#!/usr/local/bin/python3
#hashchecker.py

#Current Version: 1.0
#Version History
#   Old Version History is lost....
#   1.0 - 20200612
#       -Added shebang #!/usr/local/bin/python3 so that we don't need to pt python3 before the script

#######################################################################################################################
###REQUIRED LIBRARIES####
###simple_salesforce
#######################################################################################################################

import os
import time
import re
import argparse
import config
import csv
import json
from simple_salesforce import Salesforce



def getBarcode(dict):
    barcode = dict.get("Filename")[4:11] #get the barcode from the filename
    for b in barcode:
        if not b.isdigit(): #this makes sure that the barcode is 7 numbers. if not it'll throw a failure
            print("ERROR: File Barcode Not Found for " + sourceBasename)
        else:
            dict["Barcode"] = barcode
    return dict



def querySF(sf,barcode):
    result = sf.query("SELECT Id FROM Preservation_Object__c WHERE Name = '" + barcode + "'")
    return result

def initLog(sourceCSV):
    '''
    initializes log file

    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write("Load and Verify Script Started at: " + time.strftime("%Y-%m-%d_%H:%M:%S") + "\n")
    for f in sourceList:
        txtFile.write("From: " + f + "\n")
    txtFile.write("To: " + destination + "\n")
    txtFile.write("Hash algorithm: " + hashalg + "\n")
    txtFile.write("\n\n")
    txtFile.close()
    '''

def logNewLine(text,destination):
    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write("\n" + time.strftime("%Y-%m-%d_%H:%M:%S") + ": " + text)

def logSameLine(text,destination):
    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write(text)

def createDictList(inputArgs):
    dict_list = []
    for c in inputArgs:
        with open(c, mode='r') as infile:
            reader = csv.DictReader(infile)
            for line in reader:
                dict_list.append(line)
    return dict_list

def processList(dict_list,sf):
    for d in dict_list:
        #create json out of ordered dict
        dString = json.dumps(d)
        #some string magic to fix improperly named fields
        temp = dString.replace("messageDigestAlgorithm", "messageDigestAlgorithm__c")
        dString = temp.replace("\"messageDigest\"", "\"messageDigest__c\"")
        #turn the string back into a JSON sturcture
        j = json.loads(dString)
        #get the record ID of the associated salesforce record
        sfData = querySF(sf,d['Name'])
        recordID = sfData['records'][0]['Id']
        #insert the metadata!
        print(bcolors.OKBLUE +  "\nInserting Metadata for record: " + bcolors.ENDC + d['Name'])
        try:
            sf.Preservation_Object__c.update(recordID,j)
            print(bcolors.OKGREEN +  "\nSuccess!" + bcolors.ENDC)
        except:
            print(bcolors.FAIL +  "\nFailed!" + bcolors.ENDC)


def make_args():
    '''
    initialize arguments from the cli
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('sourceCSV',nargs='+',help="As many files are directories you would like processed. Only sidecar checksum files are processed.")
    return parser.parse_args()

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

def main():
    '''
    do the thing
    '''
    #init args from cli
    args = make_args()

    #init salesforce login#
    try:
        print(bcolors.OKBLUE +  "\nConnecting To Salesforce" + bcolors.ENDC)
        sf = Salesforce(username=config.username,password=config.password,security_token=config.security_token)
        print(bcolors.OKGREEN +  "\nSalesforce connection succesfull!" + bcolors.ENDC)
    except:
        print(bcolors.FAIL + "\nSalesforce Connection Failed. Quitting Script" + bcolors.ENDC)
        exit()


    #init variables

    #Check that input conforms
    if len(args.sourceCSV) < 1: #if less than two input arguments we have to exit
        print("CRITICAL ERROR: You must give this script at least one argument")
        exit()

    for c in args.sourceCSV:
        if os.path.splitext(c)[1] != ".csv":
            print("CRITICAL ERROR: This script can only accept CSV files!")
            exit()

    #Initialize log
    #initLog(args.sourceCSV)

    #Create dict list containing CSV info
    dict_list = createDictList(args.sourceCSV)

    #update the data from each CSV into Salesforce
    processList(dict_list,sf)
    print("\n")

    #tally up the success and failures, print the failed files.
    #this isn't in here yet

main()
