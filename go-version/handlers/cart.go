package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type CartHandler struct {
	DB *gorm.DB
}

type AddCartItemReq struct {
	ProductID uint `json:"product_id" binding:"required"`
	Quantity  int  `json:"quantity" binding:"required,gt=0"`
}

func (h *CartHandler) GetCart(c *gin.Context) {
	userID := c.GetUint("user_id")
	var cart models.Cart
	if err := h.DB.Where("user_id = ?", userID).Preload("Items.Product").First(&cart).Error; err != nil {
		c.JSON(http.StatusOK, gin.H{"items": []interface{}{}})
		return
	}
	c.JSON(http.StatusOK, cart)
}

func (h *CartHandler) AddItem(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req AddCartItemReq
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var product models.Product
	if err := h.DB.First(&product, req.ProductID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "product not found"})
		return
	}

	cart := models.Cart{}
	h.DB.Where("user_id = ?", userID).FirstOrCreate(&cart, models.Cart{UserID: userID})

	var existing models.CartItem
	if err := h.DB.Where("cart_id = ? AND product_id = ?", cart.ID, req.ProductID).First(&existing).Error; err == nil {
		existing.Quantity += req.Quantity
		h.DB.Save(&existing)
	} else {
		item := models.CartItem{
			CartID:    cart.ID,
			ProductID: req.ProductID,
			Quantity:  req.Quantity,
		}
		h.DB.Create(&item)
	}

	h.DB.Preload("Items.Product").First(&cart, cart.ID)
	c.JSON(http.StatusOK, cart)
}

func (h *CartHandler) UpdateItem(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req AddCartItemReq
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var cart models.Cart
	if err := h.DB.Where("user_id = ?", userID).First(&cart).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "cart not found"})
		return
	}

	var item models.CartItem
	if err := h.DB.Where("cart_id = ? AND product_id = ?", cart.ID, req.ProductID).First(&item).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "item not found in cart"})
		return
	}

	if req.Quantity <= 0 {
		h.DB.Delete(&item)
	} else {
		item.Quantity = req.Quantity
		h.DB.Save(&item)
	}

	h.DB.Preload("Items.Product").First(&cart, cart.ID)
	c.JSON(http.StatusOK, cart)
}

func (h *CartHandler) ClearCart(c *gin.Context) {
	userID := c.GetUint("user_id")
	h.DB.Where("user_id = ?", userID).Delete(&models.Cart{})
	c.JSON(http.StatusOK, gin.H{"message": "cart cleared"})
}
