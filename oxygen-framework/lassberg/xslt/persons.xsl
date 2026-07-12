<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="tei xs">

    <xsl:output method="html" indent="yes" doctype-system="about:legacy-compat"/>

    <!-- ===== Parameters for external resources ===== -->
    <xsl:param name="letters-base" select="'../../../data/letters/'"/>
    <xsl:param name="letters-register" select="'../../../data/register/lassberg-letters.xml'"/>

    <!-- All 170 individually-encoded letters, loaded once and reused per person via XPath
         predicates rather than re-opening files per row (see .claude/skills/build-website/ and
         the ????-glob note there: excludes the stale *_old.xml duplicates). -->
    <xsl:variable name="allLetters"
        select="collection(concat($letters-base, '?select=lassberg-letter-????.xml;recurse=no'))"/>
    <xsl:variable name="letterRegister" select="document($letters-register)"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Persons - The Laßberg Project</title>

                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65" crossorigin="anonymous"/>
                <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" />

                <link rel="preconnect" href="https://fonts.googleapis.com"/>
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="true"/>
                <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&amp;family=Roboto:wght@400;700&amp;display=swap" rel="stylesheet"/>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"/>

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
                                <li class="nav-item"><a class="nav-link active" href="#">Persons</a></li>
                                <li class="nav-item"><a class="nav-link" href="places.html">Places</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb" target="_blank">Data Analysis</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://github.com/michaelscho/lassberg" target="_blank">Repository</a></li>
                                <li class="nav-item"><a class="nav-link" href="https://www.zotero.org/groups/6109140/joseph_von_laberg/library" target="_blank">Literature</a></li>
                            </ul>
                        </div>
                    </div>
                </nav>

                <header class="page-header py-5 bg-light text-center">
                    <div class="container">
                        <h1 class="display-5">Persons</h1>
                        <p class="lead text-muted">Everyone named in the Laßberg correspondence — correspondents, family, and figures mentioned along the way.</p>
                    </div>
                </header>

                <main class="py-5">
                    <div class="container">
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
                                    <div class="col-lg col-md-6"><input type="text" class="form-control form-control-sm" id="filter-type" placeholder="Filter by type..."/></div>
                                    <div class="col-12 d-flex justify-content-between align-items-center pt-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="filterCheckbox"/>
                                            <label class="form-check-label" for="filterCheckbox">Show only persons appearing in a letter</label>
                                        </div>
                                        <span class="text-muted small" id="filteredCounter"></span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="person-table" style="width:100%">
                                        <thead>
                                            <tr>
                                                <th scope="col" style="width: 5%;"></th>
                                                <th scope="col" style="width: 30%;">Name</th>
                                                <th scope="col" style="width: 15%;">Type</th>
                                                <th scope="col" style="width: 15%;">Dates</th>
                                                <th scope="col" style="width: 15%;">Authority links</th>
                                                <th scope="col" style="width: 20%;">Letters</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <xsl:apply-templates select="//tei:person | //tei:personGrp"/>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <div id="details-templates" class="d-none">
                            <xsl:apply-templates select="//tei:person | //tei:personGrp" mode="details"/>
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
                <script src="../js/search.js"></script>
                <script src="../js/persons.js"></script>
            </body>
        </html>
    </xsl:template>

    <!-- ===== Row template ===== -->
    <xsl:template match="tei:person | tei:personGrp">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="name" select="normalize-space(tei:persName[@type='main'])"/>
        <xsl:variable name="sentLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='sent']/tei:persName/@key = $id]"/>
        <xsl:variable name="receivedLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='received']/tei:persName/@key = $id]"/>
        <xsl:variable name="mentionedRefs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']
            [some $t in tokenize(@target, '\s+') satisfies substring-after($t, '#') = $id]"/>
        <xsl:variable name="totalLetters" select="count($sentLetters) + count($receivedLetters) + count($mentionedRefs)"/>

        <xsl:variable name="typeLabel">
            <xsl:choose>
                <xsl:when test="self::tei:personGrp">Family / Group</xsl:when>
                <xsl:when test="@gender = 'CorporateBody'">Institution</xsl:when>
                <xsl:when test="@type = 'historical'">Historical</xsl:when>
                <xsl:otherwise>Contemporary</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>

        <xsl:variable name="occupations" select="string-join(tei:occupation[normalize-space(.) != ''], ' ')"/>

        <tr data-key="{$id}" data-mentions="{$totalLetters}">
            <td class="dt-control text-center">
                <button type="button" class="row-expand-btn" aria-label="Show person details" aria-expanded="false">
                    <i class="bi bi-chevron-down"></i>
                </button>
                <span class="d-none dt-search-index"><xsl:value-of select="$occupations"/></span>
            </td>
            <td><xsl:value-of select="$name"/></td>
            <td><xsl:value-of select="$typeLabel"/></td>
            <td>
                <xsl:variable name="birth" select="normalize-space(tei:birth/@when)"/>
                <xsl:variable name="death" select="normalize-space(tei:death/@when)"/>
                <xsl:choose>
                    <xsl:when test="$birth != '' or $death != ''">
                        <xsl:value-of select="$birth"/><xsl:text>–</xsl:text><xsl:value-of select="$death"/>
                    </xsl:when>
                    <xsl:otherwise><span class="text-muted">–</span></xsl:otherwise>
                </xsl:choose>
            </td>
            <td>
                <xsl:if test="@ref and normalize-space(@ref) != ''">
                    <a href="{@ref}" target="_blank" rel="noopener noreferrer" title="GND">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND" height="12"/>
                    </a>
                </xsl:if>
                <xsl:if test="tei:ref[@target and normalize-space(@target) != '']">
                    <a class="ms-1" href="{(tei:ref[@target != ''])[1]/@target}" target="_blank" rel="noopener noreferrer">Wikipedia</a>
                </xsl:if>
            </td>
            <td>
                <span class="mention-badge">
                    <xsl:choose>
                        <xsl:when test="$totalLetters = 0">
                            <span class="text-muted">0 letters</span>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:if test="count($sentLetters) &gt; 0">S <xsl:value-of select="count($sentLetters)"/></xsl:if>
                            <xsl:if test="count($receivedLetters) &gt; 0"><xsl:if test="count($sentLetters) &gt; 0"> · </xsl:if>R <xsl:value-of select="count($receivedLetters)"/></xsl:if>
                            <xsl:if test="count($mentionedRefs) &gt; 0"><xsl:if test="count($sentLetters) &gt; 0 or count($receivedLetters) &gt; 0"> · </xsl:if>M <xsl:value-of select="count($mentionedRefs)"/></xsl:if>
                        </xsl:otherwise>
                    </xsl:choose>
                </span>
            </td>
        </tr>
    </xsl:template>

    <!-- ===== Detail template (mode="details") ===== -->
    <xsl:template match="tei:person | tei:personGrp" mode="details">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="name" select="normalize-space(tei:persName[@type='main'])"/>
        <xsl:variable name="sentLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='sent']/tei:persName/@key = $id]"/>
        <xsl:variable name="receivedLetters" select="$letterRegister//tei:correspDesc[tei:correspAction[@type='received']/tei:persName/@key = $id]"/>
        <xsl:variable name="mentionedRefs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsPerson']
            [some $t in tokenize(@target, '\s+') satisfies substring-after($t, '#') = $id]"/>
        <xsl:variable name="mentionedLetterIds" select="distinct-values($mentionedRefs/ancestor::tei:TEI/@xml:id)"/>

        <template id="details-{$id}">
            <div class="collapsible-content p-3">
                <xsl:if test="tei:occupation[normalize-space(.) != '']">
                    <div class="detail-section mb-2">
                        <strong>Occupation: </strong>
                        <span class="text-muted"><xsl:value-of select="string-join(tei:occupation[normalize-space(.) != ''], '; ')"/></span>
                    </div>
                </xsl:if>
                <xsl:if test="@ana = 'needs-review'">
                    <div class="alert alert-warning py-2 px-3 small">This entry is still under review.
                        <xsl:if test="tei:note[@type='review']"> <xsl:value-of select="normalize-space(tei:note[@type='review'])"/></xsl:if>
                    </div>
                </xsl:if>

                <hr class="my-2"/>
                <h6>Letters</h6>
                <xsl:variable name="totalCount" select="count($sentLetters) + count($receivedLetters) + count($mentionedLetterIds)"/>
                <xsl:choose>
                    <xsl:when test="$totalCount = 0">
                        <p class="text-muted small mb-0">Not currently linked to any letter.</p>
                    </xsl:when>
                    <!-- Central figures (chiefly Laßberg himself) appear in thousands of letters —
                         enumerating each one is neither useful nor cheap to render, so above a
                         threshold we just summarize and point at the Letters register instead. -->
                    <xsl:when test="$totalCount &gt; 40">
                        <p class="small mb-0">
                            Sender of <xsl:value-of select="count($sentLetters)"/>, recipient of
                            <xsl:value-of select="count($receivedLetters)"/>, and mentioned in
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
                                    <xsl:with-param name="role" select="'Sender'"/>
                                </xsl:call-template>
                            </xsl:for-each>
                            <xsl:for-each select="$receivedLetters">
                                <xsl:sort select="tei:correspAction[@type='sent']/tei:date/@when"/>
                                <xsl:call-template name="letter-detail-link">
                                    <xsl:with-param name="letterId" select="@key"/>
                                    <xsl:with-param name="role" select="'Recipient'"/>
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

    <!-- Shared helper: one <li> linking to a letter, direct page if published, else a
         pre-filtered search deep-link into the Letters page. -->
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
