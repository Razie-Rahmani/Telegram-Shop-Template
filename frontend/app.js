const CONFIG = window.SHOP_CONFIG;
let cart = [];

/* ========================================
   Inline SVG icons (no emoji — accessible, theme-colored via currentColor)
   ======================================== */
const ICONS = {
    backArrow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5"></path><path d="M12 19l-7-7 7-7"></path></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>`,
    productPlaceholder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path><path d="M3.27 6.96 12 12l8.73-5.04"></path><path d="M12 22.08V12"></path></svg>`,
    emptyCart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>`,
    alert: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`
};

const customerTelegramId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

const catalogSection = document.getElementById("catalog-section");
const cartSection = document.getElementById("cart-section");
const viewCartBtn = document.getElementById("view-cart-btn");
const cartCountBadge = document.getElementById("cart-count");
const shopNameLabel = document.getElementById("shop-name-label");

shopNameLabel.textContent = CONFIG.shopName;
document.title = CONFIG.shopName;

viewCartBtn.addEventListener("click", function () {
    renderCart();
});

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value);
    return div.innerHTML;
}

function formatPrice(amount) {
    return `${escapeHtml(amount)} ${CONFIG.currencyLabel}`;
}

function updateCartBadge() {
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    if (totalItems > 0) {
        cartCountBadge.textContent = totalItems > 99 ? "99+" : totalItems;
        cartCountBadge.hidden = false;
    } else {
        cartCountBadge.hidden = true;
    }
}

/* ========================================
   Order placement
   Payment receipts are uploaded by the customer sending a photo directly
   to the bot in Telegram, not from this page — the backend matches it to
   their most recent order via customer_telegram_id. See the
   customer_receipt_photo handler in backend/app/bot/customer.py.
   ======================================== */
async function placeOrder(orderData, placeOrderBtn) {
    const originalContent = placeOrderBtn.innerHTML;
    placeOrderBtn.disabled = true;
    placeOrderBtn.innerHTML = `<span class="btn-spinner" aria-hidden="true"></span> Placing order...`;

    try {
        const response = await fetch(`${CONFIG.apiBase}/orders/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(orderData)
        });

        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }

        const result = await response.json();

        let itemsHtml = "";
        for (let name in result.items) {
            itemsHtml += `<div class="cart-item"><span class="cart-item-name">${escapeHtml(name)}</span><span class="cart-item-meta">×${escapeHtml(result.items[name])}</span></div>`;
        }

        cartSection.innerHTML = `
            <p class="order-confirmation-title">${ICONS.check} Order #${escapeHtml(result.order_id)} placed</p>
            <div class="cart-item-list">${itemsHtml}</div>
            <div id="total-price">Total due: ${formatPrice(result.total_price)}</div>
            <p>Please transfer the amount to the card below:</p>
            <div class="payment-card-number">${escapeHtml(CONFIG.paymentCardNumber)}<br>${escapeHtml(CONFIG.paymentCardHolder)}</div>
            <p>Then send a photo of the payment receipt <strong>directly in this chat with the bot</strong> so an admin can confirm your order.</p>
        `;

        cart = [];
        updateCartBadge();

    } catch (error) {
        console.error(error.message);
        placeOrderBtn.disabled = false;
        placeOrderBtn.innerHTML = originalContent;
        cartSection.insertAdjacentHTML("afterbegin", `<p class="field-error-msg">Could not place order. Please try again.</p>`);
    }
}

/* ========================================
   Catalog loading
   ======================================== */
