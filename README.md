# Auto-M3U-Playlist-Generator

#### This script will automatically create .m3u playlists for all your multi-disc games.

<br>

## How It Works:
Once the script is ran it will begin searching directories for specific disc image files from `disc_extensions` and once found will check first if there is text in the file name similar to "(Disc 1 of 2)" or "[CD3]" or some other similar variation.  A .m3u playlist will then be created with the same file name minus the disc info.

This script can also detect compilation discs or game collections though not perfectly. By default it will skip compilation discs because in most cases these are technically different games and shouldn't need playlists.  However, some of your games may have disc titles instead of numbers or multiple different versions (rereleases, patched games, etc.) and these games will be detected as compilation discs.  So if you want playlists to be made for these games set `ignore_compilation_discs = False`

<br>

## How To Use:
- Either drag one or more folders/directories onto this script or run the script in your root game directory.
