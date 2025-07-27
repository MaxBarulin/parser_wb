# F:\replicate\parser_wb\parser_wb\management\commands\parser.py

import time
from django.core.management import BaseCommand
from decimal import Decimal

# --- Импорты для Selenium ---
# Стандартный webdriver больше не нужен напрямую, но By и ожидания нужны
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # <--- ВАЖНО: Используем новую библиотеку

# Импортируем нашу модель
from parser_wb.models import GoldAppleProduct


class Command(BaseCommand):
    """
    Команда для парсинга Gold Apple (финальная версия с undetected-chromedriver).
    """
    BASE_URL = "https://goldapple.ru"

    def setup_driver(self):
        """Настраивает драйвер с использованием undetected-chromedriver."""
        self.stdout.write("Настройка драйвера undetected-chromedriver...")
        options = uc.ChromeOptions()

        # Оставляем браузер видимым для контроля
        options.add_argument("--start-maximized")
        # Некоторые дополнительные опции для маскировки
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--profile-directory=Default')
        options.add_argument("--incognito")
        options.add_argument("--disable-plugins-discovery")

        # --- ВАЖНО: Используем undetected_chromedriver ---
        driver = uc.Chrome(options=options, use_subprocess=True)

        # --- selenium-stealth больше не нужен, undetected-chromedriver делает все сам ---

        self.stdout.write(self.style.SUCCESS("Драйвер успешно настроен."))
        return driver

    def handle_popups(self, driver):
        """Надежно ищет и закрывает все возможные всплывающие окна."""
        self.stdout.write("   Поиск и закрытие всплывающих окон...")
        wait = WebDriverWait(driver, 15)  # Увеличим время ожидания

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

        # Увеличиваем паузу, чтобы дать всем скриптам защиты полностью прогрузиться
        self.stdout.write("   Пауза 10 секунд для полной инициализации страницы...")
        time.sleep(10)

        self.handle_popups(driver)

        for i in range(clicks_to_make):
            try:
                self.stdout.write(f"\n   Итерация ({i + 1}/{clicks_to_make})")

                product_selector = "article.FnxLm"
                before_count = len(driver.find_elements(By.CSS_SELECTOR, product_selector))
                self.stdout.write(f"   Товаров на странице до нажатия: {before_count}")

                load_more_button_selector = "button[data-transaction-name='ga-load-button']"
                load_more_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, load_more_button_selector))
                )

                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                      load_more_button)
                time.sleep(3)

                driver.execute_script("arguments[0].click();", load_more_button)
                self.stdout.write(self.style.SUCCESS("   Кнопка нажата."))

                self.stdout.write("   Ожидание загрузки новых товаров...")
                WebDriverWait(driver, 30).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, product_selector)) > before_count
                )
                after_count = len(driver.find_elements(By.CSS_SELECTOR, product_selector))
                self.stdout.write(self.style.SUCCESS(f"   Товары загружены. Всего на странице: {after_count}"))

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
        """Собирает детальную информацию, кликая на вкладки для раскрытия контента."""
        self.stdout.write(f"   > Сбор деталей для: {product_url}")
        details = {'name': '', 'price': Decimal('0.00'), 'rating': None, 'description': '', 'usage': '', 'country': ''}
        try:
            driver.get(product_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.WpXpS")))

            brand = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS a[content]").get_attribute('content')
            title = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS span[itemprop='name']").text
            details['name'] = f"{brand} {title}"

            price_text = driver.find_element(By.CSS_SELECTOR, "div._0Ewqc").text
            details['price'] = Decimal(''.join(c for c in price_text if c.isdigit()))

            try:
                rating_text = driver.find_element(By.CSS_SELECTOR, "div._9SOmS").text
                details['rating'] = float(rating_text.replace(',', '.'))
            except Exception:
                pass

            info_titles = driver.find_elements(By.CSS_SELECTOR, ".pdp-info-block-item-title")
            for title_element in info_titles:
                try:
                    title_text = title_element.text.lower()
                    driver.execute_script("arguments[0].click();", title_element)
                    time.sleep(0.5)
                    content_element = title_element.find_element(By.XPATH, "./following-sibling::div")
                    content_text = content_element.text
                    if 'описание' in title_text:
                        details['description'] = content_text
                    elif 'применение' in title_text:
                        details['usage'] = content_text
                    elif 'дополнительная информация' in title_text:
                        if 'страна-производитель' in content_text.lower():
                            lines = content_text.split('\n')
                            for i, line in enumerate(lines):
                                if 'страна-производитель' in line.lower() and i + 1 < len(lines):
                                    details['country'] = lines[i + 1].strip()
                                    break
                except Exception:
                    continue

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"     [!] Ошибка при сборе деталей для {product_url}: {e}"))
        return details

    def save_data_to_db(self, data: list):
        """Сохраняет данные в базу."""
        self.stdout.write("\n3. Сохранение данных в базу...")
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
        clicks_count = 4

        driver = self.setup_driver()
        all_products_data = []
        try:
            urls = self.get_product_urls(driver, category_slug, clicks_count)
            if not urls:
                self.stdout.write(self.style.WARNING("Не удалось собрать ссылки на товары. Прерывание выполнения."))
                return

            self.stdout.write(f"\n2. Начало сбора детальной информации для {min(len(urls), 20)} товаров...")
            for url in urls[:20]:
                details = self.get_product_details(driver, url)
                details['product_url'] = url
                all_products_data.append(details)

            self.save_data_to_db(all_products_data)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nПроизошла критическая ошибка: {e}"))
        finally:
            self.stdout.write("\nЗавершение работы, закрытие драйвера.")
            driver.quit()