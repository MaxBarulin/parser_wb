// Переменные для хранения экземпляров графиков и всех продуктов
let priceHistogramChart;
let discountVsRatingChart;
let allProducts = []; // 1. Объявляем и инициализируем переменную

// Функция для получения данных из таблицы
function getProducts() {
    return Array.from(document.querySelectorAll('#productTable tbody tr')).map(row => {
        return {
            name: row.children[0].innerText,
            // Предполагая, что цены теперь хранятся как числа с десятичными знаками, используйте parseFloat
            price: parseFloat(row.children[1].innerText) || 0,
            price_discount: parseFloat(row.children[2].innerText) || 0,
            rating: parseFloat(row.children[3].innerText) || 0,
            feedbacks: parseInt(row.children[4].innerText) || 0,
        };
    });
}

document.getElementById("priceRange").addEventListener("input", function() {
    const priceRangeValue = this.value;
    document.getElementById("priceValue").textContent = `0 - ${priceRangeValue} ₽`;
});

// Функция отображения продуктов на странице
function displayProducts(filteredProducts) {
    const tableBody = document.getElementById("productTable").getElementsByTagName('tbody')[0];
    tableBody.innerHTML = ''; // Очистка таблицы
    filteredProducts.forEach(product => {
        const row = tableBody.insertRow();
        row.insertCell(0).innerText = product.name;
        // Форматируем числа для отображения (если они Decimal)
        row.insertCell(1).innerText = (product.price).toFixed(2);
        row.insertCell(2).innerText = (product.price_discount).toFixed(2);
        row.insertCell(3).innerText = (product.rating).toFixed(1);
        row.insertCell(4).innerText = product.feedbacks;
    });
}

// Функция фильтрации продуктов
function applyFilters(products) {
    // Используем parseFloat/parseInt и учитываем пустые значения
    const maxPrice = parseFloat(document.getElementById("priceRange").value) || 0;
    const minRating = parseFloat(document.getElementById("minRating").value) || 0;
    const minReviews = parseInt(document.getElementById("minReviews").value, 10) || 0;

    // Фильтруем по максимальной цене (верхняя граница диапазона)
    const filteredProducts = products.filter(product =>
        product.price <= maxPrice &&
        product.rating >= minRating &&
        product.feedbacks >= minReviews
    );

    return filteredProducts;
}

// Функция для сортировки продуктов
function sortProducts(products, sortBy) {
    // Создаем копию массива, чтобы не мутировать оригинальный
    const sortedProducts = [...products];
    switch (sortBy) {
        case "nameAsc":
            return sortedProducts.sort((a, b) => a.name.localeCompare(b.name));
        case "nameDesc":
            return sortedProducts.sort((a, b) => b.name.localeCompare(a.name));
        case "priceAsc":
            return sortedProducts.sort((a, b) => a.price - b.price);
        case "priceDesc":
            return sortedProducts.sort((a, b) => b.price - a.price);
        case "ratingAsc":
            return sortedProducts.sort((a, b) => a.rating - b.rating);
        case "ratingDesc":
            return sortedProducts.sort((a, b) => b.rating - a.rating);
        case "reviewsAsc":
            return sortedProducts.sort((a, b) => a.feedbacks - b.feedbacks);
        case "reviewsDesc":
            return sortedProducts.sort((a, b) => b.feedbacks - a.feedbacks);
        default:
            return sortedProducts;
    }
}

// --- ЕДИНСТВЕННЫЙ обработчик для кнопки фильтрации ---
document.getElementById("filterBtn").addEventListener("click", () => {
    // Всегда работаем с исходным массивом allProducts
    const filteredProducts = applyFilters(allProducts);
    displayProducts(filteredProducts);
    createPriceHistogram(filteredProducts);
    createDiscountVsRatingChart(filteredProducts);
});

// --- ЕДИНСТВЕННЫЙ обработчик для кнопки сортировки ---
document.getElementById("sortBtn").addEventListener("click", () => {
    // Получаем текущие (отфильтрованные) данные из таблицы
    const currentProducts = getProducts();
    const sortBy = document.getElementById("sortOptions").value;
    const sortedProducts = sortProducts(currentProducts, sortBy);
    displayProducts(sortedProducts);
    // Обновляем графики после сортировки
    createPriceHistogram(sortedProducts);
    createDiscountVsRatingChart(sortedProducts);
});

// Функция для создания гистограммы цен (без изменений)
function createPriceHistogram(products) {
    const priceRanges = [0, 1000, 2000, 3000, 4000, 5000];
    const priceCounts = new Array(priceRanges.length - 1).fill(0);

    products.forEach(product => {
        for (let i = 0; i < priceRanges.length - 1; i++) {
            if (product.price >= priceRanges[i] && product.price < priceRanges[i + 1]) {
                priceCounts[i]++;
                break;
            }
        }
    });

    const ctx = document.getElementById('priceHistogram').getContext('2d');
    const labels = priceRanges.slice(0, -1).map((range, index) => `${range} - ${priceRanges[index + 1]}`);

    if (priceHistogramChart) {
        priceHistogramChart.data.labels = labels;
        priceHistogramChart.data.datasets[0].data = priceCounts;
        priceHistogramChart.update();
    } else {
        priceHistogramChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Количество товаров',
                    data: priceCounts,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
            }
        });
    }
}

// Функция для создания линейного графика размера скидки на товар против рейтинга товара (без изменений)
function createDiscountVsRatingChart(products) {
    const discounts = products.map(product => product.price - product.price_discount);
    const ratings = products.map(product => product.rating);

    const ctx = document.getElementById('discountVsRating').getContext('2d');

    if (discountVsRatingChart) {
        discountVsRatingChart.data.labels = ratings;
        discountVsRatingChart.data.datasets[0].data = discounts;
        discountVsRatingChart.update();
    } else {
        discountVsRatingChart = new Chart(ctx, {
            type: 'line', // Или 'scatter' для точек
            data: {
                labels: ratings,
                datasets: [{
                    label: 'Размер скидки',
                    data: discounts,
                    fill: false,
                    borderColor: 'rgba(255, 99, 132, 1)'
                }]
            },
            options: {
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Рейтинг товара'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Размер скидки'
                        }
                    }
                }
            }
        });
    }
}

// --- Инициализация ---
// 2. Используем DOMContentLoaded и правильный порядок
document.addEventListener('DOMContentLoaded', (event) => {
    // Получаем все продукты один раз при загрузке страницы
    allProducts = getProducts();
    // Отображаем их
    displayProducts(allProducts);
    // Создаем графики на основе всех продуктов
    createPriceHistogram(allProducts);
    createDiscountVsRatingChart(allProducts);
});
// 3. Удаляем старые вызовы в конце файла
