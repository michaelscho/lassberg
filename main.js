new Vue({
    el: '#app',
    data: {
      // Your data properties will be placed here
    },
    methods: {
        loadData() {
          axios.get('data\register\final_register.csv')
            .then(response => {
              this.csvData = Papa.parse(response.data, { header: true }).data;
            })
            .catch(error => {
              console.error('Error fetching CSV data:', error);
            });
          
    },
    },
    mounted() {
      // Lifecycle hook to load data when the app is mounted
      this.loadData();
    },
  });
  