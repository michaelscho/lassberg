<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="xs"
    version="2.0" xmlns:tei="http://www.tei-c.org/ns/1.0">
    <xsl:output method="text" encoding="UTF-8"></xsl:output>

    <xsl:template match="/">
        <xsl:text>{"id": "</xsl:text>
        <xsl:apply-templates select="//tei:TEI/@xml:id"/>
        <xsl:text>", "metadata": {</xsl:text>
        <xsl:apply-templates select="//tei:sourceDesc"/>
        <xsl:apply-templates select="//tei:correspDesc"/>
        <xsl:text>}, </xsl:text>
        <xsl:apply-templates select="//tei:div[@type='original']"/>
        <xsl:text>, </xsl:text>
        <xsl:apply-templates select="//tei:div[@type='normalized']"/>
        
        <xsl:text>}</xsl:text>
    </xsl:template>
    
    <xsl:template match="//tei:sourceDesc">
        <xsl:text>"Signature": "</xsl:text>
        <xsl:apply-templates select="./tei:msDesc/tei:msIdentifier/tei:settlement"/>
        <xsl:text>, </xsl:text>
        <xsl:apply-templates select="./tei:msDesc/tei:msIdentifier/tei:repository"/>
        <xsl:text>, </xsl:text>
        <xsl:apply-templates select="./tei:msDesc/tei:msIdentifier/tei:idno[@type='signature']"/>
        <xsl:text>", "printed": "</xsl:text>
        <xsl:apply-templates select="./tei:msDesc/tei:additional/tei:surrogates/tei:bibl[@type='printed']"/>
        
        <xsl:text>",</xsl:text>
    </xsl:template>
    
    <xsl:template match="//tei:correspDesc">
        <xsl:text>"Sender": "</xsl:text>
        <xsl:apply-templates select="./tei:correspAction[@type='sent']/tei:persName"/>
        <xsl:text>", </xsl:text>
    
        <xsl:text>"Receiver": "</xsl:text>
        <xsl:apply-templates select="./tei:correspAction[@type='received']/tei:persName"/>
        <xsl:text>", </xsl:text>
        
        <xsl:text>"Date": "</xsl:text>
        <xsl:apply-templates select="./tei:correspAction[@type='sent']/tei:date"/>
        <xsl:text>", "mentioned": {"places": [</xsl:text>

        <xsl:for-each select=".//tei:note/tei:ref[@type='cmif:mentionsPlace']">
            <xsl:text>"</xsl:text>
                <xsl:value-of select="."/>
            <xsl:text>"</xsl:text>
            <xsl:if test="position() != last()">
                <xsl:text>, </xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>], "persons":[</xsl:text>
        
        <xsl:for-each select=".//tei:note/tei:ref[@type='cmif:mentionsPerson']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="."/>
            <xsl:text>"</xsl:text>
            <xsl:if test="position() != last()">
                <xsl:text>, </xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>], "literature":[</xsl:text>
        
        <xsl:for-each select=".//tei:note/tei:ref[@type='cmif:mentionsBibl']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="."/>
            <xsl:text>"</xsl:text>
            <xsl:if test="position() != last()">
                <xsl:text>, </xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>]</xsl:text>
        
        
        <xsl:text>}</xsl:text>
        
    </xsl:template>
        
    
    <xsl:template match="//tei:surrogates//tei:ref">
        <xsl:apply-templates/>
    </xsl:template>
    
    <xsl:template match="//tei:div[@type='original']">
        <xsl:text>"original": "</xsl:text>
            <xsl:apply-templates/>
        <xsl:text>"</xsl:text>
    </xsl:template>

    <xsl:template match="//tei:div[@type='normalized']">
        <xsl:text>"normalized": "</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>"</xsl:text>
    </xsl:template>
 
    <xsl:template match="//tei:body//tei:rs">
        
        <xsl:apply-templates/>
        
    </xsl:template>
    
    
    <xsl:template match="text()">
        <xsl:value-of select="replace(.,'\s+', ' ')"/>
    </xsl:template>
    

</xsl:stylesheet>