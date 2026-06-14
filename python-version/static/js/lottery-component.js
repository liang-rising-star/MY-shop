// 抽奖转盘组件
Vue.component('lottery-wheel', {
    props: {
        wheelData: {
            type: Object,
            required: true
        },
        userTickets: {
            type: Number,
            default: 0
        },
        userPoints: {
            type: Number,
            default: 0
        }
    },
    data() {
        return {
            isSpinning: false,
            currentRotation: 0,
            selectedPrize: null,
            showResult: false,
            freeCount: 0,
            maxFree: 0
        }
    },
    computed: {
        canDraw() {
            if (this.isSpinning) return false;
            
            // 检查免费次数
            if (this.maxFree > 0 && this.freeCount < this.maxFree) {
                return true;
            }
            
            // 检查抽奖券
            if (this.userTickets > 0) {
                return true;
            }
            
            // 检查积分
            if (this.wheelData.price_type === 'points' && this.userPoints >= this.wheelData.price_value) {
                return true;
            }
            
            return false;
        },
        drawCost() {
            if (this.maxFree > 0 && this.freeCount < this.maxFree) {
                return '免费';
            }
            
            if (this.userTickets > 0) {
                return '1张券';
            }
            
            if (this.wheelData.price_type === 'points') {
                return `${this.wheelData.price_value}积分`;
            }
            
            return '未知';
        }
    },
    methods: {
        async draw() {
            if (!this.canDraw || this.isSpinning) return;
            
            try {
                this.isSpinning = true;
                this.showResult = false;
                
                const res = await axios.post('/api/lottery/draw', {
                    wheel_id: this.wheelData.id,
                    type: 'auto'
                });
                
                if (res.data.success) {
                    // 计算旋转角度
                    const prizeIndex = this.getPrizeIndex(res.data.prize.id);
                    const angle = 360 - (prizeIndex * (360 / this.wheelData.prizes.length)) - (360 / this.wheelData.prizes.length / 2);
                    const extraSpins = Math.floor(Math.random() * 3 + 3) * 360;
                    
                    this.currentRotation += extraSpins + angle;
                    
                    // 旋转动画
                    this.$refs.wheelBg.style.transform = `rotate(${this.currentRotation}deg)`;
                    
                    // 等待动画完成
                    await new Promise(resolve => setTimeout(resolve, 4000));
                    
                    this.selectedPrize = res.data.prize;
                    this.showResult = true;
                    
                    // 更新用户资源
                    if (res.data.cost_type === 'free') {
                        this.freeCount++;
                    } else if (res.data.cost_type === 'ticket') {
                        this.$emit('update:tickets', this.userTickets - 1);
                    } else if (res.data.cost_type === 'points') {
                        this.$emit('update:points', this.userPoints - res.data.cost_value);
                    }
                    
                    // 触发事件
                    this.$emit('won', res.data);
                }
            } catch (err) {
                console.error('抽奖失败:', err);
                alert(err.response?.data?.detail || '抽奖失败，请重试');
                this.isSpinning = false;
            }
        },
        getPrizeIndex(prizeId) {
            const index = this.wheelData.prizes.findIndex(p => p.id === prizeId);
            return index >= 0 ? index : 0;
        },
        closeResult() {
            this.showResult = false;
            this.isSpinning = false;
            this.selectedPrize = null;
        },
        getPrizeColor(index) {
            const colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'
            ];
            return colors[index % colors.length];
        }
    },
    template: `
        <div class="lottery-container">
            <div class="lottery-wheel" :class="{ spinning: isSpinning }">
                <div class="lottery-wheel-light"></div>
                <div class="lottery-wheel-bg" ref="wheelBg" :style="{ transform: 'rotate(' + currentRotation + 'deg)' }">
                    <div v-for="(prize, index) in wheelData.prizes" 
                         :key="prize.id"
                         class="prize-segment"
                         :style="{
                             position: 'absolute',
                             width: '50%',
                             height: '50%',
                             left: 0,
                             top: 0,
                             transformOrigin: '100% 100%',
                             transform: 'rotate(' + (index * 36) + 'deg)',
                             clipPath: 'polygon(0 0, 100% 0, 100% 100%)',
                             background: getPrizeColor(index)
                         }">
                        <div :style="{
                            position: 'absolute',
                            left: 0,
                            bottom: 0,
                            width: '200%',
                            height: '200%',
                            transform: 'rotate(-' + (index * 36) + 'deg)',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            paddingTop: '30%'
                        }">
                            <img v-if="prize.image_url" :src="prize.image_url" style="width: 40px; height: 40px; border-radius: 50%;">
                            <span style="font-size: 12px; color: #fff; text-align: center; margin-top: 5px;">
                                {{ prize.name }}
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="lottery-center-bg"></div>
                
                <button class="lottery-btn" 
                        @click="draw" 
                        :disabled="!canDraw || isSpinning">
                    <span>抽奖</span>
                    <span class="price">{{ drawCost }}</span>
                </button>
            </div>
            
            <!-- 奖品列表 -->
            <div class="prize-list">
                <div v-for="prize in wheelData.prizes" :key="prize.id" class="prize-item">
                    <img v-if="prize.image_url" :src="prize.image_url" :alt="prize.name">
                    <div v-else style="width: 60px; height: 60px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-gift" style="font-size: 24px; color: #999;"></i>
                    </div>
                    <div class="name">{{ prize.name }}</div>
                </div>
            </div>
            
            <!-- 抽奖结果弹窗 -->
            <div v-if="showResult" class="lottery-modal" @click.self="closeResult">
                <div class="lottery-result">
                    <h3>{{ selectedPrize?.is_winner ? '恭喜您!' : '感谢参与' }}</h3>
                    <div class="prize-name">{{ selectedPrize?.name }}</div>
                    <div class="prize-desc">{{ selectedPrize?.description }}</div>
                    <button @click="closeResult">确定</button>
                </div>
            </div>
        </div>
    `
});
