<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0">
    
    <!-- Output as HTML -->
    <xsl:output method="html" indent="yes"/>
    
    <!-- Main template -->
    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>The Lassberg Letters</title>
                <link href="../css/styles.css" rel="stylesheet"/>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
                <script src="../js/letters.js"></script>
            </head>
            <body>
                <div id="app" class="container">
                    <nav class="navbar navbar-dark bg-dark navbar-expand-lg">
                        <div class="container-fluid">
                            <a class="navbar-brand" href="#">Laßberg Letters</a>
                            
                                <ul class="navbar-nav">
                                    <li class="nav-item">
                                        <a class="nav-link" href="../index.html">Welcome</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" href="/lassberg/html/letters.html">Letters</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link"
                                            href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb">Data
                                            Analysis</a>
                                    </li>
                                    
                                    <li class="nav-item">
                                        <a class="nav-link" href="https://github.com/michaelscho/lassberg">Repository</a>
                                    </li>
                                </ul>
                            
                        </div>
                    </nav>
                    <div>
                        <h2 class="my-4">Register of letters</h2>
                        <p><span id="filteredCounter">0</span> letters selected.</p>
                        <p><label><input type="checkbox" id="filterCheckbox"/> Show only transcribed letters.</label></p>
                        <table class="table table-striped" id="letter-table">
                            <thead>
                                <tr>
                                    <th scope="col">
                                        Date <br/><input type="text" data-column="0" placeholder="Filter Date"/>
                                    </th>
                                    <th scope="col">
                                        From (GND) <br/><input type="text" data-column="1" placeholder="Filter From"/>
                                    </th>
                                    <th scope="col">
                                        To (GND) <br/><input type="text" data-column="2" placeholder="Filter To"/>
                                    </th>
                                    <th scope="col">
                                        Place <br/><input type="text" data-column="3" placeholder="Filter Place"/>
                                    </th>
                                    <th scope="col">
                                        Provenance <br/><input type="text" data-column="4" placeholder="Filter Provenance"/>
                                    </th>
                                    <th scope="col">Mentioned <br/><input type="text" data-column="5" placeholder="Filter Mentions"/></th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Populate the table rows here -->
                                <xsl:apply-templates select="//tei:correspDesc"/>
                            </tbody>
                        </table>
                    </div>
                </div>
                
            </body>
        </html>
    </xsl:template>
    
    <!-- Template for each correspDesc -->
    <xsl:template match="tei:correspDesc">
        <tr data-status="{@change}">
            <!-- Date -->
            <td>
                <xsl:apply-templates select="tei:correspAction[@type='sent']/tei:date"/>
            </td>
            <!-- From (GND) -->
            <td>
                <xsl:apply-templates select="tei:correspAction[@type='sent']/tei:persName"/>
            </td>
            <!-- To (GND) -->
            <td>
                <xsl:apply-templates select="tei:correspAction[@type='received']/tei:persName"/>
            </td>
            <!-- Place -->
            <td>
                <xsl:apply-templates select="tei:correspAction[@type='sent']/tei:placeName"/>
            </td>
            <!-- Provenance -->
            <td>
                <xsl:apply-templates select="tei:note[@type='aufbewahrungsort']"/>, <xsl:apply-templates select="tei:note[@type='aufbewahrungsinstitution']"/> 
            </td>

        <td>
            <!--<button class="btn btn-primary btn-sm" data-bs-toggle="collapse" data-bs-target="#{@key}-details" aria-expanded="false">Expand</button>-->
            <button class="btn btn-primary btn-sm" data-target="#{@key}-details">Expand</button>
            
            <xsl:choose>
                <xsl:when test="@change='online'">
                    <a href="/lassberg/html/letters/{@key}.html" class="btn btn-primary btn-sm" target="_blank" rel="noopener noreferrer">Open Letter</a>
                </xsl:when>
            </xsl:choose>
              
        </td>
        </tr>
        <tr class="collapse collapsible-row" id="{@key}-details">
            <td colspan="7" class="p-3">
                <div class="card">
                    <div class="card-body">

                        <div class="row">
                            <!-- Left Stack -->
                            <div class="col-md-6">
                                <div class="detail-section mb-3">
                                    <strong>Signatur: </strong>
                                    <span class="text-muted"><xsl:apply-templates select="tei:note[@type='signatur']"/></span>
                                </div>
                                <div class="detail-section mb-3">
                                    <strong>Harris: </strong>
                                    <span class="text-muted"><xsl:apply-templates select="tei:note[@type='nummer_harris']"/></span>
                                </div>
                                <div class="detail-section mb-3">
                                    <strong>Journal: </strong>
                                    <span class="text-muted"><xsl:apply-templates select="tei:note[@type='journalnummer']"/></span>
                                </div>
                            </div>
                            
                            <!-- Right Stack -->
                            <div class="col-md-6">
                                <div class="detail-section mb-3">
                                    <strong>Druck: </strong>
                                    <a href="{./tei:note[@type='published_in']/@target}">
                                        <xsl:apply-templates select="tei:note[@type='published_in']"/>
                                    </a>
                                </div>
                                <div class="detail-section mb-3">
                                    <strong>Scan: </strong>
                                    <a href="{./tei:note[@type='url_facsimile']}">
                                        <xsl:apply-templates select="tei:note[@type='url_facsimile']"/>
                                    </a>
                                </div>
                            </div>
                        </div>
                        
                        <xsl:choose>
                            <!-- If status is "online", fetch summary and additional mentions -->
                            <xsl:when test="@change='online'">
                                <div class="row mt-4">
                                    <div class="col-md-12">
                                        <strong>Zusammenfassung:</strong>
                                        <p class="text-muted">
                                            <xsl:variable name="externalSummary" select="document(concat('../../../data/letters/', @key, '.xml'))//tei:div[@type='summary']"/>
                                            <xsl:value-of select="$externalSummary"/> (Diese Zusammenfassung wurde automatisch erstellt.)
                                        </p>
                                    </div>
                                </div>
                               
                                <div class="row">
                                    <!-- Mentioned Persons -->
                                    <div class="col-md-4 mentioned-persons">
                                        <strong>Erwähnte Personen:</strong>
                                        <ul class="list-unstyled">
                                            <xsl:variable name="mentionedPersons" 
                                                select="document(concat('../../../data/letters/', @key, '.xml'))//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']"/>
                                            
                                            <!-- Iterate over each mentioned person reference -->
                                            <xsl:for-each select="$mentionedPersons">
                                                <!-- Split @target attribute into separate IDs -->
                                                <xsl:for-each select="tokenize(@target, '\s+')">
                                                    <xsl:variable name="targetId" select="substring-after(., '#')" />
                                                    <xsl:variable name="person" 
                                                        select="document('../../../data/register/lassberg-persons.xml')//tei:person[@xml:id=$targetId]  
                                                        | document('../../../data/register/lassberg-persons.xml')//tei:personGrp[@xml:id=$targetId]" />
                                                    
                                                    <li class="mb-3">
                                                        <xsl:choose>
                                                            <xsl:when test="$person">
                                                                <a href="{string($person/tei:ref[@target][1]/@target)}">
                                                                    <xsl:value-of select="$person/tei:persName[@type='main']"/>
                                                                </a>
                                                                (<xsl:value-of select="$person/@type"/>)
                                                                <xsl:if test="$person/@ref">
                                                                    <a href="{string($person/@ref)}">
                                                                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12"/>
                                                                    </a>
                                                                </xsl:if>
                                                            </xsl:when>
                                                            <xsl:otherwise>
                                                                <em>Person not found</em>
                                                            </xsl:otherwise>
                                                        </xsl:choose>
                                                    </li>
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </ul>
                                    </div>
                                </div>
                                
                                
                                <div class="col-md-4 mentioned-places">
                                    <strong>Erwähnte Orte:</strong>
                                    <ul class="list-unstyled">
                                        <xsl:variable name="mentionedPlaces" 
                                            select="document(concat('../../../data/letters/', @key, '.xml'))//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPlace']"/>
                                        <xsl:for-each select="$mentionedPlaces">
                                            <xsl:variable name="targetId" select="substring-after(@target, '#')" />
                                            <xsl:variable name="place" 
                                                select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id=$targetId]" />
                                            <li class="mb-3">
                                                <xsl:choose>
                                                    <xsl:when test="$place">
                                                        <xsl:value-of select="$place/tei:placeName"/>
                                                        <a href="{string($place/tei:placeName/@ref)}"><img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="WIKIDATA Icon" height="12"/></a>
                                                        <xsl:variable name="geo" select="tokenize($place/tei:location/tei:geo, ',')" />
                                                        <a href="https://www.openstreetmap.org/?mlat={normalize-space($geo[1])}&amp;mlon={normalize-space($geo[2])}">
                                                            Show on OSM
                                                        </a>
                                                    </xsl:when>
                                                    <xsl:otherwise>
                                                        <em>Place not found</em>
                                                    </xsl:otherwise>
                                                </xsl:choose>
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </div>
                                
                                <div class="col-md-4 mentioned-literature">
                                    <strong>Erwähnte Literatur:</strong>
                                    <ul class="list-unstyled">
                                        <xsl:variable name="mentionedLiterature" 
                                            select="document(concat('../../../data/letters/', @key, '.xml'))//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsBibl']"/>
                                        
                                        <xsl:for-each select="$mentionedLiterature">
                                            <xsl:variable name="targetId" select="substring-after(@target, '#')" />
                                            <xsl:variable name="bibl" select="document('../../../data/register/lassberg-literature.xml')//tei:bibl[@xml:id=$targetId]" />
                                            
                                            <li class="mb-3">
                                                <xsl:choose>
                                                    <xsl:when test="$bibl">
                                                        <!-- Extracting all author names -->
                                                        <xsl:variable name="authors">
                                                            <xsl:for-each select="$bibl/tei:author">
                                                                <xsl:variable name="authorRef" select="substring-after(@key, '#')"/>
                                                                <xsl:variable name="authorName" select="document('../../../data/register/lassberg-persons.xml')//tei:person[@xml:id = $authorRef]/tei:persName/text()"/>
                                                                <xsl:value-of select="$authorName"/>
                                                                <xsl:if test="position() != last()"> 
                                                                    <xsl:text>; </xsl:text> 
                                                                </xsl:if>
                                                            </xsl:for-each>
                                                        </xsl:variable>
                                                        
                                                        <xsl:if test="normalize-space($authors) != ''">
                                                            <xsl:value-of select="normalize-space($authors)"/>
                                                            <xsl:text>: </xsl:text>
                                                        </xsl:if>
                                                        
                                                        <xsl:value-of select="$bibl/tei:title"/>
                                                        <xsl:if test="not(ends-with(normalize-space($bibl/tei:title), '.'))">
                                                            <xsl:text>.</xsl:text>
                                                        </xsl:if>
                                                        
                                                        <xsl:choose>
                                                            <!-- If idno starts with 'http', make it a clickable link -->
                                                            <xsl:when test="starts-with($bibl/tei:idno, 'http')">
                                                                <a href="{$bibl/tei:idno}" target="_blank" rel="noopener noreferrer">
                                                                    <xsl:value-of select="$bibl/tei:idno"/>
                                                                </a>
                                                            </xsl:when>
                                                            <!-- Otherwise, display idno as plain text -->
                                                            <xsl:otherwise>
                                                                (<xsl:value-of select="$bibl/tei:idno"/>)
                                                            </xsl:otherwise>
                                                        </xsl:choose>
                                                    </xsl:when>
                                                    <xsl:otherwise>
                                                        <em>Literature not found</em>
                                                    </xsl:otherwise>
                                                </xsl:choose>
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </div>
                                
                                
                                
                                
                                
                                
                                
                            </xsl:when>
                            <!-- Otherwise, leave blank or provide default text -->
                            <xsl:otherwise>
                                <div class="row mt-4">
                                    <div class="col-md-12">
                                        <p class="text-muted">No additional details available.</p>
                                    </div>
                                </div>
                            </xsl:otherwise>
                        </xsl:choose>
                    </div>
                </div>
            </td>
        </tr>
        
        
    </xsl:template>
    
    <!-- Template for date
    <xsl:template match="tei:date">
        <a href="letters/{../../@key}.html">
            <xsl:value-of select="."/>
        </a>
    </xsl:template> -->
    
    <!-- Template for persName -->
    <xsl:template match="tei:persName">
        <xsl:choose>
            <!-- Check if the ana attribute exists and is not empty -->
            <xsl:when test="@ana and string-length(normalize-space(@ana)) > 0">
                <a href="{@ana}">
                    <xsl:value-of select="."/>
                </a>

            </xsl:when>
            <!-- If ana does not exist or is empty -->
            <xsl:otherwise>
                <xsl:value-of select="."/>
                <span class="ml-2">
                    <a href="{@ref}">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12"/>
                    </a>
                </span>
            </xsl:otherwise>
        </xsl:choose>
        
    </xsl:template>
    
    <!-- Template for placeName -->
    <xsl:template match="tei:placeName">  
        <xsl:value-of select="."/>
        <span><a href="{@ref}">
            <img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="WIKIDATA Icon" height="12"/>
        </a></span>
    </xsl:template>
    
    <!-- Template for notes (provenance, persons mentioned) -->
    <xsl:template match="tei:note">
        <xsl:value-of select="."/>
    </xsl:template>
    
</xsl:stylesheet>
