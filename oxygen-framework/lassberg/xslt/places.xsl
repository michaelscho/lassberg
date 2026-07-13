<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="tei xs">

    <xsl:output method="html" indent="yes" doctype-system="about:legacy-compat"/>

    <xsl:param name="letters-base" select="'../../../data/letters/'"/>
    <xsl:param name="letters-register" select="'../../../data/register/lassberg-letters.xml'"/>

    <xsl:variable name="allLetters"
        select="collection(concat($letters-base, '?select=lassberg-letter-????.xml;recurse=no'))"/>
    <xsl:variable name="letterRegister" select="document($letters-register)"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Places - The Laßberg Project</title>

                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65" crossorigin="anonymous"/>
                <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" />

                <link rel="preconnect" href="https://fonts.googleapis.com"/>
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="true"/>
                <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&amp;family=Roboto:wght@400;700&amp;display=swap" rel="stylesheet"/>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"/>
                <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>

                <link href="../css/styles.css" rel="stylesheet"/>
            </head>
            <body>
                <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
                    <div class="container">
                        <a class="navbar-brand" href="../index.html">The Laßberg Letters</a>
                        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                            <span class="navbar-toggler-icon"></span>
                        </button>
                        <div class="collapse navbar-collapse" id="navbarNav">
                            <ul class="navbar-nav ms-auto">
                                <li class="nav-item"><a class="nav-link" href="../index.html">Welcome</a></li>
                                <li class="nav-item"><a class="nav-link" href="letters.html">Letters</a></li>
                                <li class="nav-item"><a class="nav-link" href="persons.html">Persons</a></li>
                                <li class="nav-item"><a class="nav-link active" href="#">Places</a></li>
                                <li class="nav-item"><a class="nav-link" href="explore.html">Explore</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb" target="_blank">Data Analysis</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg" target="_blank">Repository</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://www.zotero.org/groups/6109140/joseph_von_laberg/library" target="_blank">Literature</a></li>
                            </ul>
                        </div>
                    </div>
                </nav>

                <header class="page-header py-5 bg-light text-center">
                    <div class="container">
                        <h1 class="display-5">Places</h1>
                        <p class="lead text-muted">Every place named in the Laßberg correspondence, sized by how often it appears in a letter.</p>
                    </div>
                </header>

                <main class="py-5">
                    <div class="container">
                        <div class="card shadow-sm mb-3">
                            <div class="card-body p-0">
                                <div id="places-map"></div>
                            </div>
                        </div>

                        <div class="card shadow-sm mb-3">
                            <div class="card-body">
                                <label for="global-search" class="form-label small text-muted mb-1">Search across letters, persons, places and literature</label>
                                <input type="search" class="form-control" id="global-search" placeholder="e.g. a name, a place, a title, or a word from a letter..." autocomplete="off"/>
                                <div id="letter-search-results" class="list-group mt-2 d-none"></div>
                            </div>
                        </div>
                        <div class="card shadow-sm">
                            <div class="card-header bg-light p-3">
                                <div class="row gy-2 gx-3 align-items-center">
                                    <div class="col-lg col-md-6"><input type="text" class="form-control form-control-sm" id="filter-name" placeholder="Filter by name..."/></div>
                                    <div class="col-12 d-flex justify-content-between align-items-center pt-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="filterCheckbox"/>
                                            <label class="form-check-label" for="filterCheckbox">Show only places appearing in a letter</label>
                                        </div>
                                        <span class="text-muted small" id="filteredCounter"></span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="place-table" style="width:100%">
                                        <thead>
                                            <tr>
                                                <th scope="col" style="width: 5%;"></th>
                                                <th scope="col" style="width: 35%;">Name</th>
                                                <th scope="col" style="width: 15%;">Coordinates</th>
                                                <th scope="col" style="width: 20%;">Authority link</th>
                                                <th scope="col" style="width: 25%;">Letters</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <xsl:apply-templates select="//tei:place"/>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <div id="details-templates" class="d-none">
                            <xsl:apply-templates select="//tei:place" mode="details"/>
                        </div>
                    </div>
                </main>

                <footer class="bg-dark text-white text-center py-3">
                    <div class="container"></div>
                </footer>

                <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
                    integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"
                    crossorigin="anonymous"></script>
                <script src="https://cdn.jsdelivr.net/npm/minisearch@6.3.0/dist/umd/index.min.js"></script>
                <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
                <script src="../js/search.js"></script>
                <script src="../js/places.js"></script>

                <!-- Overview map: places.js reads each table row's data-lat/data-lon/data-count
                     attributes (below) to build one circle marker per place — building marker
                     popups from raw XPath-extracted text directly in a hand-written JS string
                     literal here would need fragile manual escaping (place names can contain
                     apostrophes), whereas letting the browser decode HTML data-attributes and
                     build the popup text in JS is safe by construction. -->
                <script>
                    var map = L.map('places-map', { scrollWheelZoom: false }).setView([47.6, 9.2], 7);
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                        attribution: '&amp;copy; <a href="https://carto.com/attributions">CARTO</a> &amp;copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                        subdomains: 'abcd', maxZoom: 19
                    }).addTo(map);
                </script>
            </body>
        </html>
    </xsl:template>

    <!-- ===== Row template ===== -->
    <xsl:template match="tei:place">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="name" select="normalize-space(tei:placeName)"/>
        <xsl:variable name="geo" select="tokenize(normalize-space(tei:location/tei:geo), ',')"/>
        <xsl:variable name="sentLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='sent']/tei:placeName/@key = $id]"/>
        <xsl:variable name="mentionedRefs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPlace'][substring-after(@target,'#') = $id]"/>
        <xsl:variable name="totalLetters" select="count($sentLetters) + count($mentionedRefs)"/>
        <xsl:variable name="cappedTotal" select="if ($totalLetters &gt; 30) then 30 else $totalLetters"/>

        <tr data-key="{$id}" data-mentions="{$totalLetters}" data-name="{$name}">
            <xsl:if test="count($geo) = 2">
                <xsl:attribute name="data-lat"><xsl:value-of select="normalize-space($geo[1])"/></xsl:attribute>
                <xsl:attribute name="data-lon"><xsl:value-of select="normalize-space($geo[2])"/></xsl:attribute>
                <xsl:attribute name="data-radius"><xsl:value-of select="5 + ($cappedTotal * 0.5)"/></xsl:attribute>
            </xsl:if>
            <td class="dt-control text-center">
                <button type="button" class="row-expand-btn" aria-label="Show place details" aria-expanded="false">
                    <i class="bi bi-chevron-down"></i>
                </button>
            </td>
            <td>
                <xsl:choose>
                    <xsl:when test="count($geo) = 2">
                        <a href="#" class="place-map-link" data-place-id="{$id}"><xsl:value-of select="$name"/></a>
                    </xsl:when>
                    <xsl:otherwise><xsl:value-of select="$name"/></xsl:otherwise>
                </xsl:choose>
            </td>
            <td>
                <xsl:choose>
                    <xsl:when test="count($geo) = 2"><i class="bi bi-geo-alt-fill text-muted"></i></xsl:when>
                    <xsl:otherwise><span class="text-muted">–</span></xsl:otherwise>
                </xsl:choose>
            </td>
            <td>
                <xsl:if test="tei:placeName/@ref and normalize-space(tei:placeName/@ref) != ''">
                    <a href="{tei:placeName/@ref}" target="_blank" rel="noopener noreferrer">Wikidata</a>
                </xsl:if>
            </td>
            <td>
                <span class="mention-badge">
                    <xsl:choose>
                        <xsl:when test="$totalLetters = 0">
                            <span class="text-muted">0 letters</span>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:if test="count($sentLetters) &gt; 0">Sent from <xsl:value-of select="count($sentLetters)"/></xsl:if>
                            <xsl:if test="count($mentionedRefs) &gt; 0"><xsl:if test="count($sentLetters) &gt; 0"> / </xsl:if>Mentioned <xsl:value-of select="count($mentionedRefs)"/></xsl:if>
                        </xsl:otherwise>
                    </xsl:choose>
                </span>
            </td>
        </tr>
    </xsl:template>

    <!-- ===== Detail template ===== -->
    <xsl:template match="tei:place" mode="details">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="name" select="normalize-space(tei:placeName)"/>
        <xsl:variable name="sentLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='sent']/tei:placeName/@key = $id]"/>
        <xsl:variable name="mentionedRefs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPlace'][substring-after(@target,'#') = $id]"/>
        <xsl:variable name="mentionedLetterIds" select="distinct-values($mentionedRefs/ancestor::tei:TEI/@xml:id)"/>
        <xsl:variable name="totalCount" select="count($sentLetters) + count($mentionedLetterIds)"/>

        <template id="details-{$id}">
            <div class="collapsible-content p-3">
                <xsl:if test="tei:desc">
                    <div class="detail-section mb-2"><span class="text-muted"><xsl:value-of select="normalize-space(tei:desc)"/></span></div>
                </xsl:if>
                <p class="small mb-2">
                    <a href="explore.html?node={$id}" class="btn btn-outline-secondary btn-sm">
                        Show network graph
                    </a>
                </p>
                <xsl:if test="@ana = 'needs-review'">
                    <div class="alert alert-warning py-2 px-3 small">This entry is still under review.
                        <xsl:if test="tei:note[@type='review']"> <xsl:value-of select="normalize-space(tei:note[@type='review'])"/></xsl:if>
                    </div>
                </xsl:if>

                <hr class="my-2"/>
                <h6>Letters</h6>
                <xsl:choose>
                    <xsl:when test="$totalCount = 0">
                        <p class="text-muted small mb-0">Not currently linked to any letter.</p>
                    </xsl:when>
                    <xsl:when test="$totalCount &gt; 40">
                        <p class="small mb-0">
                            Sent from <xsl:value-of select="count($sentLetters)"/> and mentioned in
                            <xsl:value-of select="count($mentionedLetterIds)"/> of the encoded
                            letters — too many to list here.
                            <a href="letters.html?q={encode-for-uri($name)}">Browse in the Letters register</a>.
                        </p>
                    </xsl:when>
                    <xsl:otherwise>
                        <ul class="list-unstyled mb-0 small">
                            <xsl:for-each select="$sentLetters">
                                <xsl:sort select="tei:correspAction[@type='sent']/tei:date/@when"/>
                                <xsl:call-template name="letter-detail-link">
                                    <xsl:with-param name="letterId" select="@key"/>
                                    <xsl:with-param name="role" select="'Sent from'"/>
                                </xsl:call-template>
                            </xsl:for-each>
                            <xsl:for-each select="$mentionedLetterIds">
                                <xsl:call-template name="letter-detail-link">
                                    <xsl:with-param name="letterId" select="."/>
                                    <xsl:with-param name="role" select="'Mentioned'"/>
                                </xsl:call-template>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
        </template>
    </xsl:template>

    <xsl:template name="letter-detail-link">
        <xsl:param name="letterId"/>
        <xsl:param name="role"/>
        <xsl:variable name="cd" select="$letterRegister//tei:correspDesc[@key = $letterId]"/>
        <xsl:variable name="date" select="normalize-space($cd/tei:correspAction[@type='sent']/tei:date/@when)"/>
        <li class="mb-1">
            <span class="text-muted"><xsl:value-of select="$role"/>: </span>
            <xsl:choose>
                <xsl:when test="$cd/@change = 'online'">
                    <a href="letters/{$letterId}.html" target="_blank" rel="noopener noreferrer"><xsl:value-of select="$letterId"/></a>
                </xsl:when>
                <xsl:otherwise>
                    <a href="letters.html?q={$letterId}"><xsl:value-of select="$letterId"/></a>
                </xsl:otherwise>
            </xsl:choose>
            <xsl:if test="$date != ''"> (<xsl:value-of select="$date"/>)</xsl:if>
        </li>
    </xsl:template>

</xsl:stylesheet>
