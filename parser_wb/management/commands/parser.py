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
    Команда для парсинга Gold Apple (финальная версия с надежным последовательным сбором).
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
        Улучшенный метод сбора данных с Gold Apple с альтернативными селекторами
        """
        self.stdout.write(f"\n> Сбор данных для: {product_url}")
        details = {
            'name': '',
            'price': Decimal('0.00'),
            'rating': None,
            'description': '',
            'usage': '',
            'country': '',
            'product_url': product_url
        }

        try:
            # 1. Загрузка страницы
            driver.get(product_url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h1[contains(@class, 'product-title') or contains(@class, 'WpXpS')]"))
            )
            time.sleep(3)

            # 2. Сбор названия товара (несколько вариантов)
            try:
                name_parts = []
                # Вариант 1 - современная версия
                brand = driver.find_element(By.XPATH, "//h1//a[contains(@class, 'brand') or @itemprop='brand']").text
                name = driver.find_element(By.XPATH, "//h1//span[contains(@class, 'name') or @itemprop='name']").text
                details['name'] = f"{brand} {name}".strip()
                self.stdout.write(self.style.SUCCESS(f"   + Название (новый селектор): {details['name']}"))
            except Exception:
                try:
                    # Вариант 2 - старый селектор
                    brand = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS a[content]").get_attribute('content')
                    title = driver.find_element(By.CSS_SELECTOR, "h1.WpXpS span[itemprop='name']").text
                    details['name'] = f"{brand} {title}".strip()
                    self.stdout.write(self.style.SUCCESS(f"   + Название (старый селектор): {details['name']}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   - Не удалось собрать название: {e}"))

            # 3. Сбор цены (более гибкий подход)
            try:
                price_element = driver.find_element(By.XPATH,
                                                    "//div[contains(@class, 'price') or contains(@class, '_0Ewqc')] | "
                                                    "//span[@itemprop='price'] | "
                                                    "//meta[@itemprop='price']")

                price_text = price_element.get_attribute('content') or price_element.text
                details['price'] = Decimal(''.join(c for c in price_text if c.isdigit()))
                self.stdout.write(self.style.SUCCESS(f"   + Цена собрана: {details['price']}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   - Не удалось собрать цену: {e}"))

            # 4. Сбор рейтинга (новый подход)
            try:
                # Основной способ - через класс _9SOmS
                rating_element = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div._9SOmS"))
                )
                rating_text = rating_element.text.strip()
                details['rating'] = float(rating_text.replace(',', '.'))
                self.stdout.write(self.style.SUCCESS(f"   + Рейтинг: {details['rating']}"))
            except Exception:
                try:
                    # Fallback 1 - абсолютный XPath
                    rating_element = driver.find_element(
                        By.XPATH, '//*[@id="__layout"]/div/main/div[2]/div/div[3]/a[1]/div/div[1]'
                    )
                    details['rating'] = float(rating_element.text.strip().replace(',', '.'))
                    self.stdout.write(self.style.SUCCESS(f"   + Рейтинг (fallback 1): {details['rating']}"))
                except Exception:
                    try:
                        # Fallback 2 - поиск по тексту "оценка товара"
                        rating_element = driver.find_element(
                            By.XPATH, "//div[contains(text(), 'оценка товара')]/preceding-sibling::div[1]"
                        )
                        details['rating'] = float(rating_element.text.strip().replace(',', '.'))
                        self.stdout.write(self.style.SUCCESS(f"   + Рейтинг (fallback 2): {details['rating']}"))
                    except Exception:
                        self.stdout.write(self.style.WARNING("   - Рейтинг не найден"))

            # 5. Сбор описания (расширенный поиск)
            try:
                # Ищем по атрибутам, классам или текстовым меткам
                desc_element = driver.find_element(By.XPATH,
                                                   "//div[@itemprop='description'] | "
                                                   "//div[contains(@class, 'description')] | "
                                                   "//div[contains(@class, 'product-description')] | "
                                                   "//h2[contains(text(), 'Описание')]/following-sibling::div")

                details['description'] = desc_element.text.strip()
                self.stdout.write(self.style.SUCCESS("   + Описание найдено"))
            except Exception:
                self.stdout.write(self.style.WARNING("   - Описание не найдено"))

            # 6. Поиск страны и применения через XPath по текстовым меткам
            try:
                # Ищем все информационные блоки
                info_blocks = driver.find_elements(By.XPATH,
                                                   "//div[contains(@class, 'info-block')] | "
                                                   "//div[contains(@class, 'specifications')] | "
                                                   "//div[contains(@class, 'attributes')]")

                for block in info_blocks:
                    block_text = block.text.lower()

                    # Страна производства
                    if not details['country'] and ('страна' in block_text or 'произв' in block_text):
                        try:
                            country = block.find_element(By.XPATH,
                                                         ".//div[contains(text(), 'Страна')]/following-sibling::div | "
                                                         ".//td[contains(text(), 'Страна')]/following-sibling::td").text
                            details['country'] = country.strip()
                            self.stdout.write(self.style.SUCCESS(f"     + Страна: {details['country']}"))
                        except:
                            pass

                    # Применение
                    if not details['usage'] and 'применение' in block_text:
                        try:
                            usage = block.find_element(By.XPATH,
                                                       ".//div[contains(text(), 'Применение')]/following-sibling::div | "
                                                       ".//td[contains(text(), 'Применение')]/following-sibling::td").text
                            details['usage'] = usage.strip()
                            self.stdout.write(self.style.SUCCESS("     + Применение найдено"))
                        except:
                            pass

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   - Ошибка при поиске характеристик: {e}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"   [!] Критическая ошибка: {e}"))

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

            self.stdout.write(f"\n2. Начало сбора детальной информации для {min(len(urls), 3)} товаров...")
            for i, url in enumerate(urls[:3]):
                details = self.get_product_details(driver, url)
                details['product_url'] = url
                all_products_data.append(details)

                if i < len(urls[:3]) - 1:
                    pause = random.uniform(1.5, 4.0)
                    self.stdout.write(f"   --- Пауза {pause:.1f} сек. ---")
                    time.sleep(pause)

            self.save_data_to_db(all_products_data)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nПроизошла критическая ошибка: {e}"))
        finally:
            try:
                self.stdout.write("\nЗавершение работы, закрытие драйвера.")
                driver.quit()
            except Exception:
                pass
