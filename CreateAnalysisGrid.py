# ---------------------------------------------------------------------------
# NAME: CreateAnalysisGrid.py
# Version: 2.0 (ArcGIS 10.2)
# Author: Research Planning, Inc.
#
# Usage: CreateAnalysisGrid <input_analysis_database> <extent> <cell_size> <output_coordinate_system> {mask_layer}
#
# Required Arguments: 
#   input_analysis_database - Name of analysis geodatabase
#   extent - Extent of analysis grid
#   cell_size - Size of each grid cell in analysis grid
#   output_coordinate_system - Coordinate system of analysis grid
#
# Optional Arguments:
#   mask_layer - Polygonal mask for analysis grid
#
# Description: Create analysis grid and points for anlyzing contaminant surfaces
#
# Notes:  Currently the tool is designed to only be run via the ARD HEA Toolbox.
#
# Date Created: February 3, 2010
#
# Date V 1.0 Modified: February 16, 2010  - Modified to create grid polygons
#                      March 8, 2010      - Added code to update PROJECT_ATTRIBUTE table for cell size
#                      March 9, 2010      - Added code to update PROJECT_ATTRIBUTE table for total number of cells with values
#                      March 11, 2010     - Added code to update PROJECT_ATTRIBUTE table for units of measurement
#                      November 30, 2010  - Added code to check for projected coordinate system
#                      June 1, 2011       - Edited for Arc 10.0 functionality, and changed data structure to store site attr. docs and analyst name, removed analysis poly creation
#                      September 15, 2012 - Changed to utilize user supplied contaminant name, Additional bug fixes
#
# Date V 2.0 Modified: September 17, 2013 - Changed to arcpy
# ---------------------------------------------------------------------------

class unprojected(Exception):
    pass

class toobig(Exception):
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
arcpy.AddToolbox(tbx_home+"Conversion Tools.tbx")
arcpy.AddToolbox(tbx_home+"Data Management Tools.tbx")

try:
    # Report version...
    ver = ARD_HEA_Tools.version()
    arcpy.AddMessage("ARD HEA Tools Version: " + ver)
    
    # Script arguments...
    geoDB = sys.argv[1]
    grdExtent = sys.argv[2]
    grdCellSize = sys.argv[3]
    grdCoordinateSystem = sys.argv[4]
    grdMaskLayer = sys.argv[5]

    # Check for projected coordinate system...
    env.outputCoordinateSystem = grdCoordinateSystem
    units = env.outputCoordinateSystem.linearUnitName.upper()
    if units == "":
        raise unprojected

    # Local variables...
    COCTable = geoDB + "\\COC_DATA"
    SiteAttr = geoDB + "\\SITE_ATTRIBUTES"
    AnalysisGrid = geoDB + "\\ANALYSIS_GRID"
    AnalysisPnts = geoDB + "\\ANALYSIS_PNTS"
    AnalysisGridLayer = "ANALYSIS_GRID_LYR"
    AnalysisPntsLayer = "ANALYSIS_PNTS_LYR"
    prjAttr = geoDB + "\\PROJECT_ATTRIBUTES"
    
    # Process: Delete all rows from the site attribute and contaminant raster tables
    arcpy.DeleteRows_management(COCTable)
    arcpy.DeleteRows_management(SiteAttr)

    # Process: Remove all previously generated contaminant surfaces...
    env.workspace = geoDB
    rasterList = arcpy.ListRasters("IDW_*", "GRID")
    for raster in rasterList:
        arcpy.Delete_management(raster)
        arcpy.Delete_management(geoDB + "\\" + raster)

    rasterList = arcpy.ListRasters("NN_*", "GRID")
    for raster in rasterList:
        arcpy.Delete_management(raster)
        arcpy.Delete_management(geoDB + "\\" + raster)

    # Set the geoprocessing environment...
    env.overwriteOutput = 1
    env.XYTolerance = "0.0000001"
    if grdMaskLayer <> '#':
      env.mask = grdMaskLayer

    # Make raster
    arcpy.CreateConstantRaster_sa(AnalysisGrid, "1", "INTEGER", grdCellSize, grdExtent)

    # Check size
    rowsGrid = arcpy.SearchCursor(AnalysisGrid)
    rowGrid = rowsGrid.next()
    count = rowGrid.COUNT
    del rowGrid
    del rowsGrid
    if count >= 500000:
        arcpy.AddMessage("  Warning! Cell count : "+str(count)+" is greater than 500,000 and may slow down processing")
        # raise toobig
    else:
        arcpy.AddMessage("  Cell count: "+str(count))

    # Process: Raster to Point...
    env.SnapRaster = AnalysisGrid
    arcpy.RasterToPoint_conversion(AnalysisGrid, AnalysisPnts, "VALUE")

    # Process: Add Field
    arcpy.AddField_management(AnalysisPnts, "GRID_ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    rows = arcpy.UpdateCursor(AnalysisPnts)
    row = rows.next()
    while row:
        row.GRID_ID = row.POINTID
        rows.updateRow(row)
        row = rows.next()
    del rows
    del row
    
    # Process: Delete Field
    arcpy.DeleteField_management(AnalysisPnts, "POINTID;GRID_CODE")

    #Process: Update contaminant inventory table
    desc = arcpy.Describe(AnalysisGrid)
    units = desc.SpatialReference.LinearUnitName.upper()
    rows = arcpy.UpdateCursor(prjAttr)
    row = rows.next()
    row.CELL_SIZE = grdCellSize
    row.TOTAL_CELLS = count
    row.UNITS = units 
    rows.updateRow(row)
    del row
    del rows

    if count >= 10000:
        arcpy.AddMessage("When setting the cell size for this analysis, users should consider the number of contaminants that will be included in the HEA as well as the number of years for extrapolating into the future.  If you anticipate needing more than three to five contaminants in the analysis and/or more than 100 years of analysis, it is recommended that you limit the study area to less than 10,000 grid cells by either increasing the size of the grid or sub-dividing the study area.")

    # Process: Make Feature Layers...
    arcpy.MakeFeatureLayer_management(AnalysisPnts, AnalysisPntsLayer, "", "", "")
    arcpy.MakeRasterLayer_management(AnalysisGrid, AnalysisGridLayer, "#", "#", "#")

except toobig:
    if arcpy.Exists(AnalysisGrid):
        arcpy.Delete_management(AnalysisGrid)
    if arcpy.Exists(AnalysisPnts):
        arcpy.Delete_management(AnalysisPnts)
    arcpy.AddError("\n*** ERROR ***\nCannot create analysis grid with more than 200,000 cells.\nReduce grid cell count by either increasing the size of the grid cells, using a mask, or sub-dividing the study area.\n")
    print "\n*** ERROR ***\nCannot create analysis grid with more than 200,000 cells.\n"
                
except unprojected:
    arcpy.AddError("\n*** ERROR ***\nCannot create analysis grid with an unprojected coordinate system.\n")
    print "\n*** ERROR ***\nCannot create analysis grid with an unprojected coordinate system.\nReduce grid cell count by either increasing the size of the grid cells, using a mask, or sub-dividing the study area.\n"

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
