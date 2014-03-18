<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" >
    <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes" omit-xml-declaration="no" />

    <xsl:template match="/*">
        <results>
            <xsl:copy-of select="Esri/DataProperties/lineage"/>
        </results>
    </xsl:template>

</xsl:stylesheet>