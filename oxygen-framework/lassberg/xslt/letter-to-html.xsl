<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0">

    <!-- Output HTML with indentation -->
    <xsl:output method="html" indent="yes"/>

    <!-- Main template: match the root TEI element -->
    <xsl:template match="/tei:TEI">
        <html xmlns:tei="http://www.tei-c.org/ns/1.0" lang="en">
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>The Lassberg Letters</title>
                <link href="../../css/styles.css" rel="stylesheet"/>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
                    rel="stylesheet"/>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"/>
                <script src="../../js/letters.js"/>
                <!-- Leaflet CSS from CDN -->
                <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
                <!-- Mirador JS -->
                <script src="https://unpkg.com/mirador@latest/dist/mirador.min.js"></script>    
            
            </head>
            <body>
                <div id="app" class="container">
                    <nav class="navbar navbar-dark bg-dark navbar-expand-lg">
                        <div class="container-fluid">
                            <a class="navbar-brand" href="#">Laßberg Letters</a>
                            <ul class="navbar-nav">
                                <li class="nav-item">
                                    <a class="nav-link" href="../../index.html">Welcome</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" href="../letters.html">Letters</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb"
                                        >Data Analysis</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg"
                                        >Repository</a>
                                </li>
                            </ul>
                        </div>
                    </nav>

                    <div class="container my-4">
                        <!-- Header: display title and publication statement -->
                        <header class="mb-4">
                            <h1>
                                <xsl:value-of
                                    select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title"/>
                            </h1>
                            <p class="lead">
                                <xsl:apply-templates select="tei:teiHeader/tei:fileDesc/tei:publicationStmt"/>
                            </p>
                        </header>

                        <!-- Leaflet Map Section -->
                        <section id="map" class="mb-4">

                            <div id="mapid"/>
                        </section>

                        <!-- Metadata Section -->
                        <section id="metadata" class="mb-4">
                            <h2>Metadata</h2>
                            <p> <strong>Signatur: </strong> <xsl:value-of
                                select="//tei:msIdentifier/tei:settlement"/>, <xsl:value-of
                                select="//tei:msIdentifier/tei:repository"/>, <xsl:value-of
                                select="//tei:msIdentifier/tei:idno[@type = 'signature']"/> </p>
                            <p>
                                <strong>Registernummer (Laßberg): </strong>
                                <xsl:value-of
                                    select="//tei:msIdentifier/tei:idno[@type = 'register-lassberg']"
                                />
                            </p>
                            <p>
                                <strong>Registernummer (Harris): </strong>
                                <xsl:value-of
                                    select="//tei:msIdentifier/tei:idno[@type = 'register-harris']"
                                />
                            </p>

                            <p>
                                <strong>Gedruck in: </strong>
                                <a href="{//tei:additional/tei:surrogates/tei:bibl/tei:ref}">
                                    <xsl:value-of
                                        select="//tei:additional/tei:surrogates/tei:bibl/text()"/>
                                </a>
                            </p>
                        </section>
                        <!-- Original Text Section -->
                        <section id="original-text" class="mb-4">
                            <h2>Original Text</h2>
                            <div>
                                <xsl:apply-templates select="tei:text//tei:div[@type = 'original']"
                                />
                            </div>
                            
                            

                            <xsl:variable name="doc-id" select="/tei:TEI/@xml:id"/>
                                <xsl:choose>

                                    <xsl:when test="document('../../../data/register/lassberg-letters.xml')//tei:correspDesc[@key = $doc-id]/tei:note[@type='iiif_manifest']">
                                        <div class="mirador-parent">
                                            <div id="mirador-viewer"></div>
                                        </div>                                    </xsl:when>
                                    <xsl:otherwise></xsl:otherwise> <!-- Default value -->
                                </xsl:choose>
                            
                        
                        </section>
                        
                                  
                        
                        <section id="normalised-text" class="mb-4">
                            <h2>Normalisierter Text</h2>
                            <div>
                                <xsl:apply-templates
                                    select="tei:text//tei:div[@type = 'normalized']"/>
                            </div>
                        </section>
                        <!-- Translation Section -->
                        <section id="translation" class="mb-4">
                            <h2>Translation</h2>
                            <div>
                                <xsl:apply-templates
                                    select="tei:text//tei:div[@type = 'translation']"/>
                            </div>
                        </section>
                    </div>
                </div>
                <!-- Leaflet JS from CDN -->
                <script src="https://unpkg.com/leaflet/dist/leaflet.js"/>
                <!-- Initialize the Leaflet map -->
                <script>
                    <xsl:variable name="sentPlaceName" select="//tei:correspAction[@type = 'sent']/tei:placeName"/>
                    <xsl:variable name="sentPlace" select="substring-after(//tei:correspAction[@type = 'sent']/tei:placeName/@key, '#')"/>
                    <xsl:variable name="sentPlaceCoord" select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $sentPlace]/tei:location/tei:geo/text()"/>
                    // Create the map and set its view to a default coordinate and zoom level.
                    var map = L.map('mapid').setView([<xsl:value-of select="normalize-space($sentPlaceCoord)"/>], 7);
                    // Set up the OpenStreetMap tile layer.
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: 'Map data <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
                    }).addTo(map);
                    
                    
                    // Optionally add a marker at the center
                    <!--"document(concat('../../../data/letters/', @key, '.xml'))//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']"-->
                    // Define custom marker icons.
                    var mentionedIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.4/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                    });
                    
                    L.marker([<xsl:value-of select="normalize-space($sentPlaceCoord)"/>]).addTo(map)
                    .bindPopup('<xsl:value-of select="normalize-space($sentPlaceName)"/>')
                    .openPopup();
                    
                    <xsl:for-each select="//tei:ref[@type = 'cmif:mentionsPlace']">
                        <xsl:variable name="mentionedPlaceName" select="./tei:rs"/>
                        <xsl:variable name="mentionedPlace" select="substring-after(./@target, '#')"/>
                        <xsl:variable name="mentionedPlaceCoord" select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $mentionedPlace]/tei:location/tei:geo/text()"/>
                        
                        var popupText = "<xsl:value-of select="normalize-space($mentionedPlaceName)"/>";
                        L.marker([<xsl:value-of select="normalize-space($mentionedPlaceCoord)"/>], {icon: mentionedIcon}).addTo(map)
                        .bindPopup(popupText);
                    </xsl:for-each>
                    
                </script>
                <!-- Bootstrap 5 JS Bundle (includes Popper) -->
                <script>
                    // Initialize all tooltips
                    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
                    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
                    new bootstrap.Tooltip(tooltipTriggerEl)
                    })
                </script>
                
                <xsl:variable name="doc-id" select="/tei:TEI/@xml:id"/>
                <xsl:variable name="iiif-manifest" 
                    select="document('../../../data/register/lassberg-letters.xml')//tei:correspDesc[@key = $doc-id]//tei:note[@type='iiif_manifest']/text()"/>
                
                
                
                <xsl:variable name="iiif-canvas">
                    <xsl:choose>
                        <xsl:when test="document('../../../data/register/lassberg-letters.xml')//tei:correspDesc[@key = $doc-id]/tei:note[@type='iiif_canvas']">
                            <xsl:text>canvasId: "</xsl:text><xsl:value-of select="normalize-space(document('../../../data/register/lassberg-letters.xml')//tei:correspDesc[@key = $doc-id]/tei:note[@type='iiif_canvas'])"/><xsl:text>",</xsl:text>
                        </xsl:when>
                        <xsl:otherwise></xsl:otherwise> <!-- Default value -->
                    </xsl:choose>
                </xsl:variable>
                <xsl:choose>
                    <xsl:when test="$iiif-manifest">
                <script>
                    document.addEventListener('DOMContentLoaded', function () {
                    Mirador.viewer({
                    id: "mirador-viewer", // The ID of the div where Mirador will be initialized
                    windows: [
                    {
                    manifestId: "<xsl:value-of select='$iiif-manifest'/>", // Replace with your IIIF manifest file path
                    <xsl:value-of select='$iiif-canvas'/> // Opens the first canvas by default
                    viewType: "single", // Ensures single-page view mode
                    defaultView: "single"}
                    ]
                    });
                    });
                </script>
                    </xsl:when>
                    <xsl:otherwise></xsl:otherwise>
                </xsl:choose>
                
                
            </body>
        </html>
    </xsl:template>

    <!-- Template for rs elements: using an attribute value template -->
    <xsl:template match="tei:rs">
        <xsl:variable name="rsKey" select="substring-after(./@key, '#')"/>
        <xsl:variable name="rsType" select="./@type"/>
        <xsl:variable name="rsKeyText">
            <xsl:choose>
                <!-- Case for Person -->
                <xsl:when test="$rsType = 'person'">
                    <xsl:value-of select="document('../../../data/register/lassberg-persons.xml')//tei:person[@xml:id = $rsKey]/tei:persName/text()"/>
                </xsl:when>
                
                <!-- Case for Place -->
                <xsl:when test="$rsType = 'place'">
                    <xsl:value-of select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $rsKey]/tei:placeName/text()"/>
                </xsl:when>
                
                <xsl:when test="$rsType = 'bibl'">
                    <xsl:variable name="authors">
                        <xsl:for-each select="document('../../../data/register/lassberg-literature.xml')//tei:bibl[@xml:id = $rsKey]/tei:author">
                            <xsl:variable name="authorRef" select="substring-after(@key, '#')"/>
                            <xsl:variable name="authorName" select="document('../../../data/register/lassberg-persons.xml')//tei:person[@xml:id = $authorRef]/tei:persName/text()"/>
                            <xsl:value-of select="$authorName"/>
                            <xsl:if test="position() != last()"> 
                                <xsl:text>; </xsl:text> 
                            </xsl:if>
                        </xsl:for-each>
                    </xsl:variable>
                    
                    <xsl:variable name="title" select="document('../../../data/register/lassberg-literature.xml')//tei:bibl[@xml:id = $rsKey]/tei:title"/>
                    
                    <xsl:if test="normalize-space($authors) != ''">
                        <xsl:value-of select="normalize-space($authors)"/>
                        <xsl:text>: </xsl:text>
                    </xsl:if>
                    
                    <xsl:value-of select="$title"/>
                    
                    <xsl:if test="not(ends-with(normalize-space($title), '.'))">
                        <xsl:text>.</xsl:text>
                    </xsl:if>
                </xsl:when>
                
                
                
                <!-- Default case if none of the above match -->
                <xsl:otherwise>
                    <xsl:text>Unknown</xsl:text>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        
      
            
        <span class="rs-{@type}" data-bs-toggle="tooltip"
            data-bs-html="true"
            data-bs-placement="auto"
            title="&lt;strong&gt;{$rsKeyText}&lt;/strong&gt;">
            <xsl:apply-templates/>
            <xsl:variable name="rsKey" select="substring-after(./@key, '#')"/>
            <xsl:variable name="rsType" select="./@type"/>
            <xsl:choose>
                <!-- Case for Person -->
                <xsl:when test="$rsType = 'person'">
                    <a href="{document('../../../data/register/lassberg-persons.xml')//tei:person[@xml:id = $rsKey]/@ref}"><img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12"/></a>
                </xsl:when>
                
                <!-- Case for Place -->
                <xsl:when test="$rsType = 'place'">
                    <a href="{string(document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $rsKey]/tei:placeName/@ref)}"><img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="WIKIDATA Icon" height="12"/></a>
                </xsl:when>
                
                <!-- Case for Literature -->
                <xsl:when test="$rsType = 'bibl'">
                    <xsl:variable name="link" select="document('../../../data/register/lassberg-literature.xml')//tei:bibl[@xml:id = $rsKey]/tei:idno/text()"/>
                    <xsl:if test="$link">
                        <xsl:text></xsl:text>
                        <a href="{$link}">📖</a>
                        <xsl:text></xsl:text>
                    </xsl:if>
                    
                </xsl:when>
                
                <!-- Default case if none of the above match -->
                <xsl:otherwise>
                    <xsl:text></xsl:text>
                </xsl:otherwise>
            </xsl:choose>
            
            </span>
    </xsl:template>

    <xsl:template match="//tei:additional/tei:surrogates/tei:bibl/tei:ref">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="//tei:ref">
        <a>
            <xsl:if test="@target">
                <xsl:attribute name="href">
                    <xsl:value-of select="@target"/>
                </xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </a>
    </xsl:template>
    
    <xsl:template match="//tei:licence">
        <a>
            <xsl:if test="@target">
                <xsl:attribute name="href">
                    <xsl:value-of select="@target"/>
                </xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </a>
    </xsl:template>
    
    

</xsl:stylesheet>
