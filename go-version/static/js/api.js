const API = {
  token: localStorage.getItem('token'),

  async request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' }
    if (this.token) headers['Authorization'] = 'Bearer ' + this.token
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || '请求失败')
    return data
  },

  // Auth
  register: (u, p, e) => API.request('POST', '/api/register', { username: u, password: p, email: e }),
  login: (u, p) => API.request('POST', '/api/login', { username: u, password: p }),
  getProfile: () => API.request('GET', '/api/profile'),

  // Categories
  listCategories: () => API.request('GET', '/api/categories'),
  createCategory: (d) => API.request('POST', '/api/admin/categories', d),
  updateCategory: (id, d) => API.request('PUT', '/api/admin/categories/' + id, d),
  deleteCategory: (id) => API.request('DELETE', '/api/admin/categories/' + id),

  // Products
  listProducts: (q) => API.request('GET', '/api/products'+q),
  getProduct: (id) => API.request('GET', '/api/products/' + id),
  createProduct: (d) => API.request('POST', '/api/admin/products', d),
  updateProduct: (id, d) => API.request('PUT', '/api/admin/products/' + id, d),
  deleteProduct: (id) => API.request('DELETE', '/api/admin/products/' + id),
  updateBlindBoxPool: (id, d) => API.request('PUT', '/api/admin/products/' + id + '/blindbox', d),

  // Card Keys
  importCardKeys: (pid, keys) => API.request('POST', '/api/admin/cardkeys/import', { product_id: pid, keys }),
  listCardKeys: (pid) => API.request('GET', '/api/admin/cardkeys?product_id=' + pid),
  deleteCardKey: (id) => API.request('DELETE', '/api/admin/cardkeys/' + id),
  exportCardKeys: (pid) => API.request('GET', '/api/admin/cardkeys/export?product_id=' + pid),

  // Coupons
  createCoupon: (d) => API.request('POST', '/api/admin/coupons', d),
  listCoupons: () => API.request('GET', '/api/admin/coupons'),
  deleteCoupon: (id) => API.request('DELETE', '/api/admin/coupons/' + id),
  claimCoupon: (code) => API.request('POST', '/api/coupon/claim', { code }),
  getMyCoupons: () => API.request('GET', '/api/coupons/mine'),

  // Orders
  createOrder: (pid, qty, coupon) => API.request('POST', '/api/orders', { product_id: pid, quantity: qty, coupon_code: coupon }),
  listOrders: () => API.request('GET', '/api/orders'),
  getOrder: (id) => API.request('GET', '/api/orders/' + id),
  adminListOrders: () => API.request('GET', '/api/admin/orders'),

  // Reviews
  createReview: (d) => API.request('POST', '/api/reviews', d),
  listReviews: (pid) => API.request('GET', '/api/reviews?product_id=' + pid),
  deleteReview: (id) => API.request('DELETE', '/api/admin/reviews/' + id),
}
