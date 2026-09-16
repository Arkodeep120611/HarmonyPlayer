(() => {
  const HP = window.HarmonyPlayer = window.HarmonyPlayer || {};
  const apiFetch = HP.apiFetch;
  const formatTime = HP.formatTime;
  const config = HP.config || {};
  const storage = {
    queue: "harmonyplayer.queue",
    volume: "harmonyplayer.volume",
    speed: "harmonyplayer.speed",
    shuffle: "harmonyplayer.shuffle",
    repeat: "harmonyplayer.repeat",
    muted: "harmonyplayer.muted",
  };

  const state = {
    catalog: [],
    catalogById: new Map(),
    queue: [],
    activeList: [],
    activeIndex: -1,
    currentSong: null,
    shuffle: localStorage.getItem(storage.shuffle) === "true",
    repeat: localStorage.getItem(storage.repeat) || "off",
    muted: localStorage.getItem(storage.muted) === "true",
    volume: Number(localStorage.getItem(storage.volume) || config.settings?.volume || 70),
    speed: Number(localStorage.getItem(storage.speed) || config.settings?.playback_speed || 1),
  };

  const audio = document.getElementById("player-audio");
  const ui = {};
  let draggingQueueIndex = null;

  function isTypingTarget(target) {
    if (!target) return false;
    const tag = target.tagName;
    return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(tag);
  }

  function songLabel(song) {
    return `${song.title} — ${song.artist}`;
  }

  function artworkGradient(seed) {
    const text = String(seed);
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
      hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
    }
    const hue = hash % 360;
    return `linear-gradient(135deg, hsl(${hue}, 84%, 58%), hsl(${(hue + 70) % 360}, 78%, 45%))`;
  }

  function initials(song) {
    const title = (song.title || "").trim();
    const artist = (song.artist || "").trim();
    const value = `${title.charAt(0)}${artist.charAt(0)}`.trim() || "♪";
    return value.slice(0, 2).toUpperCase();
  }

  function setArtwork(el, song) {
    if (!el || !song) return;
    el.style.background = artworkGradient(song.title + song.artist + song.album);
    el.innerHTML = `<span>${initials(song)}</span>`;
  }

  function setCatalog(songs) {
    state.catalog = Array.isArray(songs) ? songs.slice() : [];
    state.catalogById = new Map(state.catalog.map((song) => [Number(song.id), song]));
    hydrateQueue();
  }

  function addToCatalog(song) {
    if (!song || !song.id) return;
    const existingIndex = state.catalog.findIndex((track) => Number(track.id) === Number(song.id));
    if (existingIndex >= 0) {
      state.catalog[existingIndex] = song;
    } else {
      state.catalog.unshift(song);
    }
    state.catalogById.set(Number(song.id), song);
    if (state.activeList === state.catalog && existingIndex < 0) {
      state.activeList = state.catalog.slice();
    }
  }

  function resolveSong(songOrId) {
    if (!songOrId) return null;
    if (typeof songOrId === "object") return songOrId;
    return state.catalogById.get(Number(songOrId)) || null;
  }

  function saveQueue() {
    localStorage.setItem(storage.queue, JSON.stringify(state.queue.map((song) => song.id)));
  }

  function hydrateQueue() {
    const raw = localStorage.getItem(storage.queue);
    if (!raw) {
      state.queue = [];
      renderQueue();
      return;
    }
    try {
      const ids = JSON.parse(raw);
      state.queue = Array.isArray(ids)
        ? ids.map((id) => resolveSong(id)).filter(Boolean)
        : [];
    } catch (_error) {
      state.queue = [];
    }
    renderQueue();
  }

  function syncControls() {
    if (ui.volume) ui.volume.value = String(state.volume);
    if (ui.speed) ui.speed.value = String(state.speed);
    if (ui.mute) ui.mute.textContent = state.muted ? "Unmute" : "Mute";
    if (ui.shuffle) ui.shuffle.classList.toggle("is-active", state.shuffle);
    if (ui.repeat) ui.repeat.textContent = state.repeat === "off" ? "↻" : state.repeat === "all" ? "↻1" : "↻∞";
  }

  function persistSettings() {
    localStorage.setItem(storage.volume, String(state.volume));
    localStorage.setItem(storage.speed, String(state.speed));
    localStorage.setItem(storage.shuffle, String(state.shuffle));
    localStorage.setItem(storage.repeat, String(state.repeat));
    localStorage.setItem(storage.muted, String(state.muted));
    apiFetch("/api/settings", {
      method: "PUT",
      json: {
        theme: document.documentElement.dataset.theme || "dark",
        volume: state.volume,
        playback_speed: state.speed,
      },
    }).catch(() => {});
  }

  function updatePlayerChrome(song) {
    ui.title.textContent = song ? song.title : "Nothing selected";
    ui.meta.textContent = song ? `${song.artist} • ${song.album}` : "Add a song from your library.";
    if (song) {
      setArtwork(ui.artwork, song);
    } else {
      ui.artwork.style.background = "linear-gradient(135deg, #7c6cff, #22c1c3)";
      ui.artwork.innerHTML = "<span>♪</span>";
    }
  }

  function renderQueue() {
    if (!ui.queueList) return;
    ui.queueList.innerHTML = "";
    if (!state.queue.length) {
      const empty = document.createElement("div");
      empty.className = "queue-item";
      empty.innerHTML = '<div><div class="queue-item-title">Queue is empty</div><div class="queue-item-meta">Add songs from the library.</div></div>';
      ui.queueList.appendChild(empty);
      return;
    }
    state.queue.forEach((song, index) => {
      const item = document.createElement("div");
      item.className = "queue-item";
      item.draggable = true;
      item.dataset.index = String(index);
      item.innerHTML = `
        <div>
          <div class="queue-item-title">${song.title}</div>
          <div class="queue-item-meta">${song.artist}</div>
        </div>
        <div class="button-row">
          <button class="button button-secondary button-small" type="button" data-queue-play="${index}">Play</button>
          <button class="button button-secondary button-small" type="button" data-queue-remove="${index}">Remove</button>
        </div>
      `;
      ui.queueList.appendChild(item);
    });
  }

  function setTransportState() {
    if (!ui.play) return;
    ui.play.textContent = audio.paused ? "▶" : "⏸";
    ui.play.setAttribute("aria-label", audio.paused ? "Play" : "Pause");
  }

  function setProgress() {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    ui.currentTime.textContent = formatTime(current);
    ui.totalTime.textContent = formatTime(duration);
    ui.seek.value = duration > 0 ? String((current / duration) * 1000) : "0";
  }

  async function playResolvedSong(song, contextList = null, preserveContext = false) {
    const resolved = resolveSong(song);
    if (!resolved) return;
    if (!preserveContext) {
      state.activeList = Array.isArray(contextList) && contextList.length ? contextList.slice() : state.catalog.slice();
      state.activeIndex = state.activeList.findIndex((track) => Number(track.id) === Number(resolved.id));
      if (state.activeIndex < 0) {
        state.activeList.unshift(resolved);
        state.activeIndex = 0;
      }
    } else if (!state.activeList.length) {
      state.activeList = state.catalog.slice();
      state.activeIndex = state.activeList.findIndex((track) => Number(track.id) === Number(resolved.id));
    }
    state.currentSong = resolved;
    audio.src = resolved.stream_url;
    audio.playbackRate = state.speed;
    audio.volume = state.muted ? 0 : state.volume / 100;
    audio.muted = state.muted;
    updatePlayerChrome(resolved);
    setTransportState();
    await audio.play();
  }

  function shuffleList(list) {
    const copy = list.slice();
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function playFromList(list, index = 0, shuffle = false) {
    const songs = Array.isArray(list) ? list.map(resolveSong).filter(Boolean) : [];
    if (!songs.length) return;
    const ordered = shuffle ? shuffleList(songs) : songs;
    state.activeList = ordered;
    state.activeIndex = Math.max(0, Math.min(index, ordered.length - 1));
    playResolvedSong(ordered[state.activeIndex], ordered);
  }

  function nextTrack() {
    if (state.queue.length) {
      playQueueItem(0);
      return;
    }
    if (!state.activeList.length) return;
    if (state.repeat === "one" && state.currentSong) {
      playResolvedSong(state.currentSong, state.activeList, true);
      return;
    }
    if (state.shuffle) {
      const candidates = state.activeList.filter((song) => !state.currentSong || Number(song.id) !== Number(state.currentSong.id));
      const pool = candidates.length ? candidates : state.activeList;
      const randomSong = pool[Math.floor(Math.random() * pool.length)];
      if (randomSong) {
        state.activeIndex = state.activeList.findIndex((song) => Number(song.id) === Number(randomSong.id));
        playResolvedSong(randomSong, state.activeList, true);
      }
      return;
    }
    let nextIndex = state.activeIndex + 1;
    if (nextIndex >= state.activeList.length) {
      if (state.repeat === "all") {
        nextIndex = 0;
      } else {
        audio.pause();
        setTransportState();
        return;
      }
    }
    state.activeIndex = nextIndex;
    playResolvedSong(state.activeList[state.activeIndex], state.activeList, true);
  }

  function previousTrack() {
    if (!state.activeList.length) return;
    if (audio.currentTime > 3) {
      audio.currentTime = 0;
      return;
    }
    const prevIndex = state.activeIndex > 0 ? state.activeIndex - 1 : (state.repeat === "all" ? state.activeList.length - 1 : 0);
    state.activeIndex = prevIndex;
    playResolvedSong(state.activeList[prevIndex], state.activeList, true);
  }

  function enqueue(song, playNext = false) {
    const resolved = resolveSong(song);
    if (!resolved) return;
    if (playNext) {
      state.queue.splice(0, 0, resolved);
    } else {
      state.queue.push(resolved);
    }
    saveQueue();
    renderQueue();
  }

  function playQueueItem(index) {
    const song = state.queue[index];
    if (!song) return;
    state.queue.splice(index, 1);
    saveQueue();
    renderQueue();
    playResolvedSong(song, state.activeList, true);
  }

  function removeQueueItem(index) {
    state.queue.splice(index, 1);
    saveQueue();
    renderQueue();
  }

  function clearQueue() {
    state.queue = [];
    saveQueue();
    renderQueue();
  }

  function setRepeat(nextValue) {
    state.repeat = nextValue;
    syncControls();
    persistSettings();
  }

  function cycleRepeat() {
    const order = ["off", "all", "one"];
    const nextIndex = (order.indexOf(state.repeat) + 1) % order.length;
    setRepeat(order[nextIndex]);
  }

  function setShuffle(enabled) {
    state.shuffle = Boolean(enabled);
    syncControls();
    persistSettings();
  }

  function toggleMute() {
    state.muted = !state.muted;
    audio.muted = state.muted;
    audio.volume = state.muted ? 0 : state.volume / 100;
    syncControls();
    persistSettings();
  }

  function setVolume(volume) {
    state.volume = Math.max(0, Math.min(100, Number(volume)));
    audio.volume = state.muted ? 0 : state.volume / 100;
    syncControls();
    persistSettings();
  }

  function setSpeed(speed) {
    state.speed = Math.max(0.5, Math.min(2, Number(speed)));
    audio.playbackRate = state.speed;
    syncControls();
    persistSettings();
  }

  function updateTheme(theme) {
    document.documentElement.dataset.theme = theme === "light" ? "light" : "dark";
    persistSettings();
  }

  function bindDom() {
    ui.play = document.getElementById("player-play-btn");
    ui.prev = document.getElementById("player-prev-btn");
    ui.next = document.getElementById("player-next-btn");
    ui.shuffle = document.getElementById("player-shuffle-btn");
    ui.repeat = document.getElementById("player-repeat-btn");
    ui.clearQueue = document.getElementById("player-clear-queue-btn");
    ui.mute = document.getElementById("player-mute-btn");
    ui.volume = document.getElementById("player-volume");
    ui.speed = document.getElementById("player-speed");
    ui.seek = document.getElementById("player-seek");
    ui.currentTime = document.getElementById("player-current-time");
    ui.totalTime = document.getElementById("player-total-time");
    ui.title = document.getElementById("player-track-title");
    ui.meta = document.getElementById("player-track-meta");
    ui.artwork = document.getElementById("player-artwork");
    ui.queueList = document.getElementById("player-queue-list");

    if (ui.play) ui.play.addEventListener("click", () => (audio.paused ? audio.play() : audio.pause()));
    if (ui.prev) ui.prev.addEventListener("click", previousTrack);
    if (ui.next) ui.next.addEventListener("click", nextTrack);
    if (ui.shuffle) ui.shuffle.addEventListener("click", () => setShuffle(!state.shuffle));
    if (ui.repeat) ui.repeat.addEventListener("click", cycleRepeat);
    if (ui.clearQueue) ui.clearQueue.addEventListener("click", clearQueue);
    if (ui.mute) ui.mute.addEventListener("click", toggleMute);
    if (ui.volume) ui.volume.addEventListener("input", (event) => setVolume(event.target.value));
    if (ui.speed) ui.speed.addEventListener("change", (event) => setSpeed(event.target.value));
    if (ui.seek) {
      ui.seek.addEventListener("input", () => {
        if (Number.isFinite(audio.duration) && audio.duration > 0) {
          audio.currentTime = (Number(ui.seek.value) / 1000) * audio.duration;
        }
      });
    }
    if (ui.queueList) {
      ui.queueList.addEventListener("click", (event) => {
        const playIndex = event.target.closest("[data-queue-play]")?.dataset.queuePlay;
        const removeIndex = event.target.closest("[data-queue-remove]")?.dataset.queueRemove;
        if (playIndex !== undefined) playQueueItem(Number(playIndex));
        if (removeIndex !== undefined) removeQueueItem(Number(removeIndex));
      });
      ui.queueList.addEventListener("dragstart", (event) => {
        const item = event.target.closest(".queue-item");
        if (!item) return;
        draggingQueueIndex = Number(item.dataset.index);
        event.dataTransfer.effectAllowed = "move";
      });
      ui.queueList.addEventListener("dragover", (event) => {
        event.preventDefault();
        const item = event.target.closest(".queue-item");
        if (item) item.classList.add("drag-over");
      });
      ui.queueList.addEventListener("dragleave", (event) => {
        event.target.closest(".queue-item")?.classList.remove("drag-over");
      });
      ui.queueList.addEventListener("drop", (event) => {
        event.preventDefault();
        const target = event.target.closest(".queue-item");
        if (!target || draggingQueueIndex === null) return;
        const targetIndex = Number(target.dataset.index);
        const [moved] = state.queue.splice(draggingQueueIndex, 1);
        state.queue.splice(targetIndex, 0, moved);
        saveQueue();
        renderQueue();
        draggingQueueIndex = null;
      });
    }
  }

  function attachKeyboardShortcuts() {
    document.addEventListener("keydown", (event) => {
      if (isTypingTarget(event.target)) return;
      if (event.code === "Space") {
        event.preventDefault();
        audio.paused ? audio.play() : audio.pause();
      } else if (event.key.toLowerCase() === "n") {
        event.preventDefault();
        nextTrack();
      } else if (event.key.toLowerCase() === "p") {
        event.preventDefault();
        previousTrack();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        audio.currentTime = Math.max(0, audio.currentTime - 5);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        audio.currentTime = Math.min(audio.duration || audio.currentTime + 5, audio.currentTime + 5);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setVolume(state.volume + 5);
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setVolume(state.volume - 5);
      }
    });
  }

  async function initCatalog() {
    const embedded = HP.pageData && Array.isArray(HP.pageData.songs) ? HP.pageData.songs : null;
    if (embedded && embedded.length) {
      setCatalog(embedded);
      return;
    }
    try {
      const response = await apiFetch("/api/songs");
      const data = await response.json();
      setCatalog(data.songs || []);
    } catch (_error) {
      setCatalog([]);
    }
  }

  function initAudioEvents() {
    audio.addEventListener("play", setTransportState);
    audio.addEventListener("pause", setTransportState);
    audio.addEventListener("loadedmetadata", setProgress);
    audio.addEventListener("timeupdate", setProgress);
    audio.addEventListener("durationchange", setProgress);
    audio.addEventListener("ended", nextTrack);
  }

  function initFromSettings() {
    const settings = config.settings || {};
    setVolume(Number(settings.volume ?? state.volume));
    setSpeed(Number(settings.playback_speed ?? state.speed));
    state.muted = localStorage.getItem(storage.muted) === "true";
    state.shuffle = localStorage.getItem(storage.shuffle) === "true";
    state.repeat = localStorage.getItem(storage.repeat) || "off";
    syncControls();
  }

  HP.player = {
    playSong: playResolvedSong,
    playList: playFromList,
    enqueue,
    playQueueItem,
    removeQueueItem,
    clearQueue,
    nextTrack,
    previousTrack,
    setShuffle,
    setRepeat,
    toggleMute,
    setVolume,
    setSpeed,
    updateTheme,
    addToCatalog,
    getCatalog: () => state.catalog.slice(),
    getQueue: () => state.queue.slice(),
    getCurrentSong: () => state.currentSong,
    getPlaylistOrder: () => state.activeList.slice(),
  };

  HP.playerReady = false;
  HP.whenReady = (callback) => {
    if (HP.playerReady) {
      callback(HP.player);
      return;
    }
    document.addEventListener("harmonyplayer:ready", () => callback(HP.player), { once: true });
  };

  document.addEventListener("DOMContentLoaded", async () => {
    if (!audio) return;
    bindDom();
    initAudioEvents();
    attachKeyboardShortcuts();
    initFromSettings();
    syncControls();
    await initCatalog();
    hydrateQueue();
    if (state.catalog.length && !state.activeList.length) {
      state.activeList = state.catalog.slice();
    }
    HP.playerReady = true;
    document.dispatchEvent(new CustomEvent("harmonyplayer:ready", { detail: { player: HP.player } }));
  });
})();
