// Global ElectroShop Javascript

document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initAJAXCart();
  initAJAXWishlist();
  initSkeletonLoaders();
});

// ==========================================
// DARK MODE HANDLER
// ==========================================
function initDarkMode() {
  const toggleBtn = document.getElementById('dark-mode-toggle');
  if (!toggleBtn) return;

  const currentTheme = localStorage.getItem('theme');
  if (currentTheme === 'dark') {
    document.body.classList.add('dark-mode');
    toggleBtn.innerHTML = '<i class="bi bi-sun-fill"></i>';
  } else {
    toggleBtn.innerHTML = '<i class="bi bi-moon-fill"></i>';
  }

  toggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    let theme = 'light';
    if (document.body.classList.contains('dark-mode')) {
      theme = 'dark';
      toggleBtn.innerHTML = '<i class="bi bi-sun-fill"></i>';
    } else {
      toggleBtn.innerHTML = '<i class="bi bi-moon-fill"></i>';
    }
    localStorage.setItem('theme', theme);
  });
}

// ==========================================
// TOAST NOTIFICATIONS
// ==========================================
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) {
    // Create container dynamically if it doesn't exist
    const newContainer = document.createElement('div');
    newContainer.id = 'toast-container';
    newContainer.className = 'toast-container';
    document.body.appendChild(newContainer);
  }

  const toastId = 'toast-' + Date.now();
  const bgClass = type === 'success' ? 'bg-success' : type === 'danger' ? 'bg-danger' : 'bg-warning';
  
  const toastHTML = `
    <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 show" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  
  document.getElementById('toast-container').insertAdjacentHTML('beforeend', toastHTML);
  const element = document.getElementById(toastId);
  
  // Auto remove after 4 seconds
  setTimeout(() => {
    element.classList.remove('show');
    setTimeout(() => element.remove(), 500);
  }, 4000);
}

// ==========================================
// SKELETON LOADER HANDLER
// ==========================================
function initSkeletonLoaders() {
  const skeletons = document.querySelectorAll('.skeleton-wrapper');
  if (skeletons.length === 0) return;

  // Simulate page content load for testing skeleton visibility
  window.addEventListener('load', () => {
    setTimeout(() => {
      skeletons.forEach(wrapper => {
        wrapper.classList.remove('skeleton-active');
        const realContent = wrapper.querySelector('.skeleton-content');
        const skeletonMock = wrapper.querySelector('.skeleton-mock');
        if (realContent) realContent.classList.remove('d-none');
        if (skeletonMock) skeletonMock.classList.add('d-none');
      });
    }, 600); // 600ms load delay simulation
  });
}

// ==========================================
// AJAX CART ACTIONS
// ==========================================
function initAJAXCart() {
  // Catch add to cart form submits to do AJAX instead of full page reloads
  const cartAddForms = document.querySelectorAll('.ajax-cart-add-form');
  cartAddForms.forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = form.action;
      const formData = new FormData(form);

      try {
        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        if (response.ok) {
          // Update the global badge count and subtotal
          const data = await response.json();
          updateCartBadge();
          showToast('Produk berhasil dimasukkan ke keranjang belanja.');
        } else {
          showToast('Gagal menambahkan produk ke keranjang.', 'danger');
        }
      } catch (err) {
        // Fallback standard submit if fetch fails
        form.submit();
      }
    });
  });

  // Quantity updates on cart detail page
  const qtyInputs = document.querySelectorAll('.cart-qty-input');
  qtyInputs.forEach(input => {
    input.addEventListener('change', async () => {
      const productId = input.dataset.productId;
      const quantity = input.value;
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      
      const formData = new FormData();
      formData.append('quantity', quantity);
      formData.append('csrfmiddlewaretoken', csrfToken);

      try {
        const response = await fetch(`/cart/update/${productId}/`, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        const resData = await response.json();
        if (response.ok) {
          showToast('Jumlah barang berhasil diubah.');
          // Reload page to re-calculate subtotals and checkout totals easily
          window.location.reload();
        } else {
          showToast(resData.error || 'Gagal mengubah jumlah barang.', 'danger');
          window.location.reload();
        }
      } catch (err) {
        window.location.reload();
      }
    });
  });
}

// Helper to pull current count from DRF API dynamically
async function updateCartBadge() {
  const badges = document.querySelectorAll('.cart-badge');
  if (badges.length === 0) return;

  try {
    const response = await fetch('/api/cart/');
    if (response.ok) {
      const cart = await response.json();
      badges.forEach(badge => {
        badge.textContent = cart.total_items;
        if (cart.total_items > 0) {
          badge.classList.remove('d-none');
        } else {
          badge.classList.add('d-none');
        }
      });
    }
  } catch (err) {
    console.error('Error fetching cart badge info:', err);
  }
}

// ==========================================
// AJAX WISHLIST ACTION
// ==========================================
function initAJAXWishlist() {
  const wishlistBtns = document.querySelectorAll('.ajax-wishlist-btn');
  wishlistBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const productId = btn.dataset.productId;
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

      const formData = new FormData();
      formData.append('product_id', productId);
      formData.append('csrfmiddlewaretoken', csrfToken);

      try {
        const response = await fetch(`/cart/wishlist/toggle/${productId}/`, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        const data = await response.json();
        if (response.ok) {
          if (data.added) {
            btn.innerHTML = '<i class="bi bi-heart-fill text-danger"></i>';
            showToast('Produk ditambahkan ke Wishlist.');
          } else {
            btn.innerHTML = '<i class="bi bi-heart text-muted"></i>';
            showToast('Produk dihapus dari Wishlist.');
          }
        } else {
          showToast('Harap login terlebih dahulu untuk mengelola wishlist.', 'danger');
        }
      } catch (err) {
        showToast('Terjadi kesalahan koneksi.', 'danger');
      }
    });
  });
}