async function getData() {
    const url = `${CONFIG.apiBase}/products`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }

        const result = await response.json();
        catalogSection.setAttribute("aria-busy", "false");

        if (!result.length) {
            catalogSection.innerHTML = `
                <div class="empty-state">
                    ${ICONS.productPlaceholder}
                    <p>No products available right now. Check back soon!</p>
                </div>`;
            return;
        }

        let html = "";
        for (let item of result) {
            const media = item.image_url
                ? `<img class="product-photo" src="${escapeHtml(CONFIG.apiBase + item.image_url)}" alt="${escapeHtml(item.name)}" loading="lazy">`
                : `<div class="product-icon">${ICONS.productPlaceholder}</div>`;
            const description = item.description
                ? `<span class="product-description">${escapeHtml(item.description)}</span>`
                : "";
            html += `
                <div class="product-card">
                    ${media}
                    <span class="product-name">${escapeHtml(item.name)}</span>
                    ${description}
                    <span class="price">${formatPrice(item.price)}</span>
                    <button type="button" class="add-to-cart-btn" data-id="${item.id}">Add to cart</button>
                </div>`;
        }

        catalogSection.innerHTML = html;

        const buttons = document.querySelectorAll(".add-to-cart-btn");
        for (let button of buttons) {
            button.addEventListener("click", function () {
                const productID = Number(button.dataset.id);

                const existingItem = cart.find(cartItem => cartItem.id === productID);
                if (existingItem) {
                    existingItem.quantity += 1;
                } else {
                    const product = result.find(p => p.id === productID);
                    cart.push({ id: productID, name: product.name, price: product.price, quantity: 1 });
                }

                updateCartBadge();

                const originalLabel = button.textContent;
                button.classList.add("just-added");
                button.textContent = "Added";
                setTimeout(() => {
                    button.classList.remove("just-added");
                    button.textContent = originalLabel;
                }, 900);
            });
        }

    } catch (error) {
        console.error(error.message);
        catalogSection.setAttribute("aria-busy", "false");
        catalogSection.innerHTML = `
            <div class="error-state">
                ${ICONS.alert}
                <p>Couldn't load products. Check your connection and try again.</p>
                <button type="button" id="retry-load-btn">Retry</button>
            </div>`;
        const retryBtn = document.getElementById("retry-load-btn");
        if (retryBtn) {
            retryBtn.addEventListener("click", () => {
                catalogSection.setAttribute("aria-busy", "true");
                catalogSection.innerHTML = `
                    <div class="loading-state">
                        <span class="spinner" aria-hidden="true"></span>
                        <p>Loading products...</p>
                    </div>`;
                getData();
            });
        }
    }
}
getData();

/* ========================================
   Cart rendering
   ======================================== */
function renderCart() {
    try {
        catalogSection.hidden = true;
        cartSection.hidden = false;

        if (cart.length === 0) {
            cartSection.innerHTML = `
                <button type="button" id="back-to-catalog-btn">${ICONS.backArrow} Back to shop</button>
                <div class="empty-state">
                    ${ICONS.emptyCart}
                    <p>Your cart is empty.</p>
                </div>`;
        } else {
            let totalPrice = 0;
            let html = `<button type="button" id="back-to-catalog-btn">${ICONS.backArrow} Back to shop</button>`;
            for (let item of cart) {
                totalPrice += item.quantity * item.price;
                html += `<div class="cart-item"><span class="cart-item-name">${escapeHtml(item.name)}</span><span class="cart-item-meta">${formatPrice(item.price)} × ${escapeHtml(item.quantity)}</span></div>`;
            }

            html += `<div id="total-price">Total: ${formatPrice(totalPrice)}</div>`;
            html += `
                <form id="checkout-form">
                    <div class="field"><label for="name">Full name</label><input type="text" id="name" required /></div>
                    <div class="field"><label for="address">Address</label><input type="text" id="address" required /></div>
                    <div class="field"><label for="postal-code">Postal code</label><input type="text" id="postal-code" inputmode="numeric" required /></div>
                    <div class="field"><label for="phone-number">Phone number</label><input type="tel" id="phone-number" inputmode="tel" required /></div>
                    <button type="submit" id="place-order-btn">Place order</button>
                </form>`;

            cartSection.innerHTML = html;

            const checkoutForm = document.getElementById("checkout-form");
            checkoutForm.addEventListener("submit", function (event) {
                event.preventDefault();

                const fields = [
                    ["name", "customer_name"],
                    ["address", "address"],
                    ["postal-code", "postal_code"],
                    ["phone-number", "phone_number"]
                ];

                let hasError = false;
                const values = {};
                for (const [fieldId, key] of fields) {
                    const input = document.getElementById(fieldId);
                    const value = input.value.trim();
                    input.classList.toggle("field-error", value === "");
                    if (value === "") hasError = true;
                    values[key] = value;
                }
                if (hasError) return;

                const items = cart.reduce((acc, item) => {
                    acc[item.name] = item.quantity;
                    return acc;
                }, {});

                const orderData = {
                    customer_telegram_id: String(customerTelegramId),
                    customer_name: values.customer_name,
                    address: values.address,
                    postal_code: values.postal_code,
                    phone_number: values.phone_number,
                    items: items,
                    total_price: totalPrice
                };

                placeOrder(orderData, document.getElementById("place-order-btn"));
            });
        }

        const backToCatalog = document.getElementById("back-to-catalog-btn");
        backToCatalog.addEventListener("click", function () {
            catalogSection.hidden = false;
            cartSection.hidden = true;
        });

    } catch (error) {
        console.error(error.message);
    }
}