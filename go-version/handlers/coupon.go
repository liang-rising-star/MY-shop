package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type CouponHandler struct {
	DB *gorm.DB
}

func (h *CouponHandler) Create(c *gin.Context) {
	var req struct {
		Code      string    `json:"code" binding:"required"`
		Type      string    `json:"type" binding:"required"`
		Value     float64   `json:"value" binding:"required"`
		MinAmount float64   `json:"min_amount"`
		MaxUses   int       `json:"max_uses"`
		ExpiresAt time.Time `json:"expires_at" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	cp := models.Coupon{
		Code: req.Code, Type: models.CouponType(req.Type),
		Value: req.Value, MinAmount: req.MinAmount,
		MaxUses: req.MaxUses, ExpiresAt: req.ExpiresAt,
	}
	if err := h.DB.Create(&cp).Error; err != nil {
		c.JSON(http.StatusConflict, gin.H{"error": "优惠码已存在"})
		return
	}
	c.JSON(http.StatusCreated, cp)
}

func (h *CouponHandler) List(c *gin.Context) {
	var coupons []models.Coupon
	h.DB.Order("created_at desc").Find(&coupons)
	c.JSON(http.StatusOK, coupons)
}

func (h *CouponHandler) Delete(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	h.DB.Delete(&models.Coupon{}, id)
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}

func (h *CouponHandler) Validate(c *gin.Context) {
	var req struct {
		Code   string  `json:"code" binding:"required"`
		Amount float64 `json:"amount" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var cp models.Coupon
	if err := h.DB.Where("code = ?", req.Code).First(&cp).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "优惠码不存在"})
		return
	}

	if time.Now().After(cp.ExpiresAt) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "优惠码已过期"})
		return
	}
	if cp.MaxUses > 0 && cp.UsedCount >= cp.MaxUses {
		c.JSON(http.StatusBadRequest, gin.H{"error": "优惠码已被用完"})
		return
	}
	if req.Amount < cp.MinAmount {
		c.JSON(http.StatusBadRequest, gin.H{"error": "未达到最低使用金额"})
		return
	}

	var discount float64
	if cp.Type == models.CouponPercent {
		discount = req.Amount * cp.Value / 100
	} else {
		discount = cp.Value
	}
	if discount > req.Amount {
		discount = req.Amount
	}

	c.JSON(http.StatusOK, gin.H{
		"valid":    true,
		"coupon":   cp,
		"discount": discount,
	})
}

func (h *CouponHandler) Claim(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req struct {
		Code string `json:"code" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var cp models.Coupon
	if err := h.DB.Where("code = ?", req.Code).First(&cp).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "优惠码不存在"})
		return
	}

	var existing models.UserCoupon
	if err := h.DB.Where("user_id = ? AND coupon_id = ?", userID, cp.ID).First(&existing).Error; err == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "已领取过此优惠券"})
		return
	}

	h.DB.Create(&models.UserCoupon{UserID: userID, CouponID: cp.ID})
	c.JSON(http.StatusOK, gin.H{"message": "领取成功", "coupon": cp})
}

func (h *CouponHandler) MyCoupons(c *gin.Context) {
	userID := c.GetUint("user_id")
	var ucs []models.UserCoupon
	h.DB.Where("user_id = ? AND used_at IS NULL", userID).Preload("Coupon").Find(&ucs)
	c.JSON(http.StatusOK, ucs)
}
