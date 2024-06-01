from flair.models import SequenceTagger
from flair.data import Sentence
from flair.nn import Classifier
from flair.data import Label

letter_text_1 = """Hochwohlgebomer  Herr  und  Gönner! 

Da  ich  einen  Pack  Bücher  von  Ihnen  erwartete  und dieser  nicht  angekommen  ist,  so  bin  ich  etwas  unruhig  geworden; nicht  etwa  deswegen,  weil  ich  der  Bücher  sehr  bedürfte, sondern  weil  ich  fürchte,  Sie  möchten  von  einem  Rückfall betroffen  und  wieder  krank  geworden  sein.  Doch  vielleicht sind  Sie  nach  Heiligenberg  verreist,  durch  Gäste  gehindert oder  über  eine  neue  Entdeckung  im  alten  Bardenhain 80  versessen,  daß  Sie  des  armen  Diakonus  an  der  Sitter  ganz vergessen  haben. 
Daß  ich  weder  so  glücklich  in  Entdeckungen,  noch  so vergeßlich  bin,  sollen  Ihnen  mitkommende  Schriften  beweisen. Das  alte  Zürich  hat,  wie  ich  hoffe,  auch  für  Sie  manches  bemerkenswerthe ;  die  Helvetia  und  das  St.  Gallische  Neujahrsblatt sind  Fortsetzungen.  Für  den  Gebrauch  der  Müllerschen Alterthümer  bin  ich  Ihnen  sehr  dankbar;  sie  dienten  mir  zum Theil  als  Erläuterung  zum  alten  Zürich.  Sollte  das  Appenzellische  Landbuch  nicht  auch  Beiträge  für  Herrn  Grimm  enthalten? 
Mit  Grimms  Alterthümem  bin  ich  bald  fertig;  daß  so viele  mir  unverständliche  nordische  Stellen  angeführt  und nicht  übersetzt  sind,  verdrießt  mich  nicht  selten. 
Leben  Sie  wohl  und  gedenken  Sie  zuweilen Ihres Pupikofer. Bischofzeil,  den  17.  Jan.  1829."""

letter_text_2 = """Mein verehrtester Herr und Nachbar!
Wie übel es doch Ihrem Schneehuhn ergangen ist! Wohl war in der Todesstunde demselben kein geringer Trost die Hoffnung von einem sachverständigen Gaumen der Feinheit und Schmackhaftigkeit gerühmt zu werden und somit wenigstens einen Schatten des Nachruhms einzuernten. Wie schmeichelhaft mochte die Aussicht sein, in der Zelle des heiligen Eppo zum Opfer zu dienen, und von einem so hocherfahrenen des edlen Weidwerks durch und durch kundigen Jäger gespeist zu werden.
Nun kommt es einem armen Chorsänger in die Hände, der nichts anderes als Erdäpfel und Kalbsbraten zu beurteilen versteht und alle Hoffnung auf eine auch nur augenblickliche Berühmtheit ist verschwunden. Was wird die gute Frau Doktorin dazu sagen? Unser einer denkt dabei an die Brosamen, die von des Reichen Tische fielen und dankt gar schön.
Aber selbst im Alten Jahr nochmals zu Ihnen zu kommen will mir nicht gelingen; ich sollte die Kommentationen fatales des edelen Mannes Rütiner in einigen Tagen zurück gehen lassen, und bin kaum zur Hälfte damit fertig. Was er doch von der Frau des gelehrten Fritz Jakob vom Anwyl schreibt! Tom. I. p. 31. heißt es: Uxor Jacobi Fritz von Anwyl tum cum libros biblio pola adfert: "supersunt aegrotanti podagra vel immensum pretium dicit poscere, ne emat. Si vir sciret, contunderetur". Liest man dies nicht auch im Gedichte der herrischen Frau auf Ihrer bemalten Scheibe.
Herr Dekan Däniker wünscht Ihnen guten Empfang der Morgenblätter, die Sie mit Muße durchgehen können. Die früheren Jahrgänge hat er nicht mehr. Mit der Abfassung des Thurgauer Neujahrsstücks bitte ich, Nachsicht zu tragen. Das Schaffhauserische werden Sie wohl bereits bekommen haben: aber Herr Pfarrer Kirchhofer lobt die Empfänglichkeit dafür nicht sehr.
Wir haben am Neujahrabend auf dem Schloss ein Abendessen, dem Herr Oberamtmann und Herr Dekan Däniker mit ihren Frauen beiwohnen werden; wir werden auch Punsch anfertigen, und den jungen Leuten und den Laien Gelegenheit zum Tanz verschaffen. Wollen Sie nicht auch dabei sein? Am Tage des heiligen Bertholdus, der im Kalender freilich nach dem unschuldigen Schäfer Abel den Ehrenplatz lässt, spreche ich um eine Suppe in Eppishausen ein: da werden Sie doch wohl nicht ausweichen?
Und nun Gott befohlen, das Alte Jahr! Das Neue bringe Ihnen recht viele Antiquitäten ins Haus, und nehme Ihnen keines der Güter, die Sie bereits besitzen. Mir erhalte es Ihre freundschaftliche Wohlwollen und das Vergnügen, recht oft bei Ihnen zu sein.
Leben Sie wohl, wie es von Herzen wünscht. Ihr Diac. Pupikofer Bischofzell den 30. Dez. 1828."""


# NER using Flair ~NER~
# load model
tagger = Classifier.load('de-ner-large')
tagger.to('cpu')
    
# make example sentence in any of the four languages
sentence = Sentence(letter_text_1)

# predict NER tags
tagger.predict(sentence)

list_of_entities = []

# print predicted NER spans
for entity in sentence.get_spans('ner'):
    tag: Label = entity.labels[0]
    #print(f'{entity.text} [{tag.value}] ({tag.score:.4f})')
    list_of_entities.append([entity.text, tag.value])
    
print(list_of_entities)

        