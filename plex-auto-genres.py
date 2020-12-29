import os
import sys
import argparse
import math
import time
import json
import signal
import datetime
from tmdbv3api import TMDb, Movie, TV
from jikanpy import Jikan
from plexapi.myplex import MyPlexAccount, PlexServer

jikan = Jikan()
tmdb = TMDb()
movie = Movie()
tv = TV()

signal.signal(signal.SIGINT, signal.default_int_handler)

PLEX_USERNAME = os.getenv("PLEX_USERNAME")
PLEX_PASSWORD = os.getenv("PLEX_PASSWORD")
PLEX_SERVER_NAME = os.getenv("PLEX_SERVER_NAME")
PLEX_BASE_URL = os.getenv("PLEX_BASE_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
tmdb.api_key = os.getenv("TMDB_API_KEY")

example_text = '''example:

 python plex-auto-genres.py --library "Anime Shows" --type anime
'''

parser = argparse.ArgumentParser(description='Adds genre tags (collections) to your Plex media.', epilog=example_text)
parser.add_argument('--library', action='store', dest='library', nargs=1,
                    help='The exact name of the Plex library to generate genre collections for.')
parser.add_argument('--type', dest='type', action='store', choices=('anime', 'standard-movie', 'standard-tv'), nargs=1,
                    help='The type of media contained in the library')


if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

args = parser.parse_args()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def connect_to_plex():
    print('\nConnecting to Plex...')
    try:
        if PLEX_USERNAME is not None and PLEX_PASSWORD is not None and PLEX_SERVER_NAME is not None:
            account = MyPlexAccount(PLEX_USERNAME, PLEX_PASSWORD)
            plex = account.resource(PLEX_SERVER_NAME).connect()
        elif PLEX_BASE_URL is not None and PLEX_TOKEN is not None:
            plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
        else:
            raise Exception("No valid credentials found. See the README for more details.")
    except Exception as e:
        print(str(e))
        sys.exit(0)
    return plex


def get_sleep_time(type):
    if ("standard" in type):
        return 0.5 # tmdb doesn't have a rate limit, but we sleep for 0.5 anyways
    else:
        return 8 #Jikan fetch requires 2 request with a 4 second sleep on each request

def fetch_anime(title):
    title = title.split(' [')[0]
    if (len(title.split()) > 10):
        title = " ".join(title.split()[0:10])
    time.sleep(4)
    search_result = jikan.search('anime', title, page=1)
    result_id = search_result['results'][0]['mal_id']
    time.sleep(4)
    anime_jikan = jikan.anime(result_id)
    genres = anime_jikan['genres']
    genres_list = []
    for genre in genres:
        genres_list.append(genre['name'])
    return genres_list

def fetch_standard(title):
    time.sleep(0.5)
    if (args.type[0] == 'standard-movie'):
        db = movie
    else:
        db = tv
    search = db.search(title)
    if (len(search) == 0):
        return []
    details = db.details(search[0].id)
    genre_list = []
    for genre in details.genres:
        genre_list.extend(genre['name'].split(' & '))
    return genre_list

def generate():
    plex = connect_to_plex()
    finished_media = []
    failed_media = []
    if (os.path.isfile('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-tags-finished.txt')):
        with open('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-tags-finished.txt') as save_data:
            finished_media = json.load(save_data)
    if (os.path.isfile('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-failures.txt')):
        with open('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-failures.txt') as save_data:
            failed_media = json.load(save_data)
    try:
        medias = plex.library.section(args.library[0]).all()
        total_count = len(medias)
        unfinished_count = 0
        for m in medias:
            if (m.title not in finished_media):
                unfinished_count += 1
        finished_count = total_count - unfinished_count

        eta = ((unfinished_count * get_sleep_time(args.type[0])) / 60) * 2
        time_now = datetime.datetime.now()
        time_done = time_now + datetime.timedelta(minutes=eta)
        print("Found {} media entries under {} ({}/{} completed), estimated time to completion ~{} minutes ({})...\n".format(total_count, args.library[0], finished_count, total_count, math.ceil(eta), time_done.strftime("%I:%M %p")))

        working_index = 0
        for m in medias:
            working_index += 1
            if (m.title in finished_media or m.title in failed_media):
                printProgressBar(working_index, total_count, prefix = 'Progress:', suffix = 'Complete', length = 50)
                continue
            if (args.type[0] == 'anime'):
                genres = fetch_anime(m.title)
            else:
                genres = fetch_standard(m.title)

            if (len(genres) == 0):
                failed_media.append(m.title)
                continue
            for genre in genres:
                m.addCollection(genre.strip())

            finished_media.append(m.title)
            printProgressBar(working_index, total_count, prefix = 'Progress:', suffix = 'Complete', length = 50)
        print('\n'+bcolors.FAIL+'Failed to get genre information for '+str(len(failed_media))+' entries. '+bcolors.ENDC+'See '+'plex-'+args.library[0]+'-'+args.type[0]+'-failures.txt')

    except KeyboardInterrupt:
        print('\n\nOperation interupted, progress has been saved.')
        pass
    except Exception as e:
        print(str(e))

    if (len(finished_media) > 0):
        with open('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-tags-finished.txt', 'w') as filehandle:
            json.dump(finished_media, filehandle)
    if (len(failed_media) > 0):
        with open('/logs/plex-'+args.library[0]+'-'+args.type[0]+'-failures.txt', 'w') as filehandle:
            json.dump(failed_media, filehandle)
    
    sys.exit(0)

if __name__ == '__main__':
    print("\nYou are about to create ["+bcolors.WARNING+args.type[0]+bcolors.ENDC+"] genre collection tags for the library ["+bcolors.WARNING+args.library[0]+bcolors.ENDC+"] on your server ["+bcolors.WARNING+(PLEX_SERVER_NAME or PLEX_BASE_URL)+bcolors.ENDC+"].")
    generate()