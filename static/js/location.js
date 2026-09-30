document.addEventListener('DOMContentLoaded', function () {
  const button = document.getElementById('detect-location-btn');
  if (!button) return;

  button.addEventListener('click', function () {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported in this browser. Please enter coordinates manually.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      function (position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        document.getElementById('latitude-field').value = latitude;
        document.getElementById('longitude-field').value = longitude;

        fetch('/api/location', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ latitude, longitude })
        }).then(function (res) {
          return res.json();
        }).then(function (data) {
          if (data.success) {
            alert('Location detected and saved successfully.');
          } else {
            alert(data.message || 'Could not save location.');
          }
        }).catch(function () {
          alert('Location is available, but the server request failed.');
        });
      },
      function () {
        alert('Location permission was denied. You can still enter coordinates manually.');
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  });
});
