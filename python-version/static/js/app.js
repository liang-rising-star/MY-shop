const { createApp, ref, computed, watch, onMounted, nextTick } = Vue

console.log('[DEBUG] Vue loaded:', typeof Vue)
console.log('[DEBUG] createApp:', typeof createApp)

const app = createApp({
  setup() {
    console.log('[DEBUG] setup() called')
    const page = ref('home')
    const scrolled = ref(false)
    const menuOpen = ref(false)
    const isReg = ref(false)
    let savedToken = null
    try { savedToken = localStorage.getItem('token') } catch(e) {}
    const token = ref(savedToken)
    const toasts = ref([])
    const setupRequired = ref(false)
    const setupUser = ref('')
    const setupPass = ref('')
    const setupEmail = ref('')
    const setupErr = ref('')
    const adminView = ref(false)

    const products = ref([])
    const categories = ref([])
    const orders = ref([])
    const allOrders = ref([])
    const coupons = ref([])
    const myCoupons = ref([])
    const cardKeys = ref([])
    const reviews = ref([])
    const user = ref(null)
    const detail = ref(null)
    const detailMediaList = ref([])
    const detailMediaIdx = ref(0)
    const detailVideoRef = ref(null)
    const videoThumbnails = ref({})
    const lastOrder = ref(null)
    const search = ref('')
    const catFilter = ref('')
    const typeFilter = ref('')
    const authUser = ref('')
    const authPass = ref('')
    const authEmail = ref('')
    const authErr = ref('')
    const captchaKey = ref('')
    const captchaImage = ref('')
    const captchaCode = ref('')
    const users = ref([])
    const adminTab = ref('dashboard')
    const adminMenu = [
      { key:'dashboard', icon:'📊', label:'系统概览' },
      { key:'products', icon:'📦', label:'商品管理' },
      { key:'categories', icon:'📂', label:'分类管理' },
      { key:'keys', icon:'🔑', label:'卡密管理' },
      { key:'orders', icon:'📋', label:'订单管理' },
      { key:'users', icon:'👥', label:'用户管理' },
      { key:'coupons', icon:'🎫', label:'优惠券' },
      { key:'settings', icon:'⚙', label:'系统设置' },
    ]
    const showProductForm = ref(false)
    const showCouponForm = ref(false)
    const showCatForm = ref(false)
    const settings = ref({ ShopName:'MY-Shop', ShopDesc:'穿越维度的购物体验', PageSize:20, AllowRegister:true })
    const config = ref({
      shop_name: '',
      logo: '',
      background_url: '',
      background_mobile_url: '',
      service_qq: '',
      service_wechat: '',
      service_email: '',
      qrcode1_title: '',
      qrcode1_url: '',
      qrcode2_title: '',
      qrcode2_url: ''
    })
    const showService = ref(false)
    const editingProduct = ref(null)
    const prodForm = ref({ Name:'',Description:'',Price:0,CategoryID:0,Type:'normal',ImageURL:'' })
    const catForm = ref({ Name:'',SortOrder:0 })
    const couponForm = ref({ Code:'',Type:'percentage',Value:0,MinAmount:0,MaxUses:0,ExpiresAt:'' })
    const keysInput = ref('')
    const keyProductID = ref(0)
    const claimCode = ref('')
    const buyQty = ref(1)
    const ucData = ref(null)
    const eventSettings = ref({enabled:false,banner_title:'',banner_desc:'',show_progress:true,show_countdown:true})
    const eventProducts = ref([])
    const ucTab = ref('overview')
    const ucOrders = ref([])
    const orderFilter = ref('')
    const orderStatuses = [{k:'',l:'全部'},{k:'pending',l:'待支付'},{k:'paid',l:'已支付'},{k:'completed',l:'已完成'},{k:'refunded',l:'已退款'}]
    const profileForm = ref({email:'',phone:'',real_name:''})
    const pwForm = ref({old:'',new1:'',new2:''})
    const pwErr = ref('')
    const rechargeRecords = ref([])
    const rechargeAmt = ref(0)
    const rechargePayMethod = ref('')
    const availablePayMethods = ref([])
    const upgradeAmt = ref(0)
    const showUpgrade = ref(false)
    const poolProduct = ref(null)
    const poolModal = ref(false)
    const currentPool = ref([])

    const levelRequirements = [
      { level: 1, req: 0 },
      { level: 2, req: 100 },
      { level: 3, req: 500 },
      { level: 4, req: 2000 },
      { level: 5, req: 10000 },
    ]
    const nextLevel = computed(() => {
      if (!ucData.value?.user) return null
      const currentLevel = ucData.value.user.level || 1
      const totalRecharge = ucData.value.user.total_recharge || 0
      for (const req of levelRequirements) {
        if (req.level === currentLevel + 1) {
          return req
        }
      }
      return null
    })
    const ucTabs = [
      {k:'overview', l:'概览'},
      {k:'orders', l:'我的商品'},
      {k:'assets', l:'充值'},
      {k:'coupons', l:'优惠券'},
      {k:'profile', l:'资料'},
      {k:'security', l:'安全'}
    ]

    function navigate(name, extra) {
      if ((name === 'lottery' || name === 'events') && !token.value) {
        toast('请先登录后参与', 'error')
        page.value = 'login'
        isReg.value = false
        history.pushState(null, '', '/login')
        return
      }
      if (name === 'login') isReg.value = false
      page.value = name
      let path = name === 'home' ? '/' : '/' + name
      if (extra) path += '/' + extra
      history.pushState(null, '', path)
    }

    function initRoute() {
      const path = window.location.pathname
      const parts = path.split('/').filter(Boolean)
      const route = parts[0] || 'home'
      if (route === 'login') isReg.value = false
      page.value = route
      if (route === 'detail' && parts[1]) {
        const pid = parseInt(parts[1])
        if (pid) {
          const loadDetail = (d) => {
            detail.value = d
            setupDetailMedia(d.product, d.product.id)
          }
          if (!detail.value) {
            API.getProduct(pid).then(d => loadDetail(d)).catch(e => console.error('initRoute error:', e))
          } else {
            setupDetailMedia(detail.value.product, pid)
          }
        }
      }
    }
    function setupDetailMedia(product, pid) {
      if (!product) return
      stopAutoSlide()
      stopVideo()
      let imgs = product.images ? product.images.split(',').filter(u=>u.trim()) : []
      if (product.video_url && !imgs.some(u => isVideoUrl(u))) {
        const vids = product.video_url.split(',').filter(u=>u.trim())
        vids.forEach(url => imgs.push(url))
      }
      imgs.forEach(url => {
        if (isVideoUrl(url) && !videoThumbnails.value[url]) {
          fetch('/api/admin/products/' + pid + '/thumbnail?video_url=' + encodeURIComponent(url)).then(r=>r.json()).then(data=>{
            if (data.thumbnail) { videoThumbnails.value[url] = data.thumbnail; }
          }).catch(()=>{});
        }
      })
      detailMediaList.value = [...imgs]
      detailMediaIdx.value = 0
      preloadMedia(imgs)
      nextTick(() => { startAutoSlide(); })
    }

    const filtered = computed(() => {
      let list = products.value
      if (catFilter.value) list = list.filter(p => p.category_id == catFilter.value)
      if (typeFilter.value) list = list.filter(p => p.type === typeFilter.value)
      if (search.value) {
        const q = search.value.toLowerCase()
        list = list.filter(p => (p.name || p.Name || '').toLowerCase().includes(q))
      }
      return list
    })

const lotteryProducts = computed(() => products.value.filter(p => p.type === 'blindbox'))
const timedProducts = computed(() => eventProducts.value)
    
    async function loadEvents() {
      if (!token.value) return
      try {
        const d = await API.request('GET', '/api/events')
        eventSettings.value = d.settings || eventSettings.value
        eventProducts.value = d.products || []
      } catch(e) {}
    }

    async function loadConfig() {
      try {
        const d = await API.request('GET', '/api/site/settings')
        if (d.settings) {
          config.value = { ...config.value, ...d.settings }
          // 更新页面标题
          if (d.settings.title) {
            document.title = `${d.settings.shop_name || 'MY-Shop'} - ${d.settings.title}`
          }
        }
      } catch(e) {}
    }

    function countdown(timeStr) {
      if (!timeStr) return ''
      const diff = new Date(timeStr).getTime() - Date.now()
      if (diff <= 0) return '已结束'
      return `${Math.floor(diff/3600000)}h ${Math.floor((diff%3600000)/60000)}m ${Math.floor((diff%60000)/1000)}s`
    }

    function toast(msg, type = 'success') {
      const id = Date.now()
      toasts.value.push({ id, message: msg, type })
      setTimeout(() => {
        const idx = toasts.value.findIndex(t => t.id === id)
        if (idx >= 0) toasts.value.splice(idx, 1)
      }, 3000)
    }

    const showConfirmModal=ref(false),confirmMessage=ref('')
    let _confirmResolve=null
    function confirmAsync(msg){showConfirmModal.value=true;confirmMessage.value=msg;return new Promise(r=>{_confirmResolve=r})}
    function confirmResolveFn(v){showConfirmModal.value=false;if(_confirmResolve)_confirmResolve(v);_confirmResolve=null}

    function copy(text) { navigator.clipboard?.writeText(text).then(() => toast('已复制')) }
    function statusText(s) { return { pending:'待支付',paid:'已支付',shipped:'已发货',completed:'已完成',cancelled:'已取消',failed:'失败',refunded:'已退款' }[s] || s }
    function formatDate(t) { return t ? t.slice(0,19).replace('T',' ') : '' }

    async function loadProducts(featured=0) { try { const q=featured?'?featured=1':''; const d = await API.listProducts(q); products.value = d.products || [] } catch(e){} }
    async function loadCaptcha() { try { const d = await API.getCaptcha(); captchaKey.value = d.key; captchaImage.value = d.image } catch(e){} }
    async function loadCategories() { try { categories.value = await API.listCategories() } catch(e){} }
    async function loadOrders() { if(!token.value) return; try { orders.value = await API.listOrders() } catch(e){} }
    async function loadAllOrders() { try { allOrders.value = await API.adminListOrders() } catch(e){} }
    async function loadUsers() { try { users.value = await API.request('GET','/api/admin/users') } catch(e){} }
    async function loadCoupons() { try { coupons.value = await API.listCoupons() } catch(e){} }
    async function loadProfile() {
      if (!token.value) return
      try { user.value = await API.getProfile() } catch(e) { token.value=null; try { localStorage.removeItem('token') } catch(e2) {} }
    }
    async function loadMyCoupons() { if(!token.value) return; try { myCoupons.value = await API.getMyCoupons() } catch(e){} }
    async function loadCardKeys() { if(!keyProductID.value) return; try { cardKeys.value = await API.listCardKeys(keyProductID.value) } catch(e){} }
    async function loadReviews(pid) { try { const d=await API.listReviews(pid); reviews.value=d.reviews||[] } catch(e){ reviews.value=[] } }
    watch(keyProductID, loadCardKeys)
    watch(isReg, () => { loadCaptcha() })

    async function checkSetup() {
      try { const d=await API.request('GET','/api/setup/status'); setupRequired.value=d.setup_required }
      catch(e){ setupRequired.value=true }
    }
    async function initSetup() {
      setupErr.value=''
      if(!setupUser.value||!setupPass.value){ setupErr.value='请填写完整'; return }
      try {
        await API.request('POST','/api/setup/init',{ username:setupUser.value, password:setupPass.value, email:setupEmail.value })
        setupRequired.value=false; toast('管理员创建成功，请登录')
        navigate('login')
      } catch(e){ setupErr.value=e.message }
    }
    function toggleAdminView() {
      adminView.value=!adminView.value
      if(adminView.value){ navigate('admin'); loadAllOrders(); loadCoupons() }
      else navigate('home')
    }

    function goProfile() {
      if (!token.value) { navigate('login'); return }
      navigate('profile')
    }

    async function doLogin() {
      authErr.value=''
      if (!captchaCode.value) { authErr.value='请输入验证码'; return }
      try {
        const d=await API.login(authUser.value, authPass.value, captchaKey.value, captchaCode.value)
        token.value=d.token; API.token=d.token; try { localStorage.setItem('token',d.token) } catch(e) {}
        authUser.value=authPass.value=captchaCode.value=''; toast('登录成功')
        loadProfile(); loadOrders(); loadMyCoupons(); loadCaptcha()
        navigate('home')
      } catch(e){ authErr.value=e.message; loadCaptcha() }
    }
    async function doReg() {
      authErr.value=''
      if (!captchaCode.value) { authErr.value='请输入验证码'; return }
      try { await API.register(authUser.value, authPass.value, authEmail.value, captchaKey.value, captchaCode.value); toast('注册成功，请登录'); isReg.value=false; loadCaptcha() } catch(e){ authErr.value=e.message; loadCaptcha() }
    }
    function logout() {
      token.value=null; API.token=null; try { localStorage.removeItem('token') } catch(e) {}
      user.value=null; orders.value=[]; myCoupons.value=[]
      toast('已退出'); navigate('home')
    }

    async function viewProduct(p) {
      if (!p) { toast('商品数据错误', 'error'); return }
      const pid = p.id ?? p.ID
      if (!pid) { toast('商品ID错误', 'error'); return }
      detail.value=null; lastOrder.value=null; buyQty.value=1; reviews.value=[]; detailMediaList.value=[]; detailMediaIdx.value=0
      try { 
        const d=await API.getProduct(pid); 
        detail.value=d;
        setupDetailMedia(d.product, pid)
        loadReviews(pid)
      } catch(e){ toast(e.message,'error') }
      navigate('detail', pid)
    }

    function isVideoUrl(url) {
      return url && (url.includes('.mp4') || url.includes('.webm') || url.includes('.mov'));
    }
    function preloadMedia(list) {
      list.forEach(url => {
        if (!url || !url.trim()) return;
        if (isVideoUrl(url)) {
          const v = document.createElement('video');
          v.src = url;
          v.preload = 'auto';
          v.muted = true;
          v.style.display = 'none';
          document.body.appendChild(v);
          v.onloadeddata = () => { document.body.removeChild(v); };
          setTimeout(() => { if (v.parentNode) document.body.removeChild(v); }, 15000);
        } else {
          const img = new Image();
          img.src = url;
        }
      });
    }
    let autoSlideTimer = null
    let userClicked = false
    function handleFirstInteraction() {
      userClicked = true;
      const vid = detailVideoRef.value;
      if (vid && vid.tagName === 'VIDEO' && !vid.paused) { vid.muted = false; }
      document.removeEventListener('click', handleFirstInteraction);
    }
    function startAutoSlide() {
      stopAutoSlide();
      if (detailMediaList.value.length <= 1) return;
      const cur = detailMediaList.value[detailMediaIdx.value] || '';
      if (isVideoUrl(cur)) {
        setTimeout(() => {
          const vid = detailVideoRef.value;
          if (vid && vid.tagName === 'VIDEO') {
            vid.muted = !userClicked;
            vid.onended = () => {
              detailMediaIdx.value = (detailMediaIdx.value + 1) % detailMediaList.value.length;
            };
          }
        }, 500);
      } else {
        autoSlideTimer = setInterval(() => {
          detailMediaIdx.value = (detailMediaIdx.value + 1) % detailMediaList.value.length;
        }, 5000);
      }
    }
    function stopAutoSlide() {
      if (autoSlideTimer) { clearInterval(autoSlideTimer); autoSlideTimer = null; }
      const vid = detailVideoRef.value;
      if (vid && vid.tagName === 'VIDEO') { vid.onended = null; }
    }
    function pauseAutoSlide() { stopAutoSlide(); }
    function resumeAutoSlide() { startAutoSlide(); }
    function prevMedia() { stopAutoSlide(); stopVideo(); detailMediaIdx.value = (detailMediaIdx.value - 1 + detailMediaList.value.length) % detailMediaList.value.length; }
    function nextMedia() { stopAutoSlide(); stopVideo(); detailMediaIdx.value = (detailMediaIdx.value + 1) % detailMediaList.value.length; }
    function selectMedia(i) {
      stopAutoSlide(); stopVideo();
      detailMediaIdx.value = i;
      const url = detailMediaList.value[i] || '';
      if (isVideoUrl(url)) {
        nextTick(() => {
          const vid = detailVideoRef.value;
          if (vid) { vid.src = url; vid.muted = true; vid.play().then(() => { vid.muted = false; }).catch(() => {}); }
        });
      }
      nextTick(() => { startAutoSlide(); });
    }
    function getVideoThumb(url) { return videoThumbnails.value[url] || ''; }
    function stopVideo() {
      const vid = detailVideoRef.value;
      if (vid && vid.tagName === 'VIDEO') { vid.pause(); vid.currentTime = 0; vid.onended = null; }
    }
    function handleVideoLoaded() {
      const vid = detailVideoRef.value;
      if (!vid || vid.tagName !== 'VIDEO') return;
      vid.muted = true;
      vid.play().then(() => { if (userClicked) vid.muted = false; }).catch(() => {});
    }

    const currentVideoSrc = computed(() => {
      const url = detailMediaList.value[detailMediaIdx.value] || '';
      return isVideoUrl(url) ? url : '';
    })

    watch(currentVideoSrc, (newSrc) => {
      if (!newSrc) return;
      nextTick(() => {
        const vid = detailVideoRef.value;
        if (vid && vid.tagName === 'VIDEO') {
          vid.muted = true;
          vid.play().then(() => { if (userClicked) vid.muted = false; }).catch(() => {});
        }
      });
    })
    async function checkout(product) {
      if(!token.value){ toast('请先登录','error'); navigate('login'); return }
      const pid = product.id || product.ID
      if(!pid){ toast('商品ID错误','error'); return }
      try {
        const d = await API.previewOrder(pid, buyQty.value||1, '')
        payPreview.value = d
        selectedPayMethod.value = d.payment_methods.length ? d.payment_methods[0].id : 'balance'
        selectedCouponId.value = null
        promoCodeInput.value = ''
        promoMsg.value = ''
        paySubmitting.value = false
        showPayModal.value = true
      } catch(e){ toast(e.message,'error') }
    }

    const showPayModal = ref(false)
    const payPreview = ref(null)
    const selectedPayMethod = ref('')
    const selectedCouponId = ref(null)
    const promoCodeInput = ref('')
    const promoMsg = ref('')
    const promoMsgType = ref('')
    const paySubmitting = ref(false)

    function selectCoupon(c) {
      if (selectedCouponId.value === c.id) {
        selectedCouponId.value = null
        refreshPreview()
      } else {
        selectedCouponId.value = c.id
        refreshPreview(c.code)
      }
    }

    async function applyPromoCode() {
      if (!promoCodeInput.value) return
      promoMsg.value = ''
      await refreshPreview(promoCodeInput.value)
    }

    async function refreshPreview(couponCode) {
      try {
        const pid = payPreview.value ? (detail.value?.product?.id) : null
        if (!pid) return
        const code = couponCode || ''
        const d = await API.previewOrder(pid, buyQty.value||1, code)
        payPreview.value = d
        if (code) {
          if (d.coupon_info && d.coupon_info.valid) {
            promoMsg.value = '优惠券已生效'
            promoMsgType.value = 'ok'
          } else if (d.coupon_info && !d.coupon_info.valid) {
            promoMsg.value = d.coupon_info.reason || '优惠券不可用'
            promoMsgType.value = 'err'
          } else {
            promoMsg.value = '优惠码无效'
            promoMsgType.value = 'err'
          }
        }
      } catch(e){ toast(e.message,'error') }
    }

    async function confirmPay() {
      if (!selectedPayMethod.value || !payPreview.value) return
      
      // 检查支付方式是否可用
      if (selectedPayMethod.value !== 'balance') {
        const methodNames = {alipay:'支付宝',wxpay:'微信支付',qqpay:'QQ钱包',mazf:'码支付',yishoumi:'易收米',usdt:'USDT'}
        const availableMethods = payPreview.value.payment_methods || []
        const isAvailable = availableMethods.some(m => m.id === selectedPayMethod.value)
        if (!isAvailable) {
          toast(`支付方式【${methodNames[selectedPayMethod.value] || selectedPayMethod.value}】不可用`, 'error')
          return
        }
        // 第三方支付暂未对接，直接提示
        toast(`支付通道【${methodNames[selectedPayMethod.value]}】暂未完成对接，请联系客服或管理员修复`, 'error')
        return
      }
      
      // 余额支付 - 检查余额是否足够
      if (selectedPayMethod.value === 'balance') {
        const userBalance = payPreview.value.user_balance || 0
        if (userBalance < payPreview.value.final_price) {
          toast('余额不足，请先充值', 'error')
          return
        }
      }
      
      paySubmitting.value = true
      try {
        const pid = detail.value?.product?.id
        const orderD = await API.createOrder(pid, buyQty.value||1, promoCodeInput.value || '')
        const order = orderD.order
        if (selectedPayMethod.value === 'balance') {
          try {
            await API.payOrder(order.id, 'balance')
            showPayModal.value = false
            toast('支付成功！')
            lastOrder.value = order
            loadOrders(); loadProducts(); loadProfile(); loadMyCoupons()
          } catch(e) {
            showPayModal.value = false
            if (e.message && e.message.includes('余额不足')) {
              toast('余额不足，请先充值', 'error')
            } else {
              toast('支付失败: ' + e.message, 'error')
            }
          }
        }
      } catch(e){
        showPayModal.value = false
        if (e.message && e.message.includes('余额不足')) {
          toast('余额不足，请先充值', 'error')
        } else {
          toast(e.message,'error')
        }
      }
      paySubmitting.value = false
    }

    function saveProduct() {
      const f=prodForm.value; if(!f.Name||!f.Price){ toast('请填写必要信息','error'); return }
      const data={...f}
      if(editingProduct.value){
        API.updateProduct(editingProduct.value.ID,data).then(()=>{ toast('已更新'); showProductForm.value=false; editingProduct.value=null; prodForm.value={Name:'',Description:'',Price:0,CategoryID:0,Type:'normal',ImageURL:''}; loadProducts() }).catch(e=>toast(e.message,'error'))
      } else {
        API.createProduct(data).then(()=>{ toast('已创建'); showProductForm.value=false; prodForm.value={Name:'',Description:'',Price:0,CategoryID:0,Type:'normal',ImageURL:''}; loadProducts() }).catch(e=>toast(e.message,'error'))
      }
    }
    function editProduct(p) { editingProduct.value=p; prodForm.value={Name:p.Name,Description:p.Description,Price:p.Price,CategoryID:p.CategoryID,Type:p.Type,ImageURL:p.ImageURL}; showProductForm.value=true }
    async function deleteProduct(id) { if(!await confirmAsync('确定删除？')) return; API.deleteProduct(id).then(()=>{ toast('已删除'); loadProducts() }).catch(e=>toast(e.message,'error')) }
    function selectProductForKeys(p) { keyProductID.value=p.id||p.ID; adminTab.value='keys' }
    async function selectProductForPool(p) {
      const pid = p.id || p.ID
      poolProduct.value = p; poolModal.value = true
      try { const d = await API.getProduct(pid); currentPool.value = d.pool || [] } catch(e){ currentPool.value = [] }
    }
    async function importKeys() {
      if(!keyProductID.value){ toast('请选择商品','error'); return }
      try { const d=await API.importCardKeys(keyProductID.value,keysInput.value); toast(d.message+' 共'+d.count+'条'); keysInput.value=''; loadCardKeys(); loadProducts() } catch(e){ toast(e.message,'error') }
    }
    async function createCoupon() {
      const f=couponForm.value; if(!f.Code||!f.Value){ toast('请填写信息','error'); return }
      try { await API.createCoupon({...f,ExpiresAt:new Date(f.ExpiresAt).toISOString()}); toast('已创建'); couponForm.value={Code:'',Type:'percentage',Value:0,MinAmount:0,MaxUses:0,ExpiresAt:''}; loadCoupons() } catch(e){ toast(e.message,'error') }
    }
    function deleteCoupon(id) { API.deleteCoupon(id).then(()=>{ toast('已删除'); loadCoupons() }).catch(e=>toast(e.message,'error')) }
    async function createCategory() {
      if(!catForm.value.Name) return; try { await API.createCategory(catForm.value); toast('已创建'); catForm.value={Name:'',SortOrder:0}; loadCategories() } catch(e){ toast(e.message,'error') }
    }
    function deleteCategory(id) { API.deleteCategory(id).then(()=>{ toast('已删除'); loadCategories() }).catch(e=>toast(e.message,'error')) }
    async function saveSettings() {
      try { await API.request('POST','/api/admin/settings', settings.value); toast('设置已保存') }
      catch(e){ toast(e.message,'error') }
    }
    async function loadUC() {
      if (!token.value) return
      try {
        ucData.value = await API.request('GET', '/api/user/center')
        if (ucData.value?.user) {
          profileForm.value = { email: ucData.value.user.Email||'', phone: ucData.value.user.Phone||'', real_name: ucData.value.user.RealName||'' }
          user.value = ucData.value.user
        }
      } catch(e) { console.error(e) }
    }
    async function loadUCOrders() {
      if (!token.value) return
      try { ucOrders.value = (await API.request('GET', '/api/user/orders?status='+orderFilter.value+'&page=1')).orders || [] }
      catch(e) { console.error(e) }
    }
    async function updateProfile() {
      try { await API.request('PUT', '/api/user/profile', profileForm.value); toast('资料已更新'); loadUC() }
      catch(e) { toast(e.message, 'error') }
    }
    async function changePw() {
      pwErr.value = ''
      if (pwForm.value.new1 !== pwForm.value.new2) { pwErr.value = '两次密码不一致'; return }
      try { await API.request('POST', '/api/user/password', { old_password: pwForm.value.old, new_password: pwForm.value.new1 }); toast('密码已修改'); pwForm.value = {old:'',new1:'',new2:''} }
      catch(e) { pwErr.value = e.message }
    }
    async function loadRechargeRecords() {
      if (!token.value) return
      try { rechargeRecords.value = (await API.request('GET', '/api/user/recharges')) || [] }
      catch(e) { console.error(e) }
    }
    async function doRecharge() {
      if (!rechargeAmt.value || rechargeAmt.value <= 0) return
      if (!rechargePayMethod.value) { toast('请选择支付方式', 'error'); return }
      try {
        const result = await API.request('POST', '/api/recharge', { amount: rechargeAmt.value, method: rechargePayMethod.value })
        toast(result.message || '订单已创建')
        if (result.pay_url) { toast('请前往支付页面完成付款', 'info') }
        rechargeAmt.value = 0
        loadRechargeRecords()
      }
      catch(e) { toast(e.message, 'error') }
    }
    async function loadPayMethods() {
      try { const d = await API.getPaymentMethods(); availablePayMethods.value = d.methods || []; if (availablePayMethods.value.length && !rechargePayMethod.value) rechargePayMethod.value = availablePayMethods.value[0].id }
      catch(e) {}
    }
    async function doUpgrade() {
      if (!upgradeAmt.value || upgradeAmt.value <= 0) return
      try { 
        await API.request('POST', '/api/user/upgrade', { amount: upgradeAmt.value }); 
        toast('积分升级成功'); 
        showUpgrade.value = false; 
        upgradeAmt.value = 0; 
        loadUC(); 
      }
      catch(e) { toast(e.message, 'error') }
    }
    async function claimCoupon() {
      if(!claimCode.value) return; try { await API.claimCoupon(claimCode.value); toast('领取成功'); claimCode.value=''; loadMyCoupons() } catch(e){ toast(e.message,'error') }
    }

    async function startLotteryDraw(poolId) {
      if (!token.value) {
        toast('请先登录后参与抽奖', 'error')
        page.value = 'login'
        history.pushState(null, '', '/login')
        return
      }
      try {
        const result = await API.request('POST', '/api/lottery/draw', { pool_id: poolId, use_points: true })
        if (result.is_winner) {
          toast(`恭喜获得：${result.prize.name}！`, 'success')
        } else {
          toast('很遗憾，未中奖，再接再厉！', 'info')
        }
      } catch(e) {
        if (e.needLogin || e.status === 401) {
          toast('请先登录后参与抽奖', 'error')
          try { localStorage.removeItem('token') } catch(e) {}
          token.value = null
          page.value = 'login'
          history.pushState(null, '', '/login')
        } else {
          toast(e.message, 'error')
        }
      }
    }

    async function startEventPurchase(productId) {
      if (!token.value) {
        toast('请先登录后参与活动', 'error')
        page.value = 'login'
        history.pushState(null, '', '/login')
        return
      }
      try {
        const product = await API.request('GET', '/api/products/' + productId)
        if (product.product && product.product.type === 'timed') {
          toast('正在跳转购买...', 'info')
          viewProduct(product.product)
        } else {
          toast('商品不可购买', 'error')
        }
      } catch(e) {
        if (e.needLogin || e.status === 401) {
          toast('请先登录后参与活动', 'error')
          try { localStorage.removeItem('token') } catch(e) {}
          token.value = null
          page.value = 'login'
          history.pushState(null, '', '/login')
        } else {
          toast(e.message, 'error')
        }
      }
    }

    watch(page, (p) => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      if (p !== 'detail') { stopAutoSlide(); stopVideo(); }
      if (p === 'home' || p === 'lottery') loadProducts()
      if (p === 'events') loadEvents()
      if (p === 'featured') loadProducts(1)
      if (p === 'products') { loadProducts(); loadCategories() }
      if (p === 'orders') loadOrders()
      if (p === 'profile') { loadUC(); loadMyCoupons(); loadUCOrders(); loadRechargeRecords(); loadPayMethods() }
      if (p === 'admin') { loadAllOrders(); loadCoupons(); loadCategories(); loadProducts(); loadUsers() }
    })

    watch(detailMediaIdx, () => {
      stopAutoSlide();
      nextTick(() => { startAutoSlide(); });
    })

    watch(token, () => { if(token.value){ loadProfile(); loadOrders(); loadMyCoupons() } })

    window.addEventListener('popstate', initRoute)

    onMounted(() => {
      document.addEventListener('click', handleFirstInteraction, { once: true });
      initRoute()
      if (page.value !== 'detail') {
        checkSetup()
        loadConfig()
        loadProducts()
        loadCategories()
        loadProfile()
        loadCaptcha()
      }
      initParticles()
      window.addEventListener('scroll', () => { scrolled.value = window.scrollY > 50 })
    })

    function initParticles(theme) {
      theme = theme || window._initialTheme || 'cyberpunk'
      const canvas = document.getElementById('particle-canvas')
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      let w, h, particles = [], animationId
      
      function getParticleConfig(t) {
        switch(t) {
          case 'simple': return { count:40, minR:3, maxR:6, speed:0.3, color:'rgba(59,130,246,1)', lineDist:120, attract:true }
          case 'cute': return { count:30, minR:8, maxR:15, speed:0.2, color:'rgba(255,105,180,1)', lineDist:100, attract:false, hearts:true }
          case 'anime': return { count:50, minR:2, maxR:5, speed:0.4, color:'rgba(255,107,157,1)', lineDist:100, attract:false }
          default: return { count:80, minR:0.5, maxR:2.5, speed:0.5, color:'rgba(0,240,255,1)', lineDist:150, attract:false }
        }
      }
      
      const config = getParticleConfig(theme)
      const resize = () => { w=canvas.width=window.innerWidth; h=canvas.height=window.innerHeight }
      resize(); window.addEventListener('resize', resize)
      
      for(let i=0;i<config.count;i++) {
        particles.push({
          x:Math.random()*w, y:Math.random()*h,
          vx:(Math.random()-0.5)*config.speed, vy:(Math.random()-0.5)*config.speed,
          r:Math.random()*(config.maxR-config.minR)+config.minR,
          alpha:Math.random()*0.5+0.3, heart:config.hearts?Math.random()>0.5:false
        })
      }
      
      function drawHeart(x,y,r,color,alpha) {
        ctx.save(); ctx.translate(x,y); ctx.fillStyle = color.replace('1)',alpha+')');
        ctx.beginPath();
        ctx.moveTo(0,r*0.3);
        ctx.bezierCurveTo(-r*0.5,-r*0.3,-r,r*0.1,-r*0.5,r*0.6);
        ctx.bezierCurveTo(-r*0.2,r*r*0.8,r*0.2,r*r*0.8,r*0.5,r*0.6);
        ctx.bezierCurveTo(r,r*0.1,r*0.5,-r*0.3,0,r*0.3);
        ctx.fill(); ctx.restore();
      }
      
      function draw() {
        if (animationId) cancelAnimationFrame(animationId)
        ctx.clearRect(0,0,w,h)
        
        for(const p of particles){ 
          p.x+=p.vx; p.y+=p.vy; 
          if(p.x<0)p.x=w; if(p.x>w)p.x=0; if(p.y<0)p.y=h; if(p.y>h)p.y=0; 
          
          if(config.hearts && p.heart) {
            drawHeart(p.x,p.y,p.r,config.color,p.alpha)
          } else {
            ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); 
            ctx.fillStyle = config.color.replace('1)',p.alpha+')'); ctx.fill();
            ctx.shadowBlur=10; ctx.shadowColor=config.color; ctx.shadowBlur=0;
          }
        }
        
        for(let i=0;i<particles.length;i++) for(let j=i+1;j<particles.length;j++){ 
          const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y, dist=Math.sqrt(dx*dx+dy*dy); 
          if(dist<config.lineDist){ 
            const alpha=0.15*(1-dist/config.lineDist)
            ctx.beginPath(); ctx.moveTo(particles[i].x,particles[i].y); ctx.lineTo(particles[j].x,particles[j].y); 
            ctx.strokeStyle = config.color.replace('1)',alpha+')');
            ctx.lineWidth=1; ctx.stroke();
            
            if(config.attract) {
              const force = (config.lineDist - dist)/config.lineDist * 0.01
              particles[i].vx += dx*force; particles[i].vy += dy*force
              particles[j].vx -= dx*force; particles[j].vy -= dy*force
            }
          }
        }
        animationId = requestAnimationFrame(draw)
      }
      draw()
    }

    return {
      page, scrolled, menuOpen, isReg, token, toasts,
      setupRequired, setupUser, setupPass, setupEmail, setupErr, adminView,
      products, categories, orders, allOrders, coupons, myCoupons, cardKeys, reviews,
      user, detail, detailMediaList, detailMediaIdx, detailVideoRef, videoThumbnails, getVideoThumb, handleVideoLoaded, currentVideoSrc, prevMedia, nextMedia, selectMedia, pauseAutoSlide, resumeAutoSlide, isVideoUrl, lastOrder, search, catFilter, typeFilter,
      authUser, authPass, authEmail, authErr, captchaKey, captchaImage, captchaCode,
      adminTab, adminMenu, showProductForm, editingProduct, prodForm,
      catForm, couponForm, keysInput, keyProductID, claimCode, buyQty,
      filtered, lotteryProducts, timedProducts, countdown,
      ucData, ucTab, ucOrders, orderFilter, orderStatuses, profileForm, pwForm, pwErr, ucTabs,
      loadUC, loadUCOrders, updateProfile, changePw, doRecharge, rechargeAmt, rechargePayMethod, availablePayMethods, loadPayMethods, doUpgrade, showUpgrade, upgradeAmt,
      levelRequirements, nextLevel,
      users, adminMenu, showCouponForm, showCatForm, settings, saveSettings,
      navigate, initSetup, toggleAdminView,
      toast, copy, statusText, formatDate,
      loadProducts, loadCategories, loadOrders, loadAllOrders, loadCoupons, loadConfig,
      loadProfile, loadMyCoupons, loadCardKeys, loadReviews, loadUsers, loadCaptcha, loadEvents, loadRechargeRecords, loadPayMethods,
      rechargeRecords, poolProduct, poolModal, currentPool,
      doLogin, doReg, logout, goProfile, viewProduct, checkout,
      saveProduct, editProduct, deleteProduct, selectProductForKeys, selectProductForPool,
      importKeys, createCoupon, deleteCoupon, createCategory, deleteCategory, claimCoupon,
      initParticles,
      startLotteryDraw,
      startEventPurchase,
      checkSetup,
      config,
      showService,
      eventSettings, eventProducts,
      showPayModal, payPreview, selectedPayMethod, selectedCouponId,
      promoCodeInput, promoMsg, promoMsgType, paySubmitting,
      selectCoupon, applyPromoCode, confirmPay,
      showConfirmModal, confirmMessage, confirmResolveFn
    }
  }
})

app.mount('#app')
