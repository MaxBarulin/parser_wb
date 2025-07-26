from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='название товара')
    price = models.PositiveIntegerField(verbose_name='цена')
    price_discount = models.PositiveIntegerField(verbose_name='цена со скидкой')
    rating = models.DecimalField(max_digits=10, decimal_places=1, verbose_name='рейтинг')
    feedbacks = models.PositiveIntegerField(verbose_name='количество отзывов')

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
