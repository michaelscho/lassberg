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
                                                <th scope="col" style="width: 5%;"></th> <th scope="col" style="width: 10%;">ID</th>
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
                
                <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
                <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
                    integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"
                    crossorigin="anonymous"></script>
                <script src="../js/letters.js"></script>
            </body>
        </html>
    </xsl:template>
    
    <xsl:template match="tei:correspDesc">
        <tr data-status="{@change}" data-key="{@key}">
            <xsl:attribute name="data-harris" select="normalize-space(tei:note[@type='nummer_harris'])"/>
            
            <td class="dt-control text-center"><i class="bi bi-plus-lg"></i></td>
            <td><xsl:value-of select="@key"/></td>
            <td><xsl:value-of select="normalize-space(tei:correspAction[@type='sent']/tei:date/@when)"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='received']/tei:persName"/></td>
            <td><xsl:apply-templates select="tei:correspAction[@type='sent']/tei:placeName"/></td>
            <td>
                <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsort'])"/>, <xsl:value-of select="normalize-space(tei:note[@type='aufbewahrungsinstitution'])"/>
            </td>
        </tr>
    </xsl:template>
    
    <xsl:template match="tei:persName | tei:placeName">
        <xsl:value-of select="normalize-space(.)"/>
        <xsl:if test="@ref">
            <a href="{@ref}" target="_blank" class="ms-1" title="External Record">
                <xsl:choose>
                    <xsl:when test="self::tei:persName">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND" height="12"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <img src="https://upload.wikimedia.org/wikipedia/commons/f/ff/Wikidata-logo.svg" alt="Wikidata" height="12"/>
                    </xsl:otherwise>
                </xsl:choose>
            </a>
        </xsl:if>
    </xsl:template>
    
</xsl:stylesheet>