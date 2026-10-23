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
                <title>Manuscripts - The Laßberg Project</title>

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
                                <li class="nav-item"><a class="nav-link" href="persons.html">Persons</a></li>
                                <li class="nav-item"><a class="nav-link" href="places.html">Places</a></li>
                                <li class="nav-item"><a class="nav-link active" href="#">Manuscripts</a></li>
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
                        <h1 class="display-5">Manuscripts</h1>
                        <p class="lead text-muted">Manuscripts mentioned in the Laßberg correspondence or from Laßberg's collection, linked to the
                            <a href="https://handschriftenportal.de/" target="_blank" rel="noopener noreferrer">Handschriftenportal</a>
                            where possible.</p>
                    </div>
                </header>

                <main class="py-5">
                    <div class="container">
                        <div class="card shadow-sm mb-3">
                            <div class="card-body">
                                <label for="global-search" class="form-label small text-muted mb-1">Search across letters, persons, places, literature and manuscripts</label>
                                <input type="search" class="form-control" id="global-search" placeholder="e.g. a name, a place, a title, or a word from a letter..." autocomplete="off"/>
                                <div id="letter-search-results" class="list-group mt-2 d-none"></div>
                            </div>
                        </div>
                        <div class="card shadow-sm">
                            <div class="card-header bg-light p-3">
                                <div class="row gy-2 gx-3 align-items-center">
                                    <div class="col-lg col-md-6"><input type="text" class="form-control form-control-sm" id="filter-name" placeholder="Filter by name or shelfmark..."/></div>
                                    <div class="col-12 d-flex justify-content-between align-items-center pt-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="filterCheckbox"/>
                                            <label class="form-check-label" for="filterCheckbox">Show only manuscripts mentioned in a letter</label>
                                        </div>
                                        <span class="text-muted small" id="filteredCounter"></span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="manuscript-table" style="width:100%">
                                        <thead>
                                            <tr>
                                                <th scope="col" style="width: 5%;"></th>
                                                <th scope="col" style="width: 30%;">Name</th>
                                                <th scope="col" style="width: 25%;">Place, library</th>
                                                <th scope="col" style="width: 20%;">Shelfmark</th>
                                                <th scope="col" style="width: 10%;">Letters</th>
                                                <th scope="col" style="width: 10%;">HSP</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <xsl:apply-templates select="//tei:msDesc"/>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <div id="details-templates" class="d-none">
                            <xsl:apply-templates select="//tei:msDesc" mode="details"/>
                        </div>
                    </div>
                </main>

                <footer class="bg-dark text-white text-center py-3">
                    <div class="container"><span class="small">Manuscript descriptions: <a class="text-white" href="https://handschriftenportal.de/">Handschriftenportal</a></span></div>
                </footer>

                <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
                    integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"
                    crossorigin="anonymous"></script>
                <script src="https://cdn.jsdelivr.net/npm/minisearch@6.3.0/dist/umd/index.min.js"></script>
                <script src="../js/search.js"></script>
                <script src="../js/manuscripts.js"></script>
            </body>
        </html>
    </xsl:template>

    <!-- name = msName, else "place, library, shelfmark" -->
    <xsl:function name="tei:ms-name" as="xs:string">
        <xsl:param name="ms" as="element()"/>
        <xsl:variable name="id" select="$ms/tei:msIdentifier"/>
        <xsl:sequence select="if (normalize-space($id/tei:msName) != '') then normalize-space($id/tei:msName)
            else string-join(($id/tei:settlement, $id/tei:repository, $id/tei:idno[@type = 'shelfmark'])[normalize-space(.) != ''], ', ')"/>
    </xsl:function>

    <xsl:template match="tei:msDesc">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="ident" select="tei:msIdentifier"/>
        <xsl:variable name="name" select="tei:ms-name(.)"/>
        <xsl:variable name="refs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsBibl'][substring-after(@target,'#') = $id]"/>
        <xsl:variable name="hsp" select="normalize-space($ident/tei:altIdentifier[@type='hsp']/tei:idno)"/>
        <tr data-key="{$id}" data-mentions="{count($refs)}" data-name="{$name}">
            <td class="dt-control text-center">
                <button type="button" class="row-expand-btn" aria-label="Show manuscript details" aria-expanded="false">
                    <i class="bi bi-chevron-down"></i>
                </button>
            </td>
            <td><xsl:value-of select="$name"/><xsl:if test="@ana = 'needs-review'"> <span class="badge bg-warning text-dark" title="identification under review">?</span></xsl:if></td>
            <td><xsl:value-of select="string-join(($ident/tei:settlement, $ident/tei:repository)[normalize-space(.) != ''], ', ')"/></td>
            <td><xsl:value-of select="$ident/tei:idno[@type = 'shelfmark']"/></td>
            <td><span class="mention-badge"><xsl:value-of select="count($refs)"/></span></td>
            <td>
                <xsl:if test="$hsp != ''">
                    <a href="https://handschriftenportal.de/search?hspobjectid={$hsp}" target="_blank" rel="noopener noreferrer">HSP</a>
                </xsl:if>
            </td>
        </tr>
    </xsl:template>

    <xsl:template match="tei:msDesc" mode="details">
        <xsl:variable name="id" select="@xml:id"/>
        <xsl:variable name="ident" select="tei:msIdentifier"/>
        <xsl:variable name="name" select="tei:ms-name(.)"/>
        <xsl:variable name="refs" select="$allLetters//tei:note[@type='mentioned']/tei:ref[@type='cmif:mentionsBibl'][substring-after(@target,'#') = $id]"/>
        <xsl:variable name="letterIds" select="distinct-values($refs/ancestor::tei:TEI/@xml:id)"/>
        <xsl:variable name="hsp" select="normalize-space($ident/tei:altIdentifier[@type='hsp']/tei:idno)"/>
        <template id="details-{$id}">
            <div class="collapsible-content p-3">
                <xsl:if test="tei:history/tei:provenance">
                    <div class="detail-section mb-2"><strong>Provenance:</strong> <xsl:value-of select="normalize-space(tei:history/tei:provenance)"/></div>
                </xsl:if>
                <xsl:for-each select="$ident/tei:altIdentifier[@type != 'hsp']">
                    <div class="detail-section mb-1 small"><span class="text-muted"><xsl:value-of select="@type"/>: </span><xsl:value-of select="normalize-space(tei:idno)"/></div>
                </xsl:for-each>
                <xsl:if test="$hsp != ''">
                    <p class="small mb-2"><a href="https://handschriftenportal.de/search?hspobjectid={$hsp}" target="_blank" rel="noopener noreferrer">Handschriftenportal</a>
                        · <a href="explore.html?ms={$id}">Description in Explore</a></p>
                </xsl:if>
                <p class="small mb-2"><a href="explore.html?node={$id}" class="btn btn-outline-secondary btn-sm">Show network graph</a></p>
                <xsl:if test="@ana = 'needs-review'">
                    <div class="alert alert-warning py-2 px-3 small">This entry is still under review.
                        <xsl:if test="tei:note"> <xsl:value-of select="normalize-space(tei:note)"/></xsl:if>
                    </div>
                </xsl:if>
                <hr class="my-2"/>
                <h6>Letters</h6>
                <xsl:choose>
                    <xsl:when test="count($letterIds) = 0">
                        <p class="text-muted small mb-0">Not currently linked to any letter.</p>
                    </xsl:when>
                    <xsl:otherwise>
                        <ul class="list-unstyled mb-0 small">
                            <xsl:for-each select="$letterIds">
                                <xsl:sort select="."/>
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
