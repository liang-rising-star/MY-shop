// 抽奖管理模块
const lotteryManagement = {
    wheels: [],
    prizes: [],
    currentWheel: null,
    editingWheel: null,
    editingPrize: null,
    
    showToast(msg, type='error') {
      const el = document.createElement('div');
      el.style.cssText = `position:fixed;top:80px;right:20px;z-index:99999;padding:12px 24px;border-radius:8px;font-size:0.9rem;min-width:200px;backdrop-filter:blur(10px);border:1px solid ${type==='error'?'#ff4444':'var(--primary)'};color:${type==='error'?'#ff4444':'var(--primary)'};background:${type==='error'?'rgba(255,0,0,0.1)':'rgba(0,240,255,0.1)'};animation:slide-in 0.3s ease`;
      el.textContent = msg;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 3000);
    },
    
    confirmAsync(msg) {
      return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:99999';
        overlay.innerHTML = `<div style="background:var(--bg2);border:1px solid var(--primary);border-radius:12px;width:400px;overflow:hidden;box-shadow:0 0 40px rgba(0,0,0,0.5)"><div style="padding:1rem 1.5rem;border-bottom:1px solid var(--border)"><h3 style="font-size:1rem;color:var(--primary);margin:0">确认操作</h3></div><div style="padding:1.5rem;font-size:0.95rem;color:var(--text)"><p style="margin:0;line-height:1.6">${msg}</p></div><div style="display:flex;justify-content:flex-end;gap:0.8rem;padding:1rem 1.5rem;border-top:1px solid var(--border)"><button onclick="this.closest('.confirm-overlay')?.remove()" style="padding:0.4rem 0.8rem;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:6px;cursor:pointer">取消</button><button id="confirm-ok-btn" style="padding:0.4rem 0.8rem;background:var(--primary);border:none;color:#fff;border-radius:6px;cursor:pointer">确定</button></div></div>`;
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:99999';
        document.body.appendChild(overlay);
        overlay.querySelector('#confirm-ok-btn').onclick = () => { overlay.remove(); resolve(true); };
        overlay.querySelectorAll('button')[0].onclick = () => { overlay.remove(); resolve(false); };
      });
    },
    
    // 加载所有转盘
    async loadWheels() {
        try {
            const res = await axios.get('/api/lottery/wheels/admin');
            this.wheels = res.data.wheels || [];
        } catch (err) {
            console.error('加载转盘失败:', err);
        }
    },
    
    // 创建转盘
    async createWheel(data) {
        try {
            const res = await axios.post('/api/admin/lottery/wheels', data);
            if (res.data.success) {
                await this.loadWheels();
                return res.data.id;
            }
        } catch (err) {
            console.error('创建转盘失败:', err);
            throw err;
        }
    },
    
    // 更新转盘
    async updateWheel(wheelId, data) {
        try {
            await axios.put(`/api/admin/lottery/wheels/${wheelId}`, data);
            await this.loadWheels();
        } catch (err) {
            console.error('更新转盘失败:', err);
            throw err;
        }
    },
    
    // 删除转盘
    async deleteWheel(wheelId) {
        if (!(await this.confirmAsync('确定要删除这个转盘吗？所有关联的奖品也会被删除！'))) return;
        
        try {
            await axios.delete(`/api/admin/lottery/wheels/${wheelId}`);
            await this.loadWheels();
        } catch (err) {
            console.error('删除转盘失败:', err);
            throw err;
        }
    },
    
    // 添加奖品
    async createPrize(data) {
        try {
            const res = await axios.post('/api/admin/lottery/prizes', data);
            if (res.data.success) {
                await this.loadWheels();
                return res.data.id;
            }
        } catch (err) {
            console.error('添加奖品失败:', err);
            throw err;
        }
    },
    
    // 更新奖品
    async updatePrize(prizeId, data) {
        try {
            await axios.put(`/api/admin/lottery/prizes/${prizeId}`, data);
            await this.loadWheels();
        } catch (err) {
            console.error('更新奖品失败:', err);
            throw err;
        }
    },
    
    // 渲染转盘列表
    renderWheelList() {
        const container = document.getElementById('lottery-wheels-list');
        if (!container) return;
        
        if (this.wheels.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无转盘，点击上方按钮创建</div>';
            return;
        }
        
        container.innerHTML = this.wheels.map(wheel => `
            <div class="wheel-card" data-wheel-id="${wheel.id}">
                <div class="wheel-header">
                    <h3>${wheel.name}</h3>
                    <div class="wheel-actions">
                        <button class="btn btn-s btn-p" onclick="lotteryManagement.editWheel(${wheel.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-s btn-a" onclick="lotteryManagement.deleteWheel(${wheel.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="wheel-info">
                    <p>${wheel.description || '无描述'}</p>
                    <div class="wheel-meta">
                        <span>价格: ${wheel.price_value}${wheel.price_type === 'points' ? '积分' : '券'}</span>
                        <span>每日免费: ${wheel.free_daily}次</span>
                        <span>状态: ${wheel.is_active ? '启用' : '禁用'}</span>
                    </div>
                </div>
                <div class="prizes-section">
                    <h4>奖品列表 (${wheel.prizes?.length || 0}/10)</h4>
                    <div class="prizes-grid">
                        ${(wheel.prizes || []).map(prize => `
                            <div class="prize-item" data-prize-id="${prize.id}">
                                <div class="prize-info">
                                    <strong>${prize.name}</strong>
                                    <span class="prize-type">${this.getPrizeTypeName(prize.prize_type)}</span>
                                    <span class="prize-prob">${prize.probability}%</span>
                                    ${prize.is_default ? '<span class="badge">保底</span>' : ''}
                                </div>
                                <div class="prize-actions">
                                    <button class="btn btn-xs btn-p" onclick="lotteryManagement.editPrize(${prize.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-xs btn-a" onclick="lotteryManagement.deletePrize(${prize.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn btn-sm btn-p" onclick="lotteryManagement.showAddPrize(${wheel.id})">
                        <i class="fas fa-plus"></i> 添加奖品
                    </button>
                </div>
            </div>
        `).join('');
    },
    
    // 显示创建/编辑转盘弹窗
    showWheelModal(wheel = null) {
        this.editingWheel = wheel;
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'wheel-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${wheel ? '编辑转盘' : '创建转盘'}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="wheel-form">
                        <div class="form-group">
                            <label>转盘名称 *</label>
                            <input type="text" name="name" value="${wheel?.name || ''}" required>
                        </div>
                        <div class="form-group">
                            <label>描述</label>
                            <textarea name="description">${wheel?.description || ''}</textarea>
                        </div>
                        <div class="form-group">
                            <label>价格类型</label>
                            <select name="price_type">
                                <option value="points" ${wheel?.price_type === 'points' ? 'selected' : ''}>积分</option>
                                <option value="ticket" ${wheel?.price_type === 'ticket' ? 'selected' : ''}>抽奖券</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>价格</label>
                            <input type="number" name="price_value" value="${wheel?.price_value || 10}" min="1">
                        </div>
                        <div class="form-group">
                            <label>每日免费次数</label>
                            <input type="number" name="free_daily" value="${wheel?.free_daily || 0}" min="0">
                        </div>
                        <div class="form-group">
                            <label>最低积分要求</label>
                            <input type="number" name="min_points" value="${wheel?.min_points || 0}" min="0">
                        </div>
                        <div class="form-group">
                            <label>每日最多抽奖次数</label>
                            <input type="number" name="max_daily" value="${wheel?.max_daily || 0}" min="0" placeholder="0表示不限制">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" name="is_active" ${wheel?.is_active !== false ? 'checked' : ''}>
                                启用
                            </label>
                        </div>
                        <div class="form-group">
                            <label>排序</label>
                            <input type="number" name="sort_order" value="${wheel?.sort_order || 0}">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-p" onclick="lotteryManagement.saveWheel()">
                        ${wheel ? '保存' : '创建'}
                    </button>
                    <button class="btn btn-s" onclick="document.getElementById('wheel-modal').remove()">
                        取消
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    },
    
    // 保存转盘
    async saveWheel() {
        const form = document.getElementById('wheel-form');
        const formData = new FormData(form);
        
        const data = {
            name: formData.get('name'),
            description: formData.get('description'),
            price_type: formData.get('price_type'),
            price_value: parseInt(formData.get('price_value')),
            free_daily: parseInt(formData.get('free_daily')),
            min_points: parseInt(formData.get('min_points')),
            max_daily: parseInt(formData.get('max_daily')),
            is_active: form.querySelector('[name="is_active"]').checked,
            sort_order: parseInt(formData.get('sort_order'))
        };
        
        try {
            if (this.editingWheel) {
                await this.updateWheel(this.editingWheel.id, data);
            } else {
                await this.createWheel(data);
            }
            
            document.getElementById('wheel-modal')?.remove();
            this.renderWheelList();
        } catch (err) {
            this.showToast('保存失败: ' + (err.response?.data?.detail || err.message));
        }
    },
    
    // 编辑转盘
    editWheel(wheelId) {
        const wheel = this.wheels.find(w => w.id === wheelId);
        if (wheel) {
            this.showWheelModal(wheel);
        }
    },
    
    // 显示添加奖品弹窗
    showAddPrize(wheelId) {
        this.currentWheel = wheelId;
        this.editingPrize = null;
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'prize-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>添加奖品</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="prize-form">
                        <div class="form-group">
                            <label>奖品名称 *</label>
                            <input type="text" name="name" required>
                        </div>
                        <div class="form-group">
                            <label>奖品类型 *</label>
                            <select name="prize_type" required>
                                <option value="points">积分</option>
                                <option value="coupon">优惠券</option>
                                <option value="ticket">抽奖券</option>
                                <option value="product">商品</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>奖品值</label>
                            <input type="text" name="prize_value" placeholder="积分数量/优惠券ID/商品ID">
                            <small>积分: 输入积分数; 优惠券: 输入优惠券ID; 抽奖券: 输入数量; 商品: {"product_id":1,"quantity":1}</small>
                        </div>
                        <div class="form-group">
                            <label>中奖概率 (%)</label>
                            <input type="number" name="probability" value="0" min="0" max="100" step="0.01">
                        </div>
                        <div class="form-group">
                            <label>库存 (-1为无限)</label>
                            <input type="number" name="stock" value="-1">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" name="is_default">
                                保底奖品（概率为0时触发）
                            </label>
                        </div>
                        <div class="form-group">
                            <label>排序</label>
                            <input type="number" name="sort_order" value="0">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-p" onclick="lotteryManagement.savePrize()">添加</button>
                    <button class="btn btn-s" onclick="document.getElementById('prize-modal').remove()">
                        取消
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    },
    
    // 保存奖品
    async savePrize() {
        const form = document.getElementById('prize-form');
        const formData = new FormData(form);
        
        const data = {
            wheel_id: this.currentWheel,
            name: formData.get('name'),
            prize_type: formData.get('prize_type'),
            prize_value: formData.get('prize_value'),
            probability: parseFloat(formData.get('probability')),
            stock: parseInt(formData.get('stock')),
            is_default: form.querySelector('[name="is_default"]').checked,
            sort_order: parseInt(formData.get('sort_order'))
        };
        
        try {
            await this.createPrize(data);
            document.getElementById('prize-modal')?.remove();
            await this.loadWheels();
            this.renderWheelList();
        } catch (err) {
            this.showToast('添加失败: ' + (err.response?.data?.detail || err.message));
        }
    },
    
    // 编辑奖品
    editPrize(prizeId) {
        // 找到奖品
        for (const wheel of this.wheels) {
            const prize = wheel.prizes?.find(p => p.id === prizeId);
            if (prize) {
                this.currentWheel = wheel.id;
                this.editingPrize = prize;
                
                const modal = document.createElement('div');
                modal.className = 'modal';
                modal.id = 'prize-modal';
                modal.innerHTML = `
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3>编辑奖品</h3>
                            <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                        </div>
                        <div class="modal-body">
                            <form id="prize-form">
                                <div class="form-group">
                                    <label>奖品名称 *</label>
                                    <input type="text" name="name" value="${prize.name}" required>
                                </div>
                                <div class="form-group">
                                    <label>奖品类型 *</label>
                                    <select name="prize_type" required>
                                        <option value="points" ${prize.prize_type === 'points' ? 'selected' : ''}>积分</option>
                                        <option value="coupon" ${prize.prize_type === 'coupon' ? 'selected' : ''}>优惠券</option>
                                        <option value="ticket" ${prize.prize_type === 'ticket' ? 'selected' : ''}>抽奖券</option>
                                        <option value="product" ${prize.prize_type === 'product' ? 'selected' : ''}>商品</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>奖品值</label>
                                    <input type="text" name="prize_value" value="${prize.prize_value}">
                                </div>
                                <div class="form-group">
                                    <label>中奖概率 (%)</label>
                                    <input type="number" name="probability" value="${prize.probability}" min="0" max="100" step="0.01">
                                </div>
                                <div class="form-group">
                                    <label>库存 (-1为无限)</label>
                                    <input type="number" name="stock" value="${prize.stock}">
                                </div>
                                <div class="form-group">
                                    <label>
                                        <input type="checkbox" name="is_default" ${prize.is_default ? 'checked' : ''}>
                                        保底奖品
                                    </label>
                                </div>
                                <div class="form-group">
                                    <label>排序</label>
                                    <input type="number" name="sort_order" value="${prize.sort_order}">
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-p" onclick="lotteryManagement.updatePrizeData()">保存</button>
                            <button class="btn btn-s" onclick="document.getElementById('prize-modal').remove()">
                                取消
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
                return;
            }
        }
    },
    
    // 更新奖品数据
    async updatePrizeData() {
        const form = document.getElementById('prize-form');
        const formData = new FormData(form);
        
        const data = {
            name: formData.get('name'),
            prize_type: formData.get('prize_type'),
            prize_value: formData.get('prize_value'),
            probability: parseFloat(formData.get('probability')),
            stock: parseInt(formData.get('stock')),
            is_default: form.querySelector('[name="is_default"]').checked,
            sort_order: parseInt(formData.get('sort_order'))
        };
        
        try {
            await this.updatePrize(this.editingPrize.id, data);
            document.getElementById('prize-modal')?.remove();
            await this.loadWheels();
            this.renderWheelList();
        } catch (err) {
            this.showToast('保存失败: ' + (err.response?.data?.detail || err.message));
        }
    },
    
    // 获取奖品类型名称
    getPrizeTypeName(type) {
        const names = {
            'points': '积分',
            'coupon': '优惠券',
            'ticket': '抽奖券',
            'product': '商品'
        };
        return names[type] || type;
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', async () => {
    if (document.getElementById('lottery-wheels-list')) {
        await lotteryManagement.loadWheels();
        lotteryManagement.renderWheelList();
    }
});
