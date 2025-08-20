<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0">

    <xsl:output method="html" indent="yes" doctype-system="about:legacy-compat"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Register of Letters - The Laßberg Project</title>

                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet"
                    integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65"
                    crossorigin="anonymous" />

                <link rel="preconnect" href="https://fonts.googleapis.com"/>
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="true"/>
                <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&amp;family=Roboto:wght@400;700&amp;display=swap"
                    rel="stylesheet"/>

                <link rel="stylesheet"
                    href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"/>

                <link href="../css/styles.css" rel="stylesheet"/>
            </head>
            <body>

                <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
                    <div class="container">
                        <a class="navbar-brand" href="../index.html">The Laßberg Letters</a>
                        <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
                            data-bs-target="#navbarNav" aria-controls="navbarNav"
                            aria-expanded="false" aria-label="Toggle navigation">
                            <span class="navbar-toggler-icon"></span>
                        </button>
                        <div class="collapse navbar-collapse" id="navbarNav">
                            <ul class="navbar-nav ms-auto">
                                <li class="nav-item"><a class="nav-link" href="../index.html">Welcome</a></li>
                                <li class="nav-item"><a class="nav-link active" href="#">Letters</a></li>
                                <li class="nav-item"><a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb"
                                        target="_blank">Data Analysis</a></li>
                                <li class="nav-item"><a class="nav-link"
                                        href="https://github.com/michaelscho/lassberg"
                                        target="_blank">Repository</a></li>
                                <li class="nav-item"><a class="nav-link"
                                        href="https://www.zotero.org/groups/6109140/joseph_von_laberg/library"
                                        target="_blank">Literature</a></li>
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
                                    <div class="col-lg-3">
                                        <input type="text" class="form-control form-control-sm" id="filter-sender" data-column="1" placeholder="Filter by sender..."/>
                                    </div>
                                    <div class="col-lg-3">
                                        <input type="text" class="form-control form-control-sm" id="filter-recipient" data-column="2" placeholder="Filter by recipient..."/>
                                    </div>
                                    <div class="col-lg-3">
                                        <input type="text" class="form-control form-control-sm" id="filter-place" data-column="3" placeholder="Filter by place..."/>
                                    </div>
                                    <div class="col-lg-3">
                                         <input type="text" class="form-control form-control-sm" id="filter-provenance" data-column="4" placeholder="Filter by provenance..."/>
                                    </div>
                                    <div class="col-12 d-flex justify-content-between align-items-center pt-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="filterCheckbox"/>
                                            <label class="form-check-label" for="filterCheckbox">
                                                Show only transcribed letters
                                            </label>
                                        </div>
                                        <span class="text-muted small" id="filteredCounter">0 letters shown</span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="letter-table" style="width:100%">
                                        <thead>
                                            <tr>
                                                <th scope="col" class="text-center">Details</th>
                                                <th scope="col">Date</th>
                                                <th scope="col">From</th>
                                                <th scope="col">To</th>
                                                <th scope="col">Place</th>
                                                <th scope="col">Provenance</th>
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

                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
                    integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HqnECQrOpS"
                    crossorigin="anonymous"></script>
                <script src="../js/letters.js"></script>

            </body>
        </html>
    </xsl:template>

    <xsl:template match="tei:correspDesc">
        <tr data-status="{@change}">
            <td class="text-center">
                 <button class="btn btn-outline-secondary btn-sm" data-bs-toggle="collapse" data-bs-target="#{@key}-details" aria-expanded="false">
                     <i class="bi bi-plus-lg"></i>
                 </button>
            </td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:date"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='received']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:placeName"/></td>
            <td>
                <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsort'])"/>, <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsinstitution'])"/> 
            </td>
        </tr>
        
        <tr class="collapse" id="{@key}-details">
            <td colspan="6" class="p-3 bg-light">
                <div class="collapsible-content p-2">
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Harris ID:</strong> <span class="text-muted"><xsl:value-of select="tei:note[@type='nummer_harris']"/></span><br/>
                            <strong>Signature:</strong> <span class="text-muted"><xsl:value-of select="tei:note[@type='signatur']"/></span><br/>
                            <strong>Journal:</strong> <span class="text-muted"><xsl:value-of select="tei:note[@type='journalnummer']"/></span>
                        </div>
                        <div class="col-md-6">
                            <strong>Scan:</strong>
                            <xsl:choose>
                                <xsl:when test="normalize-space(tei:note[@type='url_facsimile'])">
                                    <a href="{tei:note[@type='url_facsimile']}" target="_blank"><xsl:value-of select="tei:note[@type='url_facsimile']"/></a>
                                </xsl:when>
                                <xsl:otherwise><span class="text-muted">Not available</span></xsl:otherwise>
                            </xsl:choose><br/>
                            <strong>Print:</strong>
                            <xsl:choose>
                                <xsl:when test="normalize-space(tei:note[@type='published_in'])">
                                    <a href="{tei:note[@type='published_in']/@target}" target="_blank"><xsl:value-of select="tei:note[@type='published_in']"/></a>
                                </xsl:when>
                                <xsl:otherwise><span class="text-muted">Not available</span></xsl:otherwise>
                            </xsl:choose>
                        </div>
                    </div>
                    <xsl:if test="@change='online'">
                        <hr/>
                        <h6>Letter Summary</h6>
                        <p class="text-muted small">
                            <xsl:variable name="externalSummary" select="document(concat('../../../data/letters/', @key, '.xml'))//tei:div[@type='summary']"/>
                            <xsl:value-of select="$externalSummary"/>
                            <i>(This summary was generated automatically.)</i>
                        </p>
                    </xsl:if>
                </div>
            </td>
        </tr>
    </xsl:template>

    <xsl:template match="tei:persName">
        <xsl:value-of select="."/>
        <xsl:if test="@ref">
            <a href="{@ref}" target="_blank" class="ms-1" title="GND Record">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND" height="12"/>
            </a>
        </xsl:if>
    </xsl:template>

    <xsl:template match="tei:placeName">
        <xsl:value-of select="."/>
        <xsl:if test="@ref">
            <a href="{@ref}" target="_blank" class="ms-1" title="Wikidata Record">
                <img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="Wikidata" height="12"/>
            </a>
        </xsl:if>
    </xsl:template>

    <xsl:template match="tei:note">
        <xsl:value-of select="."/>
    </xsl:template>

</xsl:stylesheet>