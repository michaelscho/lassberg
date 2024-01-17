# The Lassberg Letters
*Disclaimer: Code and dataset of this repository is still under development and may change substantially. Thus, it is not meant for citation at this point. If sufficiently prepared, the data will be made available as a citeable source via zenodo.*

## Overview
This repository is dedicated to Joseph von Laßberg, an important German scholar of medieval literature in the 18th and 19th century. The repository focuses on collecting, analyzing and encoding Laßberg's vast correspondence of 3265 known letters, mainly focused on the study of medieval history and literature. Thus, the correspondence is an important source for the history of medieval studies in general, but also of major importance for book and library studies in particular. Eventually, the correspondence will be available as TEI encoded XML-files including metadata and the letter's texts. To tackle this massive amount of letters and to make them accessible for research, machine learning applications will be tested and used, such as Automated Text Recognition (OCR and HTR), LLMs to automate summarizing and normalisation, as well as NER and Topic Modelling methods. Thus, the repository also tries to create resources dedicated to the application of such tools for historical research. Lastly, a quantitative analysis of the data will be available. 

## Roadmap
This repository will be developed in six steps:
1. Digital registers have been prepared using Harris 1991 as a starting point. Harris' register has been digitized and enriched considerably by adding and retrieving GND data via `http://lobid.org/gnd/` and Wikidata.
2. TEI encoded registers of persons and places have been created. 
3. A TEI XML template has been created that works for the encoding of each letter following [correspsearch guidlines](https://correspsearch.net/de/dokumentation.html).
4. An OxygenXML framework has been created for easy markup of the letters (`./oxygen-actions`and `oxygen-framework`).
6. An automated Worflow has been created for processing scanned letters (`./src/trans_to_tei.py`).
7. Dataanalysis is developed as a Jupyter Notebook (`./analysis/Jupyter Notebooks`)
8. Cypher import is developed for easy import of data to local [Neo4J](https://neo4j.com) installation (`./neo4j/import-data.cql`)
9. As a proof of concept, the correspondence between Laßberg and Johann Adam Pupikofer is added as text taken from printed sources using ATR, NER and GPT-4 based normalization and summaries of the letters in English and German. These letters have also been encoded in XML in `data/letters`). In due course, this text will be replaced with text recocnized from scanned letters.

## Dataset
Data can be found in `data`, python-scripts used for processing are stored in `src` with log-files in `log`. `data/register` contains a register of all letters with relevant meta- and linked data in `./data/register/register.csv` (';'-separated) as final version. It is based on Harris 1991, but substantially enriched by linked data and digital facsimile, wherever possible. From this file, tei-encoded person- and place-registers have been created as `./data/register/lassberg-persons.xml` and `./data/register/lassberg-persons.xml`, respectively `unique_persons.csv` and `places_persons.csv`. In this process, coordinates have been added to places and GND data has been retrieved for each person. This data was stored as json-files in `data/gnd` using gnd-number as filenames. Based on the final register, each letter's metadata was encoded in TEI in `data/letters` using a uniqque project id as filename. The letter's text (as well as summaries, named entities and key topics) will be added to each of these files starting with the large correspondence between Laßberg and Johann Adam Pubilofer[Johann Adam Pupikofer](https://de.wikipedia.org/wiki/Johann_Adam_Pupikofer). Processed letters can be found in `data/letters`.

## Workflow


## Analysis

## Literature
Harris 1991: Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.
