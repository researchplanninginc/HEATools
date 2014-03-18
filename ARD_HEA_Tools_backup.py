# ---------------------------------------------------------------------------
# NAME: ARD HEA Tools.py
# Version: 2.0 (ArcGIS 10.2)
# Author: Research Planning, Inc.
#
# Description: Module containing reuseable code for ARD HEA Tool python scripts
#
# Notes:  Currently the tool is designed to only be run via the ARD HEA Toolbox.
#
# Date Created: December 11, 2012
# Date Modified: September 13, 2013
#
# ---------------------------------------------------------------------------

def version():
    text = "2.0"
    return text

def valueout (wfile, preface, content):
    import arcpy
    if content is not None and content != " ":
        arcpy.AddMessage("  " + str(preface)+ " " + str(content))
        wfile.write("  " + str(preface)+ " " + str(content) + "\n")
    else:
        arcpy.AddMessage("  " + str(preface)+ " UNKNOWN")
        wfile.write("  " + str(preface)+ " UNKNOWN\n")

def stringout (wfile, preface, content):
    import arcpy
    if content is not None:            
        arcpy.AddMessage("  " + str(preface)+ " " + content)
        wfile.write("  " + str(preface)+ " " + content + "\n")
    else:
        arcpy.AddMessage("  " + str(preface)+ " UNKNOWN")
        wfile.write("  " + str(preface)+ " UNKNOWN\n")    

def textout (wfile, content):           
    import arcpy
    arcpy.AddMessage(str(content))
    wfile.write(str(content) + "\n")

def get_process_history (directory, inputLayer):
    import arcpy
    xmlDoc = directory + "\\temp.xml"
    f = open(xmlDoc, "w")
    f.write("<metadata xml:lang=\"en\"></metadata>")
    f.close()
    arcpy.MetadataImporter_conversion(inputLayer, xmlDoc)
    f = open(xmlDoc, "r")
    mdText = f.read()
    f.close()
    start = mdText.find("<Process")
    stop = mdText.rfind("</Process>")+10
    if start != -1:
        process_history_text = mdText[start:stop]
    else:
        process_history_text = ""
    arcpy.Delete_management(xmlDoc)
    return process_history_text

def set_process_history (directory, inputLayer, process_history_text):
    import arcpy
    import string
    xmlDoc = directory + "\\temp.xml"
    newxmlDoc = directory + "\\newtemp.xml"
    f = open(xmlDoc, "w")
    f.write("<metadata xml:lang=\"en\"></metadata>")
    f.close()
    arcpy.MetadataImporter_conversion(inputLayer, xmlDoc)
    f = open(xmlDoc, "r")
    mdText = f.read()
    f.close()
    start = mdText.find("<Process")
    stop = mdText.rfind("</Process>")+10
    old = mdText[start:stop]
    if start != -1:
        newmdText = string.replace(mdText, old, process_history_text, 1)
    else:
        newmdText = mdText
    f = open(newxmlDoc, "w")
    f.write(newmdText)
    f.close()
    arcpy.MetadataImporter_conversion(newxmlDoc, inputLayer)    
    arcpy.Delete_management(xmlDoc)
    arcpy.Delete_management(newxmlDoc)

def sanitize (input):
    import string
    whitelist = string.letters + string.digits + "_"
    output = ''
    flag = 0
    for char in input:
        if char in whitelist:
            output += char
            if flag == 1:
                flag = 0
        else:
            if flag == 0:
                output += '_'
                flag = 1
            else:
                flag = 1
    if output[0] in string.digits:
        output = "N"+output
    return output.strip("_")

def sanitizetext (input):
    import string
    whitelist = string.letters + string.digits + "_"
    output = ''
    flag = 0
    for char in input:
        if char in whitelist:
            output += char
            if flag == 1:
                flag = 0
        else:
            if flag == 0:
                output += '_'
                flag = 1
            else:
                flag = 1
    return output.strip("_")

