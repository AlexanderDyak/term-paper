from datetime import datetime
from fake_useragent import UserAgent
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
from requests import get
import os
import psycopg2

next_end_url = ''


class MyError(Exception):
    pass


class Parser:
    page_urls_list = []

    def __init__(self):
        self.url = None
        self.soup = None
        self.end_url = None
        self.next_end_url = None

    def get_all_site_information(self, url, header):
        try:
            self.url = url
            page_list = get(self.url, headers=header)
            if page_list.status_code == 404:
                raise MyError('site is disabled or ads are over')
            self.soup = BeautifulSoup(page_list.text, "lxml")
            return True
        except MyError:
            return False

    def get_ads_urls(self, tag, target_information, class_=None, href=None, target=None, text=None):
        urls_list = []
        urls = self.soup.findAll(tag, class_=class_, href=href, target=target, text=text)
        for url in urls:
            if target_information in url.get('href'):
                urls_list.append('https://zakupki.gov.ru' + url.get('href'))
        return urls_list

    def relevance_checking(self):
        if self.url == self.end_url:
            return False
        return True


class DBwork(Parser):
    def __init__(self):
        super().__init__()
        self.inn = None
        self.company_name = None
        self.purchase_name = None
        self.notice_id = None
        self.date = None
        self.company_region = None
        self.purchase_price = None


    def get_page_information(self, tg):
        pars_list = []
        target_list = {'Наименование объекта закупки', 'Наименование закупки', 'Размещено', 'Наименование организации',
                       'Организация, осуществляющая размещение', 'Место нахождения'}
        for i in target_list:
            try:
                pars_list.append(self.soup.find(text=i).find_next(tg).text.strip())
            except:
                continue
        for define in pars_list:
            try:
                list(map(int, define.split('.')))
                self.date = define
                continue
            except:
                pass
            if define == define.upper() and not (('российская федерация' in define.lower().split(',')[0] and
                                                  define.lower().split(',')[1].isdigit) or define.lower().split(',')[
                                                     0].isdigit()):
                self.company_name = define.capitalize()
                continue
            elif ('российская федерация' in define.lower().split(',')[0] and define.lower().split(',')[1].isdigit) or \
                    define.lower().split(',')[0].isdigit():
                DBwork.get_company_region(self, define.lower())
                continue
            else:
                self.purchase_name = define
        DBwork.get_purchase_price(self)
        return True

    def get_notice_id(self):
        notice_id = self.soup.find('a', attrs={'target': '_blank', 'href': ''})
        if not notice_id:
            notice_id = self.soup.find('a', attrs={'target': '_blank', 'href': '#'})
            self.notice_id = notice_id.text.strip()[2:]
            return False
        self.notice_id = notice_id.text.strip()[2:]
        return True

    def look_at_curdare(self):
        return self.date

    def get_purchase_price(self):
        price = self.soup.find('div', class_='price-block__value')
        if not price:
            price = self.soup.find('span', class_='cardMainInfo__content cost')
            if not price:
                return
        self.purchase_price = round(int(''.join(price.text.strip()[:price.text.strip().find(',')].split())) / 1000000000, 2)
    def get_company_inn(self):
        try:
            self.inn = self.soup.find('div', class_='ml-1 common-text__value').text.strip()
        except:
            return

    def get_company_region(self, address: str):
        try:
            if 'москва' in address:
                self.company_region = 'Московская область'
            if 'санкт-петербург' in address:
                self.company_region = 'Ленинградская область'
            regs = ['респ', 'ао', 'край', 'обл', 'автономн']
            for i in address.split(','):
                for j in regs:
                    for k in i.split():
                        if k.find(j) != -1:
                            region = i.replace(k, '').strip().capitalize()
                            if j == regs[0]:
                                self.company_region = region + ' республика'
                                return
                            elif j == regs[1] or j == regs[-1]:
                                self.company_region = region + ' автономный округ'
                                return
                            elif j == regs[2]:
                                self.company_region = region + ' край'
                                return
                            elif j == regs[3]:
                                self.company_region = region + ' область'
                                return
        except:
            return

    def get_docs_install_url(self, tg, hr, dt, tl, header):
        docs = self.soup.findAll(tg, attrs={'href': hr, 'data-tooltip': dt})
        if not docs:
            docs = self.soup.findAll(tg, attrs={'href': hr, 'title': tl})
        for i in docs:
            if len(i.text.split()) == 0:
                continue
            try:
                file_name = i.get('data-tooltip')[i.get('data-tooltip').find('>') + 1:i.get('data-tooltip').rfind('<')]
            except AttributeError:
                file_name = i.text.strip()
            if 'https' in i.get('href'):
                DBwork.docs_install(self, i.get('href'), header,
                                    file_name)
            else:
                DBwork.docs_install(self, 'https://zakupki.gov.ru' + i.get('href'), header,
                                    file_name)
        return

    def docs_install(self, file_link, header, file_name):
        if not os.path.isdir(self.notice_id):
            os.mkdir(self.notice_id)
        os.chdir(self.notice_id)
        try:
            r = get(url=file_link, stream=True, headers=header)
        except:
            return
        with open(file_name, 'wb') as f:
            f.write(r.content)
        os.chdir('..')
    def db_connection(self):
        '''подключаемся к базе'''
        self.connection = psycopg2.connect(user="postgres",
                                           # пароль, который указали при установке PostgreSQL
                                           password="",
                                           host="127.0.0.1",
                                           port="5432",
                                           database="postgres_db")
        self.cursor = self.connection.cursor()

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS state_parse
                                        (   ID SERIAL PRIMARY KEY   NOT NULL,
                                            ID_закупки    VARCHAR,
                                            Объект_закупки   TEXT,
                                            Регион  VARCHAR,
                                            Название_компании VARCHAR,
                                            Дата_закупки    DATE,
                                            Итоговая_сумма  REAL,
                                            ИНН_компании VARCHAR,
                                            Путь_до_документов VARCHAR,
                                            Ссылка  VARCHAR
                                            ); ''')
        self.connection.commit()
        self.cursor.execute(
            "INSERT INTO state_parse (ID_закупки, Объект_закупки, Регион, Название_компании, Дата_закупки, Итоговая_сумма, ИНН_компании, Путь_до_документов, Ссылка) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (self.notice_id, self.purchase_name, self.company_region, self.company_name, self.date, self.purchase_price,
             self.inn, os.path.join(os.getcwd(), self.notice_id), self.url))
        self.connection.commit()


def look_at_prev_end_url():
    if not os.path.exists('url_relevance.txt'):
        f = open('url_relevance.txt', "w")
        f.close()
    with open('url_relevance.txt', 'r') as url_file:
        end_url = url_file.read()
    return end_url


def next_end_url_update(next_end_url):
    with open('url_relevance.txt', 'w') as url_file:
        url_file.write(next_end_url)


def main():
    """костыль1 - глобальная переменная next_end_url, нужна, чтобы записать следующим последним url текущий, если программа
    будет прервана вручную
    костыль2 - переменная exeption, нужна, чтобы сразу выйти из 2-ух циклов"""
    global next_end_url
    if not os.path.isdir('StateProc_Docs'):
        os.mkdir('StateProc_Docs')
    os.chdir('StateProc_Docs')
    """используем рандомного юзера, чтобы сайт не понял, что это парсинг"""
    user = UserAgent().random
    header = {'User-Agent': user}
    """текущая дата указывается для поиска нужных объявлений, идем перебором с текущей даты"""
    current_date = datetime.now()
    main_page = Parser()
    """всего на сайте максимально показывается 100 страниц и мы идем в цикле, пока есть эти страницы, цикл while True
    был выбран для того, чтобы на 100-ой странице можно было изменить дату, и, соответственно условия поиска, для того,
    чтобы увидеть более ранние записи, а также для того, чтобы выйти из цикла при нахождении уже существующей записи"""
    page_number = 1
    pars_page = None
    end_url = look_at_prev_end_url()
    exeption = False
    while True:
        """начинаем с начальной страницы, всего на начальной странице показывается 10 объявлений, сосавляем их список
        и идем в цикле по каждому"""
        main_page.get_all_site_information(
            'https://zakupki.gov.ru/epz/order/extendedsearch/results.html?morphology=on&search-filter=%D0%94%D0%B0%D1'
            f'%82%D0%B5+%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&pageNumber={page_number}'
            '&sortDirection=false '
            '&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=PUBLISH_DATE&fz44=on&fz223=on&pc=on&priceFromGeneral'
            f'=1000000000&currencyIdGeneral=-1&publishDateTo={current_date.strftime("%d.%m.%Y")}', header)
        list_of_urls = main_page.get_ads_urls(tag='a', target_information='common-info', class_=False, href=True,
                                              target='_blank', text=True)
        for next_page_url in list_of_urls:
            '''следующее условие нужно для того, чтобы сохранить самый первый url, на следующий вызов программы мы
            будем идти до него'''
            if not next_end_url:
                next_end_url = list_of_urls[0]
            pars_page = DBwork()
            pars_page.end_url = end_url
            pars_page.get_all_site_information(next_page_url, header)
            '''проверяем, не совпал ли url текущего объявления с конечным'''
            relevance = pars_page.relevance_checking()
            if not relevance:
                next_end_url_update(next_end_url)
                exeption = True
                break
            '''на сайте существуют объявления 2-ух типов, определяем тип текущего объявления найдя его id'''
            ad_type_definition = pars_page.get_notice_id()
            if not ad_type_definition:
                pars_page.get_page_information('span')
            else:
                pars_page.get_page_information('div')
            pars_page.get_company_inn()
            """смотрим есть ли в объявлении документы"""
            docs_url = pars_page.get_ads_urls('a', 'documents', 'tabsNav__item', True)[0]
            if docs_url:
                pars_page.get_all_site_information(docs_url, header)
                pars_page.get_docs_install_url('a', True, True, True, header)
            pars_page.db_connection()
        page_number += 1
        if exeption:
            break
        if page_number == 100:
            """если мы достигли последней, 100-ой страницы, то теперь будем выполнять поиск с другими параметрами,
            чтобы увидеть более старые объявления"""
            current_date = pars_page.look_at_curdare()
            page_number = 1
    next_end_url_update(next_end_url)

try:
    if __name__ == '__main__':
        main()
except ConnectionError:
    print('No internet connection')
except KeyboardInterrupt:
    print('program interrupted manually')
    next_end_url_update(next_end_url)
