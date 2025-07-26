import decimal
import urllib

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

        # --- Исправлено: правильный способ получения списка товаров ---
        # В новом API товары лежат прямо в json_file['products']
        # В старом (или другом формате) могли быть в json_file['data']['products']
        products = json_file.get('products')
        if products is None:
            # fallback на старую структуру
            products = json_file.get('data', {}).get('products', [])
        # -------------------------------

        # --- Упрощена проверка ---
        if not isinstance(products, list):
            print(f"[WARN] В ответе API не найден корректный список товаров. Тип: {type(products)}")
            print(f"[WARN] Ключи ответа: {list(json_file.keys())}")
            return data_list  # Возвращаем пустой список
        # --------------------------

        # --- Исправлено: цикл по products, а не по json_file['data']['products'] ---
        for data in products:  # Используем 'products' напрямую
            try:
                # Обработка каждого товара
                name = data.get('name', 'Без названия')

                # --- Исправлено: Получение цены ---
                # Цена в копейках, НЕ делим на 100, а преобразуем в Decimal
                price_basic = data.get('sizes', [{}])[0].get('price', {}).get('basic')
                # Если цена есть, преобразуем копейки в рубли и сохраняем как Decimal
                if price_basic is not None:
                    # Decimal(str(...)) более точно, чем float
                    price = decimal.Decimal(price_basic) / 100
                else:
                    price = decimal.Decimal('0.00')
                # -------------------------------

                # --- Исправлено: Цена со скидкой ---
                price_product = data.get('sizes', [{}])[0].get('price', {}).get('product')
                if price_product is not None:
                    salePriceU = decimal.Decimal(price_product) / 100
                else:
                    # Если скидочной цены нет, используем базовую
                    salePriceU = price
                # -----------------------------------

                # Рейтинг и отзывы
                # --- Исправлено: используем 'reviewRating' ---
                rating = data.get('reviewRating', None)  # Может быть None
                # ---------------------------------------------
                feedbacks = data.get('feedbacks', 0)

                data_list.append({
                    'name': name,
                    'price': price,  # Decimal, представляющий рубли
                    'salePriceU': salePriceU,  # Decimal, представляющий рубли
                    'rating': rating,  # float или None
                    'feedbacks': feedbacks,  # int
                })
            except Exception as e:
                print(f"[ERROR] Ошибка обработки товара {data.get('id', 'unknown')}: {e}")
                # Продолжаем обработку остальных товаров
                continue

        return data_list

    @retry(tries=5)
    def scrap_page(self, page: int, category_id: int = None, category_name: str = None) -> dict:
        """Сбор данных со страниц"""
        if not category_id and not category_name:
            raise ValueError("Необходимо указать либо category_id, либо category_name")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.wildberries.ru",
            "Connection": "keep-alive",
            "Referer": "https://www.wildberries.ru/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }

        # Используем v14 API
        base_url = "https://search.wb.ru/exactmatch/ru/common/v14/search"
        params = {
            "appType": "1",
            "curr": "rub",
            "dest": "123589415", # Важно: правильный dest
            "lang": "ru",
            "page": str(page),
            "resultset": "catalog" # Важно: получаем каталог
        }

        # Приоритет: сначала используем menu_v3_{id}, потом имя категории
        if category_id:
            params["query"] = f"menu_v3_{category_id}"
        elif category_name:
            params["query"] = category_name # Можно оставить как есть или закодировать
        else:
            # Этот случай уже обработан выше, но на всякий случай
            raise ValueError("Не указаны параметры для поиска")

        # Собираем URL
        url = base_url + "?" + urllib.parse.urlencode(params)

        print(f"[DEBUG] Запрашиваемый URL (товары): {url}")

        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f'[DEBUG] Статус: {r.status_code} Страница {page} Идет сбор...')

            if r.status_code != 200:
                print(f"[DEBUG] Ответ сервера: {r.text[:500]}...")
                # Если ошибка 404 или 500, повторять бесполезно, бросаем исключение
                if r.status_code in [404, 500, 403]:
                    raise requests.exceptions.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status() # Повторить для других ошибок


            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса: {e}")
            raise # Повторить попытку благодаря @retry

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
            if not category:
                raise ValueError(f"Категория '{catalog_name}' не найдена")

            print(f"Найденная категория: {category.get('name')}")
            category_id = category.get('id')
            if not category_id:
                # fallback на имя категории, если ID нет
                print(f"[WARN] У категории нет ID, используем имя категории как запрос")
                category_name_for_query = category.get('name')
                category_id_for_query = None
            else:
                category_name_for_query = None
                category_id_for_query = category_id

            data_list = []
            for page in range(1, count_page + 1):
                try:
                    data = self.scrap_page(
                        page=page,
                        category_id=category_id_for_query,
                        category_name=category_name_for_query
                    )

                    # --- НОВОЕ: Проверка структуры ответа ---
                    if not isinstance(data, dict):
                        print(f"[ERROR] Ответ API для страницы {page} не является словарем: {type(data)}")
                        break  # Останавливаем парсинг, так как формат непонятен

                    # Проверяем, есть ли товары
                    products_list = data.get('products') or data.get('data', {}).get('products')
                    if products_list is None:
                        print(
                            f"[WARN] В ответе для страницы {page} не найден ключ 'products' или 'data.products'. Ключи: {list(data.keys())}")
                        # Можно остановиться или продолжить (в зависимости от логики)
                        # break # Останавливаем, если ожидаем товары
                        products_list = []  # Или считаем, что товаров нет на этой странице

                    if not isinstance(products_list, list):
                        print(f"[WARN] Список товаров для страницы {page} не является списком: {type(products_list)}")
                        products_list = []

                    # page_products = self.get_data_from_json(data) # Старая строка
                    # Новая логика: передаем уже найденный список товаров
                    # Но если get_data_from_json теперь сам ищет 'products', можно оставить как есть
                    # Для надежности, можно немного изменить get_data_from_json, чтобы он принимал
                    # либо весь dict (и сам ищет products), либо сразу список products.
                    # Пока оставим как есть, но с проверкой выше.
                    page_products = self.get_data_from_json(data)
                    # --- КОНЕЦ НОВОГО ---

                    if len(page_products) > 0:
                        data_list.extend(page_products)
                        print(f"[INFO] Страница {page}: собрано {len(page_products)} товаров.")
                    else:
                        print(f"[INFO] Страница {page} не содержит товаров, останавливаемся.")
                        break
                except requests.exceptions.HTTPError as e:
                    print(f"[ERROR] Сервер вернул ошибку для страницы {page}: {e}. Останавливаем парсинг.")
                    break
                except Exception as e:
                    print(f"[WARN] Ошибка при сборе страницы {page}: {e}. Пробуем повторить...")

            print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
            # сохранение найденных данных
            self.save_bd(data_list)
            print('\nДанные сохранены в базу.')
        except:
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
