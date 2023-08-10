<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0">
    
    <xsl:output method="xml" indent="yes"/>
    
    <!-- Match the root of the TEI document -->
    <xsl:template match="/">
        <!-- Create a root for the output -->
        <note type="mentioned">
            <!-- Iterate over each rs element within a div[type='original'] with TEI namespace -->
            <xsl:for-each select="//tei:div[@type='original']//tei:rs">
                <!-- Determine the 'ref' type based on 'rs' type -->
                <xsl:variable name="refType">
                    <xsl:choose>
                        <xsl:when test="@type='person'">cmif:mentionsPerson</xsl:when>
                        <xsl:when test="@type='place'">cmif:mentionsPlace</xsl:when>
                        <xsl:when test="@type='bibl'">cmif:mentionsBibl</xsl:when>
                        <xsl:otherwise>unknownType</xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                
                <!-- Extract the document path and the id from the key attribute -->
                <xsl:variable name="docPath" select="substring-before(@key, '#')"/>
                <xsl:variable name="docID" select="substring-after(@key, '#')"/>
                
                <!-- Open the document specified in docPath -->
                <xsl:variable name="targetDocument" select="document($docPath)"/>
                
                <!-- Define the content to be fetched based on the rs type -->
                <xsl:variable name="content">
                    <xsl:choose>
                        <xsl:when test="@type='person'">
                            <xsl:value-of select="$targetDocument//tei:person[@xml:id=$docID]/tei:persName"/>
                        </xsl:when>
                        <xsl:when test="@type='place'">
                            <xsl:value-of select="$targetDocument//tei:place[@xml:id=$docID]/tei:placeName"/>
                        </xsl:when>
                        <xsl:when test="@type='bibl'">
                            <xsl:value-of select="$targetDocument//tei:bibl[@xml:id=$docID]/tei:title"/>
                        </xsl:when>
                        <xsl:otherwise>Unknown</xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                
                <!-- Wrap each rs element with ref, setting the determined type, target attribute and the fetched content -->
                <ref type="{$refType}" target="{@key}">
                    <rs>
                        <xsl:value-of select="$content"/>
                    </rs>
                </ref>
            </xsl:for-each>
        </note>
    </xsl:template>
    
</xsl:stylesheet>
