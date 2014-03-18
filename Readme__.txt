EQUATE - NOAA ARD Habitat Equivalency Analysis Tool 
ArcGIS Toolbox Components - Version 2.0

CONTENTS
==============================================================
These files contain an ArcGIS toolbox and associated Python scripts developed for NOAA's Assessment and Response Division to allow for automated calculation of Habitat Equivalency Analyses (HEA).  These tools allow simple creation and population of an ESRI personal geodatabase intended for use in subsequent analyses via an interface in Microsoft Access.  The tools provide for simple import and visualization of the analyses conducted in Microsoft Access via ArcGIS cartographic functionality.

These tools are developed for use in ArcGIS versions 10.0, 10.1, and 10.2.


CHANGES IN THIS VERSION
==============================================================

- update to arcpy instantiation
- bug fixes

KNOWN ISSUES
=============================================================

- Changes to the way metadata are handled in XML templates between ArcGIS versions
  9.3.1 and 10.0 mean that metadata lineage handling functionality is behaving differently 
  in this version. This will be fixed in a later update.


INSTALLATION
==============================================================


1.) These files should be unzipped and placed together in a specific directory on the users computer.  

2.) Open ArcMap

3.) If upgrading from a previous version, and the toolbox is present in the ArcToolbox window, right-click on the ARD HEA Tools toolbox and select "Remove".

4.) Right-click on the background of the ArcToolbox window and select "Add Toolbox".

5.) Navigate to the directory where these files were unzipped and select the "ARD HEA Tools.tbx" file.

See tool-specific context help for additional information regarding the use of these tools to conduct analysis.

Note that the tools require the use of the metadata templates and layer files included with these scripts.  These files should NOT be moved from the directory where the toolbox and python scripts are located.