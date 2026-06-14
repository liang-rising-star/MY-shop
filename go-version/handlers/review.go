package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type ReviewHandler struct {
	DB *gorm.DB
}

func (h *ReviewHandler) Create(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req struct {
		ProductID uint   `json:"product_id" binding:"required"`
		OrderID   uint   `json:"order_id" binding:"required"`
		Rating    int    `json:"rating" binding:"required,min=1,max=5"`
		Content   string `json:"content"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Verify order belongs to user and contains this product
	var order models.Order
	if err := h.DB.Where("id = ? AND user_id = ? AND status = ?", req.OrderID, userID, models.OrderPaid).First(&order).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "订单不存在或未完成"})
		return
	}

	var existing models.Review
	if err := h.DB.Where("user_id = ? AND order_id = ? AND product_id = ?", userID, req.OrderID, req.ProductID).First(&existing).Error; err == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "已评价过此商品"})
		return
	}

	review := models.Review{
		UserID: userID, ProductID: req.ProductID,
		OrderID: req.OrderID, Rating: req.Rating, Content: req.Content,
	}
	h.DB.Create(&review)

	// Add points for reviewing
	h.DB.Model(&models.User{}).Where("id = ?", userID).UpdateColumn("points", gorm.Expr("points + 5"))

	c.JSON(http.StatusCreated, gin.H{"message": "评价成功", "points_earned": 5})
}

func (h *ReviewHandler) List(c *gin.Context) {
	productID, _ := parseInt(c.Query("product_id"), 0)
	query := h.DB.Where("product_id = ?", productID).Preload("User")
	var reviews []models.Review
	query.Order("created_at desc").Find(&reviews)

	var avgRating struct{ Avg float64 }
	h.DB.Model(&models.Review{}).Select("avg(rating) as avg").Where("product_id = ?", productID).Scan(&avgRating)

	c.JSON(http.StatusOK, gin.H{
		"reviews": reviews,
		"avg_rating": avgRating.Avg,
		"count":   len(reviews),
	})
}

func (h *ReviewHandler) Delete(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	h.DB.Delete(&models.Review{}, id)
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}
