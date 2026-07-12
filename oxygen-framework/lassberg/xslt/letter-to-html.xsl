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
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"
                    rel="stylesheet"/>
                <link rel="preconnect" href="https://fonts.googleapis.com"/>
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous"/>
                <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&amp;family=Roboto:wght@400;700&amp;display=swap" rel="stylesheet"/>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"/>
                <!-- Leaflet CSS from CDN -->
                <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
                <!-- Mirador JS -->
                <script src="https://unpkg.com/mirador@latest/dist/mirador.min.js"></script>

            </head>
            <body>
                <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
                    <div class="container">
                        <a class="navbar-brand" href="../../index.html">The Laßberg Letters</a>
                        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                            <span class="navbar-toggler-icon"></span>
                        </button>
                        <div class="collapse navbar-collapse" id="navbarNav">
                            <ul class="navbar-nav ms-auto">
                                <li class="nav-item">
                                    <a class="nav-link" href="../../index.html">Welcome</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" href="../letters.html">Letters</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" href="../persons.html">Persons</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" href="../places.html">Places</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb"
                                        target="_blank">Data Analysis</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg"
                                        target="_blank">Repository</a>
                                </li>
                            </ul>
                        </div>
                    </div>
                </nav>

                <header class="page-header py-4">
                    <div class="container">
                        <h1 class="mb-2">
                            <xsl:value-of
                                select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title"/>
                        </h1>
                        <p class="lead mb-0">
                            <xsl:apply-templates select="tei:teiHeader/tei:fileDesc/tei:publicationStmt"/>
                        </p>
                    </div>
                </header>

                <main class="py-4">
                    <div class="container">
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
                        <xsl:variable name="transcriptionDiv"
                            select="(tei:text//tei:div[@type = 'original'] | tei:text//tei:div[@type = 'print'])[1]"/>
                        <section id="original-text" class="mb-4">
                            <h2>Original Text
                                <xsl:choose>
                                    <xsl:when test="$transcriptionDiv/@type = 'print'">
                                        <span class="transcription-source badge-print"
                                            title="OCR-Texterfassung aus der gedruckten Edition, siehe Metadaten/Gedruckt in">Transcribed from the printed edition (OCR)</span>
                                    </xsl:when>
                                    <xsl:when test="$transcriptionDiv/@type = 'original'">
                                        <span class="transcription-source badge-manuscript"
                                            title="Diplomatische Transkription der Handschrift">Transcribed from the manuscript (Transkribus)</span>
                                    </xsl:when>
                                    <xsl:otherwise/>
                                </xsl:choose>
                            </h2>
                            <div>
                                <xsl:apply-templates select="$transcriptionDiv"/>
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
                </main>

                <footer class="bg-dark text-white text-center py-3">
                    <div class="container">
                        <p class="mb-0"><a href="../letters.html">Back to the Letters</a></p>
                    </div>
                </footer>

                <!-- Leaflet JS from CDN -->
                <script src="https://unpkg.com/leaflet/dist/leaflet.js"/>
                <!-- Initialize the Leaflet map -->
                <script>
                    <xsl:variable name="sentPlaceName" select="//tei:correspAction[@type = 'sent']/tei:placeName"/>
                    <xsl:variable name="sentPlace" select="substring-after(//tei:correspAction[@type = 'sent']/tei:placeName/@key, '#')"/>
                    <xsl:variable name="sentPlaceCoord" select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $sentPlace]/tei:location/tei:geo/text()"/>
                    // Create the map and set its view to a default coordinate and zoom level.
                    var map = L.map('mapid', { scrollWheelZoom: false }).setView([<xsl:value-of select="normalize-space($sentPlaceCoord)"/>], 7);
                    // Muted basemap (CARTO Positron) instead of the default colourful OSM tiles,
                    // to match the edition's restrained palette.
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                    attribution: '&amp;copy; <a href="https://carto.com/attributions">CARTO</a> &amp;copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                    subdomains: 'abcd',
                    maxZoom: 19
                    }).addTo(map);

                    // Sender's place: filled circle in the edition's accent colour.
                    L.circleMarker([<xsl:value-of select="normalize-space($sentPlaceCoord)"/>], {
                    radius: 8, color: '#143761', weight: 2, fillColor: '#1d4e89', fillOpacity: 0.85
                    }).addTo(map)
                    .bindPopup('<xsl:value-of select="normalize-space($sentPlaceName)"/>')
                    .openPopup();

                    // Mentioned places: smaller, lighter circles in a secondary tone.
                    <xsl:for-each select="//tei:ref[@type = 'cmif:mentionsPlace']">
                        <xsl:variable name="mentionedPlaceName" select="./tei:rs"/>
                        <xsl:variable name="mentionedPlace" select="substring-after(./@target, '#')"/>
                        <xsl:variable name="mentionedPlaceCoord" select="document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $mentionedPlace]/tei:location/tei:geo/text()"/>

                        var popupText = "<xsl:value-of select="normalize-space($mentionedPlaceName)"/>";
                        L.circleMarker([<xsl:value-of select="normalize-space($mentionedPlaceCoord)"/>], {
                        radius: 6, color: '#8a3a91', weight: 1.5, fillColor: '#b57cc0', fillOpacity: 0.75
                        }).addTo(map)
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

    <!-- Templates for the epistolary-formula elements introduced 2026-07-10 (docs/TEI.md,
         "opener/closer/dateline/salute/signed/address"). Without these, XSLT's built-in default
         template applies to their children with no HTML wrapper, so text from a <p>, an
         <opener>, and a <closer> would all run together with no block separation. -->
    <xsl:template match="tei:p">
        <p><xsl:apply-templates/></p>
    </xsl:template>

    <xsl:template match="tei:opener">
        <div class="letter-opener"><xsl:apply-templates/></div>
    </xsl:template>

    <xsl:template match="tei:closer">
        <div class="letter-closer"><xsl:apply-templates/></div>
    </xsl:template>

    <xsl:template match="tei:address">
        <p class="letter-address"><xsl:apply-templates/></p>
    </xsl:template>

    <xsl:template match="tei:dateline">
        <p class="letter-dateline"><xsl:apply-templates/></p>
    </xsl:template>

    <xsl:template match="tei:salute">
        <p class="letter-salute"><xsl:apply-templates/></p>
    </xsl:template>

    <xsl:template match="tei:signed">
        <p class="letter-signed"><xsl:apply-templates/></p>
    </xsl:template>

    <xsl:template match="tei:postscript">
        <div class="letter-postscript"><xsl:apply-templates/></div>
    </xsl:template>

    <!-- Archival apparatus (docs/TEI.md, "Archivalische Apparate") — never the letter's own
         voice, kept visually distinct via CSS rather than blended into opener/closer/p. -->
    <xsl:template match="tei:fw">
        <div class="letter-fw"><xsl:apply-templates/></div>
    </xsl:template>

    <xsl:template match="tei:add">
        <div class="letter-add"><xsl:apply-templates/></div>
    </xsl:template>

    <!-- Manuscript-transcription line breaks (only present in type="original" divs). -->
    <xsl:template match="tei:lb">
        <br/>
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
