# ---------------------------------------------------------------------------
# NAME: InterpolateContaminantSurfaceNN.py
# Version: 2.0 (ArcGIS 10.2)
# Author: Research Planning, Inc.
#
# Usage: InterpolateContaminantSurfaceNN <input_analysis_database> <filtered_contaminant_layer> <value_field>
#   <boolean_log_transform> {cell_size} {mask_layer}
#
# Required Arguments: 
#   input_analysis_database - Name of analysis geodatabase
#   filtered_contaminant_layer - Name of filtered contaminant layer to interpolate
#   value_field - Value field to interpolate in contaminant layer
#   boolean_log_transform - Boolean flag indicating if natural log of values is performed on contaminant values
# 
# Optional Arguments:
#   {cell_size} - Size of each grid cell in resulting interpolated surface
#   {mask_layer} - Polygonal mask for resulting surface
#
# Description: Interpolates a surface from the filtered contaminant points using
#              the natural neighbor technique.
#
# Notes:  Currently the tool is designed to only be run via the ARD HEA Toolbox.
#
# Date Created: March 9, 2010
# Date Modified: March 16, 2010     - Added code to log transform values before interpolating.  Multiply values
#                                   by 1000, floor values at 1, log transform values, interpolate, and finally
#                                   back transform values
#                June 1, 2011       - Edited for Arc 10.0 functionality
#                September 15, 2012 - Additional bug fixes
#                March 7, 2014      - Converted to arcpy V2.0
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
    NNCellSize = sys.argv[5]

    # Local variables...
    desc = arcpy.Describe(COCLayer)
    scriptPath = sys.path[0]
    xmlTemp = scriptPath + "\\interpolation_metadata_template.xml"
    if desc.DataType == "FeatureLayer":
        COCLayerBase = COCLayer.split(os.sep)[-1]
    else:
        COCLayerBase = desc.Basename
    NNOut = geoDB + "\\NN_temp"
    ExpOut = geoDB + "\\Exp_NN_temp"
    maskOut = geoDB + "\\NN_mask_temp"
    NNLayer = "NN_" + COCLayerBase
    AnalysisGrid = geoDB + "\\ANALYSIS_GRID"
    COCInvent = geoDB + "\\COC_INVENTORY"
    COCLocation = desc.CatalogPath
    COCFieldString = arcpy.AddFieldDelimiters(COCLocation, COCField)
    chkString1 = COCFieldString + " <= 0"
    outRaster = geoDB + "\\NN_" + COCLayerBase
    currDir = os.path.dirname(geoDB)

    # Set the geoprocessing environment...
    env.overwriteOutput = 1
    env.snapRaster = geoDB + "\\ANALYSIS_GRID"
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

    #Process: Update contaminant inventory table and check for filtered...
    rows = arcpy.UpdateCursor(COCInvent, "[FILTER_LAYER_NAME] = '" + COCLayerBase + "'")
    row = rows.next()
    if row:
        row.INTERP_LAYER_NAME = NNLayer
        row.INTERP_TYPE = "NN"
        row.LOG_TRANSFORM = PerfLog
        rows.updateRow(row)
    else:
        raise filtered
    del row
    del rows

    # Process: Remove any previous interpolated surfaces...
    if arcpy.Exists("NN_" + COCLayerBase):
        arcpy.Delete_management("NN_" + COCLayerBase)
    if arcpy.Exists(geoDB + "\\NN_" + COCLayerBase):
        arcpy.Delete_management(geoDB + "\\NN_" + COCLayerBase)

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
        arcpy.NaturalNeighbor_sa(geoDB + "\\temp_data", COCField, NNOut, NNCellSize)        
        # arcpy.Times_sa(NNOut, AnalysisGrid, maskOut)
	# arcpy.Exp_sa(maskOut, ExpOut)
	arcpy.Exp_sa(NNOut, ExpOut)
	MARaster = arcpy.Raster(ExpOut) / 1000
	MARaster.save(outRaster)

    else:
        arcpy.AddMessage("Interpolating values...")
        arcpy.CopyFeatures_management(COCLayer, geoDB + "\\temp_data")
        arcpy.NaturalNeighbor_sa(geoDB + "\\temp_data", COCField, NNOut, NNCellSize)        
        arcpy.Times_sa(NNOut, AnalysisGrid, maskOut)
	MARaster = arcpy.Raster(maskOut) * 1
	# MARaster = arcpy.Raster(NNOut) * 1
	MARaster.save(outRaster)
    
    # Process: Capture geoprocessing history...
    history  = ARD_HEA_Tools.get_process_history(currDir, geoDB + "\\temp_data")
    if history is not None and history != "":                         
        history  = history  + ARD_HEA_Tools.get_process_history(currDir, outRaster)
    if history is not None and history != "":
        history  = history  + ARD_HEA_Tools.get_process_history(currDir, NNOut)

    # Process: Cleanup temp files.. 
    arcpy.Delete_management(geoDB + "\\temp_data")
    arcpy.Delete_management(maskOut)
    arcpy.Delete_management(NNOut)
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

    # Process: Make Feature Layers...
    arcpy.MakeRasterLayer_management(outRaster, NNLayer, "#", "#", "#")
    
    # Process: Compact database
    arcpy.Compact_management(geoDB)

except nogrid:
    arcpy.AddError("\n*** ERROR ***\nCannot interpolate without defined analysis grid.  Create analysis grid.\n")
    print "\n*** ERROR ***\nCannot interpolate without defined analysis grid.  Create analysis grid.\n"

except filtered:
    arcpy.AddError("\n*** ERROR ***\nInterpolation must be run on filtered contaminant layers\n")
    print "\n*** ERROR ***\nInterpolation must be run on filtered contaminant layers\n"

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

