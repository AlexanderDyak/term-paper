import os
from state_parse import Parser
from requests import get


class DBwork(Parser):
    def __init__(self):
        super().__init__()
        self.company_name = None
        self.purchase_name = None
        self.notice_id = None
        self.date = None
        self.company_region = None
        self.purchase_price = None
        self.purchase_stage = None
        self.property = None

    def get_page_information(self, tag, notice_id_cls, purchase_and_company_name_cls, price_cls, date_cls, stage_cls):
        print('Парсинг закупки ' + self.url)
        self.notice_id = DBwork.get_notice_id(self, tag, notice_id_cls)
        self.purchase_name, self.company_name = DBwork.get_purchase_and_company_name(self, tag,
                                                                                     purchase_and_company_name_cls)
        self.date = DBwork.get_date(self, tag, date_cls)
        self.purchase_price = DBwork.get_price(self, tag, price_cls)
        self.purchase_stage = DBwork.get_stage(self, tag, stage_cls)
        DBwork.property_definition(self)
        print(self.notice_id)
        print(self.purchase_name)
        print(self.company_name)
        print(self.date)
        print(self.purchase_price)
        print(self.purchase_stage)

    def look_at_curdare(self):
        return self.date

    def get_notice_id(self, tag, notice_id_cls):
        notice_id = self.ads[3].find(tag, notice_id_cls)
        return notice_id.text.strip()[2:]

    def get_purchase_and_company_name(self, tag, purchase_and_company_name_cls):
        step = self.ads[3].findAll(tag, purchase_and_company_name_cls)
        purchase_name = step[0].text.strip()
        company_name = step[1].text.strip()
        return purchase_name, company_name

    def get_date(self, tag, date_cls):
        date = self.ads[3].find(tag, date_cls)
        return date.text.strip()

    def get_price(self, tag, price_cls):
        purchase_price = self.ads[3].find(tag, price_cls)
        return int(''.join(purchase_price.text.strip()[:-5].split())) / 1000000000

    def get_stage(self, tag, stage_cls):
        stage = self.ads[3].find(tag, stage_cls)
        return stage.text.strip()

    def get_company_region(self):
        address = ''
        for item in self.ads:
            if 'Место нахождения' in item.text:
                a = item.text[item.text.find('Место нахождения') + 20:].strip()
                address = a[:a.find('\n')].split(',')
                break
        matches = ['обл', 'кра', 'респ', 'автоном', 'моск', 'петербур']
        region = ''
        for item in address:
            if any(x in item.lower() for x in matches):
                if 'моск' in item.lower():
                    region = 'Область Московская'
                elif 'петербур' in item.lower():
                    region = 'Область Ленинградская'
                else:
                    r = item.strip().lower().split()
                    region = ' '.join([i.capitalize() for i in r])
                    break
        self.company_region = region
        print(self.company_region)
        print('-----------')

    def property_definition(self):
        pass

    def Documents_checking(self):
        if 'Документы' in self.ads[0].text:
            for i in str(self.ads[0]).split('<a'):
                if 'Документы' in i:
                    if not os.path.isdir("StateProc_Docs"):
                        os.mkdir("StateProc_Docs")
                    if not os.path.isdir("StateProc_Docs/" + self.notice_id):
                        os.mkdir("StateProc_Docs/" + self.notice_id)
                    os.chdir("StateProc_Docs/" + self.notice_id)
                    return i[i.find('href=') + 6:i.find('>') - 1]
        return False

    def Documents(self, file_link, file_extension, header, file_number):
        r = get(url=file_link, stream=True, headers=header)
        with open(f'document{file_number}{file_extension}', 'wb') as f:
            f.write(r.content)
