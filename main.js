// Import VueRouter
const VueRouter = window.VueRouter;
Vue.use(VueRouter);

// Define your components here
const WelcomePage = {
  template: `
    <div>
    <h1 class="my-4">The Laßberg Letters</h1>
    <h2 class="my-4">Introduction</h2>
    <p>Joseph Maria Christoph Freiherr von Laßberg (1770-1855) was a German scholar, bibliophile, and literary collector who played a significant role in the cultural and intellectual life of the early 19th century. Born in Donaueschingen, Laßberg was educated in law and cameralism at the Universities of Straßburg and Freiburg and pursued a successful career in service of the House of Fürstenberg (<router-link to="/literature#Bader1955">Bader 1955</router-link>, <router-link to="/literature#Graf2010">Graf 2010</router-link>, <router-link to="/literature#Schupp1982">Schupp 1982</router-link>, <router-link to="/literature#Sprague2011">Sprague 2011</router-link>). However, in the wake of the loss of sovereignty sealed at the Congress of Vienna, the mediatised nobility compensated, among other things, through an increased interest in the Middle Ages, which they romantically idealized as a better time. Thus, many aristocratic scholars attempted to collect and study medieval artifacts and united several medievalist disciplines into a politically connoted patriotic archaeology, in service of the noble interests. From then on, the efforts of the lower nobility's scholarship were directed towards the exploration of medieval writings and other remains of that era (<router-link to="/literature#Graf2010">Graf 2010</router-link>, <router-link to="/literature#Schupp2006">Schupp 2006</router-link>). This explains Laßberg deep interest in the study of medieval literature. Indeed, he dedicated much of his resources to collecting and studying manuscripts, books, and other literary artifacts. His private library, today scattered, comprised over 10,000 volumes and included many rare medieval German manuscripts, which he painstakingly acquired from various monastic libraries and private collections (<router-link to="/literature#Bothien2001">Bothien 2001</router-link>, <router-link to="/literature#Gantert2001">Gantert 2001</router-link>, <router-link to="/literature#Obhof2001">Obhof 2001</router-link>, <router-link to="/literature#Obhof2005">Obhof 2005</router-link>, <router-link to="/literature#Schupp2002">Schupp 2002</router-link>, <router-link to="/literature#Schupp1993">Schupp 1993</router-link>, <router-link to="/literature#Weidhase2002">Weidhase 2002</router-link>).</p>

    <p>Laßberg's scholarly pursuits focused primarily on German medieval literature, and his efforts to preserve, edit, and disseminate these works had a lasting impact on the emerging field of Medieval Studies in Germany, by providing access to his library (and brokering access to others) for other scholars. By sharing his extensive collection, he facilitated the study and dissemination of medieval literature, contributing significantly to the development and growth of Medieval Studies during the 19th century. Thus, it is not surprising, that his correspondence (<router-link to="/repository">data/register/final_register.csv</router-link>, <router-link to="/literature#Harris1991">Harris 1991</router-link>) unveils an extensive network of connections with distinguished scholars, writers, and cultural figures of his time. Among Laßberg's most prominent correspondents were the Brothers Grimm, Jacob and Wilhelm, who shared his passion for the preservation of Germany's cultural heritage. Other notable figures in Laßberg's network included the historian and philologist Karl Lachmann, the writer and collector Achim von Arnim, and the poet Clemens Brentano. Together, his letters offer a rare insight into a dynamic and influential intellectual community that contributed significantly to the development of German Romanticism and the resurgence of interest in the nation's presumed medieval past.</p>
    </div>
    
                `,
};
const LettersPage = {
  props: ["lettersData"],
  template: `
  <div>
    <h1 class="my-4">The Lassberg Letters</h1>
    <h2 class="my-4">Register</h2>
    <p>{{ filteredDataCount }} letters selected. Click on date for further information.</p>
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">Date<input v-model="filters.date" type="text"/></th>
          <th scope="col">From (GND)<input v-model="filters.name_from" type="text"/></th>
          <th scope="col">To (GND)<input v-model="filters.name_to" type="text"/></th>
          <th scope="col">Place<input v-model="filters.place" type="text"/></th>
          <th scope="col">Provenance<input v-model="filters.provenance" type="text"/></th>
          <th scope="col">Mentioned<input v-model="filters.persons" type="text"/></th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="(item, id) in filteredData" :key="id" >
          <td><router-link :to="'/letter/' + item.id">{{ item.date }}</router-link></td>
          <td>
            <!-- Case 1: Name has a wiki URL and a GND number -->
            <template v-if="item['sent-from-information'] !== '-' && item['sent-from-gnd'] !== '-'">
              <a :href="item['sent-from-information']">{{ item['sent-from-name'] }}</a>
              <span class="ml-2">
                <a :href="'https://lobid.org/gnd/' + item['sent-from-gnd']">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
                </a>
              </span>
            </template>
            
            <!-- Case 2: Name has no wiki page but a GND number -->
            <template v-else-if="item['sent-from-information'] === '-' && item['sent-from-name'] !== '-'">
              {{ item['sent-from-name'] }}
              <span class="ml-2">
                <a :href="'https://lobid.org/gnd/' + item['sent-from-gnd']">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
                </a>
              </span>
            </template>
            
            <!-- Case 3: Name has no wiki page and no GND number -->
            <template v-else>
              {{ item['sent-from-name'] }}
            </template>
          </td>

          <td>
          <!-- Case 1: Name has a wiki URL and a GND number -->
          <template v-if="item['received-by-information'] !== '-' && item['received-by-gnd'] !== '-'">
            <a :href="item['received-by-information']">{{ item['received-by-name'] }}</a>
            <span class="ml-2">
              <a :href="'https://lobid.org/gnd/' + item['received-by-gnd']">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
              </a>
            </span>
          </template>
          
          <!-- Case 2: Name has no wiki page but a GND number -->
          <template v-else-if="item['received-by-information'] === '-' && item['received-by-name'] !== '-'">
            {{ item['received-by-name'] }}
            <span class="ml-2">
              <a :href="'https://lobid.org/gnd/' + item['received-by-gnd']">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
              </a>
            </span>
          </template>
          
          <!-- Case 3: Name has no wiki page and no GND number -->
          <template v-else>
            {{ item['received-by-name'] }}
          </template>
        </td>

          <td>{{ item['place-sent-from-name'] }}</td>
          <td>{{ item['owning-institution-place'] || '' }}, {{ item['owning-institution-name'] || '' }}</td>
          <td>{{ item.persons_mentioned }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  `,
  data() {
    return {
      filters: {
        date: "",
        place: "",
        name_from: "",
        name_to: "",
        provenance: "",
        persons: "",      },
    };
  },
  methods: {
    

  },

  computed: {
    filteredData() {
      if (!this.lettersData) {
        return [];
      }
      return this.lettersData.filter((item) => {
        // Concatenate owning institution place and name
        const owningInstitution = `${item['owning-institution-place']} ${item['owning-institution-name']}`.toLowerCase();
  
        return (
          item.date.toLowerCase().includes(this.filters.date.toLowerCase()) &&
          item['sent-from-name'].toLowerCase().includes(this.filters.name_from.toLowerCase()) &&
          item['received-by-name'].toLowerCase().includes(this.filters.name_to.toLowerCase()) &&
          item['place-sent-from-name'].toLowerCase().includes(this.filters.place.toLowerCase()) &&
          owningInstitution.includes(this.filters.provenance.toLowerCase()) &&
          // Add other filters as necessary, for persons, topics, etc.
          true // Placeholder for other conditions
        );
      });
    },
  
    filteredDataCount() {
      return this.filteredData.length;
    },
  
    filteredDataIds() {
      return this.filteredData.map((_, index) => `filteredItem-${index}`);
    },
  },
  

  mounted() {
  },
};

