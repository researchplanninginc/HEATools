# ---------------------------------------------------------------------------
# NAME: DescribeAnalysisDatabase.py
# Version: 2.0 (ArcGIS 10.2)
# Author: Research Planning, Inc.
#
# Usage: DescribeAnalysisDatabase <input_analysis_database>
#
# Required Arguments: 
#   input_analysis_database - Name of analysis geodatabase
#
# Description: Writes all attributes of a HEA analysis databse to a autodoc-like text file
#
# Notes:  Currently the tool is designed to only be run via the ARD HEA Toolbox.
#
# Date Created: November 18, 2010
# Date Modified: June 1, 2011       - Edited for Arc 10.0 functionality
#                September 15, 2012 - Changed to utilize user supplied contaminant name, Additional bug fixes
#                March 7, 2014      - converted to arcpy for V2
#                March 11, 2015     - added code to check if depth field in the SITE_ATTRIBUTES table is called "DEPTH" (legacy) or "DEPTH_ID"
#
# ---------------------------------------------------------------------------

class baddatabase(Exception):
    pass

# Import system modules
import ARD_HEA_Tools
import sys
import string
import os
import traceback
import arcpy
from arcpy import env
import datetime
import xml.etree.ElementTree as xml
from xml.dom import minidom

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")

# Load required toolboxes...
sub_folder = "ArcToolbox/Toolboxes/"
install_dir = arcpy.GetInstallInfo("desktop")['InstallDir'].replace("\\","/")
tbx_home = os.path.join(install_dir, sub_folder)
arcpy.AddToolbox(tbx_home+"Spatial Analyst Tools.tbx")
arcpy.AddToolbox(tbx_home+"Data Management Tools.tbx")
arcpy.AddToolbox(tbx_home+"Conversion Tools.tbx")

