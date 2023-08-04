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
  props: ["csvData"],
  template: `
  <div>
    <h1 class="my-4">The Lassberg Letters</h1>
    <h2 class="my-4">Register</h2>
    <p>{{ filteredDataCount }} letters selected. Click on date for further information.</p>
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">Date<input v-model="filters.date" type="text"/></th>

          <th scope="col">From/To Laßberg<input v-model="filters.fromTo" type="text"/></th>

          <th scope="col">Name (GND)<input v-model="filters.name" type="text"/></th>
          
          <th scope="col">Place<input v-model="filters.place" type="text"/></th>

          <th scope="col">Provenance<input v-model="filters.provenance" type="text"/></th>

          <th scope="col">Persons<input v-model="filters.persons" type="text"/></th>

          <th scope="col">Topics<input v-model="filters.topics" type="text"/></th>

  
        </tr>
      </thead>

      <tbody>
      <tr v-for="(item, id) in filteredData" :key="id" >

          <td><router-link :to="'/letter/' + item.ID">{{ item.Datum }}</router-link><template v-if="item.normalized_text !== ''"><img
          src="img/green_checkmark.svg"
          height="12"
          width="12"/>
        </template></td>
          <td>{{ item['VON/AN'] === 'VON' ? 'from Laßberg' : 'to Laßberg' }}</td>

          <td>
          <!-- Case 1: Name has a wiki URL and a GND number -->
          <template v-if="item.Wiki !== '-' && item.GND !== '-'">
            <a :href="item.Wiki">{{ item.Name }}</a>
            <span class="ml-2">
              <a :href="'https://lobid.org/gnd/' + item.GND">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
              </a>
            </span>
          </template>
        
          <!-- Case 2: Name has no wiki page but a GND number -->
          <template v-else-if="item.Wiki === '-' && item.GND !== '-'">
            {{ item.Name }}
            <span class="ml-2">
              <a :href="'https://lobid.org/gnd/' + item.GND">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12">
              </a>
            </span>
          </template>
        
          <!-- Case 3: Name has no wiki page and no GND number -->
          <template v-else>
            {{ item.Name }}
          </template>
        </td>
        
          
          <td>{{ item.Ort }}</td>
          
          <td>{{ item.Aufbewahrungsort || '' }}, {{ item.Aufbewahrungsinstitution  || '' }}</td>

          <td>{{ item.persons_mentioned }}</td>

          <td>{{ item.topics_mentioned }}</td>
          
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
        name: "",
        provenance: "",
        persons: "",
        topics: "",
        fromTo: "",
      },
    };
  },
  methods: {
    

  },

  computed: {
    filteredData() {
      if (!this.csvData) {
        return [];
      }
      return this.csvData.filter((item) => {
        return (
          item.Datum &&
          item.Datum.toLowerCase().includes(this.filters.date.toLowerCase()) &&
          item.Ort.toLowerCase().includes(this.filters.place.toLowerCase()) &&
          item.Name.toLowerCase().includes(this.filters.name.toLowerCase()) &&
          item.persons_mentioned.toLowerCase().includes(this.filters.persons.toLowerCase()) &&
          item.topics_mentioned.toLowerCase().includes(this.filters.topics.toLowerCase()) &&
          (item.Aufbewahrungsort + ", " + item.Aufbewahrungsinstitution)
            .toLowerCase()
            .includes(this.filters.provenance.toLowerCase()) &&
          item["VON/AN"]
            .toLowerCase()
            .includes(this.filters.fromTo.toLowerCase())
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
  props: ["id", "csvData"],
  data() {
    return {
      letter: {},
    };
  },
  mounted() {
    this.findLetterById();
  },
  methods: {
    findLetterById() {
      this.letter = this.csvData.find(item => item.ID === this.id);
      if (!this.letter) {
        console.error('Letter not found with ID:', this.id);
      }
    },
  },
  template: `
    <div>
      <h1 class="my-4">{{ letter['VON/AN'] === 'VON' ?  'Joseph von Laßberg': letter.Name }} to {{ letter['VON/AN'] === 'VON' ? letter.Name : 'Joseph von Laßberg' }} ({{ letter.Datum === "Unbekannt" ? "Unknown" : new Date(letter.Datum).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' }) }})</h1>
      <p><strong>Date:</strong> {{ letter.Datum }}</p>
      <p><strong>Name:</strong> {{ letter.Name }}</p>
      <p><strong>Place:</strong> {{ letter.Ort }}</p>
      <p><strong>Journal:</strong> {{ letter.Journalnummer }}</p>
      <p><strong>Harris 1991:</strong> {{ letter.Nummer_Harris }}</p>
      <p><strong>Provenance:</strong> {{ letter.Aufbewahrungsort || '' }}, {{ letter.Aufbewahrungsinstitution  || '' }}</p>
      <p><strong>Printed:</strong> <a :href="letter.url">{{ letter.text }}</a></p>
      <p><strong>Summary:</strong> {{ letter.summary_en }} (<i>This summary was automatically created using GPT 4.</i>)</p>
      <p><strong>Text:</strong> {{ letter.letter_text }}</p>
      <p><strong>Normalized Text:</strong> {{ letter.normalized_text }} (<i>This normalization was automatically created using GPT 4.</i>)</p>

      <p><router-link to="/letters">Back to Letters</router-link></p>
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
  { path: "/letter/:id", component: LetterView, props: (route) => ({ id: route.params.id, csvData: app.csvData }) },
  { path: "/literature", component: LiteraturePage },
  { path: "/analysis", component: AnalysisPage },
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
const app = new Vue({
  el: "#app",
  router,
  data: {
    csvData: [],
    isLoading: true,
  },
  methods: {
    loadData() {
      axios
        .get("data/register/register_for_web.csv")
        .then((response) => {
          this.csvData = Papa.parse(response.data, { header: true }).data;

          // sort by date, 'Unbekannt' last
          this.csvData.sort((a, b) => {
            if (a.Datum === "Unbekannt" && b.Datum === "Unbekannt") {
              return 0;
            } else if (a.Datum === "Unbekannt") {
              return 1;
            } else if (b.Datum === "Unbekannt") {
              return -1;
            } else {
              return new Date(a.Datum) - new Date(b.Datum);
            }
          });

          console.log(this.csvData);
          this.isLoading = false;
        })
        .catch((error) => {
          console.error("Error fetching CSV data:", error);
        });
    },
    getData() {
      return {
        csvData: this.csvData,
        isLoading: this.isLoading,
      };
    },
  },
  mounted() {
    this.loadData();
  },
});
