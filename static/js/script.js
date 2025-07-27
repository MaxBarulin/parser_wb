// F:/replicate/parser_wb/static/parser_wb/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    let allProducts = [];

    // Функция для считывания данных из таблицы в массив объектов
    function getInitialProducts() {
        const products = [];
        document.querySelectorAll('#productTable tbody tr').forEach(row => {
            products.push({
                name: row.querySelector('.product-name').innerText,
                price: parseFloat(row.querySelector('.product-price').innerText) || 0,
                rating: parseFloat(row.querySelector('.product-rating').innerText) || 0,
                country: row.querySelector('.product-country').innerText,
                product_url: row.querySelector('.product-url a').href,
            });
        });
        return products;
    }

    // Функция для перерисовки таблицы на основе отфильтрованного/отсортированного массива
    function displayProducts(products) {
        const tableBody = document.querySelector('#productTable tbody');
        tableBody.innerHTML = ''; // Очищаем старые данные
        products.forEach(product => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td class="product-name">${product.name}</td>
                <td class="product-price">${product.price.toFixed(2)}</td>
                <td class="product-rating">${product.rating ? product.rating.toFixed(1) : '-'}</td>
                <td class="product-country">${product.country || '-'}</td>
                <td class="product-url"><a href="${product.product_url}" target="_blank">Перейти</a></td>
            `;
        });
    }

    // Единая функция для обновления таблицы
    function updateView() {
        const maxPrice = parseFloat(document.getElementById("priceRange").value);
        const minRating = parseFloat(document.getElementById("minRating").value);
        const sortBy = document.getElementById("sortOptions").value;

        // 1. Фильтруем
        let processedProducts = allProducts.filter(p => p.price <= maxPrice && (p.rating || 0) >= minRating);

        // 2. Сортируем (копируем массив, чтобы не менять отфильтрованный)
        const sortedProducts = [...processedProducts];
        switch (sortBy) {
            case "nameAsc": sortedProducts.sort((a, b) => a.name.localeCompare(b.name)); break;
            case "nameDesc": sortedProducts.sort((a, b) => b.name.localeCompare(a.name)); break;
            case "priceAsc": sortedProducts.sort((a, b) => a.price - b.price); break;
            case "priceDesc": sortedProducts.sort((a, b) => b.price - a.price); break;
            case "ratingAsc": sortedProducts.sort((a, b) => (a.rating || 0) - (b.rating || 0)); break;
            case "ratingDesc": sortedProducts.sort((a, b) => (b.rating || 0) - (a.rating || 0)); break;
        }

        displayProducts(sortedProducts);
    }

    // --- Навешиваем обработчики событий ---

    // Обновление значения диапазона цен
    const priceRangeInput = document.getElementById("priceRange");
    const priceValueSpan = document.getElementById("priceValue");
    priceRangeInput.addEventListener("input", () => {
        priceValueSpan.textContent = `${priceRangeInput.value} ₽`;
    });
    // Обновляем таблицу, когда пользователь отпускает ползунок
    priceRangeInput.addEventListener("change", updateView);

    document.getElementById("minRating").addEventListener("input", updateView);
    document.getElementById("sortOptions").addEventListener("change", updateView);

    // --- Первоначальная загрузка ---
    allProducts = getInitialProducts();
    // Первоначальный вызов, чтобы применить значения по умолчанию
    updateView();
});
