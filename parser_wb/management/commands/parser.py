import requests
from django.core.management import BaseCommand
from retry import retry

from parser_wb.models import Product


class Command(BaseCommand):
    """Команда запуска скрипта для парсера."""

    @staticmethod
    def get_catalogs_wb() -> dict:
        """Получаем полный каталог Wildberries"""
        url = 'https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v3.json'
        headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        return requests.get(url, headers=headers).json()

    def get_data_category(self, catalogs_wb: dict) -> list:
        """Сбор данных категорий из каталога Wildberries"""
        catalog_data = []
        if isinstance(catalogs_wb, dict) and 'childs' not in catalogs_wb:
            catalog_data.append({
                'name': f"{catalogs_wb['name']}",
                'shard': catalogs_wb.get('shard', None),
                'url': catalogs_wb['url'],
                'query': catalogs_wb.get('query', None)
            })
        elif isinstance(catalogs_wb, dict):
            catalog_data.append({
                'name': f"{catalogs_wb['name']}",
                'shard': catalogs_wb.get('shard', None),
                'url': catalogs_wb['url'],
                'query': catalogs_wb.get('query', None)
            })
            catalog_data.extend(self.get_data_category(catalogs_wb['childs']))
        else:
            for child in catalogs_wb:
                catalog_data.extend(self.get_data_category(child))
        return catalog_data

    @staticmethod
    def search_category_in_catalog(catalog_name: str, catalog_list: list) -> dict:
        """Проверка пользовательской категории на наличии в каталоге"""
        for catalog in catalog_list:
            if catalog['name'] == catalog_name:
                print(f'найдено совпадение: {catalog["name"]}')
                return catalog

    @staticmethod
    def get_data_from_json(json_file: dict) -> list:
        """Извлекаем из json данные"""
        data_list = []
        for data in json_file['data']['products']:
            name = data.get('name')
            price = int(data.get("priceU") / 100)
            salePriceU = int(data.get('salePriceU') / 100)
            rating = data.get('reviewRating')
            feedbacks = data.get('feedbacks')
            data_list.append({
                'name': name,
                'price': price,
                'salePriceU': salePriceU,
                'rating': rating,
                'feedbacks': feedbacks,
            })
        return data_list

    @retry(tries=5)
    def scrap_page(self, page: int, shard: str, query: str) -> dict:
        """Сбор данных со страниц"""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0)"}
        url = f'https://catalog.wb.ru/catalog/{shard}/catalog?appType=1&curr=rub' \
              f'&dest=-1257786' \
              f'&locale=ru' \
              f'&page={page}' \
              f'&sort=popular&spp=0' \
              f'&{query}'
        r = requests.get(url, headers=headers)
        print(f'Статус: {r.status_code} Страница {page} Идет сбор...')
        return r.json()

    @staticmethod
    def save_bd(data: list):
        """Сохранение результата в базу данных"""
        Product.objects.all().delete()  # Очищаем базу перед заполнением.
        if len(data) > 0:
            for product in data:
                create_ = Product.objects.create(
                    name=product['name'],
                    price=product['price'],
                    price_discount=product['salePriceU'],
                    rating=product['rating'],
                    feedbacks=product['feedbacks']
                )
                create_.save()
        else:
            raise ValueError

    def parser(self, catalog_name: str, count_page: int):
        """Основная функция"""
        # получаем данные по заданному каталогу
        catalog_data = self.get_data_category(self.get_catalogs_wb())
        try:
            # поиск введенной категории в общем каталоге
            category = self.search_category_in_catalog(catalog_name=catalog_name, catalog_list=catalog_data)
            data_list = []
            for page in range(1, count_page + 1):
                data = self.scrap_page(
                    page=page,
                    shard=category['shard'],
                    query=category['query'])
                if len(self.get_data_from_json(data)) > 0:
                    data_list.extend(self.get_data_from_json(data))
                else:
                    break
            print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
            # сохранение найденных данных
            self.save_bd(data_list)
            print('\nДанные сохранены в базу.')
        except TypeError:
            print('\nОшибка! Возможно не верно указана категория.')
            user = input('\nХотите узнать список из доступных категорий на Wildberries?(y/n)\n')
            if user == 'y':
                data_category = [name['name'] for name in catalog_data]
                for i in data_category:
                    print(i)

    def handle(self, *args, **options):
        while True:
            try:
                catalog_name = input('Введите название категории для сбора (или "q" для выхода):\n')
                if catalog_name == 'q':
                    break

                count_page = int(input('Сколько страниц просмотреть? (от 1 до 50):'))
                self.parser(catalog_name=catalog_name, count_page=count_page)
            except:
                print('произошла ошибка данных при вводе, проверьте правильность введенных данных,\n'
                      'Перезапуск...')
