import os

# 1. Load the dataset of 10 letters
with open(os.path.join(os.getcwd(), "..", "data", "literature", "test_summary_letters.txt"), "r", encoding="utf-8") as file:
    text = file.read()
    letters = text.split("\n")

for letter in letters:
    print(f"The letter has {len(letter)} characters, making a total of {len(letter)/4} token.")

# NER using Spacy ()

import spacy
def evaluate_spacy(letters):

    # Load the German model
    nlp = spacy.load("de_core_news_lg")
    
    for letter in letters:

        # Process the text with the model
        doc = nlp(letter)

        # Extract named entities
        for ent in doc.ents:
            print(ent.text, ent.label_)

# NER using NLTK ()

import nltk
#nltk.download("punkt")
#nltk.download("averaged_perceptron_tagger")
#nltk.download("maxent_ne_chunker")
#nltk.download("words")
def evaluate_nltk(letters):
    for letter in letters:
        # Tokenize and perform POS tagging
        tokens = nltk.word_tokenize(letter)
        tagged_tokens = nltk.pos_tag(tokens)

        # Perform NER using ne_chunk
        named_entities = nltk.ne_chunk(tagged_tokens)

        # Print the named entities
        for entity in named_entities:
            if hasattr(entity, "label"):
                print(" ".join(e[0] for e in entity), entity.label())

# NER using HanTa
from HanTa import HanoverTagger as ht

def evaluate_hanta(letters):
    for letter in letters:
        sentences = nltk.sent_tokenize(letter,language='german')
        #print(sentences)
        for sentence in sentences:
            tokenized_sent = nltk.tokenize.word_tokenize(sentence,language='german')
            #print(tokenized_sent)
            tagger = ht.HanoverTagger('morphmodel_ger.pgz')
            tags = tagger.tag_sent(tokenized_sent)
            for tag in tags:
                print(tag)
            

# NER using BERT
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

def evaluate_bert(letters):
    tokenizer = AutoTokenizer.from_pretrained("Davlan/bert-base-multilingual-cased-ner-hrl")
    model = AutoModelForTokenClassification.from_pretrained("Davlan/bert-base-multilingual-cased-ner-hrl")
    nlp = pipeline("ner", model=model, tokenizer=tokenizer)
    
    for letter in letters:
        ner_results = nlp(letter)
        for result in ner_results:
            print(result)


# NER using Flair
from flair.data import Sentence
from flair.models import SequenceTagger
def evaluate_flair(letters):
    # load tagger
    tagger = SequenceTagger.load("flair/ner-multi")
    for letter in letters:
    # make example sentence in any of the four languages
    
    # predict NER tags
        tagger.predict(letter)

    # print predicted NER spans
    print('The following NER tags are found:')
    # iterate over entities and print
    for entity in letter.get_spans('ner'):
        print(entity)



# Evaluation

#evaluate_spacy(letters)
#evaluate_nltk(letters)
#evaluate_hanta(letters)
evaluate_bert(letters) # maybe try using another model? Also, try to normalize letters using gpt first
#evaluate_flair(letters)

#https://www.researchgate.net/publication/336926568_BERT_for_Named_Entity_Recognition_in_Contemporary_and_Historical_German

#https://github.com/dbmdz/historic-ner

#https://aclanthology.org/P18-2020/

#https://stackoverflow.com/questions/72992743/named-entity-recognition-systems-for-german-texts