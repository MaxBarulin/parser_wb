# F:\replicate\parser_wb\parser_wb\management\commands\parser.py

import time
import random
from django.core.management import BaseCommand
from decimal import Decimal

# --- Импорты для Selenium и Stealth ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# Импортируем нашу модель
from parser_wb.models import GoldAppleProduct


class Command(BaseCommand):
    """
    Команда для парсинга Gold Apple (финальная версия с кликами на вкладках товара).
    """
    BASE_URL = "https://goldapple.ru"

    def setup_driver(self):
        """Настраивает драйвер с использованием undetected-chromedriver."""
        self.stdout.write("Настройка драйвера undetected-chromedriver...")
        options = uc.ChromeOptions()

        # --- Чтобы скрыть браузер, раскомментируйте следующую строку ---
        # options.add_argument("--headless=new")

        options.add_argument("--start-maximized")
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--profile-directory=Default')
        options.add_argument("--incognito")
        options.add_argument("--disable-plugins-discovery")

        driver = uc.Chrome(options=options, use_subprocess=True)

        self.stdout.write(self.style.SUCCESS("Драйвер успешно настроен."))
        return driver

    def handle_popups(self, driver):
        """Надежно ищет и закрывает все возможные всплывающие окна."""
        self.stdout.write("   Поиск и закрытие всплывающих окон...")
        wait = WebDriverWait(driver, 10)

        try:
            city_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-id='city-confirm-ok-button']")))
            driver.execute_script("arguments[0].click();", city_button)
            self.stdout.write(self.style.SUCCESS("   Окно выбора города закрыто."))
            time.sleep(2)
        except Exception:
            self.stdout.write(self.style.WARNING("   Окно выбора города не найдено."))

        try:
            cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "._0rjJ7 button")))
            driver.execute_script("arguments[0].click();", cookie_button)
            self.stdout.write(self.style.SUCCESS("   Баннер cookie закрыт."))
            time.sleep(2)
        except Exception:
            self.stdout.write(self.style.WARNING("   Баннер cookie не найден."))

    def get_product_urls(self, driver, category_slug: str, clicks_to_make: int):
        """Собирает URL товаров, нажимая на кнопку 'Показать ещё'."""
        category_url = f"{self.BASE_URL}/{category_slug}"
        self.stdout.write(f"1. Загрузка страницы категории: {category_url}")
        driver.get(category_url)

        self.stdout.write("   Пауза 10 секунд для полной инициализации страницы...")
        time.sleep(10)

        self.handle_popups(driver)

        for i in range(clicks_to_make):
            try:
                self.stdout.write(f"\n   Итерация ({i + 1}/{clicks_to_make})")

                load_more_button_selector = "button[data-transaction-name='ga-load-button']"
                load_more_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, load_more_button_selector))
                )

                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                      load_more_button)
                time.sleep(3)

                driver.execute_script("arguments[0].click();", load_more_button)
                self.stdout.write(self.style.SUCCESS("   Кнопка нажата."))

                self.stdout.write("   Пауза 5 секунд для загрузки новых товаров...")
                time.sleep(5)

            except Exception:
                self.stdout.write(
                    self.style.WARNING("   Кнопка 'Показать ещё' не найдена. Считаем, что все товары загружены."))
                break

        self.stdout.write("\nСбор всех загруженных ссылок на товары...")
        product_urls = set()
        product_elements = driver.find_elements(By.CSS_SELECTOR, "article.FnxLm a[data-transaction-name]")
        for elem in product_elements:
            href = elem.get_attribute('href')
            if href and 'promo' not in href:
                product_urls.add(href)

        self.stdout.write(self.style.SUCCESS(f"   Собрано {len(product_urls)} уникальных ссылок на товары."))
        return list(product_urls)

    def get_product_details(self, driver, product_url: str) -> dict:
        """
        Собирает детальную информацию, КЛИКАЯ на вкладки для раскрытия контента.
        """
        self.stdout.write(f"   > Сбор деталей для: {product_url}")
        details = {'name': '', 'price': Decimal('0.00'), 'rating': None, 'description': '', 'usage': '', 'country': ''}
        try:
            driver.get(product_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.WpXpS")))

            # Сбор видимых данных
            brand = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS a[content]").get_attribute('content')
            title = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS span[itemprop='name']").text
            details['name'] = f"{brand} {title}"

            price_text = driver.find_element(By.CSS_SELECTOR, "div._0Ewqc").text
            details['price'] = Decimal(''.join(c for c in price_text if c.isdigit()))

            try:
                # Находим рейтинг по селектору из каталога, он часто совпадает
                rating_text = driver.find_element(By.CSS_SELECTOR, "div.LKAfD").text
                details['rating'] = float(rating_text.replace(',', '.'))
            except Exception:
                self.stdout.write(self.style.WARNING("     - Рейтинг не найден."))

            # --- ФИНАЛЬНАЯ ЛОГИКА: КЛИКИ И СБОР СКРЫТЫХ ДАННЫХ ---
            self.stdout.write("     - Раскрытие скрытых вкладок...")
            # Находим все возможные кликабельные заголовки (и вкладки, и аккордеоны)
            clickable_headers = driver.find_elements(By.CSS_SELECTOR, ".pdp-info-block-item-title, button.ga-tabs-tab")
            for header in clickable_headers:
                try:
                    driver.execute_script("arguments[0].click();", header)
                    time.sleep(0.5)
                except Exception:
                    continue
            self.stdout.write(self.style.SUCCESS("     - Все вкладки раскрыты."))

            # --- ТЕПЕРЬ СОБИРАЕМ ДАННЫЕ С ПОЛНОСТЬЮ РАСКРЫТОЙ СТРАНИЦЫ ---
            try:
                details['description'] = driver.find_element(By.CSS_SELECTOR, "div[itemprop='description']").text
            except Exception:
                self.stdout.write(self.style.WARNING("     - Описание не найдено."))

            all_info_blocks = driver.find_elements(By.CSS_SELECTOR, ".pdp-info-block-item, .iNOUQ")
            for block in all_info_blocks:
                try:
                    block_text = block.text
                    if 'применение' in block_text.lower():
                        details['usage'] = block_text.replace('Применение\n', '').strip()
                    if 'страна-производитель' in block_text.lower() or 'страна происхождения' in block_text.lower():
                        lines = block_text.split('\n')
                        for i, line in enumerate(lines):
                            if 'страна-производитель' in line.lower() or 'страна происхождения' in line.lower():
                                if i + 1 < len(lines):
                                    details['country'] = lines[i + 1].strip()
                                    break
                except Exception:
                    continue

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"     [!] Ошибка при сборе деталей для {product_url}: {e}"))
        return details

    def save_data_to_db(self, data: list):
        """Сохраняет данные в базу."""
        self.stdout.write(f"\n3. Сохранение {len(data)} товаров в базу...")
        count, _ = GoldAppleProduct.objects.all().delete()
        self.stdout.write(f"   Удалено {count} старых записей.")
        products_to_create = [
            GoldAppleProduct(
                name=item['name'], product_url=item['product_url'], price=item['price'],
                rating=item.get('rating'), description=item['description'],
                usage=item['usage'], country=item['country']
            ) for item in data if item.get('name')
        ]
        if products_to_create:
            GoldAppleProduct.objects.bulk_create(products_to_create)
            self.stdout.write(self.style.SUCCESS(f"   Успешно сохранено {len(products_to_create)} товаров."))

    def handle(self, *args, **options):
        """Основная функция, запускающая парсер."""
        category_slug = "parfjumerija"
        clicks_count = 2

        driver = self.setup_driver()
        all_products_data = []
        try:
            urls = self.get_product_urls(driver, category_slug, clicks_count)
            if not urls:
                self.stdout.write(self.style.WARNING("Не удалось собрать ссылки на товары. Прерывание выполнения."))
                return

            self.stdout.write(f"\n2. Начало сбора детальной информации для {min(len(urls), 10)} товаров...")
            for i, url in enumerate(urls[:10]):
                details = self.get_product_details(driver, url)
                details['product_url'] = url
                all_products_data.append(details)

                if i < len(urls[:10]) - 1:
                    pause = random.uniform(1.5, 4.0)
                    self.stdout.write(f"   --- Пауза {pause:.1f} сек. ---")
                    time.sleep(pause)

            self.save_data_to_db(all_products_data)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nПроизошла критическая ошибка: {e}"))
        finally:
            self.stdout.write("\nЗавершение работы, закрытие драйвера.")
            driver.quit()