const LetterView = {
  props: {
    id: String, 
    lettersData: Array,
    personRegister: Array,
    placeRegister: Array,
    literatureRegister: Array
    },
  data() {
    return {
      letter: null,
      letterText: null,
      originalText: null,
      normalizedText: null,
      translationText: null,
      summaryText: null,
      personEntries: [],
      placeEntries: [],
      literatureEntries: []
    };
  },

  // here, something does not work due to the asynchronous loading of the data

  mounted() {
    console.log(this.personRegister, this.placeRegister, this.literatureRegister);
    this.findLetterById();
    if (this.letter) {
      this.loadTeiFile(this.id)
        .then(refs => {
          this.processRegisters(refs);
        })
        .catch(error => {
          console.error('Error in loading TEI file:', error);
        });
    } else {
      console.error('Letter not found with ID:', this.id);
    }
  },

  methods: {
    findLetterById() {
      this.letter = this.lettersData.find(item => item.id === this.id);
      if (!this.letter) {
        console.error('Letter not found with ID:', this.id);
      }
    },

    processRegisters(refs) {
      console.log('refs:', refs);
      // Filter the person register based on refs.persons
      this.personEntries = this.filterRegisterEntries(this.personRegister, refs.persons);

      // Filter the place register based on refs.places
      this.placeEntries = this.filterRegisterEntries(this.placeRegister, refs.places);

      // Filter the literature register based on refs.literature
      this.literatureEntries = this.filterRegisterEntries(this.literatureRegister, refs.literature);

      console.log('Person Entries:', this.personEntries);
      console.log('Place Entries:', this.placeEntries);
      console.log('Literature Entries:', this.literatureEntries);
    

    },
    
    filterRegisterEntries(registerArray, refs) {
      return registerArray.filter(entry => 
        refs.some(ref => ref.endsWith('#' + entry.id))
      );
    },
        
    async loadTeiFile(letterId) {
      const url = `https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/${letterId}.xml`;
      try {
        const response = await axios.get(url);
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(response.data, "text/xml");
    
        // Extracting original text
        this.originalText = this.processText(xmlDoc.querySelector('div[type="original"]'));
        // Extracting normalized text
        this.normalizedText = this.processText(xmlDoc.querySelector('div[type="normalized"]'));
        // Extracting translation text
        this.translationText = this.processText(xmlDoc.querySelector('div[type="translation"]'));
        // Extracting summary
        this.summaryText = this.processText(xmlDoc.querySelector('div[type="summary"]'));
    
        // Extracting and processing references from the header
        const refs = this.extractRefs(xmlDoc.querySelector('teiHeader'));
    
        // Load and filter registers based on extracted references
        return refs;
      } catch (error) {
        console.error('Error fetching TEI file:', error);
      }
    },

    extractRefs(teiHeader) {
      const refs = {
        persons: [],
        places: [],
        literature: []
      };
  
      teiHeader.querySelectorAll('ref[type="cmif:mentionsPerson"]').forEach(ref => {
        refs.persons.push(ref.getAttribute('target'));
      });
      teiHeader.querySelectorAll('ref[type="cmif:mentionsPlace"]').forEach(ref => {
        refs.places.push(ref.getAttribute('target'));
      });
      teiHeader.querySelectorAll('ref[type="cmif:mentionsBibl"]').forEach(ref => {
        refs.literature.push(ref.getAttribute('target'));
      });
  
      return refs;
    },
  

    processText(element) {
      if (!element) return '';
  
      // Clone the element to not modify the original XML document
      const clonedElement = element.cloneNode(true);
  
      // Process each <rs> element
      clonedElement.querySelectorAll('rs').forEach(rs => {
        const span = document.createElement('span');
        //span.style.backgroundColor = 'yellow'; 
        span.className = 'highlighted-rs';
        span.innerHTML = rs.innerHTML;
        rs.parentNode.replaceChild(span, rs);
      });

      return clonedElement.innerHTML;
    },

    processHeader(headerElement) {
      if (!headerElement) return;
  
      // Initialize metadata lists
      this.personRefs = [];
      this.placeRefs = [];
      this.literatureRefs = [];
  
      // Process and populate person references
      headerElement.querySelectorAll('ref[type="cmif:mentionsPerson"]').forEach(ref => {
        this.personRefs.push(ref.getAttribute('target'));
      });
  
      // Process and populate place references
      headerElement.querySelectorAll('ref[type="cmif:mentionsPlace"]').forEach(ref => {
        this.placeRefs.push(ref.getAttribute('target'));
      });
  
      // Process and populate literature references
      headerElement.querySelectorAll('ref[type="cmif:mentionsBibl"]').forEach(ref => {
        this.literatureRefs.push(ref.getAttribute('target'));
      });
    },
    
  },
  template: `
    <div>
    <div v-if="letter">
      <h1 class="my-4">{{ letter['sent-from-name'] }} to {{ letter['received-by-name'] }} ({{ letter.date === "Unbekannt" ? "Unknown" : new Date(letter.date).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' }) }})</h1>
      <h2>Metadata</h2>
      <p><strong>Date:</strong> {{ letter['date'] }}</p>
      <p><strong>Name:</strong> {{ letter['sent-from-name'] }}</p>
      <p><strong>Place:</strong> {{ letter['place-sent-from-name'] }}</p>
      <p><strong>Journal:</strong> {{ letter['journal-number-lassberg'] }}</p>
      <p><strong>Harris 1991:</strong> {{ letter['register-number-harris'] }}</p>
      <p><strong>Provenance:</strong> {{ letter['owning-institution-place'] || '' }}, {{ letter['owning-institution-name']  || '' }}</p>
      <p><strong>Printed:</strong> <a :href="letter['printed-publication-url']">{{ letter['printed-publication-name'] }}</a></p>      
      <h2>Mentioned Persons</h2>
      <ul>
      <li v-for="person in personEntries" :key="person.key">
        
        {{ person.name }} (GND: <a :href="person.gnd">{{ person.gnd }}</a>,
        Info: <a :href="person.wiki">{{ person.wiki }}</a>)
      </li>
    </ul>
      <h2>Mentioned Places</h2>  
      <ul>
      <li v-for="place in placeEntries" :key="place.key">
        {{ place.name }} (Wikidata: <a :href="place.wikidata">{{ place.wikidata }}</a>)
      </li>
    </ul>
      <h2>Mentioned References</h2>
      <ul>
      <li v-for="literature in literatureEntries" :key="literature.key">
      {{ literature.author }}: {{ literature.title }}. {{ literature.pubPlace }}, {{ literature.date }} (<a :href="literature.idno">{{ literature.idno }}</a>)  
      </li>
    </ul>
      <h2>Summary</h2>
      <p><div v-html="summaryText"></div></p>
      <p><strong>Prepared by GPT4</strong></p>
      <h2>Original Text</h2>
      <p><div v-html="originalText"></div></p>
      <h2>Normalized Text</h2>
      <p><div v-html="normalizedText"></div></p>
      <p><strong>Prepared by GPT4</strong></p>
      <h2>Translation</h2>
      <p><div v-html="translationText"></div></p>
      <p><strong>Prepared by GPT4</strong></p>
      <p><router-link to="/letters">Back to Letters</router-link></p>
      </div>
      </div>
  `,
};

