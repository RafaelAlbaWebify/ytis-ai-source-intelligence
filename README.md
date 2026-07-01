# YTIS - YouTube Intelligence System

YTIS is a local Python/NiceGUI tool for building upload-ready YouTube channel research packs.

## What V1 does

- Downloads English subtitles from a YouTube channel using yt-dlp.
- Removes duplicate `en-orig` subtitle files.
- Cleans `.srt` subtitles into `.txt` transcripts.
- Creates `ALL_TRANSCRIPTS_COMBINED.md`.
- Creates `transcript_index.csv`.
- Creates `missing_subtitles_report.csv`.
- Creates `README_ANALYSIS_PROMPT.md`.
- Creates a final ZIP in your Downloads folder.

## Project location

Recommended local path:

```text
C:\Users\ralba\Documents\GitHub\YTIS
```

## First run

Open PowerShell and run:

```powershell
cd C:\Users\ralba\Documents\GitHub\YTIS
.\run_ytis.ps1
```

The first run creates a local virtual environment and installs dependencies.

Then open the local URL shown by NiceGUI, normally:

```text
http://127.0.0.1:8080
```

## Notes

YTIS uses `yt-dlp` from the Python package installed in the virtual environment. You do not need a global yt-dlp install for this project.

Generated research packs are ignored by Git and should not be committed.
