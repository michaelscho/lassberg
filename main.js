new Vue({
    el: '#app',
    data: {
      csvData: null,
      tableColumns: ['Nummer', 'Datum', 'Ort', 'vonAn', 'Name_voll', 'GND', 'Wiki', 'Journalnummer', 'Aufbewahrungsort', 'Aufbewahrungsinstitution', 'Jahr', 'text', 'url', 'place_id', 'date', 'letter_text', 'status_letter_text']
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
      // Lifecycle hook to load data when the app is mounted
      this.loadData();
    },
  });
  