const LiteraturePage = {
  template: `
    <div>
    <h1 class="my-4">Literature</h1>
    <ul class="list-group">
        <li class="list-group-item" id="Bader1955">(Bader 1955) Karl Siegfried Bader (ed.): Joseph Laßberg, Mittler und Sammler. Stuttgart 1955.</li>
        <li class="list-group-item" id="Boran2019">(Boran et. al 2019) Elizabethanne Boran, Marie Isabel Matthews-Schlinzig, Rebekah Ahrendt, Nadine Akkerman, Jana Dambrogio, Daniel Starza Smith, and David van der Linden: Letters. In: Howard Hotson and Thomas Wallnig (eds.): Reassembling the Republic of Letters in the Digital Age. Standards, Systems, Scholarship. Göttingen 2019 (DOI: https://doi.org/10.17875/gup2019-1146), pp. 57-78.</li>
        <li class="list-group-item" id="Bothien2001">(Bothien 2001) Heinz Bothien: Joseph von Lassberg - des letzten Ritters Bibliothek. Frauenfeld/Stuttgart/Wien 2001.</li>
        <li class="list-group-item" id="Gantert2001">(Gantert 2001) Klaus Gantert: Die Bibliothek des Freiherrn Joseph von Laßberg: ein gescheiterter Erwerbungsversuch der Königlichen Bibliothek zu Berlin in der Mitte des 19. Jahrhunderts. Beihefte zum Euphorion 42. Heidelberg 2001.</li>
        <li class="list-group-item" id="Graf2010">(Graf 2010) Klaus Graf: „Joseph von Laßberg und sein Ritterschlag auf der Burg Trifels“. archivalia.hypotheses, 2010.</li>
        <li class="list-group-item" id="Harris1991">(Harris 1991) Martin Harris: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Heidelberg 1991.</li>
        <li class="list-group-item" id="Obhof2005">(Obhof 2005) Ute Obhof: Joseph Freiherr von Laßberg (1770-1855) und seine Bibliothek: Die ’Nibelungenlied’-Handschrift C, Codex Donaueschingen 63. Karlsruhe, 2005.</li>
        <li class="list-group-item" id="Obhof2001">(Obhof 2001) Ute Obhof: Joseph Freiherr von Laßberg (1770-1855) und seine Bibliothek: 1. Begleitbuch zur Ausstellung vom 17. Februar bis 12. April 2001 in der Badischen Landesbibliothek. Karlsruhe 2001.</li>
        <li class="list-group-item" id="Schulte2004">(Schulte and von Tippelskirch 2004) Regina Schulte and Xenia von Tippelskirch: Introduction. In: Regina Schulte and Xenia von Tippelskirch (eds.): Reading, Interpreting and Historicizing: Letters as Historical Sources, European University Institute 2004 (https://hdl.handle.net/1814/2600), pp. 5-10.</li>
        <li class="list-group-item" id="Schupp2006">(Schupp 2006): Volker Schupp: Die Gründung der ‚Gesellschaft der Freunde vaterländischer Geschichte an den Quellen der Donau‘ im Spiegel der geistesgeschichtlichen Strömungen der Zeit. In: Schriften des Vereins für Geschichte und Naturgeschichte der Baar 49 (2006) (https://d-nb.info/1254211209/34), pp. 8–27.</li>
        <li class="list-group-item" id="Schupp2002">(Schupp 2002) Volker Schupp: Versteigerung der Fürstlich Fürstenbergischen Hofbibliothek Donaueschingen. Librarium: Zeitschrift der Schweizerischen Bibliophilen Gesellschaft 45 (2002) (https://freidok.uni-freiburg.de/data/6393), pp. 17–22.</li>
        <li class="list-group-item" id="Schupp1993">(Schupp 1993) Volker Schupp: Joseph von Laßberg als Handschriftensammler. In „Unberechenbare Zinsen“: bewahrtes Kulturerbe. Katalog zur Ausstellung der vom Land Baden-Württemberg erworbenen Handschriften der Fürstlich Fürstenbergischen Hofbibliothek. Stuttgart, 1993 ,pp. 14–33.</li>
        <li class="list-group-item" id="Schupp1982">(Schupp 1982): Volker Schupp: Laßberg, Freiherren von. In: Neue Deutsche Biographie 13 (1982), p. 670 (https://www.deutsche-biographie.de/pnd1081141352.html#ndbcontent)</li>
        <li class="list-group-item" id="Sprague2011">(Sprague 2011) William Maurice Sprague: Lassberg, Joseph Maria Christoph, Freiherr von. In: Albrecht Classen (ed.): Handbook of Medieval Studies: Terms - Methods - Trends. Berlin 2011 (DOI: https://doi.org/10.1515/9783110215588.2450), pp. 2450-2454.</li>
        <li class="list-group-item" id="Weidhase2002">(Weidhase 2002) Helmut Weidhase: Freiherr von Lassberg oder die fruchtbringende Gelehrsamkeit: ‚Des letzten Ritters Bibliothek‘ - in Frauenfeld und Gottlieben. In: Librarium: Zeitschrift der Schweizerischen Bibliophilen Gesellschaft 45 (2002) (DOI: https://dx.doi.org/10.5169/seals-388718), pp. 31–37.</li>
    </ul>
    </div>`,
};

