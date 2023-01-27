#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Auto M3U Playlist Generator by JDHatten
    
    This script will automatically create .m3u playlists for all your multi-disc games.

How To Use:
    Either drag one or more folders/directories onto this script or run the script in your
    root game directory.

TODO:
    [X] Create log file.
    [X] Loop instead of close after task finishes.
    [X] Handle games that may be split into different directories but with the same name
        (compilation discs). Option to not make a playlist for them as they are technically
        different games from the same package.
    [X] Detect multi-disc games without disc numbers, but with disc titles or version text.
    [X] Option for relative disc paths in playlists.
    [] Option to save all playlist in a single separate directory.
    [] Update existing playlists only if new links are to be added/removed/reordered. Option to not reorder.
    [] GUI

'''

# This script will close after the initial searches are performed, but if this is set to True
# the script will continue to run and you may keep dropping additional directories to search.
loop_script = True

# If you don't want existing playlist files overwritten, set this to False.
overwrite_playlists = True

# If your game's disc image format is not included below add it now. You can comment out
# extensions/formats you don't want to create playlists for.
#                  File Extension   Format Name (used in playlist file names when separated)
disc_extensions = { '.chd'     :     'CHD',  # A CHD image file (Compressed Hunks of Data)
                    '.cue'     :     'CUE',  # Used with BIN and IMG image files
                    '.iso'     :     'ISO',  # An ISO image file
                   #'.mds'     :     'MDS',  # Used with MDF image files (Media Descriptor File/Sidecar)
                  }

# Use relative disc paths in playlists instead of full absolute paths for better portability.
use_relative_paths = False

# This script will automatically make separate playlists for different disc formats of the
# same game. If you have any of your games in multiple formats and want them all placed in
# the same playlist, set this to True. It's also possible for example, you have disc 1 in
# one format format and disc 2 in another format, and therefore need to force combine them.
# Note: The disc format/extension will be added to playlist file names if separated "(CHD)".
force_combine_disc_formats = False

# While this script can't perfectly detect if a game is a compilation or not you can choose
# to make playlists for them even though they are technically different games.
# Possible reasons a game will be detected as a compilation:
# 1. Same "Game Title" and "Game Info" with disc numbers but located in different directories.
# 2. Same "Game Title" with no disc numbers but possible different disc titles found in "Game Info".
# 3. Same "Game Title" with no disc numbers but possible extra "version" text found in "Game Info".
ignore_compilation_discs = False

# First type of detecting compilation discs is if they're in "different directories", and
# therefore you may want to save the playlist in the directory above the location of those
# discs else it will save the playlist in the first disc's directory.
# Note: This is only if the compilation discs are found in different directories.
save_compilation_playlists_one_level_up = True

# You shouldn't have to edit these as they just get the "Game Title" and "Game Info" text.
# However, if you have some unique file naming conventions for your games and know how to
# use Regular Expressions, go for it.
# Note: The + are just added for readability.
# Example File Name:  "Game Title (Game Info 1) [Game Info 2] (etc).ext"
re_game_title_pattern = '.[^(' + '\(|\[' + ')]*'
re_game_info_pattern = ( '\s*[' + '\(|\[|\{' + '][' +
                         '\{\w|\.|\,|\;|\'|\`|\~|\!|@|\#|\$|\%|\^|\-|\_|\=|\+\}*' +
                         '\s*]*[' + '\)|\]|\}' + ']' )

# If you edit the disc regular expression pattern you should know what group holds the disc
# number and update "re_disc_number_group". A group is the text found inside (parentheses).
re_disc_number_group = 4
# Examples: "(Disc 1 of 3)", "[CD2]", etc
re_disc_info_pattern = ( '(\s*)' + '(\(|\[)' + '(CD|Disc|Disk|DVD|Game)' +
                         '\s*(\d+)\s*\w*\s*(\d*)*' + '(\)|\])' )

# Create a log file that will record all the details of each playlist created, which includes
# the full file paths of the playlists and the disc image files recorded.
# Note: Log file creation is always overwritten, not appended too.
create_log_file = True


### Don't Edit Below This Line ###

from pathlib import Path, PurePath
from os import startfile as OpenFile, walk as Search
import re
import sys

LOG_DATA = 137
NOT_SAVED = 0
SAVED = 1
OVERWRITTEN = 2
ERROR_NOT_SAVED = 3
GAME_TYPE = 0
MULTI_DISC = 10
COMPILATION = 11
COMPILATION_UP_ONE = 12
DIFF_VERSION = 13
UNKNOWN = 14

re_game_title_compiled_pattern = None
re_game_info_compiled_pattern = None
re_disc_info_compiled_pattern = None


### Compile the Regular Expression patterns for the "Game Title", "Game Info", "Disc Info".
###     --> Returns a [None]
def compileRE():
    global re_game_title_compiled_pattern
    global re_game_info_compiled_pattern
    global re_disc_info_compiled_pattern
    re_game_title_compiled_pattern = re.compile(re_game_title_pattern, re.IGNORECASE)
    re_game_info_compiled_pattern = re.compile(re_game_info_pattern, re.IGNORECASE)
    re_disc_info_compiled_pattern = re.compile(re_disc_info_pattern, re.IGNORECASE)
    return None


### Find multi disc games and get their file paths and create a file name for the playlist.
###     (dir_path) Path to a directory.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     --> Returns a [Dictionary] and [Integer]
def findMultiDiscGames(dir_path, multi_disc_games_found):
    possible_compilation_disc_paths = []
    playlist_count = 0
    seperate_disc_formats = False
    
    print('\n--------------------------------------------------------------------------')
    print(f'Searching Directory For Multi-Disc Games: {dir_path}')
    print('--------------------------------------------------------------------------\n')
    
    previous_game, possible_compilation_game, game = '','',''
    previous_playlist_file_name, previous_file_ext = '',''
    
    for root, dirs, files in Search(dir_path):
        
        previous_disc_number = 0
        
        for file in files:
            
            file_path = Path(PurePath().joinpath(root, file))
            file_ext = file_path.suffix.casefold()
            #print(f'File: {file_path}')
            
            if file_ext in disc_extensions.keys(): # Only Discs
                
                game_title = re_game_title_compiled_pattern.match(file_path.stem).group().strip()
                # "Path" will be use to differentiate between games with the same name. Not an actual path.
                game = Path(PurePath().joinpath(root, game_title))
                is_multidisc_game = re_disc_info_compiled_pattern.search(file_path.stem)
                
                # Group disc paths with the same "Game Title" to later check if it could be a compilation game.
                # This game could be: a compilation or collection of game discs (most likely),
                #                     a multi-disc game with disc titles instead of numbers, or
                #                     a different version of the same game (i.e. patched/hack/etc).
                # Note: Multi-disc games with only disc titles or versions will be ordered alphabetically, which
                #       may be the incorrect order. No way for code to detect correct order.
                ## TODO: Detect patched or hacked games? Probably not, not enough universal standards here. However...
                ## If one disc has an extra "Game Info" then it's likely a different version. What if there're multiple different versions?
                if not ignore_compilation_discs:
                    
                    if game == possible_compilation_game and not is_multidisc_game:
                        possible_compilation_disc_paths.append(file_path) # 2+
                    elif not possible_compilation_disc_paths and not is_multidisc_game:
                        possible_compilation_disc_paths.append(file_path) # 1
                    else:
                        multi_disc_games_found, playlist_count = checkForCompilationGame(
                            multi_disc_games_found, possible_compilation_game, possible_compilation_disc_paths, playlist_count
                        )
                        possible_compilation_disc_paths.clear() # 0
                    
                    possible_compilation_game = game
                
                if is_multidisc_game: # (Disc #)
                    
                    if game != previous_game:
                        seperate_disc_formats = False
                        print('--------------------------------------------------------------------------')
                        print(f'-Multi-Disc Game Found: {game.name}')
                        print('--------------------------------------------------------------------------')
                    print(f'--File Name: "{file_path.name}"')
                    
                    if game in multi_disc_games_found.keys(): # Existing Game
                        
                        current_disc_number = int(re_disc_info_compiled_pattern.search(file_path.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {current_disc_number}')
                        #print(f'--Prev Disc Number: {previous_disc_number}')
                        
                        if game == previous_game and file_ext != previous_file_ext and not force_combine_disc_formats:
                            seperate_disc_formats = True
                        
                        # Make sure to create playlist_file_name using only common matching "Game Info".
                        playlist_file_name = re_disc_info_compiled_pattern.sub('', file_path.stem)
                        if (previous_playlist_file_name.find(game.name) > -1
                            and playlist_file_name != previous_playlist_file_name
                            and current_disc_number > previous_disc_number):
                                
                                # A multi-disc game with "Disc Titles" in "Game Info" detected. So changing name of playlist.
                                current_game_info_list = re_game_info_compiled_pattern.findall(playlist_file_name)
                                previous_game_info_list = re_game_info_compiled_pattern.findall(previous_playlist_file_name)
                                matching_game_info_list = compareTwoGameInfoLists(current_game_info_list, previous_game_info_list)
                                matching_game_info = ''.join(str(game_info) for game_info in matching_game_info_list)
                                
                                playlist_file_name = f'{game.name}{matching_game_info}'
                                if seperate_disc_formats:
                                    playlist_file_name = f'{playlist_file_name} ({disc_extensions.get(file_ext, file_ext)})'
                                
                                playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                                
                                previous_playlist_file_path = Path(PurePath().joinpath(root, f'{previous_playlist_file_name}.m3u'))
                                if (playlist_file_path not in multi_disc_games_found[game].keys()
                                    and previous_playlist_file_path in multi_disc_games_found[game].keys()):
                                        value = multi_disc_games_found[game].pop(previous_playlist_file_path)
                                        multi_disc_games_found[game][playlist_file_path] = value
                                        print(f'---Changing Existing Playlist Name From: "{previous_playlist_file_name}"')
                                        print(f'                                     To: "{playlist_file_name}"')
                        
                        else:
                            if seperate_disc_formats:
                                playlist_file_name = f'{playlist_file_name} ({disc_extensions.get(file_ext, file_ext)})'
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        # Now that playlist are being seperated, rename previous playlist using previous file extension.
                        if seperate_disc_formats:
                            previous_playlist_file_name_rename = f'{previous_playlist_file_name} ({disc_extensions.get(previous_file_ext, previous_file_ext)})'
                            previous_playlist_file_path_rename = Path(PurePath().joinpath(root, f'{previous_playlist_file_name_rename}.m3u'))
                            previous_playlist_file_path = Path(PurePath().joinpath(root, f'{previous_playlist_file_name}.m3u'))
                            if (playlist_file_path not in multi_disc_games_found[game].keys()
                                and previous_playlist_file_path in multi_disc_games_found[game].keys()):
                                    value = multi_disc_games_found[game].pop(previous_playlist_file_path)
                                    multi_disc_games_found[game][previous_playlist_file_path_rename] = value
                                    print(f'---Changing Existing Playlist Name From: "{previous_playlist_file_name}"')
                                    print(f'                                     To: "{previous_playlist_file_name_rename}"')
                        
                        # Check if playlist name has already been added and make sure it uses the same playlist path.
                        playlist_file_path_exists = False
                        for existing_playlist_file_path in multi_disc_games_found[game].keys():
                            if (existing_playlist_file_path != LOG_DATA
                                and playlist_file_path.name == existing_playlist_file_path.name):
                                    playlist_file_path = existing_playlist_file_path
                                    playlist_file_path_exists = True
                                    break
                        
                        if playlist_file_path_exists:
                            if file_path not in multi_disc_games_found[game][playlist_file_path]:
                                multi_disc_games_found[game][playlist_file_path].append(file_path)
                                print(f'---Adding File Path To Existing Playlist Named: "{playlist_file_name}"')
                            else:
                                print(f'---File Path Already In Existing Playlist Named: "{playlist_file_name}"')
                                
                                # Now check to see if a playlist had a name change (a Disc Title removed) and was re-added.
                                # If so now remove that playlist... again.
                                if previous_game == game and previous_playlist_file_name != playlist_file_name:
                                    previous_playlist_file_path = Path(PurePath().joinpath(
                                        root, f'{previous_playlist_file_name}.m3u'
                                    ))
                                    if (previous_playlist_file_path in multi_disc_games_found[game].keys()
                                        and current_disc_number > previous_disc_number
                                        and file_ext == previous_file_ext): # not seperate_disc_formats?
                                            print(f'---Deleting Playlist: "{previous_playlist_file_path}"')
                                            multi_disc_games_found[game].pop(previous_playlist_file_path)
                                            playlist_count -= 1
                        
                        else:
                            multi_disc_games_found[game][playlist_file_path] = [file_path]
                            print(f'---Adding File Path To New Playlist Named: "{playlist_file_name}"')
                            playlist_count += 1
                    
                    else: # New Game Found
                        current_disc_number = int(re_disc_info_compiled_pattern.search(file_path.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {current_disc_number}')
                        
                        playlist_file_name = re_disc_info_compiled_pattern.sub('', file_path.stem)
                        previous_playlist_file_name = playlist_file_name
                        print(f'---Adding File Path To New Playlist Named: "{playlist_file_name}"')
                        playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        multi_disc_games_found[game] = { playlist_file_path : [file_path] }
                        playlist_count += 1
                        
                        multi_disc_games_found = setMultDiscGameType(multi_disc_games_found, game, MULTI_DISC)
                    
                    previous_game = game
                    previous_disc_number = current_disc_number
                    previous_playlist_file_name = playlist_file_name
                    previous_file_ext = file_ext
    
    # Final multi-disc game checks and fixes.
    multi_disc_games_found, playlist_count = checkForCompilationGame(
        multi_disc_games_found, possible_compilation_game, possible_compilation_disc_paths, playlist_count
    )
    multi_disc_games_found, playlist_count = checkForDupeGames(multi_disc_games_found, playlist_count)
    multi_disc_games_found, playlist_count = checkForSingleDiscPlaylists(multi_disc_games_found, playlist_count)
    
    #print(f'\nmulti_disc_games_found: {multi_disc_games_found}')
    
    return multi_disc_games_found, playlist_count


### Check for compilation games with disc titles instead of disk numbers.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     (possible_compilation_game) The game that was last detected as a posible compilation.
###     (possible_compilation_disc_paths) A list of compilation disc paths.
###     (playlist_count) Amount of new playlists to be created.
###     --> Returns a [Dictionary] and [Integer]
def checkForCompilationGame(multi_disc_games_found, possible_compilation_game, possible_compilation_disc_paths, playlist_count):
    
    if len(possible_compilation_disc_paths) > 1:
        print('--------------------------------------------------------------------------')
        print(f'-Compilation Game Found: {possible_compilation_game.name}')
        print('--------------------------------------------------------------------------')
        all_game_info_list = []
        matching_game_info_list = []
        disc_count = len(possible_compilation_disc_paths)
        disc_paths = []
        disc_exts = []
        seperate_disc_formats = False
        
        for disc_path in possible_compilation_disc_paths:
            all_game_info_list.extend(re_game_info_compiled_pattern.findall(disc_path.stem))
            disc_paths.append(disc_path) # copy
            if disc_path.suffix not in disc_exts:
                disc_exts.append(disc_path.suffix)
        
        if force_combine_disc_formats:
            format_count = 1
        else:
            format_count = len(disc_exts)
            if format_count > 1:
                seperate_disc_formats = True
                #disc_count /= len(disc_exts)
        
        # Get only matching Game Info
        for gi in all_game_info_list:
            if all_game_info_list.count(gi) >= disc_count / format_count:
                if gi not in matching_game_info_list:
                    matching_game_info_list.append(gi)
        game_info = ''.join(matching_game_info_list)
        
        # Create New Playlist (split if different disc formats)
        playlists = {}
        playlist_file_name = f'{possible_compilation_game.name}{game_info}'
        for path in disc_paths:
            if seperate_disc_formats:
                playlist_file_name = f'{possible_compilation_game.name}{game_info} ({disc_extensions.get(path.suffix, path.suffix)})'
            
            playlist_file_path = Path(PurePath().joinpath(possible_compilation_game.parent, f'{playlist_file_name}.m3u'))
            if playlist_file_path in playlists.keys():
                playlists[playlist_file_path].append(path)
            else:
                playlists[playlist_file_path] = [path]
        
        file_names = '"\n              "'.join(disc.name for disc in disc_paths)
        print(f'--File Names: "{file_names}"')
        if seperate_disc_formats:
            print(f'--Disc Count: {int(disc_count/format_count)} Discs Per Format')
        else:
            print(f'--Disc Count: {disc_count} Discs')
        
        # Add New Game
        if possible_compilation_game not in multi_disc_games_found.keys():
            multi_disc_games_found[possible_compilation_game] = {}
        
        for playlist, disc_paths in playlists.items():
            
            # Add New Playlist
            if playlist not in multi_disc_games_found[possible_compilation_game].keys():
                multi_disc_games_found[possible_compilation_game][playlist] = []
                playlist_count += 1
            
            # Add New Disc Paths To Playlist
            new_disc_paths_added = False
            for path in disc_paths:
                if path not in multi_disc_games_found[possible_compilation_game][playlist]:
                    multi_disc_games_found[possible_compilation_game][playlist].append(path)
                    new_disc_paths_added = True
            
            if new_disc_paths_added:
                print(f'---Adding File Paths To New Playlist Named: "{playlist.name}"')
            else:
                print(f'---File Paths Already In Existing Playlist Named: "{playlist.name}"')
                
        multi_disc_games_found = setMultDiscGameType(multi_disc_games_found, possible_compilation_game, COMPILATION)
    
    return multi_disc_games_found, playlist_count


### Check for duplicate games found in different directories that should be placed in one
### compilation playlist.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     (playlist_count) Amount of new playlists to be created.
###     --> Returns a [Dictionary] and [Integer]
def checkForDupeGames(multi_disc_games_found, playlist_count):
    
    if ignore_compilation_discs:
        return multi_disc_games_found, playlist_count
    
    multi_disc_games_found_copy = multi_disc_games_found.copy()
    dupe_games_to_remove = []
    
    for game_one, all_playlist_one in multi_disc_games_found_copy.items():
        if game_one == LOG_DATA: continue
        for game_two, all_playlist_two in multi_disc_games_found_copy.items():
            if game_two == LOG_DATA: continue
            
            if game_one != game_two and game_one.name == game_two.name: # Diff path, same name
                
                for playlist_path_one, game_disc_paths_one in all_playlist_one.copy().items():
                    if playlist_path_one == LOG_DATA: continue
                    for playlist_path_two, game_disc_paths_two in all_playlist_two.copy().items():
                        if playlist_path_two == LOG_DATA: continue
                        
                        # If playlist names are the same then this is very likely a compilation game
                        if playlist_path_one.name == playlist_path_two.name:
                            
                            # Combine playlists, but only paths that are new/different.
                            disc_paths_combined = False
                            for disc_path in game_disc_paths_two:
                                if disc_path not in game_disc_paths_one:
                                    multi_disc_games_found[game_one][playlist_path_one].append(disc_path)
                                    disc_paths_combined = True
                            
                            # And since two playlist merged into one...
                            multi_disc_games_found[game_two].pop(playlist_path_two)
                            dupe_games_to_remove.append(game_two)
                            playlist_count -= 1
                            
                            #game_file_names = [path.name for path in multi_disc_games_found[game_one][playlist_path_one]]
                            game_file_paths = '\n              '.join(
                                [f'"{str(path)}"' for path in multi_disc_games_found[game_one][playlist_path_one]]
                            )
                            
                            if save_compilation_playlists_one_level_up:
                                disc_list = multi_disc_games_found[game_one].pop(playlist_path_one)
                                compilation_playlist_file_path = Path(PurePath().joinpath(
                                    game_one.parents[1], playlist_path_one.name
                                ))
                                multi_disc_games_found[game_one][compilation_playlist_file_path] = disc_list
                                multi_disc_games_found = setMultDiscGameType(multi_disc_games_found, game_one, COMPILATION_UP_ONE)
                            
                            else:
                                multi_disc_games_found = setMultDiscGameType(multi_disc_games_found, game_one, COMPILATION)
                            
                            print('--------------------------------------------------------------------------')
                            print(f'-Multi-Disc Game Found To Be Compilation Game: {game_one.name}')
                            print('--------------------------------------------------------------------------')
                            #print(f'--File Names: "{game_file_names}"')
                            print(f'--File Paths: {game_file_paths}')
                            if disc_paths_combined:
                                print(f'---Combining Playlists Into One Named: "{playlist_path_one.name}"')
                            else:
                                print(f'---File Paths Already In Existing Playlist Named: "{playlist_path_one.name}"')
    
    for game in dupe_games_to_remove:
        multi_disc_games_found.pop(game)
    
    return multi_disc_games_found, playlist_count


### Delete single game playlists that only have one disc. In some cases when searching
### multiple times and formats are being separated there may be playlists that are re-added
### with only one disc. So delete them now as they may cause issues later.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     (playlist_count) Amount of new playlists to be created.
###     --> Returns a [Dictionary] and [Integer]
def checkForSingleDiscPlaylists(multi_disc_games_found, playlist_count):
    start_count = playlist_count
    for game, all_playlists in multi_disc_games_found.copy().items():
        if game == LOG_DATA: continue
        for playlist_path, game_disc_paths in all_playlists.copy().items():
            if playlist_path == LOG_DATA: continue
            
            if len(game_disc_paths) <= 1:
                if start_count == playlist_count:
                    print('--------------------------------------------------------------------------')
                    print('-Cleaning Up Single Disc Playlists:')
                    print('--------------------------------------------------------------------------')
                print(f'--Game Title: "{game.name}"')
                print(f'---Deleting Playlist: "{playlist_path}"')
                multi_disc_games_found[game].pop(playlist_path)
                playlist_count -= 1
    
    return multi_disc_games_found, playlist_count


### Compare two list and return the common items in a new list.
###     (game_info_list_one) Fist "Game Info" list.
###     (game_info_list_two) Second "Game Info" list.
###     --> Returns a [List]
def compareTwoGameInfoLists(game_info_list_one, game_info_list_two):
    all_game_info_list = []
    matching_game_info_list = []
    
    for game_info_list in [game_info_list_one,game_info_list_two]:
        for game_info in game_info_list:
            # To prevent dupe (extension) in game info when separating playlist when ran 2+ times.
            ext_in_game_info = game_info.replace('(','').replace(')','').strip()
            if game_info not in all_game_info_list or ext_in_game_info in disc_extensions.keys():
                all_game_info_list.append(game_info)
            else:
                if game_info not in matching_game_info_list:
                    matching_game_info_list.append(game_info)
    
    return matching_game_info_list


### Set a multi-disc game's disc type.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     (game) The game to update.
###     (game_type) The type to update: MULTI_DISC, COMPILATION, DIFF_VERSION, UNKNOWN
###     --> Returns a [Dictionary]
def setMultDiscGameType(multi_disc_games_found, game, game_type = MULTI_DISC):
    if LOG_DATA not in multi_disc_games_found[game].keys():
        multi_disc_games_found[game][LOG_DATA] = [game_type]
    else:
        multi_disc_games_found[game][LOG_DATA][GAME_TYPE] = game_type
    
    return multi_disc_games_found


### Create playlists for all multi-disc games found.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     --> Returns a [Dictionary]
def createPlaylists(multi_disc_games_found):
    playlists_not_created, new_playlists_created = 0,0
    playlists_overwritten, playlists_save_errors = 0,0
    playlist_creation = NOT_SAVED
    
    multi_disc_games_found_copy = multi_disc_games_found.copy()
    
    if LOG_DATA not in multi_disc_games_found.keys():
        multi_disc_games_found[LOG_DATA] = [0,0,0,0]
    
    print('\n--------------------------------------------------------------------------')
    print('Now creating M3U Playlists For All Multi-Disc Games Found')
    print('--------------------------------------------------------------------------\n')
    
    for game, playlists in multi_disc_games_found_copy.items():
        if game == LOG_DATA:
            continue

        playlist_number = 0
        for playlist_path, game_disc_paths in playlists.copy().items():
            
            #if len(game_disc_paths) > 1 and type(playlist_path).__name__.find('Path') > -1:
            if playlist_path != LOG_DATA and len(game_disc_paths) > 1:
                
                playlist_number += 1
                
                if len(multi_disc_games_found[game][LOG_DATA]) > playlist_number:
                    continue # This playlist creation already attempted, no need to retry.
                
                if playlist_number == 1:
                    print('--------------------------------------------------------------------------')
                    if multi_disc_games_found[game].get(LOG_DATA, [MULTI_DISC])[GAME_TYPE]:
                        print(f'-Compilation Game Title: {game.name}')
                    else:
                        print(f'-Multi-Disc Game Title: {game.name}')
                    print('--------------------------------------------------------------------------')
                
                print(f'--Playlist Path: {playlist_path}')
                
                disc_number = 0
                for disc_path in game_disc_paths:
                    disc_number += 1
                    if use_relative_paths:
                        if multi_disc_games_found[game][LOG_DATA][GAME_TYPE] == COMPILATION_UP_ONE:
                            relative_disc_path = Path(PurePath().joinpath(disc_path.parts[-2],
                                                                          disc_path.parts[-1]))
                            print(f'---Disc #{disc_number} Relative Path: {relative_disc_path}')
                        else:
                            print(f'---Disc #{disc_number} Relative Path: {disc_path.name}')
                    else:
                        print(f'---Disc #{disc_number} Path: {disc_path}')
                
                if Path.exists(playlist_path) and overwrite_playlists:
                    playlists_overwritten += 1
                    playlist_creation = OVERWRITTEN
                    
                elif Path.exists(playlist_path) and not overwrite_playlists:
                    playlists_not_created += 1
                    playlist_creation = NOT_SAVED
                else:
                    new_playlists_created += 1
                    playlist_creation = SAVED
                
                if playlist_creation > NOT_SAVED:
                    try: # Writing the disc path to the playlist file.
                        if use_relative_paths:
                            if multi_disc_games_found[game][LOG_DATA][GAME_TYPE] == COMPILATION_UP_ONE:
                                relative_disc_paths = []
                                for disc_path in game_disc_paths:
                                    relative_disc_paths.append(Path(PurePath().joinpath(disc_path.parts[-2],
                                                                                        disc_path.parts[-1])))
                                playlist_path.write_text('\n'.join([str(path) for path in relative_disc_paths]),
                                                         encoding='utf-8', errors='strict', newline=None)
                            else:
                                playlist_path.write_text('\n'.join([str(path.name) for path in game_disc_paths]),
                                                         encoding='utf-8', errors='strict', newline=None)
                        else:
                            playlist_path.write_text('\n'.join([str(path) for path in game_disc_paths]),
                                                     encoding='utf-8', errors='strict', newline=None)
                    
                    except Exception as error:
                        print(f'\nCouldn\'t save playlist file due to {type(error).__name__}: {type(error).__doc__}')
                        print(f'{error}\n')
                        if playlist_creation == OVERWRITTEN:
                            playlists_overwritten -= 1
                        elif playlist_creation == SAVED:
                            new_playlists_created -= 1
                        playlists_save_errors += 1
                        playlist_creation = f'{type(error).__name__}: {type(error).__doc__}'
                
                multi_disc_games_found[game][LOG_DATA].append(playlist_creation)
    
    multi_disc_games_found[LOG_DATA][NOT_SAVED] += playlists_not_created
    multi_disc_games_found[LOG_DATA][SAVED] += new_playlists_created
    multi_disc_games_found[LOG_DATA][OVERWRITTEN] += playlists_overwritten
    multi_disc_games_found[LOG_DATA][ERROR_NOT_SAVED] += playlists_save_errors
    
    return multi_disc_games_found


### Create log file for all playlists created.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     --> Returns a [Boolean]
def createLogFile(multi_disc_games_found):
    log_file_created = False
    
    if type(multi_disc_games_found) == dict and multi_disc_games_found.get(LOG_DATA):
        playlists_not_created = multi_disc_games_found[LOG_DATA][NOT_SAVED]
        new_playlists_created = multi_disc_games_found[LOG_DATA][SAVED]
        playlists_overwritten = multi_disc_games_found[LOG_DATA][OVERWRITTEN]
        playlists_save_errors = multi_disc_games_found[LOG_DATA][ERROR_NOT_SAVED]
    else:
        print('\nSomething went wrong creating log file.')
        return False
    
    # Print general details of playlist creation
    text_lines = []
    text_lines.append('===================================')
    text_lines.append('= Auto M3U Playlist Generator Log =')
    text_lines.append('===================================')
    text_lines.append(f'- New Playlist Created: {new_playlists_created}')
    if overwrite_playlists:
        text_lines.append(f'- Playlist Overwritten: {playlists_overwritten}')
    elif playlists_not_created:
        text_lines.append(f'- Playlist Not Created: {playlists_not_created}')
    if playlists_save_errors:
        text_lines.append(f'- Playlist Save Errors: {playlists_save_errors}')
    
    print_text_lines = text_lines.copy()
    print('\n'+'\n'.join(print_text_lines))
    
    if new_playlists_created + playlists_overwritten == 0:
        return False
    
    if create_log_file:
        
        root_path = Path(__file__).parent
        log_file_name = f'{Path(__file__).stem}__log.txt'
        log_file_path = Path(PurePath().joinpath(root_path, log_file_name))
        
        # Separate by game type
        multi_disc_games = []
        compilation_games = []
        diff_version_games = []
        #unknown_games = []
        for game, playlists in multi_disc_games_found.items():
            if game == LOG_DATA: continue
            game_log_data = playlists.get(LOG_DATA)
            
            for playlist_path, game_disc_paths in playlists.items():
                if playlist_path == LOG_DATA: continue
                
                if game_log_data:
                    if game_log_data[GAME_TYPE] == MULTI_DISC:
                        if game not in multi_disc_games:
                            multi_disc_games.append(game)
                    
                    elif (game_log_data[GAME_TYPE] == COMPILATION
                       or game_log_data[GAME_TYPE] == COMPILATION_UP_ONE):
                            if game not in compilation_games:
                                compilation_games.append(game)
                    
                    elif game_log_data[GAME_TYPE] == DIFF_VERSION:
                        if game not in diff_version_games:
                            diff_version_games.append(game)
        
        # Print out playlist sorted by game type
        if multi_disc_games:
            text_lines.append('\n---------------------------------')
            text_lines.append('Multi-Disc Game Playlists Created')
            text_lines.append('---------------------------------')
        for game in multi_disc_games:
            text_lines = printGamePlaylistDetails(multi_disc_games_found, game, text_lines)
        
        if compilation_games:
            text_lines.append('\n----------------------------------')
            text_lines.append('Compilation Game Playlists Created')
            text_lines.append('----------------------------------')
        for game in compilation_games:
            text_lines = printGamePlaylistDetails(multi_disc_games_found, game, text_lines)
        
        if diff_version_games: ## TODO:
            text_lines.append('\n-----------------------------------------')
            text_lines.append('Different Game Versions Playlists Created')
            text_lines.append('-----------------------------------------')
        for game in diff_version_games:
            text_lines = printGamePlaylistDetails(multi_disc_games_found, game, text_lines)
        
        # Write Log File
        try:
            log_file_path.write_text('\n'.join(text_lines), encoding='utf-8', errors='strict', newline=None)
            log_file_created = log_file_path # return log file path
        except Exception as error:
            print(f'\nCouldn\'t save log file due to {type(error).__name__}: {type(error).__doc__}')
            print(f'{error}\n')
    
    else:
        print('Log file creation turned off.')
    
    return log_file_created


### This will print out each playlist a game has for use in the creation of a log file.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created with the paths to each disc.
###     (game) The game to have its playlists printed out.
###     (text_lines) A list of lines to be printed.
###     --> Returns a [List]
def printGamePlaylistDetails(multi_disc_games_found, game, text_lines = []):
    playlist_creation = ['  << Already Exists / Not Overwritten >>', # NOT_SAVED
                         '  << NEW >>', # SAVED
                         '', # OVERWRITTEN
                         '  << Not Saved Due To'] # ERROR_NOT_SAVED
    game_log_data = multi_disc_games_found[game].get(LOG_DATA, [0,0,0,0])
    
    playlist_number = 1
    for playlist_path, game_disc_paths in multi_disc_games_found[game].items():
        if playlist_path == LOG_DATA: continue
        
        if playlist_number == 1:
            text_lines.append(f'\n-Game Title: {game.name}')
        
        if type(game_log_data[playlist_number]) == int:
            save_info = playlist_creation[game_log_data[playlist_number]]
        else: # Error
            save_info = f'{playlist_creation[ERROR_NOT_SAVED]} {game_log_data[playlist_number]} >>'
        
        text_lines.append(f'--Playlist Path: {playlist_path}{save_info}')
        playlist_number += 1
        
        disc_number = 1
        while disc_number <= len(game_disc_paths):
            
            if use_relative_paths:
                if multi_disc_games_found[game][LOG_DATA][GAME_TYPE] == COMPILATION_UP_ONE:
                    relative_disc_path = Path(PurePath().joinpath(game_disc_paths[disc_number-1].parts[-2],
                                                                  game_disc_paths[disc_number-1].parts[-1]))
                    text_lines.append(f'---Disc #{disc_number} Relative Path: {relative_disc_path}')
                else:
                    text_lines.append(f'---Disc #{disc_number} Relative Path: {game_disc_paths[disc_number-1].name}')
            else:
                text_lines.append(f'---Disc #{disc_number} Path: {game_disc_paths[disc_number-1]}')
            disc_number += 1
    
    return text_lines


### Open a log file for viewing.
###     (log_file_path) Path to a log file.
###     --> Returns a [None]
def openLogFile(log_file_path):
    OpenFile(log_file_path)
    return None


### Script Starts Here
if __name__ == '__main__':
    print(sys.version)
    print('\n=======================================')
    print('Auto M3U Playlist Generator by JDHatten')
    print('=======================================')
    MIN_VERSION = (3,5,0)
    MIN_VERSION_STR = '.'.join([str(n) for n in MIN_VERSION])
    assert sys.version_info >= MIN_VERSION, f'This Script Requires Python v{MIN_VERSION_STR} or Newer'
    
    compileRE()
    
    dir_paths = sys.argv[1:]
    if not dir_paths:
        dir_paths = [Path(__file__).parent]
    
    multi_disc_games_found = {}
    new_playlists_created, playlists_overwritten, n = 0,0,0
    loop = True
    while loop:
        i = 0
        for dir_path in dir_paths:
            
            multi_disc_games_found, playlist_count = findMultiDiscGames(dir_path, multi_disc_games_found)
            
            if playlist_count:
                s = 's' if playlist_count > 1 else ''
                input(f'\nAll data retrieved and ready to create playlists for {playlist_count} multi-disc game{s}. Press [ENTER] to start...')
                
                multi_disc_games_found = createPlaylists(multi_disc_games_found)
                
                playlists_not_created = multi_disc_games_found[LOG_DATA][NOT_SAVED]
                new_playlists_created = multi_disc_games_found[LOG_DATA][SAVED]
                playlists_overwritten = multi_disc_games_found[LOG_DATA][OVERWRITTEN]
                
                if new_playlists_created or playlists_overwritten or playlists_not_created:
                    print(f'\nNew Playlists Created: {new_playlists_created}')
                    if overwrite_playlists:
                        print(f'Playlists Overwritten: {playlists_overwritten}')
                    else:
                        print(f'Playlists Not Created: {playlists_not_created}')
                else:
                    print('No Playlists Created')
            
            elif n > 0:
                print('\nNo new multi-disc games found.')
            else:
                print('\nNo multi-disc games found.')
            
            n += 1
            i += 1
            if len(dir_paths) > i:
                input(f'\nPress [Enter] to continue with next directory... {dir_paths[i]}')
            else:
                #print('\nAll Done!')
                try_again = loop_script
                loop = loop_script
                while try_again:
                    dir = input('\nDrop another directory here to keep searching or press [Enter] to close and create a log file now: ')
                    dir = dir.replace('"', '')
                    ## TODO: one at a time or multiple dir split?
                    dir_path = Path(dir)
                    if dir == '':
                        loop = False
                        try_again = False
                    elif Path.exists(dir_path):
                        dir_paths = [dir_path]
                        try_again = False
                    else:
                        print(f'This is not an existing directory path: "{dir}"')
    
    log_file_created = createLogFile(multi_disc_games_found)
    if log_file_created:
        print('--> Check log for more details.')
        openLogFile(log_file_created)
