(() => {
  const HP = window.HarmonyPlayer = window.HarmonyPlayer || {};
  const apiFetch = HP.apiFetch;
  const pageSongs = (() => {
    const el = document.getElementById("library-data");
    if (!el) return [];
    try {
      return JSON.parse(el.textContent || "[]");
    } catch (_error) {
      return [];
    }
  })();
  const pagePlaylists = (() => {
    const el = document.getElementById("library-playlists");
    if (!el) return [];
    try {
      return JSON.parse(el.textContent || "[]");
    } catch (_error) {
      return [];
    }
  })();

  const state = {
    songs: pageSongs,
    playlists: pagePlaylists,
    filtered: pageSongs.slice(),
    dialogSong: null,
  };

  const els = {};

  function artworkGradient(seed) {
    let hash = 0;
    for (let i = 0; i < seed.length; i += 1) {
      hash = (hash * 33 + seed.charCodeAt(i)) >>> 0;
    }
    const hue = hash % 360;
    return `linear-gradient(135deg, hsl(${hue}, 78%, 56%), hsl(${(hue + 60) % 360}, 74%, 44%))`;
  }

  function initials(song) {
    return `${(song.title || "S").charAt(0)}${(song.artist || "A").charAt(0)}`.toUpperCase();
  }

  function renderSelectOptions(select, items, kind) {
    if (!select) return;
    select.innerHTML = `<option value="">All ${kind}s</option>`;
    const seen = new Set();
    items.forEach((song) => {
      const value = kind === "artist" ? song.artist : song.album;
      if (!value || seen.has(value)) return;
      seen.add(value);
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }

  function populateFilters() {
    renderSelectOptions(els.artistFilter, state.songs, "artist");
    renderSelectOptions(els.albumFilter, state.songs, "album");
  }

  function readFilters() {
    return {
      search: (els.search?.value || "").trim().toLowerCase(),
      sort: els.sort?.value || "recent",
      artist: els.artistFilter?.value || "",
      album: els.albumFilter?.value || "",
    };
  }

  function applyFilters() {
    const filters = readFilters();
    let songs = state.songs.slice();
    if (filters.search) {
      songs = songs.filter((song) =>
        [song.title, song.artist, song.album].some((value) => String(value || "").toLowerCase().includes(filters.search))
      );
    }
    if (filters.artist) songs = songs.filter((song) => song.artist === filters.artist);
    if (filters.album) songs = songs.filter((song) => song.album === filters.album);
    songs.sort((a, b) => {
      switch (filters.sort) {
        case "title":
          return a.title.localeCompare(b.title);
        case "artist":
          return a.artist.localeCompare(b.artist);
        case "album":
          return a.album.localeCompare(b.album);
        case "duration":
          return (a.duration || 0) - (b.duration || 0);
        default:
          return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      }
    });
    state.filtered = songs;
    renderSongs();
  }

  function renderSongs() {
    if (!els.grid || !els.empty) return;
    els.grid.innerHTML = "";
    if (!state.filtered.length) {
      els.empty.hidden = false;
      return;
    }
    els.empty.hidden = true;
    state.filtered.forEach((song) => {
      const card = document.createElement("article");
      card.className = "panel library-card";
      card.innerHTML = `
        <div class="card-body">
          <div class="artwork artwork-small" aria-hidden="true"><span>${initials(song)}</span></div>
          <div class="song-meta">
            <h3 class="song-title">${song.title}</h3>
            <div class="song-artist">${song.artist}</div>
            <div class="song-album">${song.album}</div>
            <div class="song-artist">${song.duration_label}</div>
          </div>
        </div>
        <div class="track-actions">
          <button class="button button-primary" type="button" data-play="${song.id}">Play</button>
          <button class="button button-secondary" type="button" data-queue="${song.id}">Queue</button>
          <button class="button button-secondary" type="button" data-play-next="${song.id}">Play next</button>
          <button class="button button-secondary" type="button" data-add-playlist="${song.id}">Add to playlist</button>
        </div>
      `;
      card.querySelector("[data-play]")?.addEventListener("click", () => HP.player.playSong(song, state.songs));
      card.querySelector("[data-queue]")?.addEventListener("click", () => HP.player.enqueue(song));
      card.querySelector("[data-play-next]")?.addEventListener("click", () => HP.player.enqueue(song, true));
      card.querySelector("[data-add-playlist]")?.addEventListener("click", () => openPlaylistDialog(song));
      card.querySelector(".artwork").style.background = artworkGradient(song.title + song.artist + song.album);
      els.grid.appendChild(card);
    });
  }

  function openPlaylistDialog(song) {
    state.dialogSong = song;
    if (els.dialogSongLabel) els.dialogSongLabel.textContent = `${song.title} — ${song.artist}`;
    if (els.playlistTarget) {
      els.playlistTarget.innerHTML = "";
      state.playlists.forEach((playlist) => {
        const option = document.createElement("option");
        option.value = String(playlist.id);
        option.textContent = playlist.name;
        els.playlistTarget.appendChild(option);
      });
    }
    if (els.dialog) els.dialog.showModal();
  }

  async function addSongToPlaylist() {
    if (!state.dialogSong || !els.playlistTarget) return;
    const playlistId = els.playlistTarget.value;
    if (!playlistId) return;
    const response = await apiFetch(`/api/playlists/${playlistId}/songs`, {
      method: "POST",
      json: { song_id: state.dialogSong.id },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Unable to update playlist.");
    }
    els.dialog?.close();
  }

  function enhanceUpload() {
    if (!els.uploadForm) return;
    els.uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = els.uploadStatus;
      if (status) status.textContent = "Uploading...";
      const formData = new FormData(els.uploadForm);
      try {
        const response = await apiFetch("/api/upload", { method: "POST", body: formData });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Upload failed.");
        state.songs.unshift(payload);
        HP.player?.addToCatalog?.(payload);
        populateFilters();
        applyFilters();
        els.uploadForm.reset();
        if (status) status.textContent = `Uploaded ${payload.title}.`;
      } catch (error) {
        if (status) status.textContent = error.message;
      }
    });
  }

  function bind() {
    els.search = document.getElementById("library-search");
    els.sort = document.getElementById("library-sort");
    els.artistFilter = document.getElementById("library-filter-artist");
    els.albumFilter = document.getElementById("library-filter-album");
    els.grid = document.getElementById("library-grid");
    els.empty = document.getElementById("library-empty");
    els.dialog = document.getElementById("playlist-dialog");
    els.dialogSongLabel = document.getElementById("playlist-dialog-song");
    els.playlistTarget = document.getElementById("playlist-target");
    els.uploadForm = document.getElementById("upload-form");
    els.uploadStatus = document.getElementById("upload-status");

    [els.search, els.sort, els.artistFilter, els.albumFilter].forEach((control) => {
      control?.addEventListener("input", applyFilters);
      control?.addEventListener("change", applyFilters);
    });
    document.getElementById("playlist-dialog-save")?.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        await addSongToPlaylist();
      } catch (error) {
        if (els.uploadStatus) els.uploadStatus.textContent = error.message;
      }
    });
  }

  document.addEventListener("harmonyplayer:ready", () => {
    state.songs = HP.player.getCatalog().length ? HP.player.getCatalog() : state.songs;
    state.playlists = pagePlaylists.length ? pagePlaylists : state.playlists;
    bind();
    populateFilters();
    applyFilters();
    enhanceUpload();
  }, { once: true });
})();