try:
    # Report version...
    ver = ARD_HEA_Tools.version()
    arcpy.AddMessage("ARD HEA Tools Version: " + ver)

    # Script arguments...
    geoDB = sys.argv[1]

    # Local variables...
    prjAttr = geoDB + "\\PROJECT_ATTRIBUTES"
    COCData = geoDB + "\\COC_DATA"
    COCInvent = geoDB + "\\COC_INVENTORY"
    SiteAttr = geoDB + "\\SITE_ATTRIBUTES"
    COCAnalysis = geoDB + "\\ANALYSIS_TABLE"
    resTbl = geoDB + "\\ANALYSIS_RESULTS"
    cutTbl = geoDB + "\\USER_THRESHOLDS"

    env.overwriteOutput = 1

    # Get date/time...
    now = datetime.datetime.now()
    nowstr = now.strftime("%Y%m%d%H%M%S")
    desc = arcpy.Describe(geoDB)
    outfile = desc.Path + "\\autodoc_" + nowstr +".txt"

    arcpy.AddMessage(outfile)
    if arcpy.Exists(outfile):
        arcpy.Delete_management(outfile)
    f = open(outfile, "w")
    
    # Check for valid analysis database...    
    if arcpy.Exists(geoDB + "\\PROJECT_ATTRIBUTES") == False:
        raise baddatabase

    # Report header... 
    ARD_HEA_Tools.textout(f, "\nSUMMARY OF HEA GIS GEODATABASE: " + geoDB)
    ARD_HEA_Tools.textout(f, "================================================================================================")
    ARD_HEA_Tools.textout(f, "CREATED ON: " + str(now))

    # Read project attribute table...
    rows = arcpy.SearchCursor(prjAttr)
    row = rows.next()
    while row:
        cell = row.CELL_SIZE
        cells = row.TOTAL_CELLS
        units = row.UNITS
        analyst = row.ANALYST
        sitehabdoc = row.SITE_HABITAT_DOC
        sitecondoc = row.SITE_CONDITION_DOC
        siteremdoc = row.SITE_REMEDIATION_DOC
        sitesubdoc = row.SITE_SUBSITE_DOC
        sitedepdoc = row.SITE_DEPTH_DOC
        row = rows.next()
    del row
    del rows

    # Report analysis grid parameters, if available...
    ARD_HEA_Tools.textout(f, "\nANALYSIS GRID:\n===============")
    if arcpy.Exists(geoDB + "\\ANALYSIS_GRID"):
        desc = arcpy.Describe(geoDB + "\\ANALYSIS_GRID")
        env.Extent = desc.Extent
        extent = desc.Extent
        spatialref = desc.SpatialReference
        ARD_HEA_Tools.valueout(f, "CELLS:", cells)
        ARD_HEA_Tools.valueout(f, "SIZE:", cell)
        ARD_HEA_Tools.valueout(f, "UNITS:", units)
        ARD_HEA_Tools.valueout(f, "ANALYST:", analyst)
        ARD_HEA_Tools.stringout(f, "PROJECTION:", spatialref.Name)
        ARD_HEA_Tools.stringout(f, "EXTENT:", str(extent.XMin) + ", " + str(extent.YMax) + ", " + str(extent.XMax) + ", " + str(extent.YMax))
        if cells >= 10000:
            ARD_HEA_Tools.textout(f, "\n")
            ARD_HEA_Tools.stringout(f, "WARNING:","When setting the cell size for this analysis, users should consider the number of contaminants \nthat will be included in the HEA as well as the number of years for extrapolating into the future. If you anticipate \nneeding more than three to five contaminants in the analysis and/or more than 100 years of analysis, it is recommended \nthat you limit the study area to less than 10,000 grid cells by either increasing the size of the grid or sub-dividing \nthe study area.")
            ARD_HEA_Tools.textout(f, "\n")
    else:
        ARD_HEA_Tools.textout(f, "\nNo valid analysis grid has been defined.\n")

    # Report loaded contaminant parameters, if available...
    ARD_HEA_Tools.textout(f, "\nCONTAMINANTS:\n===============")  
    recordcount = arcpy.GetCount_management(COCInvent)
    qmflag = 0
    if int(recordcount.getOutput(0)) > 0:
        ARD_HEA_Tools.textout(f, str(recordcount.getOutput(0)) + " LOADED CONTAMINANTS\nSEE REPORT APPENDICES FOR AVAILABLE QUERY MANAGER DOCUMENTATION.")
        rows = arcpy.SearchCursor(COCInvent)
        row = rows.next()
        count = 1        
        while row:
            filtflag = 1
            name = row.COC_NAME
            conc_units = row.COC_UNITS
            qmdoc = row.COC_QMDOC
            if qmdoc is not None:
                qmflag = 1
            if row.COC_XML is not None:
                xmlstring = "<lineage>" + row.COC_XML + "</lineage>"
                xmlfile = xml.fromstring(xmlstring)
                xmlread = minidom.parseString(xmlstring)
                xmlstring = xmlread.toprettyxml(indent = "  ")
            input_file = row.INPUT_LAYER_NAME
            filt_file = row.FILTER_LAYER_NAME
            stat = row.STAT_TYPE
            log = row.LOG_TRANSFORM
            mean_space = row.AVG_DIST
            interp_layer = row.INTERP_LAYER_NAME
            interp_type = row.INTERP_TYPE

            if filt_file is not None and arcpy.Exists(filt_file):            
                desc = arcpy.Describe(geoDB + "\\" + filt_file)
                spatialref = desc.SpatialReference
                units = desc.SpatialReference.LinearUnitName.upper()

            ARD_HEA_Tools.textout(f, "\n" + str(count) + ":" + str(name))
            ARD_HEA_Tools.valueout(f, "CONC. UNITS:", conc_units)
            ARD_HEA_Tools.valueout(f, "INPUT LAYER:", input_file)
            ARD_HEA_Tools.valueout(f, "FILTERED LAYER:", filt_file)
            ARD_HEA_Tools.valueout(f, "COINCIDENT SAMPLE HANDLING:", stat)
            ARD_HEA_Tools.valueout(f, "LOG TRANSFORM:", log)
            ARD_HEA_Tools.valueout(f, "MEAN POINT SPACING:", mean_space)
            
            if interp_layer != "":
                ARD_HEA_Tools.valueout(f, "INTERPOLATED LAYER:", interp_layer)
                ARD_HEA_Tools.valueout(f, "INTERPOLATION TYPE:", interp_type)
            else:
                ARD_HEA_Tools.valueout(f, "INTERPOLATED LAYER:", "No interpolation in HEA geodatabase.")

            ARD_HEA_Tools.stringout(f, "GEOPROCESSING HISTORY:", xmlstring)           

            count = count + 1
            row = rows.next()
        del row
        del rows
        del count
    else:
        ARD_HEA_Tools.textout(f,"\nNo contaminants have been loaded into the HEA geodatabase.\n")



    # Report loaded site attributes, if available...
    ARD_HEA_Tools.textout(f, "\nSITE ATTRIBUTES:\n===============")
    siterecordcount = arcpy.GetCount_management(SiteAttr)
    siteflag = 0
    if int(siterecordcount.getOutput(0)) > 0:
        ARD_HEA_Tools.textout(f, str("SEE REPORT APPENDICES FOR AVAILABLE SITE ATTRIBUTE SOURCE DOCUMENTATION."))
        siteflag = 1
        habList = []
        conList = []
        remList = []
        subList = []
        depList = []
        fieldList = arcpy.ListFields(SiteAttr)
        for fld in fieldList:
            if fld.name == "DEPTH_ID":
                DepthFld = "DEPTH_ID"
            elif fld.name == "DEPTH":
                DepthFld = "DEPTH"
        rows = arcpy.SearchCursor(SiteAttr)
        row = rows.next()
        while row:
            habList.append(str(row.getValue("HABITAT_ID")))
            conList.append(str(row.getValue("CONDITION_ID")))
            remList.append(str(row.getValue("REMEDIATION_ID")))
            subList.append(str(row.getValue("SUBSITE_ID")))
            depList.append(str(row.getValue(DepthFld)))
            row = rows.next()
        habSet = set(habList)
        conSet = set(conList)
        remSet = set(remList)
        subSet = set(subList)
        depSet = set(depList)
        habUnique = list(habSet)
        conUnique = list(conSet)
        remUnique = list(remSet)
        subUnique = list(subSet)
        depUnique = list(depSet)
        ARD_HEA_Tools.stringout(f,"HABITAT CODES:", str(habUnique))
        ARD_HEA_Tools.stringout(f,"CONDITION CODES:", str(conUnique))
        ARD_HEA_Tools.stringout(f,"REMEDIATION CODES:", str(remUnique))
        ARD_HEA_Tools.stringout(f,"SUBSITE CODES:", str(subUnique))
        ARD_HEA_Tools.stringout(f,"DEPTH CODES:", str(depUnique))
        del rows
        del row

    else:
        ARD_HEA_Tools.textout(f, "\nNo site attributes have been loaded into the HEA geodatabase.\n")


    # Report loaded HEA results, if available...
    ARD_HEA_Tools.textout(f, "\nHEA RESULTS:\n===============")
    if arcpy.Exists(resTbl):
        resrecordcount = arcpy.GetCount_management(resTbl)
        if int(resrecordcount.getOutput(0)) > 0:
            field = "Scenario_ID"
            valueList = []
            maxyear = 0
            rows = arcpy.SearchCursor(resTbl)
            row = rows.next()
            count = 1
            while row:
                valueList.append(row.getValue(field))
                if row.ExpYear > maxyear:
                   maxyear = row.ExpYear
                count = count + 1
                row = rows.next()
            uniqueSet = set(valueList)
            uniqueScen = list(uniqueSet)
            uniqueScen.sort()           
            del row
            del rows
            ARD_HEA_Tools.stringout(f, "MAX ANALYSIS YEAR:", str(maxyear))
            ARD_HEA_Tools.stringout(f, "SCENARIOS:", str(uniqueScen))
        else:
            ARD_HEA_Tools.textout(f, "\nNo HEA results have been loaded into HEA geodatabase.\n")
    else:
        ARD_HEA_Tools.textout(f, "\nNo HEA results have been loaded into HEA geodatabase.\n")

    # Report loaded injury cutoff results, if available...
    ARD_HEA_Tools.textout(f, "\nINJURY CUTOFFS:\n===============")
    if arcpy.Exists(cutTbl):
        resrecordcount = arcpy.GetCount_management(cutTbl)
        if int(resrecordcount.getOutput(0)) > 0:
            rows = arcpy.SearchCursor(cutTbl)
            row = rows.next()
            while row:
                scen = row.Scenario_ID
                coc = row.COC_NAME
                ah = row.Thres_A_High
                bh = row.Thres_B_High
                ch = row.Thres_C_High
                dh = row.Thres_D_High
                eh = row.Thres_E_High
                ap = row.Thres_A_Perc
                bp = row.Thres_B_Perc
                cp = row.Thres_C_Perc
                dp = row.Thres_D_Perc
                ep = row.Thres_E_Perc
                fp = row.Thres_F_Perc
                ARD_HEA_Tools.textout(f,"Scen: "+str(scen)+" Contaminant: "+str(coc)+" A: 0-"+str(ah)+": "+str(ap)+"% "+"B: "+str(ah)+"-"+str(bh)+": "+str(bp)+"% "+"B: "+str(ah)+"-"+str(bh)+": "+str(bp)+"% "               "\n")
                row = rows.next()
            del rows
            del row
        else:
            ARD_HEA_Tools.textout(f, "\nNo injury cutoffs have been loaded into HEA geodatabase.\n")
    else:
        ARD_HEA_Tools.textout(f, "\nNo injury cutoffs have been loaded into HEA geodatabase.\n")


    # Append QMDOC text, if available...
    if qmflag == 1:
        rows = arcpy.SearchCursor(COCInvent)
        row = rows.next()
        count = 1
        qmflag = 0
        while row:
            name = row.COC_NAME
            conc_units = row.COC_UNITS
            qmdoc = row.COC_QMDOC
            if qmdoc is not None:
                ARD_HEA_Tools.textout(f, "\n==========================================================\n")
                ARD_HEA_Tools.valueout(f, "QUERY MANAGER DOCUMENTATION TEXT FOR:", name)
                ARD_HEA_Tools.textout(f, str(qmdoc))
            count = count + 1
            row = rows.next()
        del row
        del rows
        del count
        
    # Append site attribute docs, if available...
    if siteflag ==1:
        if sitehabdoc is not None:
            xmlstring = sitehabdoc
            xmlfile = xml.fromstring(xmlstring)
            xmlread = minidom.parseString(xmlstring)
            xmlstring = xmlread.toprettyxml(indent = "  ")
            ARD_HEA_Tools.valueout(f, "SITE HABITAT ATTRIBUTES DOCUMENTATION:", xmlstring)
        if sitecondoc is not None:
            xmlstring = sitecondoc
            xmlfile = xml.fromstring(xmlstring)
            xmlread = minidom.parseString(xmlstring)
            xmlstring = xmlread.toprettyxml(indent = "  ")
            ARD_HEA_Tools.valueout(f, "SITE CONDITION ATTRIBUTES DOCUMENTATION:", xmlstring)
        if siteremdoc is not None:
            xmlstring = siteremdoc
            xmlfile = xml.fromstring(xmlstring)
            xmlread = minidom.parseString(xmlstring)
            xmlstring = xmlread.toprettyxml(indent = "  ")
            ARD_HEA_Tools.valueout(f, "SITE REMEDIATION ATTRIBUTES DOCUMENTATION:", xmlstring) 
        if sitesubdoc is not None:
            xmlstring = sitesubdoc
            xmlfile = xml.fromstring(xmlstring)
            xmlread = minidom.parseString(xmlstring)
            xmlstring = xmlread.toprettyxml(indent = "  ")
            ARD_HEA_Tools.valueout(f, "SUBSITE ATTRIBUTES DOCUMENTATION:", xmlstring)
        if sitedepdoc is not None:
            xmlstring = sitedepdoc
            xmlfile = xml.fromstring(xmlstring)
            xmlread = minidom.parseString(xmlstring)
            xmlstring = xmlread.toprettyxml(indent = "  ")
            ARD_HEA_Tools.valueout(f, "SITE DEPTH/ELEVATION ATTRIBUTES DOCUMENTATION:", xmlstring)         

    ARD_HEA_Tools.textout(f, "\nEND REPORT.\n")
    f.close()

except baddatabase:
        arcpy.AddError("\n*** ERROR ***\nGeodatabase does not appear to be a valid HEA geodatase.\n")
        print "\n*** ERROR ***\nGeodatabase does not appear to be a valid HEA geodatase.\n"

except arcpy.ExecuteError:
    # Get the tool error messages
    msgs = arcpy.GetMessage(0)
    msgs += arcpy.GetMessages(2)

    # Return tool error messages for use with a script tool
    arcpy.AddError(msgs)

    # Print tool error messages for use in Python/PythonWin
    print msgs
    
except:
    # Get the traceback object
    #
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    # Concatenate information together concerning the error into a message string
    #
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

    # Return python error messages for use in script tool or Python Window
    #
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)

    # Print Python error messages for use in Python / Python Window
    #
    print pymsg + "\n"
    print msgs

