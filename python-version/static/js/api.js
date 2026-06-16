let _savedToken = null
try { _savedToken = localStorage.getItem('token') } catch(e) {}
const API = {
  token: _savedToken,

  async request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' }
    if (this.token) headers['Authorization'] = 'Bearer ' + this.token
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined })
    const data = await res.json()
    if (!res.ok) {
      if (res.status === 401) {
        try { localStorage.removeItem('token') } catch(e) {}
        window.location.href = '/login'
        throw new Error('登录已失效，请重新登录')
      }
      const err = new Error(data.error || '请求失败')
      err.status = res.status
      err.needLogin = res.status === 401
      throw err
    }
    return data
  },

  // Captcha
  getCaptcha: () => API.request('GET', '/api/captcha'),

  // Auth
  register: (u, p, e, captchaKey, captchaCode) => API.request('POST', '/api/register', { username: u, password: p, email: e, captcha_key: captchaKey, captcha_code: captchaCode }),
  login: (u, p, captchaKey, captchaCode) => API.request('POST', '/api/login', { username: u, password: p, captcha_key: captchaKey, captcha_code: captchaCode }),
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
  previewOrder: (pid, qty, coupon) => API.request('POST', '/api/orders/preview', { product_id: pid, quantity: qty, coupon_code: coupon || '' }),
  createOrder: (pid, qty, coupon) => API.request('POST', '/api/orders', { product_id: pid, quantity: qty, coupon_code: coupon || '' }),
  payOrder: (oid, method) => API.request('POST', '/api/orders/' + oid + '/pay', { method }),
  listOrders: () => API.request('GET', '/api/orders'),
  getOrder: (id) => API.request('GET', '/api/orders/' + id),
  adminListOrders: () => API.request('GET', '/api/admin/orders'),

  // Reviews
  createReview: (d) => API.request('POST', '/api/reviews', d),
  listReviews: (pid) => API.request('GET', '/api/reviews?product_id=' + pid),
  deleteReview: (id) => API.request('DELETE', '/api/admin/reviews/' + id),

  // User Invite & Team
  getInviteCode: () => API.request('GET', '/api/user/invite'),
  bindInvite: (code) => API.request('POST', '/api/user/bind-invite', { code }),
  getTeam: () => API.request('GET', '/api/user/team'),
  getCommission: () => API.request('GET', '/api/user/commission'),

  // Payment
  getRechargeMethods: () => API.request('GET', '/api/recharge/methods'),
  getPaymentMethods: () => API.request('GET', '/api/payment/methods'),
}
