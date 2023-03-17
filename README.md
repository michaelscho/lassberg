# The Lassberg Letters
*Disclaimer: Code and dataset of this repository is still under development and may change substantially. Thus, it is not meant for citation at this point. If sufficiently prepared, the data will be made available as a citeable source via zenodo.*

## Overview
This repository is dedicated to Joseph von Laßberg, an important German scholar of medieval literature in the 18th and 19th century. The repository focuses on collecting, analyzing and encoding Laßberg's vast correspondence of 3265 known letters, mainly focused on the study of medieval history and literature. Thus, the correspondence is an important source for the history of medieval studies in general, but also of major importance for book and library studies in particular. Eventually, the correspondence will be available as TEI encoded XML-files including metadata and the letter's texts. To tackle this massive amount of letters and to make them accessible for research, machine learning applications will be tested and used, such as OCR and HTR, or GPT-3 to automate summarizing, analyzing, extracting and encoding the letters. Thus, the repository also tries to create resources dedicated to the application of such tools for historical research. Lastly, a quantitative analysis of the data will be available. 

## Roadmap
This repository will be developed in six steps:
1. Digital registers have been prepared using Harris 1991 as a starting point. Harri's register has been digitized and enriched considerably by adding and retrieving GND data via `http://lobid.org/gnd/`.
2. Each letter has been created as TEI encoded XML file including metadata. TEI encoded registers of persons and places have been created. 
3. As a proof of concept, the correspondence between Laßberg and Johann Adam Pupikofer is added as text taken from printed sources using OCR and GPT-3 based analysis of key topics, named entities and a summary of the letter in English and German (2251.xml, 2256.xml, 2260.xml, 2271.xml, 2274.xml, 2279.xml, 2287.xml, 2290.xml, 2292.xml, 2294.xml and 2296.xml in `data/letters_gpt3_processed`).
4. Text of letters available in print will be added using OCR and GPT-3 based analysis.
5. Text of letters not available in print will be added using HTR and GPT-3 based analysis.
6. Final encoding.

## Dataset
Data can be found in `data`, python-scripts used for processing are stored in `src` with log-files in `log`. `data/register` contains a register of all letters with relevant meta- and linked data in `final_register.csv` (';'-separated) as final version. It is based on Harris 1991, but substantially enriched by linked data and digital facsimile, wherever possible. From this file, tei-encoded person- and place-registers have been created as 'lassberg-persons.xml' and 'lassberg-persons.xml', respectively `unique_persons.csv` and `places_persons.csv`. In this process, coordinates have been added to places and GND data has been retrieved for each person. This data was stored as json-files in `data/gnd` using gnd-number as filenames. Based on the final register, each letter's metadata was encoded in TEI in `data/letters` using its number in Harris 1991 as filename. The letter's text (as well as summaries, named entities and key topics) will be added to each of these files starting with the large correspondence between Laßberg and Johann Adam Pubilofer[Johann Adam Pupikofer](https://de.wikipedia.org/wiki/Johann_Adam_Pupikofer). Processed letters can be found in `data/letters_gpt3_processed`. Eventually, these files will replace the files in `data/letters`.

## Workflow

## Analysis

## Literature
Harris 1991: Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.