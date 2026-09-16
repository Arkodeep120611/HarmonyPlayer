(() => {
  const HP = window.HarmonyPlayer = window.HarmonyPlayer || {};
  const apiFetch = HP.apiFetch;
  const playlist = (() => {
    const el = document.getElementById("playlist-page-data");
    if (!el) return null;
    try { return JSON.parse(el.textContent || "{}"); } catch (_error) { return null; }
  })();
  const availableSongs = (() => {
    const el = document.getElementById("playlist-available-data");
    if (!el) return [];
    try { return JSON.parse(el.textContent || "[]"); } catch (_error) { return []; }
  })();

  const elements = {
    songList: document.getElementById("playlist-song-list"),
    playBtn: document.getElementById("playlist-play-btn"),
    shuffleBtn: document.getElementById("playlist-shuffle-btn"),
    renameBtn: document.getElementById("playlist-rename-btn"),
    deleteBtn: document.getElementById("playlist-delete-btn"),
    addSongsBtn: document.getElementById("playlist-add-songs-btn"),
    songPicker: document.getElementById("playlist-song-picker"),
  };

  function artworkGradient(seed) {
    let hash = 0;
    for (let i = 0; i < seed.length; i += 1) hash = (hash * 29 + seed.charCodeAt(i)) >>> 0;
    const hue = hash % 360;
    return `linear-gradient(135deg, hsl(${hue}, 78%, 56%), hsl(${(hue + 50) % 360}, 70%, 44%))`;
  }

  function renderPlaylistSongs() {
    if (!playlist || !elements.songList) return;
    elements.songList.innerHTML = "";
    if (!playlist.songs || !playlist.songs.length) {
      elements.songList.innerHTML = '<div class="empty-state"><h3>No songs in this playlist</h3><p>Add tracks from the selector above.</p></div>';
      return;
    }
    playlist.songs.forEach((song) => {
      const row = document.createElement("div");
      row.className = "playlist-row";
      row.innerHTML = `
        <div class="artwork artwork-small"><span>${(song.title || "?").charAt(0)}${(song.artist || "?").charAt(0)}</span></div>
        <div>
          <strong>${song.title}</strong>
          <div class="song-artist">${song.artist} • ${song.album}</div>
        </div>
        <div class="actions">
          <button class="button button-secondary button-small" type="button" data-play-song="${song.id}">Play</button>
          <button class="button button-secondary button-small" type="button" data-remove-song="${song.id}">Remove</button>
        </div>
      `;
      row.querySelector(".artwork").style.background = artworkGradient(song.title + song.artist + song.album);
      row.querySelector("[data-play-song]")?.addEventListener("click", () => HP.player.playSong(song, playlist.songs));
      row.querySelector("[data-remove-song]")?.addEventListener("click", () => removeSong(song.id));
      elements.songList.appendChild(row);
    });
  }

  async function addSongs() {
    if (!playlist || !elements.songPicker) return;
    const selected = Array.from(elements.songPicker.selectedOptions).map((option) => Number(option.value));
    if (!selected.length) return;
    const response = await apiFetch(`/api/playlists/${playlist.id}/songs`, {
      method: "POST",
      json: { song_ids: selected },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to add songs.");
    playlist.songs = payload.playlist.songs || playlist.songs;
    renderPlaylistSongs();
  }

  async function removeSong(songId) {
    if (!playlist) return;
    const response = await apiFetch(`/api/playlists/${playlist.id}/songs/${songId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to remove song.");
    playlist.songs = playlist.songs.filter((song) => Number(song.id) !== Number(songId));
    renderPlaylistSongs();
  }

  async function renamePlaylist() {
    if (!playlist) return;
    const nextName = window.prompt("Rename playlist", playlist.name);
    if (!nextName || !nextName.trim()) return;
    const response = await apiFetch(`/api/playlists/${playlist.id}`, {
      method: "PUT",
      json: { name: nextName.trim() },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to rename playlist.");
    window.location.reload();
  }

  async function deletePlaylist() {
    if (!playlist) return;
    if (!window.confirm(`Delete "${playlist.name}"?`)) return;
    const response = await apiFetch(`/api/playlists/${playlist.id}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to delete playlist.");
    window.location.href = "/playlists";
  }

  function playPlaylist(shuffle = false) {
    if (!playlist || !playlist.songs || !playlist.songs.length) return;
    HP.player.playList(playlist.songs, 0, shuffle);
  }

  function bind() {
    elements.addSongsBtn?.addEventListener("click", () => addSongs().catch((error) => window.alert(error.message)));
    elements.renameBtn?.addEventListener("click", () => renamePlaylist().catch((error) => window.alert(error.message)));
    elements.deleteBtn?.addEventListener("click", () => deletePlaylist().catch((error) => window.alert(error.message)));
    elements.playBtn?.addEventListener("click", () => playPlaylist(false));
    elements.shuffleBtn?.addEventListener("click", () => playPlaylist(true));
  }

  document.addEventListener("harmonyplayer:ready", () => {
    if (playlist && playlist.songs && playlist.songs.length) {
      playlist.songs = playlist.songs.map((song) => ({ ...song }));
    }
    if (elements.songPicker && availableSongs.length) {
      elements.songPicker.innerHTML = "";
      availableSongs.forEach((song) => {
        const option = document.createElement("option");
        option.value = String(song.id);
        option.textContent = `${song.title} — ${song.artist}`;
        elements.songPicker.appendChild(option);
      });
    }
    bind();
    renderPlaylistSongs();
  }, { once: true });
})();
