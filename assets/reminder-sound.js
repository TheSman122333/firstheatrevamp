// FirstHeat break-reminder chime.
// The app starts the page title with an alarm clock (U+23F0) while a break
// reminder is showing. Flet has no audio control in its web client, so this
// script watches the title and plays a short chime with the Web Audio API.
(function () {
  var ctx = null;
  var repeat = null;

  // browsers only allow sound after the user has tapped the page
  function unlock() {
    if (!ctx) {
      try {
        ctx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (error) {
        return;
      }
    }

    if (ctx.state === "suspended") {
      ctx.resume();
    }
  }

  ["pointerdown", "touchstart", "keydown"].forEach(function (type) {
    document.addEventListener(type, unlock, true);
  });

  // three rising notes
  function chime() {
    if (navigator.vibrate) {
      navigator.vibrate([250, 120, 250]);
    }

    if (!ctx) {
      return;
    }

    var start = ctx.currentTime;

    [880, 1175, 1568].forEach(function (frequency, index) {
      var at = start + index * 0.18;
      var tone = ctx.createOscillator();
      var volume = ctx.createGain();

      tone.type = "sine";
      tone.frequency.value = frequency;
      volume.gain.setValueAtTime(0.0001, at);
      volume.gain.exponentialRampToValueAtTime(0.3, at + 0.02);
      volume.gain.exponentialRampToValueAtTime(0.0001, at + 0.4);

      tone.connect(volume);
      volume.connect(ctx.destination);
      tone.start(at);
      tone.stop(at + 0.45);
    });
  }

  // chime now and every 5 seconds while the reminder is up
  function check() {
    var reminding = document.title.indexOf("⏰") === 0;

    if (reminding && !repeat) {
      chime();
      repeat = setInterval(chime, 5000);
    }

    if (!reminding && repeat) {
      clearInterval(repeat);
      repeat = null;
    }
  }

  setInterval(check, 500);
})();
