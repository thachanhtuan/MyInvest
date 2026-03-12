// MyInvest – shared JS utilities

/**
 * Format a number with Russian locale.
 */
function fmtNum(v, decimals = 2) {
  if (v == null || isNaN(v)) return '—';
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: decimals }).format(v);
}

/**
 * Format percentage.
 */
function fmtPct(v) {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(2) + '%';
}

/**
 * Return a Bootstrap colour class based on sign.
 */
function signClass(v) {
  if (v == null) return '';
  return v >= 0 ? 'text-success' : 'text-danger';
}

/**
 * Show a toast-like alert at top of page.
 */
function showAlert(message, type = 'success') {
  const div = document.createElement('div');
  div.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
  div.style.zIndex = 9999;
  div.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  document.body.appendChild(div);
  setTimeout(() => { div.remove(); }, 4000);
}
