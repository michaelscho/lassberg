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
                                    <a class="nav-link" href="../explore.html">Explore</a>
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
                        <!-- Status banner (docs/TEI.md "Letter status model"): pages exist for
                             every encoded letter (preview tier), but only letters whose latest
                             revisionDesc status is "published" count as reviewed editions. -->
                        <xsl:variable name="latestStatus"
                            select="(/tei:TEI/tei:teiHeader/tei:revisionDesc//tei:change)[last()]/@status"/>
                        <xsl:if test="not($latestStatus = 'published')">
                            <div class="alert alert-warning letter-preview-banner" role="alert">
                                <strong>Unreviewed working text.</strong> The encoding of this letter
                                has not yet been editorially reviewed
                                (status: <xsl:value-of select="if ($latestStatus) then $latestStatus else 'draft'"/>).
                                The text may contain transcription or OCR errors &#8212; please cite with caution.
                            </div>
                        </xsl:if>

                        <div class="row g-4">
                        <!-- Sidebar: metadata, map, mentioned entities -->
                        <div class="col-lg-4 order-lg-2">
                        <aside class="letter-sidebar">

                        <!-- Metadata Section -->
                        <section id="metadata" class="mb-4">
                            <h2 class="h5">Metadata</h2>
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

                        <!-- Leaflet Map Section (hidden by the map script when no place has
                             coordinates - see the script near the end of this stylesheet) -->
                        <section id="map" class="mb-4">
                            <h2 class="h5">Places</h2>
                            <div id="mapid"/>
                            <p class="map-legend small text-muted mt-1 mb-0">
                                <span class="legend-dot" style="background:#1d4e89"/> place of sending
                                <span class="legend-dot ms-2" style="background:#b57cc0"/> places mentioned
                            </p>
                        </section>

                        <!-- Mentioned entities (from teiHeader note[type=mentioned]) -->
                        <xsl:variable name="mentionedPersons" select="//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']"/>
                        <xsl:variable name="mentionedPlaces" select="//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPlace']"/>
                        <xsl:variable name="mentionedBibl" select="//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsBibl']"/>
                        <xsl:if test="$mentionedPersons or $mentionedPlaces or $mentionedBibl">
                            <section id="mentioned" class="mb-4">
                                <h2 class="h5">Mentioned in this letter</h2>
                                <xsl:if test="$mentionedPersons">
                                    <h3 class="h6 mt-3">Persons</h3>
                                    <ul class="list-unstyled small mb-2">
                                        <xsl:for-each select="$mentionedPersons">
                                            <li>
                                                <a href="../persons.html?q={encode-for-uri(normalize-space(tei:rs))}">
                                                    <xsl:value-of select="normalize-space(tei:rs)"/>
                                                </a>
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </xsl:if>
                                <xsl:if test="$mentionedPlaces">
                                    <h3 class="h6 mt-3">Places</h3>
                                    <ul class="list-unstyled small mb-2">
                                        <xsl:for-each select="$mentionedPlaces">
                                            <li>
                                                <a href="../places.html?q={encode-for-uri(normalize-space(tei:rs))}">
                                                    <xsl:value-of select="normalize-space(tei:rs)"/>
                                                </a>
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </xsl:if>
                                <xsl:if test="$mentionedBibl">
                                    <h3 class="h6 mt-3">Literature</h3>
                                    <ul class="list-unstyled small mb-0">
                                        <xsl:for-each select="$mentionedBibl">
                                            <li class="mb-1">
                                                <xsl:value-of select="normalize-space(tei:rs)"/>
                                                <xsl:text> </xsl:text>
                                                <a href="../explore.html?node={substring-after(@target, '#')}"
                                                    title="Show in the knowledge graph" class="small">graph</a>
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </xsl:if>
                            </section>
                        </xsl:if>

                        </aside>
                        </div>

                        <!-- Main column: the letter text(s) -->
                        <div class="col-lg-8 order-lg-1">
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
                            <!-- Review provenance (docs/TEI.md "Letter status model"): show when
                                 and by whom the encoding was reviewed, if it has been. -->
                            <xsl:variable name="reviewEntry"
                                select="(/tei:TEI/tei:teiHeader/tei:revisionDesc//tei:change[@status = 'reviewed'])[last()]"/>
                            <xsl:if test="$reviewEntry">
                                <p class="text-muted small mb-2">
                                    <xsl:text>Encoding reviewed </xsl:text>
                                    <xsl:value-of select="$reviewEntry/@when"/>
                                    <xsl:if test="$reviewEntry/@who">
                                        <xsl:text> (</xsl:text>
                                        <xsl:value-of select="translate($reviewEntry/@who, '#', '')"/>
                                        <xsl:text>)</xsl:text>
                                    </xsl:if>
                                </p>
                            </xsl:if>
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
                        
                                  
                        
                        <xsl:if test="tei:text//tei:div[@type = 'normalized']">
                            <details id="normalised-text" class="text-version mb-4">
                                <summary>Normalisierter Text</summary>
                                <div>
                                    <xsl:apply-templates
                                        select="tei:text//tei:div[@type = 'normalized']"/>
                                </div>
                            </details>
                        </xsl:if>
                        <!-- Translation Section -->
                        <xsl:if test="tei:text//tei:div[@type = 'translation']">
                            <details id="translation" class="text-version mb-4">
                                <summary>Translation</summary>
                                <div>
                                    <xsl:apply-templates
                                        select="tei:text//tei:div[@type = 'translation']"/>
                                </div>
                            </details>
                        </xsl:if>
                        <!-- Related letters (filled client-side by js/related.js from the
                             precomputed embedding+graph suggestions in json/explore/related.json) -->
                        <div id="related-letters"/>
                        </div>
                        </div>
                    </div>
                </main>

                <footer class="bg-dark text-white text-center py-3">
                    <div class="container">
                        <p class="mb-0"><a href="../letters.html">Back to the Letters</a></p>
                    </div>
                </footer>

                <!-- Related-letters block (neuro-symbolic suggestions, precomputed) -->
                <script src="../../js/related.js"/>
                <!-- Leaflet JS from CDN -->
                <script src="https://unpkg.com/leaflet/dist/leaflet.js"/>
                <!-- Initialize the Leaflet map. Every marker is emitted only when its register
                     entry actually has coordinates (the old version emitted setView([], 7) for
                     letters whose place lacked coords or sat under correspAction[received] - the
                     known place-under-received quirk - which crashed the whole script and left
                     an empty map). No coordinates at all -> the map section is hidden. -->
                <script>
                    <!-- Departure place: docs/TEI.md defines placeName as the departure place
                         regardless of which correspAction wraps it, so fall back to received. -->
                    <xsl:variable name="sentPlaceName"
                        select="(//tei:correspAction[@type = 'sent']/tei:placeName,
                                 //tei:correspAction[@type = 'received']/tei:placeName)[1]"/>
                    <xsl:variable name="sentPlace" select="substring-after($sentPlaceName/@key, '#')"/>
                    <xsl:variable name="sentPlaceCoord" select="normalize-space(document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $sentPlace]/tei:location/tei:geo/text())"/>

                    <!-- Some register entries hold a "-" placeholder in <geo> (coordinates
                         unknown) - only a real "lat, lon" pair may be emitted into the JS. -->
                    <xsl:variable name="coordPattern" select="'^-?[0-9]+(\.[0-9]+)?\s*,\s*-?[0-9]+(\.[0-9]+)?$'"/>
                    var letterPlaces = [];
                    <xsl:if test="matches($sentPlaceCoord, $coordPattern)">
                    letterPlaces.push({ coords: [<xsl:value-of select="$sentPlaceCoord"/>], label: "<xsl:value-of select="normalize-space($sentPlaceName)"/>", kind: "sent" });
                    </xsl:if>
                    <xsl:for-each select="//tei:ref[@type = 'cmif:mentionsPlace']">
                        <xsl:variable name="mentionedPlace" select="substring-after(./@target, '#')"/>
                        <xsl:variable name="mentionedPlaceCoord" select="normalize-space(document('../../../data/register/lassberg-places.xml')//tei:place[@xml:id = $mentionedPlace]/tei:location/tei:geo/text())"/>
                        <xsl:if test="matches($mentionedPlaceCoord, $coordPattern) and $mentionedPlace != $sentPlace">
                    letterPlaces.push({ coords: [<xsl:value-of select="$mentionedPlaceCoord"/>], label: "<xsl:value-of select="normalize-space(./tei:rs)"/>", kind: "mentioned" });
                        </xsl:if>
                    </xsl:for-each>

                    if (letterPlaces.length === 0) {
                        document.getElementById('map').style.display = 'none';
                    } else {
                        var map = L.map('mapid', { scrollWheelZoom: false });
                        // Muted basemap (CARTO Positron) instead of the default colourful OSM
                        // tiles, to match the edition's restrained palette.
                        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                            attribution: '&amp;copy; <a href="https://carto.com/attributions">CARTO</a> &amp;copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                            subdomains: 'abcd',
                            maxZoom: 19
                        }).addTo(map);

                        var bounds = [];
                        letterPlaces.forEach(function (p) {
                            var isSent = p.kind === 'sent';
                            var marker = L.circleMarker(p.coords, isSent
                                ? { radius: 8, color: '#143761', weight: 2, fillColor: '#1d4e89', fillOpacity: 0.85 }
                                : { radius: 6, color: '#8a3a91', weight: 1.5, fillColor: '#b57cc0', fillOpacity: 0.75 }
                            ).addTo(map).bindPopup((isSent ? 'Sent from: ' : 'Mentioned: ') + p.label);
                            bounds.push(p.coords);
                        });
                        if (bounds.length > 1) {
                            map.fitBounds(bounds, { padding: [25, 25], maxZoom: 9 });
                        } else {
                            map.setView(bounds[0], 8);
                        }
                    }
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
