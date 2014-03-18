# ---------------------------------------------------------------------------
# NAME: InterpolateContaminantSurfaceIDW.py
# Version: 2.0 (ArcGIS 10.2)
# Author: Research Planning, Inc.
#
# Usage: InterpolateContaminantSurfaceIDW <input_analysis_database> <filtered_contaminant_layer> <value_field>
#   <boolean_log_transform> {cell_size} {power} {search_radius} {mask_layer} {barrier_lines}
#
# Required Arguments: 
#   input_analysis_database - Name of analysis geodatabase
#   filtered_contaminant_layer - Name of filtered contaminant layer to interpolate
#   value_field - Value field to interpolate in contaminant layer
#   boolean_log_transform - Boolean flag indicating if natural log of values is performed on contaminant values
# 
# Optional Arguments:
#   {cell_size} - Size of each grid cell in resulting interpolated surface
#   {power} - Control significance of surrounding points on the interpolated cell 
#   {search_radius} - Defines which surrounding points will be used to control the raster
#   {mask_layer} - Polygonal mask for resulting surface
#   {barrier_lines} - Polyline features to be used as a break or limit to searching
#
# Description: Interpolates a surface from the filtered contaminant points using inverse
#              distance wieghted technique.
#
# Notes:  Currently the tool is designed to only be run via the ARD HEA Toolbox.
#
# Date Created: February 3, 2010
# Date Modified: March 8, 2010      - Added code to update contaminant inventory table
#                                   - Error on interpolating a non-filtered layer
#                March 9, 2010      - Extent of output surface set to extent of analysis grid
#                March 16, 2010     - Added code to log transform values before interpolating.  Multiply values
#                                   by 1000, floor values at 1, log transform values, interpolate, and finally
#                                   back transform values
#                June 1, 2011       - Edited for Arc 10.0 functionality
#                September 15, 2012 - Changed to utilize user supplied contaminant name, Additional bug fixes
#                March 6, 2014      - Converted to arcpy V2.0
#
# ---------------------------------------------------------------------------

class nogrid(Exception):
    pass

class filtered(Exception):
    pass

class lognegative(Exception):
    pass

# Import system modules
import ARD_HEA_Tools
import sys
import string
import os
import traceback
import math
import arcpy
from arcpy import env

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")

# Load required toolboxes...
sub_folder = "ArcToolbox/Toolboxes/"
install_dir = arcpy.GetInstallInfo("desktop")['InstallDir'].replace("\\","/")
tbx_home = os.path.join(install_dir, sub_folder)
arcpy.AddToolbox(tbx_home+"Spatial Analyst Tools.tbx")