const AnalysisPage = {
  /* ... */
};

const routes = [
  { path: "/", component: WelcomePage },
  {
    path: "/letters",
    component: LettersPage,
    props: () => app.getData(),
  },
  { 
    path: "/letter/:id", 
    component: LetterView, 
    props: (route) => ({ 
      id: route.params.id, 
      lettersData: app.lettersData,
      personRegister: app.personRegister,
      placeRegister: app.placeRegister,
      literatureRegister: app.literatureRegister
    }) },
  { path: "/literature", component: LiteraturePage },
  { path: "/analysis", 
  beforeEnter() {
    location.href = "https://github.com/michaelscho/lassberg/blob/main/analysis/Jupyter%20Notebooks/lassberg-letters.ipynb";
  }, },
  {
    path: "/repository",
    beforeEnter() {
      location.href = "https://github.com/michaelscho/lassberg";
    },
  },
];

// Create the router instance
const router = new VueRouter({
  routes,
});

// Initialize the Vue app
// registers and letter data is loaded
const app = new Vue({
  el: "#app",
  router,
  data: {
    lettersData: [],
    personRegister: [],
    placeRegister: [],
    literatureRegister: [],
    isLoading: true,
  },
  methods: {
    loadData() {
      const lettersUrl = "json/letters_json.json";
      const personRegisterUrl = 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-persons.xml'; 
      const placeRegisterUrl = 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-places.xml'; 
      const literatureRegisterUrl = 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-literature.xml'; 
    
      Promise.all([
        axios.get(lettersUrl),
        axios.get(personRegisterUrl),
        axios.get(placeRegisterUrl),
        axios.get(literatureRegisterUrl)
      ]).then(([lettersResponse, personResponse, placeResponse, literatureResponse]) => {
        // Getting the letter data
        this.lettersData = lettersResponse.data;
        
         // Parsing register files
        this.personRegister = this.processPersonRegister(personResponse.data);
        this.placeRegister = this.processPlaceRegister(placeResponse.data);
        this.literatureRegister = this.processLiteratureRegister(literatureResponse.data);

        // Sort list of letters
        this.sortLettersData();
        this.isLoading = false;
      }).catch(error => {
        console.error("Error fetching data:", error);
      });
    },

    sortLettersData() {
      // sort letters by date, 'Unbekannt' last
      this.lettersData.sort((a, b) => {
        if (a.date === "Unbekannt" && b.date === "Unbekannt") {
          return 0;
        } else if (a.date === "Unbekannt") {
          return 1;
        } else if (b.date === "Unbekannt") {
          return -1;
        } else {
          return new Date(a.date) - new Date(b.date);
        }
      });
    },

    processPersonRegister(xmlData) {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlData, "text/xml");
      const ns = "http://www.tei-c.org/ns/1.0"; // Namespace URI
    
      const persons = xmlDoc.getElementsByTagNameNS(ns, 'person');
      return Array.from(persons).map(person => {
        const persName = person.querySelector('persName[type="main"]');
        const wikiRef = person.querySelector('ref[target]');
    
        // Accessing namespaced attribute 'xml:id'
        const personId = person.getAttributeNS("http://www.w3.org/XML/1998/namespace", "id");
    
        return {
          id: personId || 'Unknown',
          name: persName ? persName.textContent.trim() : 'Unknown',
          gnd: person.getAttribute('ref') || 'Unknown',
          wiki: wikiRef ? wikiRef.getAttribute('target') : 'Unknown',
        };
      });
    },
    
    

    processPlaceRegister(xmlData) {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlData, "text/xml");
      const ns = "http://www.tei-c.org/ns/1.0"; // Namespace URI
    
      const places = xmlDoc.getElementsByTagNameNS(ns, 'place');
      return Array.from(places).map(place => {
        const placeName = place.querySelector('placeName');
        // get @ref from placeName
        const wikiRef = placeName ? placeName.getAttribute('ref') : null;
        const desc = place.querySelector('desc');
        const placeId = place.getAttributeNS("http://www.w3.org/XML/1998/namespace", "id");
    
        return {
          id: placeId || 'Unknown',
          name: placeName ? placeName.textContent.trim() : 'Unknown',
          description: desc ? desc.textContent.trim() : 'Unknown',
          wikidata: wikiRef || 'Unknown',
          // Add other properties as per your XML structure
        };
      });
    },
    
    
    processLiteratureRegister(xmlData) {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlData, "text/xml");
      const ns = "http://www.tei-c.org/ns/1.0"; // Namespace URI
    
      const literatureItems = xmlDoc.getElementsByTagNameNS(ns, 'bibl');
      return Array.from(literatureItems).map(bibl => {
        const title = bibl.querySelector('title');
        const author = bibl.querySelector('author');
        const pubPlace = bibl.querySelector('pubPlace');
        const idNo = bibl.querySelector('idno');
        const literatureId = bibl.getAttributeNS("http://www.w3.org/XML/1998/namespace", "id");
        const date = bibl.querySelector('date');
        return {
          id: literatureId || 'Unknown',
          title: title ? title.textContent.trim() : 'Unknown',
          author: author ? author.textContent.trim() : 'Unknown',
          idno: idNo ? idNo.textContent.trim() : 'Unknown',
          date: date ? date.textContent.trim() : 'Unknown',
          pubPlace: pubPlace ? pubPlace.textContent.trim() : 'Unknown',

          // Add other bibliographic details as per your XML structure
        };
      });
    },
     

    getData() {
      return {
        lettersData: this.lettersData,
        isLoading: this.isLoading,
      };
    },
  },
  mounted() {
    this.loadData();
  },
});
