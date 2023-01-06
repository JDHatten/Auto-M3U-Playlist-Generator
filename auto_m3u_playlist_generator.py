#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Auto M3U Playlist Generator by JDHatten
    
    This script will automatically create .m3u playlists for all your multi-disc games.

How To Use:
    Either drag one or more folders/directories onto this script or run the script in your
    root game directory.

TODO:
    [] Create log file.
    [] Loop instead of close after task finishes.
    [X] Handle games that may be split into different directories but with the same name
        (compilation discs). Option to not make a playlist for them as they are technically
        different games from the same package.
    [X] Detect multi-disc games without disc numbers, but with disc titles or version text.

'''

from pathlib import Path, PurePath
import os
import re
import sys


# Make different playlists for different disc formats even if they have the same game title.
# If for some reason you have your games in multiple formats. Format/extension will be added
# to playlist file names.
seperate_disc_format_playlists = False

# If you don't want existing playlist files overwritten, make False.
overwrite_playlists = True

# If your disc image format is not included below add it.
# You can comment out ones you don't want to create playlists for.
disc_extensions = { 'CHD (Compressed Hunks of Data)' : '.chd',
                    'CUE BIN IMG' : '.cue',
                    'ISO' : '.iso',
                    #'MDS MDF' : '.mds'
                  }

# If you edit this regular expression pattern below you should know what group holds the disc
# number and update "re_disc_number_group". A group is the text found inside (parentheses).
# Note: The + are just added for readability.
re_disc_number_group = 4
re_disc_pattern = re.compile( '(\s*)' + '(\(|\[)' + '(Disc|CD)' +
                              '\s*(\d*)\s*\w*\s*(\d*)*' + '(\)|\])',
                              re.IGNORECASE ) # Example: "(Disc 1 of 3)", "[CD2]", etc

# You shouldn't have to edit these as they just get the "Game Title" and "Game Info" text.
# However, if you have some unique file naming conventions for your games and know how to
# use Regular Expressions, go for it.
# Example File Name:   Game Title (Game Info 1) [Game Info 2] (etc).ext
re_game_title_pattern = re.compile( '.[^(' + '\(|\[' + ')]*', re.IGNORECASE )
re_game_info_pattern = re.compile( '\s*[' + '\(|\[|\{' + '][' +
                                   '\{\w|\.|\,|\;|\'|\`|\~|\!|@|\#|\$|\%|\^|\-|\_|\=|\+\}*' +
                                   '\s*]*[' + '\)|\]|\}' + ']', re.IGNORECASE )

# While this script can't perfectly detect if a game is a compilation or not you can choose
# to make playlists for them even though they are technically different games.
# Possible reasons a game will be detected as a compilation:
# 1. Same "Game Title" and "Game Info" with disc numbers but located in different directories.
# 2. Same "Game Title" with no disc numbers but possible different "Disc Titles" found in "Game Info".
# 3. Same "Game Title" with no disc numbers but possible extra "Version Text" found in "Game Info".
ignore_compilation_discs = True

# First type of detecting compilation discs is if they're in "different directories", and
# therefore you may want to save the playlist in the directory above the location of those
# discs else it will save the playlist in the first disc's directory.
save_compilation_playlists_one_level_up = True


### Find multi disc games and get their file paths and create a file name for the playlist.
###     (dir_path) Path to a directory.
###     --> Returns a [Dictionary] and [Integer]
def findMultiDiscGames(dir_path):
    multi_disc_games_found = {}
    possible_compilation_games_found = []
    playlist_count = 0
    
    print('--------------------------------------------------------------------------')
    print(f'Searching Directory For Multi-Disc Games: {dir_path}')
    print('--------------------------------------------------------------------------\n')
    
    previous_game_title, possible_compilation_game_title, game_title = '','',''
    previous_playlist_file_name = ''
    
    for root, dirs, files in os.walk(dir_path):
        
        previous_disc_number = 0
        
        for file in files:
            
            file_path = Path(PurePath().joinpath(root, file))
            file_ext = file_path.suffix.casefold()
            #print(f'File: {file_path}')
            
            if file_ext in disc_extensions.values(): # Only Discs
                
                game_title = re_game_title_pattern.match(file_path.stem).group().strip()
                is_multidisc_game = re_disc_pattern.search(file_path.stem)
                
                # Group disc paths with the same "Game Title" to later check if it could be a compilation game.
                # Note: This could be: a compilation or collection of game discs (most likely),
                #                      a multi-disc game with disc titles instead of numbers, or
                #                      a different version of the same game (i.e. patched/hack/etc).
                ## TODO: Detect patched or hacked games? Probably not, not enough universal standards here.
                ## If one disc has an extra "Game Info" then it's likely a different version. What if there're multiple different versions?
                if not ignore_compilation_discs:
                    if game_title == possible_compilation_game_title and not is_multidisc_game:
                        possible_compilation_games_found.append(file_path) # 2+
                    elif not possible_compilation_games_found and not is_multidisc_game:
                        possible_compilation_games_found.append(file_path) # 1
                    else:
                        if len(possible_compilation_games_found) > 1:
                            print('--------------------------------------------------------------------------')
                            print(f'-Compilation Game Found: {possible_compilation_game_title}')
                            print('--------------------------------------------------------------------------')
                            all_game_info_list = []
                            matching_game_info_list = []
                            
                            for disc_path in possible_compilation_games_found:
                                game_info_list = re_game_info_pattern.findall(disc_path.stem)
                                
                                for game_info in game_info_list:
                                    if game_info not in all_game_info_list:
                                        all_game_info_list.append(game_info)
                                    else:
                                        if game_info not in matching_game_info_list:
                                            matching_game_info_list.append(game_info)
                            
                            disc_paths = [path for path in possible_compilation_games_found]
                            game_names = [path.name for path in possible_compilation_games_found]
                            game_info = ''.join(str(gi) for gi in matching_game_info_list)
                            
                            playlist_file_name = f'{possible_compilation_game_title}{game_info}'
                            if seperate_disc_format_playlists:
                                playlist_file_name = f'{playlist_file_name} ({file_ext})'
                            
                            print(f'--File Names: "{game_names}"')
                            print(f'---Adding File Paths To New Playlist Named: "{playlist_file_name}"')
                            
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                            multi_disc_games_found[possible_compilation_game_title] = { playlist_file_path : disc_paths }
                            
                            possible_compilation_games_found.clear() # 0
                    
                    possible_compilation_game_title = game_title
                
                if is_multidisc_game: # (Disc #)
                    
                    if game_title != previous_game_title:
                        print('--------------------------------------------------------------------------')
                        print(f'-Multi-Disc Game Found: {game_title}')
                        print('--------------------------------------------------------------------------')
                    previous_game_title = game_title
                    
                    print(f'--File Name: "{file_path.name}"')
                    if seperate_disc_format_playlists:
                        game_title = f'{game_title}{file_ext}'
                    
                    if game_title in multi_disc_games_found.keys(): # Existing Game
                        
                        current_disc_number = int(re_disc_pattern.search(file_path.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {current_disc_number}')
                        #print(f'--Prev Disc Number: {previous_disc_number}')
                        
                        # Make sure to create playlist_file_name using only common matching "Game Info".
                        playlist_file_name = re_disc_pattern.sub('', file_path.stem)
                        if playlist_file_name != previous_playlist_file_name and current_disc_number > previous_disc_number:
                            
                            # A multi-disc game with "Disc Titles" in "Game Info" detected. So changing name of playlist.
                            current_game_info_list = re_game_info_pattern.findall(playlist_file_name)
                            previous_game_info_list = re_game_info_pattern.findall(previous_playlist_file_name)
                            matching_game_info_list = compareTwoGameInfoLists(current_game_info_list, previous_game_info_list)
                            matching_game_info = ''.join(str(game_info) for game_info in matching_game_info_list)
                            
                            playlist_file_name = f'{game_title}{matching_game_info}'
                            if seperate_disc_format_playlists:
                                playlist_file_name = f'{playlist_file_name} ({file_ext})'
                            
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                            
                            previous_playlist_file_path = Path(PurePath().joinpath(root, f'{previous_playlist_file_name}.m3u'))
                            if playlist_file_path not in multi_disc_games_found[game_title].keys():
                                value = multi_disc_games_found[game_title].pop(previous_playlist_file_path)
                                multi_disc_games_found[game_title][playlist_file_path] = value
                                print(f'---Changing Existing Playlist Name From: "{previous_playlist_file_name}"')
                                print(f'                                     To: "{playlist_file_name}"')
                        
                        else:
                            if seperate_disc_format_playlists:
                                playlist_file_name = f'{playlist_file_name} ({file_ext})'
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        # Check if playlist name has already been added and make sure it uses the same playlist path.
                        playlist_file_path_exists = False
                        skip_compilation_disc = False
                        for existing_playlist_file_path in multi_disc_games_found[game_title].keys():
                            if playlist_file_path.name == existing_playlist_file_path.name:
                                
                                if playlist_file_path != existing_playlist_file_path: # Different Directories
                                    # Detected possible compilation game or a second+ game with the same name.
                                    # Sometimes different games may have the same name, most likely from different platforms.
                                    # Note: The different games would have to have the same "Game Info".
                                    #       So there shouldn't be any false positives, but who knows.
                                    if ignore_compilation_discs:
                                        multi_disc_games_found[game_title].pop(existing_playlist_file_path)
                                        if not multi_disc_games_found[game_title]:
                                            multi_disc_games_found.pop(game_title)
                                        skip_compilation_disc = True
                                    else:
                                        if save_compilation_playlists_one_level_up:
                                            value = multi_disc_games_found[game_title].pop(existing_playlist_file_path)
                                            compilation_playlist_file_path = Path(PurePath().joinpath(existing_playlist_file_path.parents[1], existing_playlist_file_path.name))
                                            multi_disc_games_found[game_title][compilation_playlist_file_path] = value
                                        else:
                                            compilation_playlist_file_path = existing_playlist_file_path
                                        playlist_file_path = compilation_playlist_file_path
                                        playlist_file_path_exists = True
                                else:
                                    playlist_file_path = existing_playlist_file_path
                                    playlist_file_path_exists = True
                                break
                        
                        if playlist_file_path_exists:
                            multi_disc_games_found[game_title][playlist_file_path].append(file_path)
                            print(f'---Adding File Path To Existing Playlist Named: "{playlist_file_name}"')
                        
                        elif not skip_compilation_disc:
                            multi_disc_games_found[game_title][playlist_file_path] = [file_path]
                            playlist_count += 1
                        
                        previous_disc_number = current_disc_number
                        previous_playlist_file_name = playlist_file_name
                    
                    else: # New Game Found
                        previous_disc_number = int(re_disc_pattern.search(file_path.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {previous_disc_number}')
                        
                        playlist_file_name = re_disc_pattern.sub('', file_path.stem)
                        previous_playlist_file_name = playlist_file_name
                        if seperate_disc_format_playlists:
                            playlist_file_name = f'{playlist_file_name} ({file_ext})'
                        print(f'---Adding File Path To New Playlist Named: "{playlist_file_name}"')
                        playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        multi_disc_games_found[game_title] = { playlist_file_path : [file_path] }
                        playlist_count += 1
                    
                    #print(f'\nmulti_disc_games_found: {multi_disc_games_found}')
                    #input()
    #print(f'\nmulti_disc_games_found: {multi_disc_games_found}')
    
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
            
            if game_info not in all_game_info_list:
                all_game_info_list.append(game_info)
            else:
                if game_info not in matching_game_info_list:
                    matching_game_info_list.append(game_info)
    
    return matching_game_info_list


### Create playlists for all multi-disc games found.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created and the paths to each disc.
###     (playlist_count) Amount of playlist to be created.
###     --> Returns a [Integer] and [Integer]
def createPlaylists(multi_disc_games_found, playlist_count):
    
    new_playlists_created = 0
    playlists_overwritten = 0
    
    print('\n--------------------------------------------------------------------------')
    print('Now creating M3U Playlists For All Multi-Disc Games Found')
    print('--------------------------------------------------------------------------\n')
    
    for game, playlists in multi_disc_games_found.items():
        print('--------------------------------------------------------------------------')
        print(f'-Game Title: {game}')
        print('--------------------------------------------------------------------------')
        for playlist_path, game_disc_paths in playlists.items():
            
            if len(game_disc_paths) > 1:
                print(f'--Playlist Path: {playlist_path}')
                
                n = 0
                for game_disc_path in game_disc_paths:
                    n += 1
                    print(f'---Disc #{n} Path: {game_disc_path}')
                
                if Path.exists(playlist_path) and overwrite_playlists:
                    overwrite = True
                elif Path.exists(playlist_path) and not overwrite_playlists:
                    overwrite = False
                else:
                    overwrite = True
                
                if overwrite:
                    new_playlists_created += 1
                    playlist_path.write_text('\n'.join([str(path) for path in game_disc_paths]),
                                             encoding='utf-8', errors=None, newline=None)
    
    return new_playlists_created, playlists_overwritten


### Script Starts Here
if __name__ == '__main__':
    print(sys.version)
    print('\n=======================================')
    print('Auto M3U Playlist Generator by JDHatten')
    print('=======================================\n')
    MIN_VERSION = (3,4,0)
    MIN_VERSION_STR = '.'.join([str(n) for n in MIN_VERSION])
    assert sys.version_info >= MIN_VERSION, f'This Script Requires Python v{MIN_VERSION_STR} or Newer'
    
    dir_paths = sys.argv[1:]
    new_playlists_created, playlists_overwritten = 0,0
    
    if not dir_paths:
        dir_paths = [os.path.dirname(os.path.abspath(__file__))]
    
    i = 0
    for dir_path in dir_paths:
        multi_disc_games_found, playlist_count = findMultiDiscGames(dir_path)
        if playlist_count:
            s = 's' if playlist_count > 1 else ''
            input(f'\nAll data retrieved and ready to create playlists for {playlist_count} multi-disc game{s}. Press [ENTER] to start...')
            new_playlists_created, playlists_overwritten = createPlaylists(multi_disc_games_found, playlist_count)
            if new_playlists_created or playlists_overwritten:
                print(f'\nNew Playlists Created: {new_playlists_created}')
                print(f'Playlists Overwritten: {playlists_overwritten}')
            else:
                print('No Playlists Created')
        else:
            print('\nNo multi-disc games found.')
        i =+ 1
        if len(dir_paths) > i:
            input(f'\nPress [Enter] to continue with next directory... {dir_paths[i]}')
        else:
            input('\nAll Done!')
        
