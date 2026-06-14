package handlers

import (
	"fmt"
	"math/rand"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type OrderHandler struct {
	DB *gorm.DB
}

func (h *OrderHandler) Checkout(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req struct {
		ProductID uint   `json:"product_id" binding:"required"`
		Quantity  int    `json:"quantity"`
		CouponCode string `json:"coupon_code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Quantity <= 0 {
		req.Quantity = 1
	}

	var product models.Product
	if err := h.DB.First(&product, req.ProductID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "商品不存在"})
		return
	}

	// Check availability
	now := time.Now()
	if product.Type == models.ProductTimed {
		if product.StartAt != nil && now.Before(*product.StartAt) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "抢购尚未开始"})
			return
		}
		if product.EndAt != nil && now.After(*product.EndAt) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "抢购已结束"})
			return
		}
	}

	// Check stock
	if product.Type == models.ProductBlindBox {
		// Check if pool is configured
		var poolCount int64
		h.DB.Model(&models.BlindBoxPool{}).Where("product_id = ?", product.ID).Count(&poolCount)
		if poolCount == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "盲盒奖池未配置"})
			return
		}
	} else {
		var available int64
		h.DB.Model(&models.CardKey{}).Where("product_id = ? AND status = ?", product.ID, models.CardKeyAvailable).Count(&available)
		if int(available) < req.Quantity {
			c.JSON(http.StatusBadRequest, gin.H{"error": "库存不足"})
			return
		}
	}

	totalPrice := product.Price * float64(req.Quantity)
	var discount float64
	var couponID *uint

	// Apply coupon
	if req.CouponCode != "" {
		var cp models.Coupon
		if err := h.DB.Where("code = ?", req.CouponCode).First(&cp).Error; err == nil {
			if now.Before(cp.ExpiresAt) && (cp.MaxUses <= 0 || cp.UsedCount < cp.MaxUses) && totalPrice >= cp.MinAmount {
				if cp.Type == models.CouponPercent {
					discount = totalPrice * cp.Value / 100
				} else {
					discount = cp.Value
				}
				if discount > totalPrice {
					discount = totalPrice
				}
				cp.UsedCount++
				h.DB.Save(&cp)
				couponID = &cp.ID
			}
		}
	}

	orderNo := fmt.Sprintf("%s%d", time.Now().Format("20060102150405"), userID)

	tx := h.DB.Begin()

	order := models.Order{
		OrderNo:    orderNo,
		UserID:     userID,
		TotalPrice: totalPrice,
		Discount:   discount,
		FinalPrice: totalPrice - discount,
		CouponID:   couponID,
		Status:     models.OrderPaid,
	}
	if err := tx.Create(&order).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建订单失败"})
		return
	}

	// Create order item
	item := models.OrderItem{
		OrderID:   order.ID,
		ProductID: product.ID,
		Price:     product.Price,
		Quantity:  req.Quantity,
	}
	tx.Create(&item)

	// Auto delivery: assign card keys
	var deliveredKeys []models.CardKey
	if product.Type == models.ProductBlindBox {
		// Blind box: randomly select prize from pool
		for i := 0; i < req.Quantity; i++ {
			prize := h.pickBlindBoxPrize(tx, product.ID)
			if prize == nil {
				continue
			}
			// Get a available key from prize product
			var key models.CardKey
			if err := tx.Where("product_id = ? AND status = ?", prize.ID, models.CardKeyAvailable).First(&key).Error; err != nil {
				continue
			}
			key.Status = models.CardKeySold
			key.OrderID = &order.ID
			now := time.Now()
			key.SoldAt = &now
			tx.Save(&key)
			deliveredKeys = append(deliveredKeys, key)
			tx.Model(&models.Product{}).Where("id = ?", prize.ID).UpdateColumn("total_sold", gorm.Expr("total_sold + 1"))
		}
	} else {
		var keys []models.CardKey
		tx.Where("product_id = ? AND status = ?", product.ID, models.CardKeyAvailable).Limit(req.Quantity).Find(&keys)
		for i := range keys {
			keys[i].Status = models.CardKeySold
			keys[i].OrderID = &order.ID
			now := time.Now()
			keys[i].SoldAt = &now
			tx.Save(&keys[i])
			deliveredKeys = append(deliveredKeys, keys[i])
		}
	}

	tx.Model(&models.Product{}).Where("id = ?", product.ID).UpdateColumn("total_sold", gorm.Expr("total_sold + ?", req.Quantity))

	// Add points: 1 point per yuan
	points := int(totalPrice)
	tx.Model(&models.User{}).Where("id = ?", userID).UpdateColumn("points", gorm.Expr("points + ?", points))

	tx.Commit()

	// Reload order with associations
	h.DB.Preload("Items.Product").Preload("CardKeys").First(&order, order.ID)
	c.JSON(http.StatusCreated, gin.H{
		"order":        order,
		"card_keys":    deliveredKeys,
		"points_earned": points,
		"message":      "购买成功！卡密已自动发放",
	})
}

func (h *OrderHandler) pickBlindBoxPrize(tx *gorm.DB, productID uint) *models.Product {
	var entries []models.BlindBoxPool
	tx.Where("product_id = ?", productID).Find(&entries)
	if len(entries) == 0 {
		return nil
	}

	r := rand.Float64() * 100
	var cumulative float64
	for _, e := range entries {
		cumulative += e.Probability
		if r <= cumulative {
			var prize models.Product
			if err := tx.First(&prize, e.PrizeID).Error; err != nil {
				return nil
			}
			// Check if prize has stock
			var cnt int64
			tx.Model(&models.CardKey{}).Where("product_id = ? AND status = ?", prize.ID, models.CardKeyAvailable).Count(&cnt)
			if cnt > 0 || prize.Stock == -1 {
				return &prize
			}
		}
	}
	// Fallback: return last with stock
	for _, e := range entries {
		var prize models.Product
		tx.First(&prize, e.PrizeID)
		var cnt int64
		tx.Model(&models.CardKey{}).Where("product_id = ? AND status = ?", prize.ID, models.CardKeyAvailable).Count(&cnt)
		if cnt > 0 || prize.Stock == -1 {
			return &prize
		}
	}
	return nil
}

func (h *OrderHandler) List(c *gin.Context) {
	userID := c.GetUint("user_id")
	var orders []models.Order
	h.DB.Where("user_id = ?", userID).Preload("Items.Product").Preload("CardKeys").
		Order("created_at desc").Find(&orders)
	c.JSON(http.StatusOK, orders)
}

func (h *OrderHandler) Get(c *gin.Context) {
	userID := c.GetUint("user_id")
	id, _ := parseInt(c.Param("id"), 0)

	var order models.Order
	if err := h.DB.Where("id = ? AND user_id = ?", id, userID).
		Preload("Items.Product").Preload("CardKeys").First(&order).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "订单不存在"})
		return
	}
	c.JSON(http.StatusOK, order)
}

func (h *OrderHandler) ListAll(c *gin.Context) {
	var orders []models.Order
	h.DB.Preload("Items.Product").Preload("CardKeys").Order("created_at desc").Find(&orders)
	c.JSON(http.StatusOK, orders)
}
