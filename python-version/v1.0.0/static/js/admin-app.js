
const{createApp,ref,computed,watch,onMounted}=Vue

function getCookie(name){
  const v=document.cookie.match('(^|; )'+name+'=([^;]*)');
  return v?decodeURIComponent(v[2]):null
}

const LS_TOKEN = (()=>{try{return localStorage.getItem('admin_token')||localStorage.getItem('token')}catch(e){return null}})()
const COOKIE_TOKEN = getCookie('admin_token')

createApp({
setup(){
const token=ref(LS_TOKEN||COOKIE_TOKEN||'')
const msg=ref('验证中...'),tb=ref('db'),un=ref(''),ts=ref([]),rd=ref(false),ready=ref(true)

function tst(m,ty){ts.value.push({id:Date.now(),msg:m,ty});setTimeout(()=>ts.value.splice(0,1),3000)}

const showConfirmModal=ref(false),confirmMessage=ref('')
let confirmResolve=null
function confirmAsync(msg){showConfirmModal.value=true;confirmMessage.value=msg;return new Promise(r=>{confirmResolve=r})}
function confirmResolveFn(v){showConfirmModal.value=false;if(confirmResolve)confirmResolve(v);confirmResolve=null}

const api={
  tk:token.value,
  async rq(m,p,b){
    const h={'Content-Type':'application/json'}
    if(this.tk)h['Authorization']='Bearer '+this.tk
    const r=await fetch(p,{method:m,headers:h,body:b?JSON.stringify(b):undefined})
    if(r.status==401){
      try{localStorage.removeItem('admin_token')}catch(e){}
      document.cookie='admin_token=;path=/;max-age=0'
      window.location.href='/admin-login?msg='+encodeURIComponent('登录已失效，请重新登录')
      throw new Error('登录已过期')
    }
    if(r.status==403){
      try{localStorage.removeItem('admin_token')}catch(e){}
      document.cookie='admin_token=;path=/;max-age=0'
      window.location.href='/admin-login?msg='+encodeURIComponent('没有管理员权限')
      throw new Error('没有权限')
    }
    const d=await r.json()
    if(!r.ok)throw new Error(d.detail||d.error||'请求失败')
    return d
  }
}
function initParticles(theme='cyberpunk'){
  const canvas=document.getElementById('particle-canvas')
  if(!canvas)return
  const ctx=canvas.getContext('2d')
  let w,h,particles=[],animationId
  const resize=()=>{w=canvas.width=window.innerWidth;h=canvas.height=window.innerHeight}
  resize();window.addEventListener('resize',resize)
  
  function getParticleConfig(t){
    switch(t){
      case'simple':return{count:40,minR:3,maxR:6,speed:0.3,color:'rgba(59,130,246,1)',lineDist:120,attract:true}
      case'cute':return{count:30,minR:8,maxR:15,speed:0.2,color:'rgba(255,105,180,1)',lineDist:100,attract:false,hearts:true}
      case'anime':return{count:50,minR:2,maxR:5,speed:0.4,color:'rgba(255,107,157,1)',lineDist:100,attract:false}
      default:return{count:80,minR:0.5,maxR:2.5,speed:0.5,color:'rgba(0,240,255,1)',lineDist:150,attract:false}
    }
  }
  
  const config=getParticleConfig(theme)
  for(let i=0;i<config.count;i++){
    particles.push({
      x:Math.random()*w,y:Math.random()*h,
      vx:(Math.random()-0.5)*config.speed,vy:(Math.random()-0.5)*config.speed,
      r:Math.random()*(config.maxR-config.minR)+config.minR,
      alpha:Math.random()*0.5+0.3,heart:config.hearts?Math.random()>0.5:false
    })
  }
  
  function drawHeart(x,y,r,color,alpha){
    ctx.save();ctx.translate(x,y);ctx.fillStyle=color.replace('1)',alpha+')');
    ctx.beginPath();
    ctx.moveTo(0,r*0.3);
    ctx.bezierCurveTo(-r*0.5,-r*0.3,-r,r*0.1,-r*0.5,r*0.6);
    ctx.bezierCurveTo(-r*0.2,r*r*0.8,r*0.2,r*r*0.8,r*0.5,r*0.6);
    ctx.bezierCurveTo(r,r*0.1,r*0.5,-r*0.3,0,r*0.3);
    ctx.fill();ctx.restore();
  }
  
  function draw(){
    if(animationId)cancelAnimationFrame(animationId)
    ctx.clearRect(0,0,w,h)
    
    for(const p of particles){
      p.x+=p.vx;p.y+=p.vy
      if(p.x<0)p.x=w;if(p.x>w)p.x=0
      if(p.y<0)p.y=h;if(p.y>h)p.y=0
      
      if(config.hearts&&p.heart){
        drawHeart(p.x,p.y,p.r,config.color,p.alpha)
      }else{
        ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2)
        ctx.fillStyle=config.color.replace('1)',p.alpha+')');ctx.fill()
        ctx.shadowBlur=10;ctx.shadowColor=config.color;ctx.shadowBlur=0
      }
    }
    
    for(let i=0;i<particles.length;i++)
      for(let j=i+1;j<particles.length;j++){
        const dx=particles[i].x-particles[j].x,dy=particles[i].y-particles[j].y,dist=Math.sqrt(dx*dx+dy*dy)
        if(dist<config.lineDist){
          const alpha=0.15*(1-dist/config.lineDist)
          ctx.beginPath();ctx.moveTo(particles[i].x,particles[i].y);ctx.lineTo(particles[j].x,particles[j].y)
          ctx.strokeStyle=config.color.replace('1)',alpha+')');ctx.lineWidth=1;ctx.stroke()
          
          if(config.attract){
            const force=(config.lineDist-dist)/config.lineDist*0.01
            particles[i].vx+=dx*force;particles[i].vy+=dy*force
            particles[j].vx-=dx*force;particles[j].vy-=dy*force
          }
        }
      }
    animationId=requestAnimationFrame(draw)
  }
  draw()
}
// 先从window._initialTheme获取（由内联脚本设置）
const currentTheme=ref(window._initialTheme||'cyberpunk')
initParticles(currentTheme.value)

function applyTheme(theme){
  document.body.className='';
  if(theme!=='cyberpunk')document.body.classList.add('theme-'+theme);
  localStorage.setItem('adminTheme',theme);
}

// 保存主题到后端
let savingTheme=false
async function changeTheme(theme){
  if(savingTheme)return
  savingTheme=true
  currentTheme.value=theme
  document.body.className=''
  if(theme!=='cyberpunk')document.body.classList.add('theme-'+theme)
  initParticles(theme)
  // 保存到后端
  try{
    const h={'Content-Type':'application/json'}
    if(token.value)h['Authorization']='Bearer '+token.value
    await fetch('/api/admin/site/theme',{
      method:'POST',
      headers:h,
      body:JSON.stringify({theme:theme})
    })
    tst('主题保存成功','ok')
  }catch(e){
    tst('保存失败: '+e.message,'er')
  }
  savingTheme=false
}
const ps=ref([]),or=ref([]),us=ref([]),cs=ref([]),ct=ref([]),ks=ref([]),da=ref({})
const kp=ref(0),kt=ref(''),spf=ref(false),eid=ref(0),pf=ref({name:'',description:'',price:0,category_id:0,type:'normal',delivery_type:'card_key'})
const showProductModal=ref(false),editingProduct=ref(null)
const productForm=ref({
  name:'',short_description:'',description:'',content:'',
  price:0,original_price:null,cost_price:null,discount:0,
  discount_price:null,discount_start:'',discount_end:'',
  category_id:0,image_url:'',images:'',video_url:'',
  imageList:[],
  featured:false,is_hot:false,is_new:false,is_recommend:false,is_seckill:false,
  type:'normal',stock:-1,stock_warning:10,total_stock:0,max_buy_limit:0,per_user_limit:0,
  delivery_type:'card_key',file_path:'',file_name:'',file_size:'',auto_delivery_content:'',
  is_active:true,sort_order:0,seo_title:'',seo_keywords:'',seo_description:'',
  tags:'',buy_notice:'',after_sale_notice:'',allow_comments:true
})
const refreshingStock=ref(false),stockUpdateTime=ref({}),stockPollInterval=ref(null)
const showRestockModal=ref(false),restockProduct=ref(null),restockKeys=ref(''),quickGenerateCount=ref(100)
const productFiles=ref([])
const imageFileInput=ref(null)
const recommends=ref([])
const showAddProductModal=ref(false),currentRecommendCategory=ref(null)
const eventProducts=ref([]),showEventProductModal=ref(false),editingEventProduct=ref(null)
const eventProductForm=ref({
  name:'',description:'',price:0,original_price:null,discount_price:null,
  start_at:'',end_at:'',image_url:'',imageList:[],sort_order:0,stock:-1,is_active:true
})
const eventImageFileInput=ref(null)
function openProductModal(p=null){
  productFiles.value=[];
  if(p){
    editingProduct.value=p.id;
    const urls=[];
    if(p.image_url)urls.push(p.image_url);
    if(p.images){
      const more=(typeof p.images==='string'?p.images.split(','):p.images).filter(u=>u.trim());
      more.forEach(u=>{if(!urls.includes(u))urls.push(u)});
    }
    productForm.value={
      name:p.name||'',short_description:p.short_description||'',description:p.description||'',content:p.content||'',
      price:p.price||0,original_price:p.original_price,cost_price:p.cost_price,discount:p.discount||0,
      discount_price:p.discount_price,discount_start:p.discount_start||'',discount_end:p.discount_end||'',
      category_id:p.category_id||0,image_url:p.image_url||'',images:p.images||'',video_url:p.video_url||'',
      imageList:urls,
      featured:p.featured||false,is_hot:p.is_hot||false,is_new:p.is_new||false,is_recommend:p.is_recommend||false,is_seckill:p.is_seckill||false,
      type:p.type||'normal',stock:p.stock||-1,stock_warning:p.stock_warning||10,total_stock:p.total_stock||0,max_buy_limit:p.max_buy_limit||0,per_user_limit:p.per_user_limit||0,
      delivery_type:p.delivery_type||'card_key',file_path:p.file_path||'',file_name:p.file_name||'',file_size:p.file_size||'',auto_delivery_content:p.auto_delivery_content||'',
      is_active:p.is_active!==false,sort_order:p.sort_order||0,seo_title:p.seo_title||'',seo_keywords:p.seo_keywords||'',seo_description:p.seo_description||'',
      tags:p.tags||'',buy_notice:p.buy_notice||'',after_sale_notice:p.after_sale_notice||'',allow_comments:p.allow_comments!==false
    };
    if(p.id)loadProductFiles(p.id);
  }else{
    editingProduct.value=null;
    productForm.value={
      name:'',short_description:'',description:'',content:'',
      price:0,original_price:null,cost_price:null,discount:0,
      discount_price:null,discount_start:'',discount_end:'',
      category_id:0,image_url:'',images:'',video_url:'',
      imageList:[],
      featured:false,is_hot:false,is_new:false,is_recommend:false,is_seckill:false,
      type:'normal',stock:-1,stock_warning:10,total_stock:0,max_buy_limit:0,per_user_limit:0,
      delivery_type:'card_key',file_path:'',file_name:'',file_size:'',auto_delivery_content:'',
      is_active:true,sort_order:0,seo_title:'',seo_keywords:'',seo_description:'',
      tags:'',buy_notice:'',after_sale_notice:'',allow_comments:true
    }
  }
  showProductModal.value=true
}
async function loadProductFiles(pid){
  try{
    const files=await api.rq('GET','/api/admin/products/'+pid+'/files');
    productFiles.value=files||[];
  }catch(e){
    console.error(e);
  }
}
async function handleFileUpload(event){
  if(!editingProduct.value){tst('请先保存商品后再上传文件','er');return;}
  const files=event.target.files;
  if(!files.length)return;
  for(let i=0;i<files.length;i++){
    const file=files[i];
    const formData=new FormData();
    formData.append('file',file);
    try{
      const h={}
      if(token.value)h['Authorization']='Bearer '+token.value
      const res=await fetch('/api/admin/products/'+editingProduct.value+'/files',{
        method:'POST',
        headers:h,
        body:formData
      });
      const data=await res.json();
      if(data.list)productFiles.value=data.list;
      tst('文件上传成功','ok');
    }catch(e){
      tst('文件上传失败: '+e.message,'er');
    }
  }
}
function removeProductFile(idx){
  if(!editingProduct.value)return;
  const file=productFiles.value[idx];
  if(!file.id)return;
  api.rq('DELETE','/api/admin/products/'+editingProduct.value+'/files/'+file.id).then(()=>{
    productFiles.value.splice(idx,1);
    tst('文件已删除','ok');
  }).catch(e=>tst(e.message,'er'));
}
function triggerImageUpload(){imageFileInput.value?.click()}
async function handleImageUpload(e){
  const files=e.target.files;
  if(!files.length)return;
  for(const file of files){
    const fd=new FormData();
    fd.append('file',file);
    fd.append('file_type','product_image');
    try{
      const h={};
      if(token.value)h['Authorization']='Bearer '+token.value;
      const r=await fetch('/api/admin/upload',{method:'POST',headers:h,body:fd});
      const d=await r.json();
      if(!r.ok) throw new Error(d.detail||'上传失败');
      productForm.value.imageList.push(d.url);
      tst('图片上传成功','ok');
    }catch(e){tst(e.message,'er')}
  }
  e.target.value='';
}
function removeProductImage(idx){productForm.value.imageList.splice(idx,1)}
function triggerEventImageUpload(){eventImageFileInput.value?.click()}
async function handleEventImageUpload(e){
  const files=e.target.files;
  if(!files.length)return;
  for(const file of files){
    const fd=new FormData();
    fd.append('file',file);
    fd.append('file_type','product_image');
    try{
      const h={};
      if(token.value)h['Authorization']='Bearer '+token.value;
      const r=await fetch('/api/admin/upload',{method:'POST',headers:h,body:fd});
      const d=await r.json();
      if(!r.ok) throw new Error(d.detail||'上传失败');
      eventProductForm.value.imageList.push(d.url);
      tst('图片上传成功','ok');
    }catch(e){tst(e.message,'er')}
  }
  e.target.value='';
}
function removeEventImage(idx){eventProductForm.value.imageList.splice(idx,1)}
function compressFiles(){
  if(!editingProduct.value){tst('请先保存商品','er');return;}
  if(productFiles.value.length===0){tst('请先上传文件','er');return;}
  api.rq('POST','/api/admin/products/'+editingProduct.value+'/compress').then(d=>{
    productForm.value.file_path=d.zip_path;
    productForm.value.file_name=d.file_name;
    productForm.value.file_size=d.file_size;
    tst('压缩包生成成功','ok');
  }).catch(e=>tst(e.message,'er'));
}
function addRecommendCategory(){
  recommends.value.push({id:null,category_name:'',category_id:0,product_ids:[],products:[],sort_order:0});
}
async function saveRecommend(rc){
  try{
    const data={id:rc.id,category_name:rc.category_name,category_id:rc.category_id,product_ids:rc.product_ids,sort_order:rc.sort_order};
    const res=await api.rq('POST','/api/admin/recommends',data);
    if(!rc.id&&res.id)rc.id=res.id;
    tst('保存成功','ok');
    loadRecommends();
  }catch(e){tst(e.message,'er');}
}
async function deleteRecommend(id){
  if(!id){
    const idx=recommends.value.findIndex(r=>r.id===id);
    if(idx>-1)recommends.value.splice(idx,1);
    return;
  }
  if(!(await confirmAsync('确定删除此推荐分类？')))return;
  try{
    await api.rq('DELETE','/api/admin/recommends/'+id);
    const idx=recommends.value.findIndex(r=>r.id===id);
    if(idx>-1)recommends.value.splice(idx,1);
    tst('删除成功','ok');
  }catch(e){tst(e.message,'er');}
}
function toggleProductInRecommend(rc,productId){
  if(!rc.product_ids)rc.product_ids=[];
  const idx=rc.product_ids.indexOf(productId);
  if(idx>-1)rc.product_ids.splice(idx,1);
  else rc.product_ids.push(productId);
}
function openAddProductModal(rc){
  currentRecommendCategory.value=rc;
  showAddProductModal.value=true;
}
async function loadRecommends(){
  try{
    const data=await api.rq('GET','/api/admin/recommends');
    recommends.value=data||[];
  }catch(e){console.error(e);}
}
function closeProductModal(){showProductModal.value=false;editingProduct.value=null}
function saveProduct(){const d=productForm.value;if(!d.name){tst('请输入商品名称','er');return}if(d.price<=0){tst('请输入有效的价格','er');return}d.image_url=d.imageList[0]||'';d.images=d.imageList.join(',');const fn=editingProduct.value?api.rq('PUT','/api/admin/products/'+editingProduct.value,d):api.rq('POST','/api/admin/products',d);fn.then(()=>{closeProductModal();api.rq('GET','/api/products').then(r=>ps.value=r.products||[]);tst(editingProduct.value?'商品已更新':'商品已创建','ok')}).catch(e=>tst(e.message,'er'))}
async function deleteProduct(){if(!editingProduct.value)return;if(!(await confirmAsync('确定删除此商品？此操作不可恢复！')))return;api.rq('DELETE','/api/admin/products/'+editingProduct.value).then(()=>{closeProductModal();api.rq('GET','/api/products').then(r=>ps.value=r.products||[]);tst('商品已删除','ok')}).catch(e=>tst(e.message,'er'))}
function getStockClass(p){const available=p.available_stock||0;const total=p.total_stock||0;const warning=p.stock_warning||10;if(available===0)return'empty';if(total>0&&available<=total*0.2)return'low';if(available<=warning)return'low';return'high'}
function getStockStatus(p){const available=p.available_stock||0;const total=p.total_stock||0;const warning=p.stock_warning||10;if(available===0)return'empty';if(total>0&&available<=total*0.2)return'low';if(available<=warning)return'low';return'available'}
function getStockText(p){const available=p.available_stock||0;const total=p.total_stock||0;const warning=p.stock_warning||10;if(available===0)return'已售罄';if(total>0&&available<=total*0.2)return'库存紧张';if(available<=warning)return'库存紧张';return'有货'}
function refreshAllStocks(){if(refreshingStock.value)return;refreshingStock.value=true;api.rq('GET','/api/products').then(r=>{const oldStocks={};ps.value.forEach(p=>oldStocks[p.id]=p.available_stock);ps.value=r.products||[];ps.value.forEach(p=>{if(oldStocks[p.id]!==undefined&&oldStocks[p.id]!==p.available_stock){stockUpdateTime.value[p.id]=Date.now();setTimeout(()=>{delete stockUpdateTime.value[p.id]},1000)}});refreshingStock.value=false}).catch(()=>{refreshingStock.value=false})}
function startStockPolling(){if(stockPollInterval.value)return;stockPollInterval.value=setInterval(()=>{if(tb.value==='pd'&&!showProductModal.value&&!showRestockModal.value){refreshAllStocks()}},5000)}
function stopStockPolling(){if(stockPollInterval.value){clearInterval(stockPollInterval.value);stockPollInterval.value=null}}
function openRestockModal(p){restockProduct.value=p;restockKeys.value='';quickGenerateCount.value=100;showRestockModal.value=true}
function closeRestockModal(){showRestockModal.value=false;restockProduct.value=null;restockKeys.value=''}
function getKeyCount(){if(!restockKeys.value)return 0;return restockKeys.value.split('\n').filter(k=>k.trim()).length}
function generateKey(){const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';let key='';for(let i=0;i<4;i++){if(i>0)key+='-';for(let j=0;j<4;j++){key+=chars.charAt(Math.floor(Math.random()*chars.length))}}return key}
function generateKeys(count){let keys=[];for(let i=0;i<count;i++){keys.push(generateKey())}return keys}
function generateQuickKeys(){const count=quickGenerateCount.value||100;const keys=generateKeys(count);restockKeys.value=(restockKeys.value?restockKeys.value+'\n':'')+keys.join('\n')}
function generateAndAddKeys(count){const keys=generateKeys(count);restockKeys.value=(restockKeys.value?restockKeys.value+'\n':'')+keys.join('\n')}
function confirmRestock(){if(!restockProduct.value){tst('请选择商品','er');return}let keys=[];if(restockKeys.value.trim()){keys=restockKeys.value.split('\n').filter(k=>k.trim())}if(keys.length===0){tst('请输入卡密或使用快速生成','er');return}const data={product_id:restockProduct.value.id,keys:restockKeys.value};api.rq('POST','/api/admin/cardkeys/import',data).then(()=>{closeRestockModal();refreshAllStocks();tst(`成功添加 ${keys.length} 个卡密`,'ok')}).catch(e=>tst(e.message,'er'))}

const sco=ref(false),scf=ref(false),cpc=ref({code:'',coupon_id:0,remark:'',max_uses:0,expires_at:''}),cf=ref({name:'',sort_order:0}),promoCodes=ref([]),coupons=ref([]),showAddCoupon=ref(false),newCoupon=ref({name:'',type:'percentage',value:0,min_amount:0,total_count:0,expires_at:''})
const coTab=ref('promo')
const newPromo=ref({code:'',type:'percentage',value:0,min_amount:0,max_uses:0,expires_at:'',remark:''})
const newRedeem=ref({code:'',coupon_id:0,give_count:1,max_uses:0,expires_at:'',remark:''})
const inviteRecords=ref([])
const invSettings=ref({reward_new_user:0,reward_inviter:0,reward_coupon:0,reward_coupon_count:1})
const couponRules=ref([])
const showAddRule=ref(false)
const newRule=ref({name:'',type:'register',coupon_id:0,give_count:1,product_id:0,category_id:0,min_order_amount:0,enabled:true})
const edRuleId=ref(0)
const open=ref({st_basic:true,st_theme:false,lt_basic:true,ev_basic:true,st_email:false,st_sms:false,st_pay:false,st_points:false,st_shop:false,py_alipay:false,py_wxpay:false,py_mazf:false,py_yishoumi:false,py_usdt:false,py_qqpay:false})
function toggle(k){open.value[k]=!open.value[k]}
function toggleAccordion(key){
  // 手风琴效果：只展开当前项，收起其他项
  Object.keys(open.value).forEach(k => {
    if(k.startsWith('st_') || k.startsWith('lt_') || k.startsWith('ev_') || k.startsWith('py_')){
      if(k === key){
        open.value[k] = true
      } else {
        open.value[k] = false
      }
    }
  })
}
const st=ref({shop_name:'',title:'',notice:'',keywords:'',description:'',logo:'',background_url:'',background_mobile_url:'',service_qq:'',service_wechat:'',service_email:'',qrcode1_title:'',qrcode1_url:'',qrcode2_title:'',qrcode2_url:'',register_type:'username',forget_type:'email',session_expire:86400,admin_session_expire:30,username_min_len:3,allow_register:true,login_captcha:false,register_captcha:false,trade_captcha:false,register_verification:false,email_smtp:'',email_port:465,email_secure:'ssl',email_username:'',email_password:'',sms_platform:'aliyun',sms_access_key_id:'',sms_access_key_secret:'',sms_sign_name:'',sms_template_code:'',sms_secret_id:'',sms_secret_key:'',sms_sdk_app_id:'',sms_template_id:'',sms_dxbao_username:'',sms_dxbao_password:'',sms_dxbao_template:'',default_category:'0',commodity_recommend:false,commodity_name:'推荐',pay_wx:true,pay_alipay:true,pay_mazf:false,mazf_mch_id:'',mazf_key:'',pay_yishoumi:false,yishoumi_app_id:'',yishoumi_app_key:'',yishoumi_notify_url:'',pay_usdt:false,pay_qq:false,recharge_min:10,recharge_max:5000,recharge_welfare:false,recharge_bonus:0,points_per_yuan:1,shop_closed:false,maintenance_mode:false,closed_message:'',order_timeout:30,auto_receive_days:7,email_notify:false,sms_notify:false})
const lt=ref({enabled:true,show_odds:true,anti_cheat:true,price:1,free_daily:0,points_cost:0,points_threshold:0,pool:[],pity_enabled:false,pity_count:100,pity_product_id:0,pity_odds:100})
const ev=ref({enabled:false,banner_title:'',banner_desc:'',show_progress:true,show_countdown:true})
const pay=ref({
  alipay:{enabled:false,app_id:'',private_key:''},
  wxpay:{enabled:false,mch_id:'',key:''},
  mazf:{enabled:false,mch_id:'',key:''},
  yishoumi:{enabled:false,app_id:'',app_key:'',notify_url:''},
  usdt:{enabled:false,address:''},
  qqpay:{enabled:false,mch_id:'',key:''}
})
const rechargeRecords=ref([])
const me=[
  {k:'div0',i:'',l:'数据概览',divider:true},
  {k:'db',i:'fas fa-chart-pie',l:'概览'},
  {k:'div1',i:'',l:'商品管理',divider:true},
  {k:'pd',i:'fas fa-box',l:'商品列表'},
  {k:'ct',i:'fas fa-folder',l:'分类管理'},
  {k:'ke',i:'fas fa-key',l:'卡密管理'},
  {k:'div2',i:'',l:'订单用户',divider:true},
  {k:'or',i:'fas fa-list',l:'订单管理'},
  {k:'us',i:'fas fa-users',l:'用户管理'},
  {k:'div3',i:'',l:'营销推广',divider:true},
  {k:'rc',i:'fas fa-star',l:'推荐商品'},
  {k:'cp',i:'fas fa-gift',l:'优惠券'},
  {k:'cr',i:'fas fa-magic',l:'优惠券规则'},
  {k:'co',i:'fas fa-ticket-alt',l:'优惠码/兑换码'},
  {k:'inv',i:'fas fa-user-plus',l:'邀请码'},
  {k:'ev',i:'fas fa-bullhorn',l:'活动'},
  {k:'lt',i:'fas fa-dice',l:'抽奖'},
  {k:'div4',i:'',l:'系统配置',divider:true},
  {k:'py',i:'fas fa-credit-card',l:'支付配置'},
  {k:'st',i:'fas fa-cog',l:'系统设置'}
]
const al=computed(()=>me.find(m=>m.k===tb.value)?.l||'')
const charts=ref({daily:[],monthly:[]})
const maxDaily=computed(()=>{const a=charts.value.daily;if(!a.length)return 1;const m=Math.max(...a.map(d=>d.income));return m||1})
const maxMonthly=computed(()=>{const a=charts.value.monthly;if(!a.length)return 1;const m=Math.max(...a.map(m=>m.income));return m||1})
async function ld(){
  if(!token.value){
    msg.value='请先登录'
    setTimeout(()=>window.location.href='/admin-login?msg='+encodeURIComponent('请先登录'),1500)
    return
  }
  try{
    const pr=await api.rq('GET','/api/profile')
    if(!pr.is_admin){
      msg.value='您不是管理员'
      try{localStorage.removeItem('admin_token')}catch(e){}
      document.cookie='admin_token=;path=/;max-age=0'
      setTimeout(()=>window.location.href='/',3000)
      return
    }
    un.value=pr.username||''
    // 逐个加载数据，单个失败不影响其他
    const loadAll=async()=>{
      try{const r=await api.rq('GET','/api/products');ps.value=r.products||[]}catch(e){}
      try{const r=await api.rq('GET','/api/admin/orders');or.value=r.orders||r||[]}catch(e){}
      try{const r=await api.rq('GET','/api/admin/users');us.value=r.users||r||[]}catch(e){}
      try{cs.value=await api.rq('GET','/api/admin/coupons')}catch(e){}
      try{ct.value=await api.rq('GET','/api/categories')}catch(e){}
    }
    // 异步加载数据，不阻塞页面渲染
    loadAll()
    api.rq('GET','/api/admin/dashboard?period=0').then(d=>da.value=d).catch(()=>{})
    api.rq('GET','/api/admin/dashboard/charts').then(d=>charts.value=d).catch(()=>{})
    api.rq('GET','/api/admin/config').then(d=>{if(d.config)st.value={...st.value,...d.config}}).catch(()=>{})
    api.rq('GET','/api/admin/lottery').then(d=>{if(d.settings)lt.value={...lt.value,...d.settings}}).catch(()=>{})
    api.rq('GET','/api/admin/events').then(d=>{if(d.settings)ev.value={...ev.value,...d.settings};if(d.products)eventProducts.value=d.products}).catch(()=>{})
    api.rq('GET','/api/admin/payment').then(d=>{if(d.payment)pay.value={...pay.value,...d.payment}}).catch(()=>{})
    api.rq('GET','/api/admin/recharges').then(d=>rechargeRecords.value=d.records||[]).catch(()=>{})
    loadCoupons()
    loadPromoCodes()
    loadInviteSettings()
    loadInviteRecords()
    loadCouponRules()
    ready.value=true
    applyTheme(currentTheme.value)
  }catch(e){
    if(e.message=='没有权限'){
      msg.value='您不是管理员'
      setTimeout(()=>window.location.href='/admin-login?msg='+encodeURIComponent('没有管理员权限'),3000)
    }else if(e.message=='登录已过期'){
      return
    }else{
      msg.value='加载失败: '+e.message
      setTimeout(()=>window.location.href='/admin-login?msg='+encodeURIComponent('登录已失效，请重新登录'),3000)
    }
  }
}
const appLoadEl=document.getElementById('app-loading')
onMounted(()=>{if(appLoadEl)appLoadEl.style.display='none'})
// 延迟加载数据，让界面先渲染
setTimeout(() => ld(), 200)
watch(()=>tb.value,(newVal)=>{if(newVal==='pd'){startStockPolling()}else{stopStockPolling()}})
const stockUpdateWatcher=computed(()=>JSON.stringify(stockUpdateTime.value))
function svPd(){const d=pf.value;if(!d.name||!d.price){tst('请填写完整','er');return}
  const fn=eid.value?api.rq('PUT','/api/admin/products/'+eid.value,d):api.rq('POST','/api/admin/products',d)
  fn.then(()=>{spf.value=false;eid.value=0;pf.value={name:'',description:'',price:0,category_id:0,type:'normal',delivery_type:'card_key'};api.rq('GET','/api/products').then(d=>ps.value=d.products||[]);tst('已保存','ok')}).catch(e=>tst(e.message,'er'))}
function edPd(p){eid.value=p.id;pf.value={name:p.name,description:p.description||'',price:p.price,category_id:p.category_id,type:p.type,delivery_type:p.delivery_type||'card_key'};spf.value=true}
async function dlPd(id){if(!(await confirmAsync('确定删除？')))return;api.rq('DELETE','/api/admin/products/'+id).then(()=>{api.rq('GET','/api/products').then(d=>ps.value=d.products||[]);tst('已删除','ok')}).catch(e=>tst(e.message,'er'))}
function sk(p){kp.value=p.id;tb.value='ke';selectedKeys.value=[];loadCardKeys(p.id)}
function sp(p){const e=prompt('奖池(商品ID:概率%)每行:\n2:50\n3:30');if(!e)return;api.rq('PUT','/api/admin/products/'+p.id+'/blindbox',{entries:e.trim().split('\n').map(l=>{const[pid,prob]=l.split(':');return{prize_id:parseInt(pid),probability:parseFloat(prob)}})}).then(()=>tst('奖池已更新','ok')).catch(e=>tst(e.message,'er'))}
async function imK(){if(!kp.value)return;const d=await api.rq('POST','/api/admin/cardkeys/import',{product_id:kp.value,keys:kt.value});kt.value='';api.rq('GET','/api/admin/cardkeys?product_id='+kp.value).then(d=>ks.value=d);tst('已导入 '+d.count+' 条','ok')}
async function dlK(k){if(!(await confirmAsync('确定删除此卡密？')))return;api.rq('DELETE','/api/admin/cardkeys/'+k.id).then(()=>{ks.value=ks.value.filter(x=>x.id!==k.id);tst('已删除','ok')}).catch(e=>tst(e.message,'er'))}
async function completeOrder(o){if(!(await confirmAsync('确定将此订单标记为完成？')))return;api.rq('POST','/api/admin/orders/'+o.id+'/complete',{}).then(()=>{o.status='completed';tst('订单已完成','ok')}).catch(e=>tst(e.message,'er'))}
async function cancelOrder(o){if(!(await confirmAsync('确定取消此订单？')))return;api.rq('POST','/api/admin/orders/'+o.id+'/cancel',{}).then(()=>{o.status='cancelled';tst('订单已取消','ok')}).catch(e=>tst(e.message,'er'))}
async function toggleAdmin(u){var action=u.is_admin?'取消管理员权限':'设为管理员';if(!(await confirmAsync('确定要'+action+'？')))return;api.rq('PUT','/api/admin/users/'+u.id+'/toggle-admin',{}).then(function(d){u.is_admin=d.is_admin;tst('已更新','ok')}).catch(e=>tst(e.message,'er'))}
const orFilter=ref('')
const filteredOrders=computed(()=>{if(!orFilter.value)return or.value;return or.value.filter(function(o){return o.status===orFilter.value})})
function getCouponName(couponId){const c=coupons.value.find(x=>x.id===couponId);return c?c.name:'未选择'}
async function loadCoupons(){try{const d=await api.rq('GET','/api/admin/coupons');coupons.value=d||[]}catch(e){console.error(e)}}
async function addCoupon(){const d=newCoupon.value;if(!d.name){tst('请填写优惠券名称','er');return}if(!d.value){tst('请填写优惠值','er');return}try{await api.rq('POST','/api/admin/coupons',{...d,expires_at:d.expires_at?new Date(d.expires_at).toISOString():null});newCoupon.value={name:'',type:'percentage',value:0,min_amount:0,total_count:0,expires_at:''};showAddCoupon.value=false;loadCoupons();tst('优惠券已添加','ok')}catch(e){tst('添加失败: '+e.message,'er')}}
async function delCoupon(id){if(!(await confirmAsync('确定删除此优惠券？')))return;try{await api.rq('DELETE','/api/admin/coupons/'+id);loadCoupons();tst('已删除','ok')}catch(e){tst('删除失败: '+e.message,'er')}}
async function giveCoupon(coupon){const username=prompt('请输入用户名：');if(!username)return;try{await api.rq('POST','/api/admin/coupons/'+coupon.id+'/give',{username});tst('已发放给 '+username,'ok')}catch(e){tst('发放失败: '+e.message,'er')}}
function generatePromoCode(){const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';let code='';for(let i=0;i<12;i++){if(i>0&&i%4===0)code+='-';code+=chars.charAt(Math.floor(Math.random()*chars.length))}return code}
function copyPromoCode(code){navigator.clipboard.writeText(code).then(()=>tst('优惠码已复制','ok')).catch(()=>tst('复制失败','er'))}
async function loadPromoCodes(){try{const d=await api.rq('GET','/api/admin/promo-codes');promoCodes.value=d||[]}catch(e){console.error(e)}}
async function createPromoCode(){const d=newPromo.value;if(!d.value){tst('请填写优惠值','er');return}const code=d.code||generatePromoCode();await api.rq('POST','/api/admin/promo-codes',{code,type:d.type,value:d.value,min_amount:d.min_amount,max_uses:d.max_uses,expires_at:d.expires_at?new Date(d.expires_at).toISOString():null,remark:d.remark});newPromo.value={code:'',type:'percentage',value:0,min_amount:0,max_uses:0,expires_at:'',remark:''};loadPromoCodes();tst('优惠码已创建','ok')}
async function createRedeemCode(){const d=newRedeem.value;if(!d.coupon_id){tst('请选择关联优惠券','er');return}const code=d.code||generatePromoCode();await api.rq('POST','/api/admin/promo-codes',{code,coupon_id:d.coupon_id,give_count:d.give_count,max_uses:d.max_uses,expires_at:d.expires_at?new Date(d.expires_at).toISOString():null,remark:d.remark});newRedeem.value={code:'',coupon_id:0,give_count:1,max_uses:0,expires_at:'',remark:''};loadPromoCodes();tst('兑换码已创建','ok')}
async function dlCo(id){if(!(await confirmAsync('确定删除？')))return;api.rq('DELETE','/api/admin/promo-codes/'+id).then(()=>{loadPromoCodes();tst('已删除','ok')}).catch(e=>tst(e.message,'er'))}
async function loadInviteSettings(){try{const d=await api.rq('GET','/api/admin/invites/settings');if(d.settings)invSettings.value={...invSettings.value,...d.settings}}catch(e){console.error(e)}}
async function loadInviteRecords(){try{const d=await api.rq('GET','/api/admin/invites/records');inviteRecords.value=d||[]}catch(e){console.error(e)}}
async function saveInvSettings(){await api.rq('POST','/api/admin/invites/settings',invSettings.value);tst('设置已保存','ok')}
async function loadCouponRules(){try{const d=await api.rq('GET','/api/admin/coupon-rules');couponRules.value=d||[]}catch(e){console.error(e)}}
async function createRule(){const d=newRule.value;if(!d.name||!d.coupon_id){tst('请填写完整信息','er');return}try{await api.rq('POST','/api/admin/coupon-rules',d);newRule.value={name:'',type:'register',coupon_id:0,give_count:1,product_id:0,category_id:0,min_order_amount:0,enabled:true};showAddRule.value=false;loadCouponRules();tst('规则已创建','ok')}catch(e){tst('创建失败: '+e.message,'er')}}
async function updateRule(rule){try{await api.rq('PUT','/api/admin/coupon-rules/'+rule.id,{name:rule.name,type:rule.type,coupon_id:rule.coupon_id,give_count:rule.give_count,product_id:rule.product_id,category_id:rule.category_id,min_order_amount:rule.min_order_amount,enabled:rule.enabled});tst('规则已更新','ok')}catch(e){tst('更新失败: '+e.message,'er')}}
async function deleteRule(id){if(!(await confirmAsync('确定删除此规则？')))return;try{await api.rq('DELETE','/api/admin/coupon-rules/'+id);loadCouponRules();tst('已删除','ok')}catch(e){tst('删除失败: '+e.message,'er')}}
async function mkCo(){const d=cpc.value;if(!d.coupon_id){tst('请选择关联优惠券','er');return}const code=d.code||generatePromoCode();await api.rq('POST','/api/admin/promo-codes',{code,coupon_id:d.coupon_id,remark:d.remark,max_uses:d.max_uses,expires_at:d.expires_at?new Date(d.expires_at).toISOString():null});cpc.value={code:'',coupon_id:0,remark:'',max_uses:0,expires_at:''};loadPromoCodes();tst('优惠码已创建','ok')}
async function mkCt(){if(!cf.value.name){tst('填写名称','er');return}await api.rq('POST','/api/admin/categories',cf.value);cf.value={name:'',sort_order:0};api.rq('GET','/api/categories').then(d=>ct.value=d);tst('已创建','ok')}
async function dlCt(id){if(!(await confirmAsync('确定删除？')))return;api.rq('DELETE','/api/categories/'+id).then(()=>{api.rq('GET','/api/categories').then(d=>ct.value=d);tst('已删除','ok')}).catch(e=>tst(e.message,'er'))}
async function saveSt(){await api.rq('POST','/api/admin/config',st.value);tst('设置已保存','ok')}
async function testEmail(){const email=prompt('请输入测试邮箱地址：');if(!email)return;try{await api.rq('POST','/api/admin/config/email/test',{email});tst('测试邮件发送成功','ok')}catch(e){tst('发送失败: '+e.message,'er')}}
async function testSms(){const phone=prompt('请输入测试手机号：');if(!phone)return;try{await api.rq('POST','/api/admin/config/sms/test',{phone});tst('测试短信发送成功','ok')}catch(e){tst('发送失败: '+e.message,'er')}}
async function saveLt(){await api.rq('POST','/api/admin/lottery',lt.value);tst('抽奖设置已保存','ok')}
async function saveEv(){await api.rq('POST','/api/admin/event',ev.value);tst('活动设置已保存','ok')}
async function savePay(){
  try{
    await api.rq('POST','/api/admin/payment',{payment:pay.value});
    api.rq('GET','/api/admin/recharges').then(d=>{rechargeRecords.value=d.records||[]}).catch(()=>{})
    tst('支付设置已保存','ok');
  }catch(e){tst(e.message,'er')}
}
function openEventProductModal(p=null){
  if(p){
    editingEventProduct.value=p.id;
    eventProductForm.value={
      name:p.name||'',description:p.description||'',price:p.price||0,original_price:p.original_price,discount_price:p.discount_price,
      start_at:p.start_at||'',end_at:p.end_at||'',image_url:p.image_url||'',imageList:p.image_url?[p.image_url]:[],sort_order:p.sort_order||0,stock:p.stock||-1,is_active:p.is_active!==false
    }
  }else{
    editingEventProduct.value=null;
    eventProductForm.value={
      name:'',description:'',price:0,original_price:null,discount_price:null,
      start_at:'',end_at:'',image_url:'',imageList:[],sort_order:0,stock:-1,is_active:true
    }
  }
  showEventProductModal.value=true;
}
function closeEventProductModal(){
  showEventProductModal.value=false;
  editingEventProduct.value=null;
}
async function saveEventProduct(){
  const d=eventProductForm.value;
  if(!d.name||d.price<=0){tst('请填写商品名称和有效价格','er');return}
  d.image_url=d.imageList[0]||'';
  try{
    if(editingEventProduct.value){
      await api.rq('PUT','/api/admin/events/products/'+editingEventProduct.value,d);
    }else{
      await api.rq('POST','/api/admin/events/products',d);
    }
    closeEventProductModal();
    await loadEventProducts();
    tst(editingEventProduct.value?'活动商品已更新':'活动商品已添加','ok');
  }catch(e){tst(e.message,'er')}
}
async function deleteEventProduct(p){
  if(!(await confirmAsync('确定要删除此活动商品吗？')))return;
  try{
    await api.rq('DELETE','/api/admin/events/products/'+p.id);
    await loadEventProducts();
    tst('活动商品已删除','ok');
  }catch(e){tst(e.message,'er')}
}
async function loadEventProducts(){
  try{
    const d=await api.rq('GET','/api/admin/events');
    if(d.products)eventProducts.value=d.products;
  }catch(e){tst('加载活动商品失败','er')}
}
function fm(t){return t?t.slice(0,19).replace('T',' '):''}
function stTxt(s){return{'pending':'待付款','paid':'已付款','shipped':'已发货','completed':'已完成','cancelled':'已取消'}[s]||s}
return{rd,msg,tb,un,ts,tst,ps,or,us,cs,ct,ks,da,kp,kt,spf,eid,pf,showProductModal,editingProduct,productForm,openProductModal,closeProductModal,saveProduct,deleteProduct,refreshingStock,stockUpdateTime,stockUpdateWatcher,getStockClass,getStockStatus,getStockText,refreshAllStocks,startStockPolling,stopStockPolling,showRestockModal,restockProduct,restockKeys,quickGenerateCount,openRestockModal,closeRestockModal,getKeyCount,generateKey,generateKeys,generateQuickKeys,generateAndAddKeys,confirmRestock,sco,scf,cpc,cf,promoCodes,coupons,showAddCoupon,newCoupon,coTab,newPromo,newRedeem,inviteRecords,invSettings,ready,open,toggle,toggleAccordion,st,lt,ev,pay,rechargeRecords,me,saveSt,testEmail,testSms,saveLt,saveEv,savePay,svPd,edPd,dlPd,sk,sp,imK,dlK,completeOrder,cancelOrder,toggleAdmin,orFilter,filteredOrders,mkCo,dlCo,mkCt,dlCt,fm,stTxt,al,eventProducts,showEventProductModal,editingEventProduct,eventProductForm,openEventProductModal,closeEventProductModal,saveEventProduct,deleteEventProduct,imageFileInput,triggerImageUpload,handleImageUpload,removeProductImage,eventImageFileInput,triggerEventImageUpload,handleEventImageUpload,removeEventImage,currentTheme,changeTheme,generatePromoCode,copyPromoCode,loadPromoCodes,loadCoupons,addCoupon,delCoupon,giveCoupon,getCouponName,createPromoCode,createRedeemCode,loadInviteSettings,loadInviteRecords,saveInvSettings,openAddProductModal,charts,maxDaily,maxMonthly,recommends,compressFiles,createRule,deleteRecommend,deleteRule,removeProductFile,toggleProductInRecommend,showConfirmModal,confirmMessage,confirmResolveFn}
}
}).mount('#app')
// 后备方案：监听到Vue挂载后隐藏加载层
(function(){
  var el=document.getElementById('app-loading');
  if(!el)return;
  var obs=new MutationObserver(function(){
    var app=document.getElementById('app');
    if(app&&!app.hasAttribute('v-cloak')){
      el.style.display='none';
      obs.disconnect();
    }
  });
  obs.observe(document.body,{attributes:true,subtree:true,attributeFilter:['v-cloak']});
  // 5秒后备
  setTimeout(function(){el.style.display='none';},5000);
  // 修复Vue泄漏的fa-image图标：把被包裹的.bk元素移出来
  setTimeout(function(){
    var leaked = document.querySelectorAll('#ct > i.fas.fa-image, #main > i.fas.fa-image, #app > i.fas.fa-image');
    for(var i=0;i<leaked.length;i++){
      var icon = leaked[i];
      var parent = icon.parentElement;
      while(icon.firstChild){
        parent.insertBefore(icon.firstChild, icon);
      }
      parent.removeChild(icon);
    }
  }, 100);
})();
