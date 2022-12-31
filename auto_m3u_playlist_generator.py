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
    [] Handle games that may be split into different directories but with the same name
       (compilation discs). Option to not make a playlist for them as they are ‘technically’
       different games in the same package.

'''

from pathlib import Path, PurePath
import os
import re
import sys


# Make different playlists for different disc formats even if they have the same game name.
# If for some reason you have your games in multiple formats. Format/extension will be added
# to playlist file names.
seperate_disc_format_playlists = False

# If your disc image format is not included below add it.
# You can comment out ones you don't want to create playlists for.
disc_extensions = { 'CHD (Compressed Hunks of Data)' : '.chd',
                    'CUE BIN IMG' : '.cue',
                    'ISO' : '.iso',
                    #'MDS MDF' : '.mds'
                  }

# If you edit this regular expression pattern below you must know what group holds the disc
# number and update 're_disc_number_group'. A group is the text found inside (parentheses).
re_disc_number_group = 4
re_disc_pattern = re.compile( '(\s*)' + '(\(|\[)' + '(Disc|CD)' +
                              '\s*(\d*)\s*\w*\s*(\d*)*' + '(\)|\])',
                              re.IGNORECASE ) # Ex. '(Disc 1 of 3)', '[CD2]', etc

# You shouldn't have to edit this as it just gets the 'Game Name' minus '(Any Game Info)...'
re_game_name_pattern = re.compile( '.[^(' + '\(|\[' + ')]*', re.IGNORECASE )

# Note: The + are just added for readability.


### Find multi disc games and get their file paths and create a file name for the playlist.
###     (dir_path) Path to a directory.
###     --> Returns a [Dictionary] and [Integer]
def findMultiDiscGames(dir_path):
    multi_disc_games_found = {}
    playlist_count = 0
    
    for root, dirs, files in os.walk(dir_path):
        
        print('--------------------------------------------------------------------------')
        print(f'Searching Directory For Multi-Disc Games: {root}')
        print('--------------------------------------------------------------------------')
        
        previous_disc_number = 0
        
        for file in files:
            
            file = Path(PurePath().joinpath(root, file))
            file_ext = file.suffix.casefold()
            #print(f'File: {file}')
            
            if file_ext in disc_extensions.values():
                
                game_re = re_disc_pattern.search(file.stem)
                
                if game_re:
                    
                    #print('')
                    #print(f'--game_re: {game_re}')
                    print(f'-Multi-Disc Game File Found: {file.name}')
                    
                    game_name_re = re_game_name_pattern.match(file.stem)
                    game_name = game_name_re.group().strip()
                    print(f'--Game Name: {game_name}')
                    if seperate_disc_format_playlists:
                        game_name = f'{game_name}{file_ext}'
                    
                    if game_name in multi_disc_games_found.keys():
                        
                        current_disc_number = int(re_disc_pattern.search(file.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {current_disc_number}')
                        #print(f'--Prev Disc Number: {previous_disc_number}')
                        
                        if current_disc_number <= previous_disc_number:
                            playlist_file_name = re_disc_pattern.sub('', file.stem)
                            if seperate_disc_format_playlists:
                                playlist_file_name = f'{playlist_file_name} ({file_ext})'
                            print(f'---Adding Path To New Playlist Named: {playlist_file_name}')
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        elif seperate_disc_format_playlists:
                            playlist_file_name = re_disc_pattern.sub('', file.stem)
                            playlist_file_name = f'{playlist_file_name} ({file_ext})'
                            print(f'---Adding Path To New Playlist Named: {playlist_file_name}')
                            playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        if playlist_file_path in multi_disc_games_found[game_name].keys():
                            multi_disc_games_found[game_name][playlist_file_path].append(file)
                            print(f'---Adding Path To Existing Playlist Named: {playlist_file_name}')
                        else:
                            multi_disc_games_found[game_name][playlist_file_path] = [file]
                            playlist_count += 1
                        
                        previous_disc_number = current_disc_number
                    
                    else:
                        previous_disc_number = int(re_disc_pattern.search(file.stem).group(re_disc_number_group))
                        print(f'--Disc Number: {previous_disc_number}')
                        
                        playlist_file_name = re_disc_pattern.sub('', file.stem)
                        if seperate_disc_format_playlists:
                            playlist_file_name = f'{playlist_file_name} ({file_ext})'
                        print(f'---Adding Path To New Playlist Named: {playlist_file_name}')
                        playlist_file_path = Path(PurePath().joinpath(root, f'{playlist_file_name}.m3u'))
                        
                        multi_disc_games_found[game_name] = { playlist_file_path : [file] }
                        playlist_count += 1
        
        #input()
    #print(f'\nmulti_disc_games_found: {multi_disc_games_found}')
    
    return multi_disc_games_found, playlist_count


### Create playlists for all multi-disc games found.
###     (multi_disc_games_found) Dictionary of all multi-disc games and the file paths of
###                              the playlist to be created and the paths to each disc.
###     (playlist_count) Amount of playlist to be created.
###     --> Returns a [None]
def createPlaylists(multi_disc_games_found, playlist_count):
    
    print('\n--------------------------------------------------------------------------')
    print('Now creating M3U Playlists For All Multi-Disc Games Found')
    print('--------------------------------------------------------------------------')
    
    for game, playlists in multi_disc_games_found.items():
        print(f'\n-Game Name: {game}')
        for playlist_path, game_disc_paths in playlists.items():
            print(f'--Playlist Path: {playlist_path}')
            for game_disc_path in game_disc_paths:
                print(f'---Game Disc Path: {game_disc_path}')
            playlist_path.write_text('\n'.join([str(path) for path in game_disc_paths]),
                                     encoding='utf-8', errors=None, newline=None)
    
    return None


### Script Starts Here
if __name__ == '__main__':
    print(sys.version)
    print('\n=====================================')
    print('Auto M3U Playlist Generator by JDHatten')
    print('=====================================\n')
    MIN_VERSION = (3,8,0)
    MIN_VERSION_STR = '.'.join([str(n) for n in MIN_VERSION])
    assert sys.version_info >= MIN_VERSION, f'This Script Requires Python v{MIN_VERSION_STR} or Newer'
    
    dir_paths = sys.argv[1:]
    if not dir_paths:
        dir_paths = [os.path.dirname(os.path.abspath(__file__))]
    i = 0
    for dir_path in dir_paths:
        multi_disc_games_found, playlist_count = findMultiDiscGames(dir_path)
        if playlist_count:
            s = 's' if playlist_count > 1 else ''
            input(f'\nAll data retrieved and ready to create playlists for {playlist_count} multi-disc game{s}. Press [ENTER] to start...')
            createPlaylists(multi_disc_games_found, playlist_count)
        else:
            print('\nNo multi-disc games found.')
        i =+ 1
        if len(dir_paths) > i:
            input(f'\nPress [Enter] to continue with next directory... {dir_paths[i]}')
        else:
            input('\nAll Done!')
        
