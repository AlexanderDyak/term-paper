from datetime import datetime
from fake_useragent import UserAgent
import os
from requests.exceptions import ConnectionError

from state_parse import Parser
from DBinformation import DBwork


def relevance_update(f):
    def wrapper(url):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(url)

    wrapper.has_run = False
    return wrapper


@relevance_update
def file_append(url):
    return url


def main():
    """используем рандомного юзера, чтобы сайт не понял, что это парсинг"""
    user = UserAgent().random
    header = {'User-Agent': user}
    """текущая дата указывается для поиска нужных объявлений, идем перебором с текущей даты"""
    current_date = datetime.now()
    main_page = Parser()
    """всего на сайте максимально показывается 100 страниц и мы идем в цикле, пока есть эти страницы, цикл while True
    был выбран для того, чтобы на 100-ой странице можно было изменить дату, и, соответственно условия поиска, для того,
    чтобы увидеть более ранние записи"""
    page_number = 1
    """pars_page - это сама страница объявления"""
    pars_page = None
    """exept - костыль, нужный для того, чтобы выйти из 2-ух циклов сразу"""
    exept = False
    """save_next_end_url - сохраненный конечный url, лежащий в этой переменной до востребования
    конечный url - объявление, начиная с которого данные о дальнейших объявлениях уже есть в базе"""
    save_next_end_url = None
    while True:
        """начинаем с начальной страницы, всего на одной странице показывается 10 объявлений и мы должны пройти
        следующим циклом while True, чтобы просмотреть каждое, такой цикл был выбран для удобства, в ущерб скорости
        программы"""
        main_page.Get_all_site_information(
            'https://zakupki.gov.ru/epz/order/extendedsearch/results.html?morphology=on&search-filter=%D0%94%D0%B0%D1'
            f'%82%D0%B5+%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&pageNumber={page_number}'
            '&sortDirection=false '
            '&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=PUBLISH_DATE&fz44=on&fz223=on&pc=on&priceFromGeneral'
            f'=1000000000&currencyIdGeneral=-1&publishDateTo={current_date.strftime("%d.%m.%Y")}',
            'div',
            "search-registry-entry-block box-shadow-search-input",
            header)

        while True:
            '''здесь указывается текущая директория проекта, чтобы папки с документами и файл с конечным url 
            создавались там, где нужно, небольшой костыль, бкз которого файлы не хотят сохраняться там, где нада'''
            os.chdir('C:/term paper')

            next_page_url = main_page.GetNextUrl('a', False, "_blank", True)
            if not next_page_url:
                """объявления закончились сами по себе"""
                exept = True
                break

            """идем в очередное объявление"""
            pars_page = DBwork()
            pars_page.Get_all_site_information('https://zakupki.gov.ru' + next_page_url.get('href'), 'div',
                                               "container", header)

            """две следующие функции связаны и они выполняются лишь 1 раз за все время выполнения программы
            следующим конечным url будет url того объявления, с которого мы начали выполнение программы, его мы
            сохраняем до востребования"""
            update_url = relevance_update(file_append)
            next_end_url = update_url('https://zakupki.gov.ru' + next_page_url.get('href'))
            if next_end_url:
                save_next_end_url = next_end_url

            """проверяем, если в файле вообще нет url, то вставляем текущий"""
            current_end_url = pars_page.look_at_prev_end_url()
            if not current_end_url:
                Parser.next_end_url_update('https://zakupki.gov.ru' + next_page_url.get('href'))

            """сравниваем текущий url с конечным"""
            relevance = pars_page.relevance_checking()
            if not relevance:
                """далее все объявления есть в базе и они перестают быть релевантными
                обновляем url, в следующий раз будем идти до него"""
                Parser.next_end_url_update(save_next_end_url)
                exept = True
                break
            """получаем всю нужную информацию"""
            pars_page.get_page_information('div', "registry-entry__header-mid__number", "registry-entry__body-value",
                                           "price-block__value", "data-block__value",
                                           "registry-entry__header-mid__title")
            pars_page.Get_all_site_information('https://zakupki.gov.ru' + next_page_url.get('href'), 'div',
                                               "card-common-content", header)
            pars_page.get_company_region()

            """смотрим есть ли в объявлении документы"""
            pars_page.Get_all_site_information('https://zakupki.gov.ru' + next_page_url.get('href'), 'div',
                                               "container card-layout", header)
            docs_url = pars_page.Documents_checking()
            if docs_url:
                count_files = 1
                """документы также могут находиться в разных местах, так что приходится вызывать метод 2 раза с
                 разными данными"""
                if pars_page.Get_all_site_information('https://zakupki.gov.ru' + docs_url, 'span', "count", header) or \
                        pars_page.Get_all_site_information('https://zakupki.gov.ru' + docs_url, 'span',
                                                           "section__value",
                                                           header):
                    for i in pars_page.ads:
                        docs_link = i.findAll('a')[-1].get('href')

                        """if_title - также переменная, для 1-го из 2-ух различных расположений документов"""
                        if_title = i.findAll('a')[-1].get('title')

                        """документы могут быть в 2-ух расширениях (doc и docx), также они могут находиться в разных
                        местах, для определения используем переменную file_extension"""
                        if if_title:
                            file_extension = if_title[if_title.find('.'):]
                        else:
                            extension = i.findAll('a')[-1].get('data-tooltip')
                            file_extension = extension[extension.find('.'):extension.rfind('</')]

                        """тоже для различных видов представлений"""
                        if 'https' not in docs_link:
                            docs_link = 'https://zakupki.gov.ru' + docs_link
                        pars_page.Documents(docs_link, file_extension, header, count_files)
                        count_files += 1

        page_number += 1
        if exept:
            print('Новые объявления закончились')
            break
        if page_number == 100:
            """если мы достигли последней, 100-ой страницы, то теперь будем выполнять поиск с другими параметрами,
            чтобы увидеть более старые объявления"""
            current_date = pars_page.look_at_curdare()
            page_number = 1


try:
    if __name__ == '__main__':
        main()
except ConnectionError:
    print('No internet connection')
except KeyboardInterrupt:
    print('program interrupted manually')
