document.addEventListener('DOMContentLoaded', function () {
  const button = document.getElementById('use-current-weather');
  if (!button) return;

  button.addEventListener('click', function () {
    fetch('/api/weather')
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (!data.success || !data.weather || !data.weather.current) {
          alert(data.message || 'Weather data is unavailable.');
          return;
        }
        const current = data.weather.current;
        const temperatureField = document.querySelector('input[name="temperature"]');
        const humidityField = document.querySelector('input[name="humidity"]');
        const rainfallField = document.querySelector('input[name="rainfall"]');

        if (temperatureField) temperatureField.value = current.temperature ?? '';
        if (humidityField) humidityField.value = current.humidity ?? '';
        // Crop model rainfall represents a dataset climate feature, not current precipitation.

        alert('Temperature and humidity were filled. Enter rainfall for the appropriate crop-season period; current precipitation is not equivalent.');
      })
      .catch(function () {
        alert('Unable to fetch weather for the current location.');
      });
  });
});
