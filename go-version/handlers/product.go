package handlers

import (
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type ProductHandler struct {
	DB *gorm.DB
}

func (h *ProductHandler) Create(c *gin.Context) {
	var req struct {
		Name        string  `json:"name" binding:"required"`
		Description string  `json:"description"`
		Price       float64 `json:"price" binding:"required,gt=0"`
		CategoryID  uint    `json:"category_id"`
		ImageURL    string  `json:"image_url"`
		Type        string  `json:"type"`
		Stock       int     `json:"stock"`
		StartAt     *time.Time `json:"start_at"`
		EndAt       *time.Time `json:"end_at"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	p := models.Product{
		Name: req.Name, Description: req.Description, Price: req.Price,
		CategoryID: req.CategoryID, ImageURL: req.ImageURL,
		Type: models.ProductType(req.Type), Stock: req.Stock,
		StartAt: req.StartAt, EndAt: req.EndAt,
	}
	if p.Type == "" {
		p.Type = models.ProductNormal
	}
	if p.Stock == 0 {
		p.Stock = -1
	}
	h.DB.Create(&p)
	c.JSON(http.StatusCreated, p)
}

func (h *ProductHandler) List(c *gin.Context) {
	categoryID, _ := parseInt(c.Query("category_id"), 0)
	ptype := c.Query("type")

	var products []models.Product
	query := h.DB.Where("1 = 1")
	if categoryID > 0 {
		query = query.Where("category_id = ?", categoryID)
	}
	if ptype != "" {
		query = query.Where("type = ?", ptype)
	}
	query.Preload("Category").Order("created_at desc").Find(&products)

	var total int64
	h.DB.Model(&models.Product{}).Count(&total)

	type ProductResp struct {
		models.Product
		CardKeyCount int64 `json:"card_key_count"`
	}

	var resp []ProductResp
	for _, p := range products {
		var cnt int64
		h.DB.Model(&models.CardKey{}).Where("product_id = ? AND status = ?", p.ID, models.CardKeyAvailable).Count(&cnt)
		if p.Stock > 0 {
			cnt = int64(p.Stock)
		}
		resp = append(resp, ProductResp{Product: p, CardKeyCount: cnt})
	}

	c.JSON(http.StatusOK, gin.H{"products": resp, "total": total})
}

func (h *ProductHandler) Get(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	var p models.Product
	if err := h.DB.Preload("Category").First(&p, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "商品不存在"})
		return
	}

	var cardKeyCount int64
	h.DB.Model(&models.CardKey{}).Where("product_id = ? AND status = ?", p.ID, models.CardKeyAvailable).Count(&cardKeyCount)

	// Check if timed product is available
	now := time.Now()
	available := true
	msg := ""
	if p.Type == models.ProductTimed {
		if p.StartAt != nil && now.Before(*p.StartAt) {
			available = false
			msg = "抢购尚未开始"
		}
		if p.EndAt != nil && now.After(*p.EndAt) {
			available = false
			msg = "抢购已结束"
		}
	}

	// Get blind box pool
	var pool []models.BlindBoxPool
	if p.Type == models.ProductBlindBox {
		h.DB.Where("product_id = ?", p.ID).Preload("Prize").Find(&pool)
	}

	c.JSON(http.StatusOK, gin.H{
		"product":       p,
		"card_key_count": cardKeyCount,
		"available":     available,
		"msg":           msg,
		"pool":          pool,
	})
}

func (h *ProductHandler) Update(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	var p models.Product
	if err := h.DB.First(&p, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "商品不存在"})
		return
	}
	var req struct {
		Name        string     `json:"name" binding:"required"`
		Description string     `json:"description"`
		Price       float64    `json:"price" binding:"required,gt=0"`
		CategoryID  uint       `json:"category_id"`
		ImageURL    string     `json:"image_url"`
		Type        string     `json:"type"`
		Stock       int        `json:"stock"`
		StartAt     *time.Time `json:"start_at"`
		EndAt       *time.Time `json:"end_at"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	p.Name = req.Name
	p.Description = req.Description
	p.Price = req.Price
	p.CategoryID = req.CategoryID
	p.ImageURL = req.ImageURL
	p.Type = models.ProductType(req.Type)
	p.Stock = req.Stock
	p.StartAt = req.StartAt
	p.EndAt = req.EndAt
	h.DB.Save(&p)
	c.JSON(http.StatusOK, p)
}

func (h *ProductHandler) Delete(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	h.DB.Delete(&models.Product{}, id)
	h.DB.Where("product_id = ?", id).Delete(&models.CardKey{})
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}

func (h *ProductHandler) UpdateBlindBoxPool(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	var req struct {
		Entries []struct {
			PrizeID     uint    `json:"prize_id" binding:"required"`
			Probability float64 `json:"probability" binding:"required"`
		} `json:"entries" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.DB.Where("product_id = ?", uint(id)).Delete(&models.BlindBoxPool{})
	for _, e := range req.Entries {
		h.DB.Create(&models.BlindBoxPool{
			ProductID:   uint(id),
			PrizeID:     e.PrizeID,
			Probability: e.Probability,
		})
	}
	c.JSON(http.StatusOK, gin.H{"message": "奖池已更新"})
}

// Helper
func parseInt(s string, defaultVal int) (int, error) {
	if s == "" {
		return defaultVal, nil
	}
	var n int
	_, err := fmt.Sscanf(s, "%d", &n)
	if err != nil {
		return defaultVal, err
	}
	return n, nil
}
