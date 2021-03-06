import os
import re
import requests
import html


class BandcampDL():
    message = {"unavailable": "\033[31mSome tracks in this album"
               "aren't available. Skipping...\033[0m",
               "invalid": "\033[31mInvalid album URL: {}\033[0m",
               "dl_album": "\033[33mDownloading album: {}\033[0m",
               "dl_track": "\033[33mDownloading track: {}\033[0m"
               }

    def __init__(self):
        self.album = ""
        self.artist = ""
        self.tracks = []
        self.album_url = ""
        self.cover_art_url = ""
        self.html = []

# def __print(self, string, color):
#     key = {"reset": "",
#            "red": "",
#            "green": "\033[32m",
#            "yellow": "\033[33m",
#            "blue": "\033[34m",
#            "magenta": "\033[35m",
#            "cyan":
#            }
#     print("{}{}{}".format(key[color], string, key["reset"]))

    def __unescape(self, s):
        return html.unescape(html.unescape(s))

    def __parse_album_info(self):
        i = 0
        while i < len(self.html):
            if self.html[i].startswith("    <meta name=\"description\""):
                j = i + 3
                while self.html[j] != "":
                    title_raw = ' '.join(self.html[j].split(" ")[1:])
                    title = self.__filter_name(self.__unescape(title_raw))
                    self.tracks.append(title)
                    j += 1
            if self.html[i].startswith("        <meta name=\"title\""):
                info = self.html[i].split("content=\"")
                info = info[1].split("\"")[0].split(", by ")
                self.album = self.__filter_name(self.__unescape(info[0]))
                self.artist = self.__filter_name(self.__unescape(info[1]))
            if self.html[i].startswith("            <a class=\"popupImage\""):
                cover_art = self.html[i].split("href=\"")[1].split("\">")[0]
                self.cover_art_url = cover_art
                break
            i += 1

    def __parse_track_urls(self):
        mp3_script = None
        for i in self.html:
            if i.find("<script") != -1 and i.find('mp3-128') != -1:
                mp3_script = i
                break
        track_urls = mp3_script.split("{&quot;mp3-128&quot;:&quot;")[1:]
        if len(track_urls) != len(self.tracks):
            return(False)
        i = 0
        while i < len(track_urls):
            url = track_urls[i].split('&quot;}')[0].replace('amp;', '')
            self.tracks[i] = {"title": self.tracks[i], "url": url}
            i += 1
        return(True)

    def __get_html(self):
        response = requests.get(self.album_url)
        if response.status_code != 200:
            raise Exception("Status code {}: {}"
                            .format(response.status_code, self.album_url))
        self.html = response.text.split('\n')

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

    def __check_path(self):
        if not os.path.exists("./Music"):
            os.mkdir("./Music")
        if not os.path.exists("./Music/{}".format(self.artist)):
            os.mkdir("./Music/{}" .format(self.artist))
        if not os.path.exists("./Music/{}/{}".format(self.artist,
                                                     self.album)):
            os.mkdir("./Music/{}/{}".format(self.artist,
                                            self.album))

    def __get_track(self, title, url):
        print(self.message["dl_track"].format(title), end="...")
        track_data = requests.get(url)
        file_path = "./Music/{}/{}/{}.mp3".format(self.artist,
                                                  self.album,
                                                  title)
        with open(file_path, 'wb') as file:
            try:
                file.write(track_data.content)
            except IOError:
                print("\nCouldn't write to {}".format(file_path))
            finally:
                print("\033[36mDone!\033[0m")

    def __get_album(self, album_url):
        self.__check_path()
        cover_art_data = requests.get(self.cover_art_url)
        cover_art_path = "./Music/{}/{}/cover.jpg".format(self.artist,
                                                          self.album)
        with open(cover_art_path, 'wb') as file:
            file.write(cover_art_data.content)
        for t in self.tracks:
            self.__get_track(t["title"], t["url"])

    def get_from_file(self, file):
        with open(file, 'r') as album_list:
            for album in album_list:
                if self.__is_album(album):
                    self.album_url = album.replace('\n', '')
                    print(self.message["dl_album"].format(self.album_url))
                    self.__get_html()
                    self.__parse_album_info()
                    has_tracks = self.__parse_track_urls()
                    if has_tracks:
                        self.__get_album(self.album_url)
                    else:
                        print(self.message["unavailable"])
                    # self.__get_album()
                    self.__init__()
                else:
                    print(self.message["invalid"].format(album))
                    exit(1)

    def get_from_url(self, url):
        if self.__is_album(url):
            print(self.message["dl_album"].format(url))
            self.__get_album(url)
        else:
            print(self.message["invalid"].format(url))
            exit(1)

    def __is_album(self, url):
        urlchars = r"[a-zA-Z0-9_\-*()+,;'&$!@\[\]#?/:~=%.]"
        fmt_str = r"https:\/\/{}*\.bandcamp\.com\/album\/{}*"
        if re.match(fmt_str.format(urlchars, urlchars), url):
            return True
        return False


if __name__ == '__main__':
    import sys

    bcdl = BandcampDL()

    def usage():
        print("Bandcamp album downloader")
        print("Usage:")
        print("./python3 bandcampdl.py [album url]")
        print("./python3 bandcampdl.py -f [file]")

    if (len(sys.argv) < 2 or len(sys.argv) > 3):
        usage()
    elif (sys.argv[1] == '-h'):
        usage()
    elif (sys.argv[1] == '-f'):
        bcdl.get_from_file(sys.argv[2])
    else:
        bcdl.get_from_url(sys.argv[1])
