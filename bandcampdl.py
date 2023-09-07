import html
import json
import os
import re
import requests
import sys

class Track():
    def __init__(self):
        self.title = ""
        self.url = ""


class Album():
    def __init__(self):
        self.artist = ""
        self.art_url = ""
        self.title = ""
        self.tracks = []


class BandcampDL():
    __url_chars = r"[a-zA-Z0-9_\-*()+,;'&$!@\[\]#?/:~=%.]"
    __message = {
            "invalid_album":    "\033[31mInvalid album URL: {}\033[0m",
            "invalid_artist":   "\033[31mInvalid artist URL: {}\033[0m",
            "unavailable":      "\033[31mTrack is unavailable: {}\033[0m",
            "dl_album":         "*\033[33mDownloading album: {}...\033[0m",
            "writing_to":       "--\033[33mWriting to {}...\033[0m",
            "write_error":      "\033[31mError writing to {}\033[0m",
            "done":             "\033[36mDone!\033[0m",
            "abort":            "\033[31mAborting!\033[0m",
            "building":         "\033[33mBuilding albums...\033[0m"
            }
    __wait_sequence = {
            "-":    "\\",
            "\\":   "|",
            "|":    "/",
            "/":    "-"
            }


    def usage(self):
        print("Bandcamp album downloader")
        print("Usage:")
        print("python3 bandcampdl.py [album URL]")
        print("python3 bandcampdl.py -f [file containing multiple URLs]")
        print("python3 bandcampdl.py -a [artist page]")


    def __init__(self):
        self.albums = []
        self.wait_char = "-"
        self.wait = False


    def __wait(self):
        self.wait_char = self.__wait_sequence[self.wait_char]
        print("\b" + self.wait_char, end='', flush=True)


    def __wait_start(self, message):
        self.wait = True
        print(self.__message[message] + self.wait_char, end='', flush=True)


    def __wait_over(self):
        print("\b" + self.__message["done"])



    def __build_album(self, html):
        if self.wait:
            self.__wait()
        album = Album()
        album_json = None
        for line in html:
            if album.art_url == "":
                if "class=\"popupImage\"" in line:
                    album.art_url = line.split("href=\"")[1].split("\">")[0]
            if album_json is None:
                if line.find("<script") != -1 and line.find('mp3-128') != -1:
                    line = line.split("data-tralbum=\"")[1].split("\"")[0].replace("&quot;", "\"")
                    album_json = json.loads(line)

        album.artist = self.__filter_name(album_json["artist"])
        album.title = self.__filter_name(album_json["current"]["title"])

        for t in album_json["trackinfo"]:
            track = Track()
            track.title = self.__filter_name(t["title"])
            track.url = t["file"]["mp3-128"]
            album.tracks.append(track)

        self.albums.append(album)
            

    def __get_html(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Status code {}: {}"
                            .format(response.status_code, 
                                    url))
        return response.text.split('\n')


    def __filter_name(self, name):
        key = {'&': 'and',
               '+': 'plus',
               '=': 'equals',
               '/': ' and ',
               '|': ' ',
               ':': '-'
               }
        for k, v in key.items():
            name = name.replace(k, v)
        return re.sub("[~\"#%*<>?\\{}]", '', name)


    def __get_album_urls(self, base_url, html):
        album_urls = []
        for line in html:
            if "<a href=\"/album" in line:
                tail = line.split("href=\"")[1].split("\">")[0]
                album_urls.append(base_url + tail)
        return album_urls


    def __get_albums(self, music_path="./Music"):
        if not os.path.exists(music_path):
            os.mkdir(music_path)
        for album in self.albums:
            print(self.__message["dl_album"].format(album.title))
            artist_path = "{}/{}".format(music_path, album.artist)
            album_path = "{}/{}".format(artist_path, album.title)
            if not os.path.exists(artist_path):
                os.mkdir(artist_path)
            if not os.path.exists(album_path):
                os.mkdir(album_path)

            art_path = album_path + "/cover.jpg"
            response = requests.get(album.art_url)
            self.__write_data(art_path, response.content)

            for track in album.tracks:
                track_path = album_path + "/{}.mp3".format(track.title)
                response = requests.get(track.url)
                if response.status_code != 200:
                    print(self.__message["unavailable"].format(track.title))
                else:
                    self.__write_data(track_path, response.content)


    def __is_album(self, url):
        fmt_str = r"https:\/\/{}*\.bandcamp\.com\/album\/{}*"
        if not re.match(fmt_str.format(self.__url_chars, self.__url_chars), url):
            print(self.__message["invalid_album"].format(url))
            print(self.__message["abort"])
            exit(1)


    def __is_artist(self, url):
        fmt_str = r"https:\/\/{}*\.bandcamp\.com$"
        if not re.match(fmt_str.format(self.__url_chars), url):
            print(self.__message["invalid_artist"].format(url))
            print(self.__message["abort"])
            exit(1)

    # change this to download and write
    def __write_data(self, path, data):
        with open(path, 'wb') as file:
            print(self.__message["writing_to"].format(path), end='', flush=True)
            try:
                file.write(data)
            except IOError:
                print("\n", self.__message["write_error"].format(path))
            finally:
                print(self.__message["done"])


    def get_from_list(self, url_list):
        for url in url_list:
            self.__is_album(url)
        self.__wait_start("building")
        for url in url_list:
            url = url.replace('\n', '')
            html = self.__get_html(url)
            self.__build_album(html)
        self.__wait_over()
        self.__get_albums()


    def get_from_url(self, url):
        url = url.replace('\n', '')
        self.__is_album(url)
        html = self.__get_html(url)
        self.__build_album(html)
        self.__get_albums()


    def get_from_artist(self, url):
        self.__is_artist(url)
        html = self.__get_html(url)
        album_urls = self.__get_album_urls(url, html)
        self.get_from_list(album_urls)

            
if __name__ == '__main__':
    bcdl = BandcampDL()
    if (len(sys.argv) < 2 or len(sys.argv) > 3):
        bcdl.usage()
    elif (sys.argv[1] == '-h'):
        bcdl.usage()
    elif (sys.argv[1] == '-f'):
        print("Getting urls from", sys.argv[2])
        url_list = open(sys.argv[2], "r").readlines()
        bcdl.get_from_list(url_list)
    elif (sys.argv[1] == '-a'):
        bcdl.get_from_artist(sys.argv[2])
    else:
        bcdl.get_from_url(sys.argv[1])
