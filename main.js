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
    
                ` };
const LettersPage = { 
    template: `
  <div>
    <h1 class="my-4">The Lassberg Letters</h1>
    <h2 class="my-4">Enriched Register</h2>
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">Number</th>
          <th scope="col">Date</th>
          <th scope="col">Place</th>
          <th scope="col">Name (GND)</th>
          <th scope="col">Provenance</th>
          <th scope="col">From/To Lassberg</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in csvData" :key="item.id">
          <td>{{ item.Nummer }}</td>
          <td>{{ item.date }}</td>
          <td>{{ item.Ort }}</td>
          <td v-if="item.Wiki !== '-'">
            <a :href="item.Wiki">{{ item.Name_voll }}</a>
            <span v-if="item.GND !== '-'" class="ml-2">
              <a :href="'https://lobid.org/gnd/' + item.GND"><img src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" alt="GND Icon" height="12"></a>
            </span>
          </td>
          <td v-else>
            {{ item.Name_voll }} ({{ item.GND }})
          </td>
          <td>{{ item.Aufbewahrungsort }}, {{ item.Aufbewahrungsinstitution }}</td>
          <td>{{ item['VON/AN'] }}</td>
        </tr>
      </tbody>
    </table>
  </div>
`,
data() {
    return {
        csvData: []
    };
},
methods: {
    loadData() {
        axios.get('data/register/final_register.csv')
            .then(response => {
                this.csvData = Papa.parse(response.data, { header: true }).data;
                console.log(this.csvData);
            })
            .catch(error => {
                console.error('Error fetching CSV data:', error);
            });
    }
},
mounted() {
    this.loadData();
},

     };

const LetterView = { /* ... */ };
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
    </div>`

    };

const AnalysisPage = { /* ... */ };

// Define your routes
const routes = [
    { path: '/', component: WelcomePage },
    { path: '/letters', component: LettersPage },
    { path: '/letters/:id', component: LetterView },
    { path: '/literature', component: LiteraturePage },
    { path: '/analysis', component: AnalysisPage },
    { path: '/repository', beforeEnter() { location.href = 'https://github.com/michaelscho/lassberg' } }
];

// Create the router instance
const router = new VueRouter({
    routes
});

// Initialize the Vue app
const app = new Vue({
    el: '#app',
    router,
    data: {
    },
    methods: {

    },
    mounted() {
        // Lifecycle hook to load data when the app is mounted
    },
});
