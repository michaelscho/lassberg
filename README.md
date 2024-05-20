# The Lassberg Letters
*Disclaimer: Code and dataset of this repository is still under development and may change substantially. Thus, it is not meant for citation at this point. If sufficiently prepared, the data will be made available as a citeable source via zenodo.*

## Overview
This repository is dedicated to Joseph von Laßberg, an important German scholar of medieval literature in the 18th and 19th century. The repository focuses on collecting, analyzing and encoding Laßberg's vast correspondence of 3265 known letters, mainly focused on the study of medieval history and literature.  Eventually, the correspondence is supposed to be available as TEI encoded XML-files including metadata and the letter's texts. To tackle this massive amount of letters and to make them accessible for research, machine learning applications will be tested and used, such as Automated Text Recognition, Named Entity Recognition (NER) and Large Language Models (LLM) to automate summarizing and normalisation, as well as Topic Modelling. Lastly, a quantitative analysis of the data will be available. 

## Roadmap
This repository will be developed in six steps:
1. Digital registers have been prepared using Harris 1991 as a starting point. Harris' register has been digitized and enriched considerably by adding and retrieving GND data via `http://lobid.org/gnd/` and Wikidata.
2. TEI encoded registers of persons and places have been created. 
3. A TEI XML template has been created that works for the encoding of each letter following [correspsearch guidlines](https://correspsearch.net/de/dokumentation.html).
4. An OxygenXML framework has been created for easy markup of the letters (`./oxygen-actions`and `oxygen-framework`).
5. An automated Worflow has been created for processing scanned letters (`./src/trans_to_tei.py`).
6. Data analysis is developed as a Jupyter Notebook (`./analysis/Jupyter Notebooks`)
7. Cypher import is developed for easy import of data to local [Neo4J](https://neo4j.com) installation (`./neo4j/import-data.cql`)
8. Scanning of letters
9. Processing of letters

## Dataset
Data can be found in `data`, python-scripts used for processing are stored in `src` with log-files in `log`. `data/register` contains a register of all letters with relevant meta- and linked data in `./data/register/register.csv` (';'-separated) as final version. It is based on Harris 1991, but substantially enriched by linked data and digital facsimile, wherever possible. From this file, tei-encoded person- and place-registers have been created as `./data/register/lassberg-persons.xml` and `./data/register/lassberg-persons.xml`, respectively `unique_persons.csv` and `places_persons.csv`. In this process, coordinates have been added to places and GND data has been retrieved for each person. This data was stored as json-files in `data/gnd` using gnd-number as filenames. Based on the final register, each letter's metadata was encoded as TEI in `data/letters` using a unique project id as filename. The letter's text (as well as summaries, named entities and key topics) will be added to each of these files starting with the large correspondence between Laßberg and Johann Adam Pubilofer[Johann Adam Pupikofer](https://de.wikipedia.org/wiki/Johann_Adam_Pupikofer). Processed letters can be found in `data/letters`.

## Workflow
1. **Scanning as Input:** The workflow begins with scanned letters provided by libraries and archives.
2. **Text Recognition**: The scanned documents undergo text recognition using [Transkribus](https://readcoop.eu/de/transkribus/) based on a dedicated model.
3. **Scripted Python Pipeline**: The recognized text then enters a Python pipeline, which includes several stages:
    * Transformation into TEI Format: Converting the text into the Text Encoding Initiative (TEI) format.
    * Named Entity Recognition (NER) with Flair: Flair is used for NER ([ner-german-large](https://huggingface.co/flair/ner-german-large)) to identify and categorize entities in the text, mainly persons and places. 
    * Identification: [GPT4](https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo) is used for identifying recognized entities based on existing registers.    
    * Normalization: Transcriptions are standardized to ensure full text searchability by [GPT4](https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo).
    * Translation and Summary with GPT-4: [GPT-4](https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo) is employed for translating the letters into English and generating German summary.
4. **Export as TEI-XML File**: The processed text is exported in the TEI-XML format, suitable for further processing and analysis.
5. **Post-processing**: The TEI-XML files are post-processed using OxygenXML Editor within the Lassberg framework, involving manual correction and further markup.
6. **Presentation / Analysis**:
    * GitHub Pages: The final data is presented on GitHub Pages, featuring frontend data queries implemented with Vue.js.
    * Data Analysis: Data analysis is conducted through Jupyter Notebooks.
    * Local Neo4J Instance: A local Neo4J database instance is used for data management, with imports facilitated by provided Cypher code.
7. **Long-term Archiving**: Final data will be archived [Zenodo](https://zenodo.org/), ensuring its preservation and accessibility for future research and reference.

## Literature
Harris 1991: Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.