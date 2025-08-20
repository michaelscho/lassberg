<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0" exclude-result-prefixes="tei">

    <xsl:output method="html" indent="yes" doctype-system="about:legacy-compat"/>

    <!-- ===== Parameters for external resources (adjust paths if needed) ===== -->
    <xsl:param name="letters-base" select="'../../../data/letters/'"/>
    <xsl:param name="persons-register" select="'../../../data/register/lassberg-persons.xml'"/>
    <xsl:param name="places-register" select="'../../../data/register/lassberg-places.xml'"/>
    <xsl:param name="literature-register" select="'../../../data/register/lassberg-literature.xml'"/>

    <!-- ===== Main template (keeps your new HTML shell/UI) ===== -->
    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Register of Letters - The Laßberg Project</title>

                <!-- Bootstrap + DataTables CSS -->
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65" crossorigin="anonymous"/>
                <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" />

                <!-- Fonts & Icons -->
                <link rel="preconnect" href="https://fonts.googleapis.com"/>
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="true"/>
                <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&amp;family=Roboto:wght@400;700&amp;display=swap" rel="stylesheet"/>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"/>

                <!-- Your site styles -->
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
                                <li class="nav-item"><a class="nav-link active" href="#">Letters</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb" target="_blank">Data Analysis</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg" target="_blank">Repository</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://www.zotero.org/groups/6109140/joseph_von_laberg/library" target="_blank">Literature</a></li>
                            </ul>
                        </div>
                    </div>
                </nav>

                <header class="page-header py-5 bg-light text-center">
                    <div class="container">
                        <h1 class="display-5">Register of Correspondence</h1>
                        <p class="lead text-muted">A comprehensive, filterable list of letters from the Laßberg collection.</p>
                    </div>
                </header>

                <main class="py-5">
                    <div class="container">
                        <div class="card shadow-sm">
                            <div class="card-header bg-light p-3">
                                <div class="row gy-2 gx-3 align-items-center">
                                    <div class="col-lg col-md-4"><input type="text" class="form-control form-control-sm" id="filter-id" placeholder="Filter by ID..."/></div>
                                    <div class="col-lg col-md-4"><input type="text" class="form-control form-control-sm" id="filter-date" placeholder="Filter by date..."/></div>
                                    <div class="col-lg col-md-4"><input type="text" class="form-control form-control-sm" id="filter-sender" placeholder="Filter by sender..."/></div>
                                    <div class="col-lg col-md-6"><input type="text" class="form-control form-control-sm" id="filter-recipient" placeholder="Filter by recipient..."/></div>
                                    <div class="col-lg col-md-6"><input type="text" class="form-control form-control-sm" id="filter-place" placeholder="Filter by place..."/></div>
                                    <div class="col-lg col-md-12"><input type="text" class="form-control form-control-sm" id="filter-provenance" placeholder="Filter by provenance..."/></div>
                                    <div class="col-12 d-flex justify-content-between align-items-center pt-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="filterCheckbox"/>
                                            <label class="form-check-label" for="filterCheckbox">Show only transcribed letters</label>
                                        </div>
                                        <span class="text-muted small" id="filteredCounter"></span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="letter-table" style="width:100%">
                                        <thead>
                                            <tr>
                                                <th scope="col" style="width: 5%;"></th>
                                                <th scope="col" style="width: 10%;">ID</th>
                                                <th scope="col" style="width: 10%;">Date</th>
                                                <th scope="col" style="width: 20%;">From</th>
                                                <th scope="col" style="width: 20%;">To</th>
                                                <th scope="col" style="width: 15%;">Place</th>
                                                <th scope="col" style="width: 20%;">Provenance</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <xsl:apply-templates select="//tei:correspDesc"/>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>

                <footer class="bg-dark text-white text-center py-3">
                    <div class="container">
                        <p>© 2025 The Laßberg Letters Project</p>
                    </div>
                </footer>

                <!-- JS libs -->
                <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
                    integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"
                    crossorigin="anonymous"></script>
                <script src="../js/letters.js"></script>

                <!-- Lightweight toggler in case letters.js doesn't handle pre-rendered detail rows -->
                <script>
                document.addEventListener('click', function (e) {
                    var btn = e.target.closest('.dt-control');
                    if (!btn) return;
                    var tr = btn.closest('tr');
                    var key = tr && tr.dataset ? tr.dataset.key : null;
                    if (!key) return;
                    var details = document.getElementById(key + '-details');
                    if (details) {
                        details.classList.toggle('d-none');
                        var icon = btn.querySelector('i');
                        if (icon) { icon.classList.toggle('bi-plus-lg'); icon.classList.toggle('bi-dash-lg'); }
                    }
                });
                </script>
            </body>
        </html>
    </xsl:template>

    <!-- ===== Row template: now resolves *all* data in XSLT (no external JS fetches) ===== -->
    <xsl:template match="tei:correspDesc">
        <xsl:variable name="key" select="@key"/>
        <xsl:variable name="letterPath" select="concat($letters-base, $key, '.xml')"/>
        <xsl:variable name="letterDoc" select="if (doc-available($letterPath)) then doc($letterPath) else ()"/>

        <xsl:variable name="summary" select="$letterDoc//tei:div[@type='summary']"/>
        <xsl:variable name="mentionedPersons" select="$letterDoc//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']"/>
        <xsl:variable name="mentionedPlaces" select="$letterDoc//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPlace']"/>
        <xsl:variable name="mentionedLiterature" select="$letterDoc//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsBibl']"/>

        <tr data-status="{@change}" data-key="{$key}">
            <xsl:attribute name="data-harris" select="normalize-space(tei:note[@type='nummer_harris'])"/>
            <td class="dt-control text-center"><i class="bi bi-plus-lg"></i></td>
            <td><xsl:value-of select="$key"/></td>
            <td><xsl:value-of select="normalize-space(tei:correspAction[@type='sent']/tei:date/@when)"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='received']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:placeName"/></td>
            <td>
                <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsort'])"/>, 
                <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsinstitution'])"/>
            </td>
        </tr>

        <!-- Pre-rendered details row (toggled by the plus icon) -->
        <tr id="{$key}-details" class="details-row d-none">
            <td colspan="7" class="p-3">
                <div class="card">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="detail-section mb-2">
                                    <strong>Signatur: </strong>
                                    <span class="text-muted"><xsl:value-of select="tei:note[@type='signatur']"/></span>
                                </div>
                                <div class="detail-section mb-2">
                                    <strong>Harris: </strong>
                                    <span class="text-muted"><xsl:value-of select="tei:note[@type='nummer_harris']"/></span>
                                </div>
                                <div class="detail-section mb-2">
                                    <strong>Journal: </strong>
                                    <span class="text-muted"><xsl:value-of select="tei:note[@type='journalnummer']"/></span>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="detail-section mb-2">
                                    <strong>Druck: </strong>
                                    <xsl:variable name="pub" select="tei:note[@type='published_in']"/>
                                    <xsl:choose>
                                        <xsl:when test="$pub/@target">
                                            <a href="{$pub/@target}"><xsl:value-of select="$pub"/></a>
                                        </xsl:when>
                                        <xsl:otherwise>
                                            <xsl:value-of select="$pub"/>
                                        </xsl:otherwise>
                                    </xsl:choose>
                                </div>
                                <div class="detail-section mb-2">
                                    <strong>Scan: </strong>
                                    <xsl:variable name="scan" select="tei:note[@type='url_facsimile']"/>
                                    <xsl:choose>
                                        <xsl:when test="string-length(normalize-space($scan)) &gt; 0">
                                            <a href="{$scan}"><xsl:value-of select="$scan"/></a>
                                        </xsl:when>
                                        <xsl:otherwise><span class="text-muted">—</span></xsl:otherwise>
                                    </xsl:choose>
                                </div>
                                <xsl:if test="@change='online'">
                                    <div class="detail-section mb-2">
                                        <a class="btn btn-sm btn-primary" target="_blank" rel="noopener noreferrer" href="../letters/{$key}.html">Open Letter</a>
                                    </div>
                                </xsl:if>
                            </div>
                        </div>

                        <xsl:choose>
                            <xsl:when test="$letterDoc">
                                <div class="row mt-3">
                                    <div class="col-md-12">
                                        <strong>Zusammenfassung:</strong>
                                        <p class="text-muted">
                                            <xsl:value-of select="normalize-space(string($summary))"/>
                                            <xsl:text> </xsl:text>
                                            <span class="fst-italic">(Diese Zusammenfassung wurde automatisch erstellt.)</span>
                                        </p>
                                    </div>
                                </div>

                                <div class="row">
                                    <!-- Mentioned Persons -->
                                    <div class="col-md-4 mentioned-persons">
                                        <strong>Erwähnte Personen:</strong>
                                        <ul class="list-unstyled">
                                            <xsl:for-each select="$mentionedPersons">
                                                <xsl:for-each select="tokenize(@target, '\s+')">
                                                    <xsl:variable name="targetId" select="substring-after(., '#')"/>
                                                    <xsl:variable name="person" select="doc($persons-register)//tei:person[@xml:id=$targetId] | doc($persons-register)//tei:personGrp[@xml:id=$targetId]"/>
                                                    <li class="mb-2">
                                                        <xsl:choose>
                                                            <xsl:when test="$person">
                                                                <xsl:variable name="ext" select="string(($person/tei:ref[@target])[1]/@target)"/>
                                                                <xsl:choose>
                                                                    <xsl:when test="$ext">
                                                                        <a href="{$ext}"><xsl:value-of select="$person/tei:persName[@type='main']"/></a>
                                                                    </xsl:when>
                                                                    <xsl:otherwise>
                                                                        <xsl:value-of select="$person/tei:persName[@type='main']"/>
                                                                    </xsl:otherwise>
                                                                </xsl:choose>
                                                                <xsl:text> (</xsl:text><xsl:value-of select="$person/@type"/><xsl:text>)</xsl:text>
                                                                <xsl:if test="$person/@ref">
                                                                    <a class="ms-1" href="{string($person/@ref)}"><img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND" height="12"/></a>
                                                                </xsl:if>
                                                            </xsl:when>
                                                            <xsl:otherwise><em>Person not found</em></xsl:otherwise>
                                                        </xsl:choose>
                                                    </li>
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </ul>
                                    </div>

                                    <!-- Mentioned Places -->
                                    <div class="col-md-4 mentioned-places">
                                        <strong>Erwähnte Orte:</strong>
                                        <ul class="list-unstyled">
                                            <xsl:for-each select="$mentionedPlaces">
                                                <xsl:variable name="targetId" select="substring-after(@target, '#')"/>
                                                <xsl:variable name="place" select="doc($places-register)//tei:place[@xml:id=$targetId]"/>
                                                <li class="mb-2">
                                                    <xsl:choose>
                                                        <xsl:when test="$place">
                                                            <xsl:value-of select="$place/tei:placeName"/>
                                                            <xsl:if test="$place/tei:placeName/@ref">
                                                                <a class="ms-1" href="{string($place/tei:placeName/@ref)}"><img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="Wikidata" height="12"/></a>
                                                            </xsl:if>
                                                            <xsl:variable name="geo" select="tokenize(normalize-space($place/tei:location/tei:geo), ',')"/>
                                                            <xsl:if test="count($geo) = 2">
                                                                <a class="ms-2" href="https://www.openstreetmap.org/?mlat={normalize-space($geo[1])}&amp;mlon={normalize-space($geo[2])}">Show on OSM</a>
                                                            </xsl:if>
                                                        </xsl:when>
                                                        <xsl:otherwise><em>Place not found</em></xsl:otherwise>
                                                    </xsl:choose>
                                                </li>
                                            </xsl:for-each>
                                        </ul>
                                    </div>

                                    <!-- Mentioned Literature -->
                                    <div class="col-md-4 mentioned-literature">
                                        <strong>Erwähnte Literatur:</strong>
                                        <ul class="list-unstyled">
                                            <xsl:for-each select="$mentionedLiterature">
                                                <xsl:variable name="targetId" select="substring-after(@target, '#')"/>
                                                <xsl:variable name="bibl" select="doc($literature-register)//tei:bibl[@xml:id=$targetId]"/>
                                                <li class="mb-2">
                                                    <xsl:choose>
                                                        <xsl:when test="$bibl">
                                                            <xsl:variable name="authors">
                                                                <xsl:for-each select="$bibl/tei:author">
                                                                    <xsl:variable name="authorRef" select="substring-after(@key, '#')"/>
                                                                    <xsl:variable name="authorName" select="doc($persons-register)//tei:person[@xml:id = $authorRef]/tei:persName/text()"/>
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
                                                                <xsl:when test="starts-with($bibl/tei:idno, 'http')">
                                                                    <a href="{$bibl/tei:idno}" target="_blank" rel="noopener noreferrer">
                                                                        <xsl:value-of select="$bibl/tei:idno"/>
                                                                    </a>
                                                                </xsl:when>
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
                                </div>
                            </xsl:when>
                            <xsl:otherwise>
                                <div class="row mt-3">
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

    <!-- ===== Inline element templates ===== -->
    <xsl:template match="tei:persName">
        <xsl:choose>
            <xsl:when test="@ana and normalize-space(@ana) != ''">
                <a href="{@ana}"><xsl:value-of select="normalize-space(.)"/></a>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="normalize-space(.)"/>
                <xsl:if test="@ref">
                    <a href="{@ref}" target="_blank" class="ms-1" title="GND">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND" height="12"/>
                    </a>
                </xsl:if>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="tei:placeName">
        <xsl:value-of select="normalize-space(.)"/>
        <xsl:if test="@ref">
            <a href="{@ref}" target="_blank" class="ms-1" title="Wikidata">
                <img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="Wikidata" height="12"/>
            </a>
        </xsl:if>
    </xsl:template>

</xsl:stylesheet>
