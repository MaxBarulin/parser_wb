from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='название товара')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='цена (руб.)')
    price_discount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='цена со скидкой (руб.)', null=True, blank=True)
    rating = models.DecimalField(max_digits=10, decimal_places=1, verbose_name='рейтинг')
    feedbacks = models.PositiveIntegerField(verbose_name='количество отзывов')

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

class GoldAppleProduct(models.Model):
    name = models.CharField("Наименование", max_length=255)
    product_url = models.URLField("Ссылка на продукт", max_length=1024, unique=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    rating = models.FloatField("Рейтинг", null=True, blank=True)
    description = models.TextField("Описание продукта", blank=True)
    usage = models.TextField("Инструкция по применению", blank=True)
    country = models.CharField("Страна-производитель", max_length=100, blank=True)

    class Meta:
        verbose_name = "Продукт (Gold Apple)"
        verbose_name_plural = "Продукты (Gold Apple)"

    def __str__(self):
        return self.name

