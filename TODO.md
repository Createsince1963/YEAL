# Yeal - optional ideas (not planned yet)

## To check on the real app (written without a Windows/Qt test run)
- Drive dialog: two external SSDs are both offered one after the other (0.8.6).
- Start without white flash, logo at 50 % until YouTube is dark (0.8.6).
- Ads: sound muted during an ad, back afterwards (0.8.7).
- Live stream dialog + time limit with a real stream; the limit needs ffmpeg and yt-dlp (0.8.8).
- Playlist dialog (PlaylistDialog.qml): list, Shift+click range, Download N; folder `Playlists\<name>`; playlist page (0.8.9).
- Playlist ideas: sort/search field in the dialog, per-entry thumbnails, a playlist page with the online player.

## Speech to text for videos without subtitles (optional)
Create a TXT transcript from the audio track when no subtitle transcript exists.
- Button "Transcribe audio -> TXT" in the download row (only when no transcript exists) and an optional
  profile switch "No subtitles? Transcribe audio".
- Engine: WhisperX / faster-whisper already installed in `Tools_Central\AI\WhisperX` (referenced, never copied;
  model "small" is cached locally, language auto-detected, CPU fallback). CPU is slow: a few minutes per video.
- A tested prototype of the wrapper is parked in `docs\optional\transcribe_whisperx.py`
  (command line, env, CUDA->CPU retry, never overwrites an existing TXT). Not part of the app and not packaged.
- Needed to activate: platform lookup of `whisperx.exe`, a profile flag, a job state "transcribing",
  row button + menu item, tests (a fake whisperx script is enough).