try:
    # Report version...
    ver = ARD_HEA_Tools.version()
    arcpy.AddMessage("ARD HEA Tools Version: " + ver)
    
    # Script arguments...
    geoDB = sys.argv[1]
    COCLayer = sys.argv[2]
    COCField = sys.argv[3]
    PerfLog = sys.argv[4]
    IDWCellSize = sys.argv[5]
    IDWPower = sys.argv[6]
    IDWRadius = sys.argv[7]
    IDWMask = sys.argv[8]
    IDWBarrier = sys.argv[9]

    # Local variables...
    desc = arcpy.Describe(COCLayer)
    scriptPath = sys.path[0]
    xmlTemp = scriptPath + "\\interpolation_metadata_template.xml"
    if desc.DataType == "FeatureLayer":
        COCLayerBase = COCLayer.split(os.sep)[-1]
    else:
        COCLayerBase = desc.Basename
    IDWOut = geoDB + "\\IDW_temp"
    ExpOut = geoDB + "\\Exp_IDW_temp"
    IDWLayer = "IDW_" + COCLayerBase
    AnalysisGrid = geoDB + "\\ANALYSIS_GRID"
    COCInvent = geoDB + "\\COC_INVENTORY"
    COCLocation = desc.CatalogPath
    COCFieldString = arcpy.AddFieldDelimiters( COCLocation, COCField)
    chkString1 = COCFieldString + " <= 0"
    outRaster = geoDB + "\\IDW_" + COCLayerBase
    currDir = os.path.dirname(geoDB)

    # Set the geoprocessing environment...
    env.overwriteOutput = 1
    env.snapRaster = geoDB + "\\ANALYSIS_GRID"
    env.mask = IDWMask
    desc = arcpy.Describe(geoDB + "\\ANALYSIS_GRID")
    env.extent = desc.Extent

    # Process: Check for analysis grid...
    if not arcpy.Exists(AnalysisGrid):
        raise nogrid

    # Process: Check for valid values used for non-detect limits...
    arcpy.MakeFeatureLayer_management(COCLayer, "templyr", str(chkString1))
    result = arcpy.GetCount_management("templyr")
    if int(str(result)) > 0:
        if PerfLog == "true":
            raise lognegative
        else:
            arcpy.AddMessage("\n*** WARNING ***\nAnalysis with negative non-detect limits may produce unexpected results\n")
    arcpy.Delete_management("templyr")
      
    # Process: Update contaminant inventory table and check for filtered...
    rows = arcpy.UpdateCursor(COCInvent, "[FILTER_LAYER_NAME] = '" + COCLayerBase + "'")
    row = rows.next()
    if row:
        row.INTERP_LAYER_NAME = IDWLayer
        row.INTERP_TYPE = "IDW"
        row.LOG_TRANSFORM = PerfLog
        rows.updateRow(row)
    else:
        raise filtered
    del row
    del rows

    # Process: Remove any previous interpolated surfaces...
    if arcpy.Exists("IDW_" + COCLayerBase):
        arcpy.Delete_management("IDW_" + COCLayerBase)
    if arcpy.Exists(geoDB + "\\IDW_" + COCLayerBase):
        arcpy.Delete_management(geoDB + "\\IDW_" + COCLayerBase)

    # Process: Check and log transform values if necessary...
    if PerfLog == "true":
        arcpy.AddMessage("Performing log transformation of contaminant values...")
        arcpy.CopyFeatures_management(COCLayer, geoDB + "\\temp_data")
        arcpy.MakeFeatureLayer_management(geoDB + "\\temp_data", "templyr")
        qryExpr = "[" + COCField + "] < 0.001"
        arcpy.SelectLayerByAttribute_management("templyr", "NEW_SELECTION", qryExpr)
        arcpy.CalculateField_management("templyr", COCField, "0", "PYTHON")
        arcpy.SelectLayerByAttribute_management("templyr", "SWITCH_SELECTION")
        lnExpr = "math.log((!" + COCField + "! * 1000))"
        arcpy.CalculateField_management("templyr", COCField, lnExpr, "PYTHON")       
        arcpy.Delete_management("templyr")
        arcpy.AddMessage("Interpolating values...")
        arcpy.Idw_sa(geoDB + "\\temp_data", COCField, IDWOut, IDWCellSize, IDWPower, IDWRadius, IDWBarrier)
	arcpy.Exp_sa(IDWOut, ExpOut)
	MARaster = arcpy.Raster(ExpOut) / 1000
	MARaster.save(outRaster)
        
    else:
        arcpy.AddMessage("Interpolating values...")
        arcpy.CopyFeatures_management(COCLayer, geoDB + "\\temp_data")
        arcpy.Idw_sa(geoDB + "\\temp_data", COCField, IDWOut, IDWCellSize, IDWPower, IDWRadius, IDWBarrier)
	MARaster = arcpy.Raster(IDWOut) * 1
	MARaster.save(outRaster)
        
    # Process: Capture geoprocessing history...
    history = ARD_HEA_Tools.get_process_history(currDir, geoDB + "\\temp_data")
    if history is not None and history != "": 
        history = history + ARD_HEA_Tools.get_process_history(currDir, IDWOut)
    
    # Process: Cleanup...    
    arcpy.Delete_management(geoDB + "\\temp_data")
    arcpy.Delete_management(IDWOut)
    arcpy.Delete_management(ExpOut)
        
    #Import metadata template
    arcpy.AddMessage("Updating metadata...")
    arcpy.ImportMetadata_conversion(xmlTemp, "FROM_FGDC", outRaster)
    # arcpy.MetadataImporter_conversion(xmlTemp, outRaster)


    #Record process step in COC Table
    if history  is not None and history  != "":
        rows = arcpy.UpdateCursor(COCInvent, "[FILTER_LAYER_NAME] = '" + COCLayerBase + "'")
        row = rows.next()
        row.COC_XML = history 
        rows.updateRow(row)
        del row
        del rows
        # Set ouptut geoprocessing history
        ARD_HEA_Tools.set_process_history (currDir, outRaster, history )

    # Process: Make Feature Layer
    arcpy.MakeRasterLayer_management(outRaster, IDWLayer, "", "", "")  

    # Process: Compact database
    arcpy.Compact_management(geoDB)

except nogrid:
    arcpy.AddError("\n*** ERROR ***\nCannot interpolate without defined analysis grid.  Create analysis grid.\n")
    print "\n*** ERROR ***\nCannot interpolate without defined analysis grid.  Create analysis grid.\n"

except filtered:
    arcpy.AddError("\n*** ERROR ***\nInterpolation must be run on filtered contaminant layers\n")
    print "Interpolation must be run on filtered contaminant layers"

except lognegative:
    arcpy.AddError("\n*** ERROR ***\nCannot perform log transformation on contaminant layer with negative values\n")
    print "\n*** ERROR ***\nCannot perform log transformation on contaminant layer with negative values\n"

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
