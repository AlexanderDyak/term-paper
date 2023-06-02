from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions
import psycopg2.errors
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DBWORK:
    def __init__(self):
        self.url = None
        self.purchase_text = None
        self.connection = None
        self.cursor = None
        self.driver = None
        self.realisation_level = None
        self.sphere = None
        self.industry = None
        self.city = None
        self.dates = None
        self.purchase_id = None
        self.all_money = None
        self.purchase_region = None
        self.private_percent = None
        self.gov_percent = None

    def db_connection(self):
        '''подключаемся к базе'''
        self.connection = psycopg2.connect(user="postgres",
                                           # пароль, который указали при установке PostgreSQL
                                           password="",
                                           host="127.0.0.1",
                                           port="5432",
                                           database="postgres_db")
        self.cursor = self.connection.cursor()
        try:
            self.cursor.execute('DROP TABLE rosinfa')
            self.connection.commit()
        except:
            self.connection.rollback()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS rosinfa
                                    (   ID SERIAL PRIMARY KEY   NOT NULL,
                                        ID_закупки    INT,
                                        Текст_закупки   TEXT,
                                        Сфера   VARCHAR,
                                        Отрасль VARCHAR,
                                        Город   VARCHAR,
                                        Регион  VARCHAR,
                                        Уровень_проекта VARCHAR,
                                        Дата    DATE,
                                        Итоговая_сумма  REAL,
                                        Гос_финансы VARCHAR,
                                        Частные_финансы VARCHAR,
                                        Ссылка  VARCHAR
                                        ); ''')
        self.connection.commit()

    def add_inf(self):
        self.cursor.execute(
            "INSERT INTO rosinfa (ID_закупки, Текст_закупки, Сфера, Отрасль, Город, Регион, Уровень_проекта, Дата, Итоговая_сумма, Гос_финансы, Частные_финансы, Ссылка) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (self.purchase_id, self.purchase_text, self.sphere, self.industry, self.city, self.purchase_region,
             self.realisation_level, self.dates, self.all_money, self.private_percent, self.gov_percent, self.url))
        self.connection.commit()


class PARSER(DBWORK):
    def __init__(self):
        super().__init__()

    def driver_connection(self):
        '''подключаем веб-драйвер'''
        options = Options()
        options.add_argument("--headless")
        '''options=options  можно вписать в ChromeDriverManager() чтобы браузер не открывался'''
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    def site_opening(self, url):
        return self.driver.get(url)

    def filling_out_forms(self, form, information):
        '''заполнение форм на сайте'''
        try:
            return form.send_keys(information)
        except:
            return

    def click(self, click_elem):
        try:
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, click_elem))).click()
        except:
            return

    def searching(self, mode, elem):
        try:
            result = ''
            if mode == 'xpath':
                result = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, elem)))
            elif mode == 'css':
                result = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, elem)))
            return result
        except:
            return

    def results_define(self, general_information, adding_information):
        '''получаем 2 списка с информацией и находим нужное'''
        self.realisation_level = None
        self.sphere = None
        self.industry = None
        self.city = None
        self.dates = None
        self.purchase_id = None
        self.all_money = None
        self.purchase_region = None
        self.private_percent = None
        self.gov_percent = None
        self.sphere = general_information[1]
        for j in range(len(general_information)):
            if general_information[j] == 'Отрасль':
                self.industry = general_information[j + 1]
            elif general_information[j] == 'География':
                if len(general_information[j + 1].split(',')) == 2:
                    self.city = general_information[j + 1].split(',')[1][3:]
        for j in range(len(adding_information)):
            if 'Добавлен:' in adding_information[j]:
                self.dates = adding_information[j][adding_information[j].find(':') + 2:]
            elif '№ проекта:' in adding_information[j]:
                self.purchase_id = adding_information[j][adding_information[j].find(':') + 2:]
            elif adding_information[j] == 'Субъект:':
                self.purchase_region = adding_information[j + 1]
            elif adding_information[j] == 'Всего:':
                self.all_money = float(adding_information[j + 1].split()[0]) / 1000
            elif adding_information[j].find('%') != -1:
                self.private_percent = adding_information[j]
                self.gov_percent = str(100 - int(adding_information[j][:-1])) + '%'
        self.realisation_level = general_information[-1]

    def quit(self):
        self.driver.quit()
        self.cursor.close()
        self.connection.close()


def main():
    pars_page = PARSER()
    pars_page.driver_connection()
    pars_page.db_connection()
    pars_page.site_opening("https://dpo.rosinfra.ru/user/login?page=1&return_url=https%3A%2F%2Fdpo.rosinfra.ru%2Fbase"
                           "-projects%2Fall%3Fpage%3D1")
    login = pars_page.searching('xpath', '/html/body/div[1]/div/div/div[2]/div/div/form/div/div[2]/div[1]/div['
                                         '1]/div/input')
    password = pars_page.searching('xpath', '//*[@id="__layout"]/div/div[2]/div/div/form/div/div[2]/div[2]/div['
                                            '1]/div/input')
    '''вставьте в следующие 2 строки свой email и пароль от сайта'''
    pars_page.filling_out_forms(login, "")
    pars_page.filling_out_forms(password, "")

    pars_page.click("#__layout > div > div.auth-page > div > div > form > div > div.v-form__content > button")
    page_number = 1
    try:
        while True:
            '''идем пока есть объявления'''
            for i in range(1, 10):
                try:
                    '''на странице 9 объявлений, идем по ним'''
                    page = pars_page.searching('css', f'#__layout > div > div.layout-inner_9rJ6u > div.content_2DG7H > '
                                                  f'div > div.base-project-page.p-6 > div.content-container > '
                                                  f'div.base-project-body > div:nth-child(2) > div:nth-child(2) > '
                                                  f'div:nth-child({i}) > div:nth-child(3) > div > a')
                    pars_page.purchase_text = page.text
                    pars_page.url = page.get_attribute('href')
                    pars_page.site_opening(page.get_attribute('href'))
                    '''страница с проектом довольно долго грузится, делаем вынужденное ожидание'''
                    pars_page.driver.implicitly_wait(40)
                    i = 2
                    while True:
                        subtitle_text = pars_page.searching('css',
                                                        f'#__layout > div > div.layout-inner_9rJ6u > nav > div.submenu > div:nth-child({i}) > a > span')
                        if subtitle_text.text == 'Проект':
                            pars_page.click(
                                f'#__layout > div > div.layout-inner_9rJ6u > nav > div.submenu > div:nth-child({i}) > a > span')
                            break
                        i += 1
                    all_inf = pars_page.searching('css', '#__layout > div > div.layout-inner_9rJ6u > div.content_2DG7H > '
                                                     'div > div > div.project-content.p-6 > div > '
                                                     'div.ui-col.ui-col-xs-9 > div > div > div > div.row.g-3 > '
                                                     'div:nth-child(1) > div:nth-child(2) > div > div')
                    adding_inf = pars_page.searching('css', '.project-edit__aside-wrap')
                    adding_information = adding_inf.text.split('\n')
                    general_information = all_inf.text.split('\n')
                    pars_page.results_define(general_information, adding_information)
                    pars_page.add_inf()
                    '''метод back() не используется потому что мы не знаем на сколько страниц назад нужно вернуться'''
                    pars_page.site_opening(f'https://dpo.rosinfra.ru/base-projects/all?page={page_number}')
                except:
                    pars_page.site_opening(f'https://dpo.rosinfra.ru/base-projects/all?page={page_number}')
            page_number += 1
            pars_page.site_opening(f'https://dpo.rosinfra.ru/base-projects/all?page={page_number}')
    except selenium.common.exceptions.NoSuchElementException or \
           selenium.common.exceptions.ElementClickInterceptedException:
        pass


if __name__ == '__main__':
    main()
