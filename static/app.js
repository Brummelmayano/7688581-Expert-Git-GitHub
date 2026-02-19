function cardTemplate(product) {
  return `
    <article class="card" data-product-id="${product.id}">
      <img src="${product.image}" alt="${product.name}" />
      <div class="card-body">
        <h4>${product.name}</h4>
        <p>${product.description}</p>
        <div class="meta">
          <span class="price">${product.price} ${product.currency}</span>
          <span class="stock" id="stock-${product.id}">Stock: ${product.stock}</span>
        </div>
        <button class="buy-btn" data-product="${product.id}">Acheter</button>
      </div>
    </article>
  `;
}

async function loadConfig() {
  const response = await fetch('/api/config');
  const data = await response.json();
  const paymentSelect = document.getElementById('payment-select');
  data.payment_methods.forEach((method) => {
    const option = document.createElement('option');
    option.value = method;
    option.textContent = method;
    paymentSelect.appendChild(option);
  });
}

async function loadStock() {
  const response = await fetch('/api/products');
  if (!response.ok) return [];
  const products = await response.json();
  const grid = document.getElementById('cards-grid');
  const select = document.getElementById('product-select');
  grid.innerHTML = products.map(cardTemplate).join('');

  select.innerHTML = '<option value="">Sélectionnez une carte</option>';
  products.forEach((product) => {
    const option = document.createElement('option');
    option.value = product.id;
    option.textContent = `${product.name} — ${product.price} ${product.currency}`;
    select.appendChild(option);
  });
  return products;
}

function setupQuickBuyButtons() {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('.buy-btn');
    if (!button) return;
    const product = button.dataset.product;
    document.getElementById('product-select').value = product;
    document.getElementById('checkout').scrollIntoView({ behavior: 'smooth' });
  });
}

function showFeedback(type, message) {
  const feedback = document.getElementById('feedback');
  feedback.className = type;
  feedback.textContent = message;
}

function setupCheckoutForm() {
  const form = document.getElementById('checkout-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());

    const response = await fetch('/api/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      showFeedback('error', data.error || "Une erreur est survenue pendant l'achat.");
      return;
    }
    showFeedback('success', `${data.message} Référence: ${data.order_reference}. ${data.delivery_notice}`);
    form.reset();
    await loadStock();
  });
}

(async function init() {
  await loadConfig();
  await loadStock();
  setupQuickBuyButtons();
  setupCheckoutForm();
})();
