from bs4 import BeautifulSoup
from requests import get
import os


class MyError(Exception):
    def __init__(self, text):
        self.txt = text


class Parser:
    def __init__(self):
        self.url = None
        self.tg = None
        self.cls = None
        self.ads = None
        self.end_url = None

    def Get_all_site_information(self, url, tg, cls, header):
        try:
            self.url = url
            self.tg = tg
            self.cls = cls
            page_list = get(self.url, headers=header)
            if page_list.status_code == 404:
                raise MyError('site is disabled or ads are over')
            soup = BeautifulSoup(page_list.text, "lxml")
            self.ads = soup.findAll(self.tg, class_=self.cls)
            if not self.ads:
                raise MyError('for some reason the ads are empty')
            return True
        except MyError as ErrorText:
            print(ErrorText)
            return False

    def GetNextUrl(self, tag, cls, target, text):
        for ad in self.ads:
            ad_p = ad.find(tag, class_=cls, target=target, text=text)
            self.ads.remove(ad)
            return ad_p

    def relevance_checking(self):
        if self.url == self.end_url:
            return False
        return True

    def look_at_prev_end_url(self):
        if not os.path.exists('url_relevance.txt'):
            f = open('url_relevance.txt', "w")
            f.close()
        with open('url_relevance.txt', 'r') as url_file:
            self.end_url = url_file.read()
        return self.end_url

    @staticmethod
    def next_end_url_update(url):
        with open('url_relevance.txt', 'w') as url_file:
            url_file.write(url)
